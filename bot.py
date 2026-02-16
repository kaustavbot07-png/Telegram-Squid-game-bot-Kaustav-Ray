# bot.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import random
import asyncio
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
import threading
from functools import wraps
import time
from aiohttp import web
import os

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
# Bot Token
BOT_TOKEN = "5966719769:AAEilFOlMwwEUOUFXBmmgQL11NpKMliuXbs"
ADMIN_ID = 5915172170
TARGET_GROUP_ID = -1001234567890  # Replace with actual group ID
LOG_CHANNEL_ID = -1003774210935

# Web Server Configuration
WEB_SERVER_PORT = int(os.environ.get("PORT", 8080))
WEB_SERVER_HOST = "0.0.0.0"

# MongoDB URIs (Add your MongoDB connection strings)
MONGODB_URIS = [
    "mongodb+srv://ghost1770093833371_db_user:vkvFRL7gv0TTsOIv@cluster0.junc572.mongodb.net/?appName=Cluster0",
]

# Database Configuration
DB_NAME = "bot_db"
COLLECTION_PLAYERS = "players"
COLLECTION_GLOBAL_STATS = "global_stats"

# ==================== WEB SERVER FOR UPTIME MONITORING ====================
class WebServer:
    def __init__(self):
        self.app = web.Application()
        self.setup_routes()
        self.start_time = datetime.utcnow()
        self.request_count = 0
        
    def setup_routes(self):
        """Setup web server routes"""
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/status', self.handle_status)
    
    async def handle_root(self, request):
        """Root endpoint"""
        self.request_count += 1
        return web.Response(text="Bot is running", content_type='text/plain')
    
    async def handle_health(self, request):
        """Health check endpoint"""
        self.request_count += 1
        return web.json_response({'status': 'healthy'})
    
    async def handle_status(self, request):
        """Status endpoint"""
        self.request_count += 1
        return web.json_response({
            'uptime': str(datetime.utcnow() - self.start_time),
            'requests': self.request_count
        })
    
    async def start(self):
        """Start web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
        await site.start()
        logger.info(f"🌐 Web server started on http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}")

# Initialize web server
web_server = WebServer()

# ==================== MONGODB CONFIGURATION ====================
db_connections = []
active_db = None
db_lock = threading.Lock()

def init_mongodb():
    """Initialize MongoDB connections with fallback"""
    global db_connections, active_db
    
    for uri in MONGODB_URIS:
        try:
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxPoolSize=50,
                minPoolSize=10,
                retryWrites=True,
                w='majority'
            )
            client.admin.command('ping')
            db = client[DB_NAME]
            db_connections.append(db)
            logger.info(f"✅ MongoDB connected: {uri[:30]}...")
            
            if active_db is None:
                active_db = db
                logger.info(f"✅ Active database set")
                
        except (ConnectionFailure, ConfigurationError, Exception) as e:
            logger.warning(f"❌ MongoDB failed ({type(e).__name__}): {uri[:30]}... Error: {e}")
            continue
    
    if not db_connections:
        logger.error("❌ No MongoDB connections! Using in-memory storage.")
        return False
    
    try:
        active_db[COLLECTION_PLAYERS].create_index("user_id", unique=True)
        active_db[COLLECTION_PLAYERS].create_index("xp")
        active_db[COLLECTION_PLAYERS].create_index("level")
        logger.info("✅ Database indexes created")
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")
    
    return True

def get_active_db():
    """Get active database with automatic failover"""
    global active_db, db_connections
    
    with db_lock:
        if active_db is not None:
            try:
                active_db.command('ping')
                return active_db
            except Exception:
                logger.warning("⚠️ Active DB lost, switching...")
        
        for db in db_connections:
            try:
                db.command('ping')
                active_db = db
                logger.info("✅ Switched to backup database")
                return active_db
            except Exception:
                continue
        
        logger.error("❌ All databases failed!")
        return None

mongodb_available = init_mongodb()

# ==================== CACHING & PROTECTION ====================
player_cache = {}
cache_lock = threading.Lock()
CACHE_TIMEOUT = 300

user_locks = {}
user_lock_manager = threading.Lock()

def get_user_lock(user_id):
    """Get or create lock for specific user"""
    with user_lock_manager:
        if user_id not in user_locks:
            user_locks[user_id] = asyncio.Lock()
        return user_locks[user_id]

def user_operation(func):
    """Decorator to ensure only one operation per user"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.callback_query:
            user_id = update.callback_query.from_user.id
        else:
            user_id = update.effective_user.id
        
        user_lock = get_user_lock(user_id)
        
        if user_lock.locked():
            return
        
        async with user_lock:
            return await func(update, context, *args, **kwargs)
    
    return wrapper

# ==================== DATABASE OPERATIONS ====================
def save_player_to_db(user_id, player_data):
    """Save player data to MongoDB"""
    if not mongodb_available:
        return
    
    try:
        db = get_active_db()
        if db is None:
            return
        
        player_data_copy = player_data.copy()
        player_data_copy['user_id'] = user_id
        player_data_copy['last_updated'] = datetime.utcnow()
        
        db[COLLECTION_PLAYERS].update_one(
            {'user_id': user_id},
            {'$set': player_data_copy},
            upsert=True
        )
        
        with cache_lock:
            player_cache[user_id] = {
                'data': player_data_copy,
                'timestamp': time.time()
            }
        
    except Exception as e:
        logger.error(f"Error saving player {user_id}: {e}")

def load_player_from_db(user_id):
    """Load player data from MongoDB with caching"""
    with cache_lock:
        if user_id in player_cache:
            cached = player_cache[user_id]
            if time.time() - cached['timestamp'] < CACHE_TIMEOUT:
                return cached['data']
    
    if not mongodb_available:
        return None
    
    try:
        db = get_active_db()
        if db is None:
            return None
        
        player_data = db[COLLECTION_PLAYERS].find_one({'user_id': user_id})
        
        if player_data:
            with cache_lock:
                player_cache[user_id] = {
                    'data': player_data,
                    'timestamp': time.time()
                }
            return player_data
        
        return None
        
    except Exception as e:
        logger.error(f"Error loading player {user_id}: {e}")
        return None

def get_leaderboard(limit=10):
    """Get leaderboard from database"""
    if not mongodb_available:
        return []
    
    try:
        db = get_active_db()
        if db is None:
            return []
        
        players = db[COLLECTION_PLAYERS].find().sort([("level", -1), ("xp", -1)]).limit(limit)
        return list(players)
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return []

async def init_player(user, context):
    """Initialize new player or get existing"""
    user_id = user.id
    first_name = user.first_name
    username = user.username or "None"

    player_data = load_player_from_db(user_id)
    
    if player_data is None:
        player_data = {
            'user_id': user_id,
            'name': first_name,
            'xp': 0,
            'level': 1,
            'created_at': datetime.utcnow()
        }
        save_player_to_db(user_id, player_data)

        # Log new user
        try:
            safe_first_name = first_name.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
            safe_username = username.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")

            log_msg = (
                f"🆕 **New User Joined!**\n"
                f"👤 Name: [{safe_first_name}](tg://user?id={user_id})\n"
                f"🆔 ID: `{user_id}`\n"
                f"🔗 Username: @{safe_username}"
            )
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=log_msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to log new user: {e}")

    else:
        # Ensure fields exist if updating from old version
        if 'xp' not in player_data:
            player_data['xp'] = 0
            player_data['level'] = 1
            if 'name' not in player_data:
                player_data['name'] = first_name
            save_player_to_db(user_id, player_data)
        elif 'name' not in player_data: # update name if missing
            player_data['name'] = first_name
            save_player_to_db(user_id, player_data)

    return player_data

# ==================== XP LOGIC ====================
def calculate_xp_required(level):
    """
    Calculate XP required to reach the next level.
    Formula: Base difficulty increases as level increases.
    """
    return (level ** 2) * 50 + (level * 100)

async def add_xp(user, amount, context):
    """Add XP to user and handle level up"""
    user_id = user.id

    player_data = await init_player(user, context)

    player_data['xp'] += amount
    current_level = player_data['level']
    xp_needed = calculate_xp_required(current_level)

    leveled_up = False
    while player_data['xp'] >= xp_needed:
        player_data['xp'] -= xp_needed
        player_data['level'] += 1
        current_level = player_data['level']
        xp_needed = calculate_xp_required(current_level)
        leveled_up = True

    save_player_to_db(user_id, player_data)

    if leveled_up:
        # Notify user
        try:
             await context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 **LEVEL UP!**\n\nYou are now **Level {player_data['level']}**!\nKeep chatting to gain more XP.",
                parse_mode='Markdown'
            )
        except Exception:
            # User might have blocked the bot or chat not found
            pass

        # Log level up
        try:
            safe_first_name = user.first_name.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")

            log_msg = (
                f"🆙 **Level Up!**\n"
                f"👤 User: [{safe_first_name}](tg://user?id={user_id})\n"
                f"🌟 New Level: **{player_data['level']}**"
            )
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=log_msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to log level up: {e}")

# ==================== BOT HANDLERS ====================
@user_operation
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    await init_player(user, context)
    
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        f"I am tracking your activity.\n"
        f"Every message you send earns you XP.\n"
        f"Level up and compete with others!\n\n"
        f"Commands:\n"
        f"/level - Check your current Level and XP\n"
        f"/top - View the Leaderboard",
        parse_mode='Markdown'
    )

async def level_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current level and XP"""
    user = update.effective_user
    player_data = await init_player(user, context)

    lvl = player_data['level']
    xp = player_data['xp']
    req_xp = calculate_xp_required(lvl)

    progress_bar_length = 10
    progress = int((xp / req_xp) * progress_bar_length)
    bar = "█" * progress + "░" * (progress_bar_length - progress)
    
    await update.message.reply_text(
        f"👤 **{user.first_name}**\n\n"
        f"🔰 Level: **{lvl}**\n"
        f"✨ XP: **{xp}/{req_xp}**\n"
        f"[{bar}]",
        parse_mode='Markdown'
    )

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show leaderboard (Top 200)"""
    players = get_leaderboard(200)

    if not players:
        await update.message.reply_text("📉 No data yet.")
        return

    header = "🏆 **LEADERBOARD (TOP 200)**\n\n"
    msg_chunk = ""

    for i, p in enumerate(players, 1):
        name = p.get('name', 'Unknown')
        # Escape markdown characters in name to prevent errors
        name = name.replace("*", "").replace("_", "").replace("`", "")
        lvl = p.get('level', 1)
        xp = p.get('xp', 0)
        line = f"{i}. **{name}** - Lvl {lvl} ({xp} XP)\n"

        if len(header + msg_chunk + line) > 4000:
            await update.message.reply_text(header + msg_chunk, parse_mode='Markdown')
            header = "" # Only show header on first message
            msg_chunk = line
        else:
            msg_chunk += line

    if msg_chunk:
        await update.message.reply_text(header + msg_chunk, parse_mode='Markdown')

@user_operation
async def changename_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change user name"""
    user = update.effective_user
    args = context.args

    if not args:
        await update.message.reply_text("⚠️ Usage: /changename <new_name>")
        return

    new_name = " ".join(args).strip()

    if len(new_name) > 50:
        await update.message.reply_text("❌ Name is too long (max 50 chars).")
        return

    if len(new_name) < 2:
        await update.message.reply_text("❌ Name is too short (min 2 chars).")
        return

    forbidden_names = ["iamkkronly", "Kaustav", "Ray", "filestore4u"]
    if any(forbidden.lower() in new_name.lower() for forbidden in forbidden_names):
        await update.message.reply_text("❌ This name is not allowed.")
        return

    # Update in DB
    player_data = await init_player(user, context)
    player_data['name'] = new_name
    save_player_to_db(user.id, player_data)

    # Escape markdown characters in name to prevent errors
    safe_new_name = new_name.replace("*", "").replace("_", "").replace("`", "")

    await update.message.reply_text(
        f"✅ Your name has been changed to: **{safe_new_name}**",
        parse_mode='Markdown'
    )

@user_operation
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages to award XP"""
    if not update.effective_user or update.effective_user.is_bot:
        return

    user = update.effective_user

    # Calculate random XP based on message length, but capped
    msg_len = len(update.message.text) if update.message.text else 0
    xp_gain = min(50, max(5, int(msg_len / 2))) # Min 5, Max 50 XP

    await add_xp(user, xp_gain, context)

# ==================== MAIN ====================
def main():
    """Start bot"""
    application = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("level", level_cmd))
    application.add_handler(CommandHandler("top", top_cmd))
    application.add_handler(CommandHandler("changename", changename_cmd))

    # Message Handler (for XP)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 60)
    print("🚀 XP BOT STARTED")
    print("=" * 60)
    print(f"✅ Web Server: http://0.0.0.0:{WEB_SERVER_PORT}")
    
    # Start web server and bot
    async def start_all():
        await web_server.start()
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_all())
        loop.run_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
