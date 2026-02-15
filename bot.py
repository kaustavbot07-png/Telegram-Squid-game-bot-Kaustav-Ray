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

# Web Server Configuration
WEB_SERVER_PORT = int(os.environ.get("PORT", 8080))
WEB_SERVER_HOST = "0.0.0.0"

# MongoDB URIs (Add your MongoDB connection strings)
MONGODB_URIS = [
    "mongodb+srv://ghost1770093833371_db_user:vkvFRL7gv0TTsOIv@cluster0.junc572.mongodb.net/?appName=Cluster0",
]

# Database Configuration
DB_NAME = "squid_game_bot"
COLLECTION_PLAYERS = "players"
COLLECTION_GUILDS = "guilds"
COLLECTION_TOURNAMENTS = "tournaments"
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
        self.app.router.add_get('/stats', self.handle_stats)
        self.app.router.add_get('/ping', self.handle_ping)
    
    async def handle_root(self, request):
        """Root endpoint"""
        self.request_count += 1
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Squid Game Bot</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 50px;
                    text-align: center;
                }
                .container {
                    background: rgba(0,0,0,0.3);
                    padding: 40px;
                    border-radius: 15px;
                    max-width: 600px;
                    margin: 0 auto;
                }
                h1 { font-size: 3em; margin-bottom: 20px; }
                .status { color: #00ff00; font-weight: bold; }
                .info { margin: 20px 0; }
                a { color: #00ffff; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎭 SQUID GAME BOT</h1>
                <p class="status">✅ BOT IS RUNNING</p>
                <div class="info">
                    <p>📊 <a href="/stats">View Statistics</a></p>
                    <p>❤️ <a href="/health">Health Check</a></p>
                    <p>📈 <a href="/status">System Status</a></p>
                </div>
                <p>💀 Let the games begin...</p>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
    async def handle_health(self, request):
        """Health check endpoint for UptimeRobot"""
        self.request_count += 1
        return web.json_response({
            'status': 'healthy',
            'bot': 'online',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds()
        })
    
    async def handle_ping(self, request):
        """Simple ping endpoint"""
        self.request_count += 1
        return web.Response(text='pong')
    
    async def handle_status(self, request):
        """Detailed status endpoint"""
        self.request_count += 1
        uptime = datetime.utcnow() - self.start_time
        
        return web.json_response({
            'bot_status': 'running',
            'uptime': str(uptime),
            'uptime_seconds': uptime.total_seconds(),
            'mongodb_connected': mongodb_available,
            'active_connections': len(db_connections),
            'requests_served': self.request_count,
            'cached_players': len(player_cache),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def handle_stats(self, request):
        """Statistics endpoint"""
        self.request_count += 1
        stats = get_global_stats()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bot Statistics</title>
            <meta http-equiv="refresh" content="10">
            <style>
                body {{
                    font-family: 'Courier New', monospace;
                    background: #0a0a0a;
                    color: #00ff00;
                    padding: 20px;
                }}
                .stat-box {{
                    background: #1a1a1a;
                    border: 2px solid #00ff00;
                    padding: 20px;
                    margin: 10px 0;
                    border-radius: 5px;
                }}
                h1 {{ color: #ff0000; text-align: center; }}
                .value {{ font-size: 2em; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>🎭 SQUID GAME BOT STATISTICS</h1>
            <div class="stat-box">
                <p>👥 Total Players</p>
                <p class="value">{stats.get('total_players', 0):,}</p>
            </div>
            <div class="stat-box">
                <p>🎮 Games Played</p>
                <p class="value">{stats.get('games_played', 0):,}</p>
            </div>
            <div class="stat-box">
                <p>💀 Total Deaths</p>
                <p class="value">{stats.get('total_deaths', 0):,}</p>
            </div>
            <div class="stat-box">
                <p>⏰ Last Updated</p>
                <p>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            <p style="text-align:center; margin-top:30px;">Auto-refreshes every 10 seconds</p>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
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
        active_db[COLLECTION_PLAYERS].create_index("money")
        active_db[COLLECTION_PLAYERS].create_index("games_survived")
        active_db[COLLECTION_PLAYERS].create_index("win_streak")
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

button_clicks = {}
button_click_lock = threading.Lock()
BUTTON_COOLDOWN = 2

user_locks = {}
user_lock_manager = threading.Lock()

def get_user_lock(user_id):
    """Get or create lock for specific user"""
    with user_lock_manager:
        if user_id not in user_locks:
            user_locks[user_id] = asyncio.Lock()
        return user_locks[user_id]

def check_button_cooldown(user_id, callback_data):
    """Check if user can click this button"""
    with button_click_lock:
        key = f"{user_id}_{callback_data}"
        current_time = time.time()
        
        if key in button_clicks:
            last_click = button_clicks[key]
            if current_time - last_click < BUTTON_COOLDOWN:
                return False
        
        button_clicks[key] = current_time
        
        keys_to_delete = [k for k, v in button_clicks.items() if current_time - v > BUTTON_COOLDOWN * 2]
        for k in keys_to_delete:
            del button_clicks[k]
        
        return True

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
            if update.callback_query:
                await update.callback_query.answer(
                    "⏳ Please wait, processing...",
                    show_alert=True
                )
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

def get_leaderboard(sort_field, limit=10):
    """Get leaderboard from database"""
    if not mongodb_available:
        return []
    
    try:
        db = get_active_db()
        if db is None:
            return []
        
        players = db[COLLECTION_PLAYERS].find().sort(sort_field, -1).limit(limit)
        return list(players)
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return []

def update_global_stats(stats_update):
    """Update global statistics"""
    if not mongodb_available:
        return
    
    try:
        db = get_active_db()
        if db is None:
            return
        
        db[COLLECTION_GLOBAL_STATS].update_one(
            {'_id': 'global'},
            {'$inc': stats_update, '$set': {'last_updated': datetime.utcnow()}},
            upsert=True
        )
        
    except Exception as e:
        logger.error(f"Error updating global stats: {e}")

def get_global_stats():
    """Get global statistics"""
    if not mongodb_available:
        return {'total_players': 0, 'games_played': 0, 'total_deaths': 0}
    
    try:
        db = get_active_db()
        if db is None:
            return {'total_players': 0, 'games_played': 0, 'total_deaths': 0}
        
        stats = db[COLLECTION_GLOBAL_STATS].find_one({'_id': 'global'})
        if stats:
            return stats
        return {'total_players': 0, 'games_played': 0, 'total_deaths': 0}
        
    except Exception as e:
        logger.error(f"Error getting global stats: {e}")
        return {'total_players': 0, 'games_played': 0, 'total_deaths': 0}

def get_all_user_ids():
    """Get all user IDs for broadcast"""
    if not mongodb_available:
        return []
    try:
        db = get_active_db()
        if db is None:
            return []
        users = db[COLLECTION_PLAYERS].find({}, {'user_id': 1})
        return [u['user_id'] for u in users]
    except Exception:
        return []

MARKET_ITEMS = {
    "food": {"name": "🍞 Food", "price": 10000000, "effect": "hunger", "desc": "Restore energy"},
    "medicine": {"name": "💊 Medicine", "price": 50000000, "effect": "health", "desc": "Heal injuries"},
    "weapon": {"name": "🔪 Weapon", "price": 100000000, "effect": "strength+2", "desc": "+2 Strength"},
    "protection": {"name": "🛡️ Armor", "price": 200000000, "effect": "protection", "desc": "-10% death"},
    "luck_charm": {"name": "🎰 Lucky Charm", "price": 300000000, "effect": "luck+2", "desc": "+2 Luck"},
    "revive_token": {"name": "💉 Revive", "price": 500000000, "effect": "revive", "desc": "Auto-revive"},
    "shield": {"name": "🛡️ Shield", "price": 450000000, "effect": "block", "desc": "Block death"},
    "double_reward": {"name": "💎 2x Reward", "price": 300000000, "effect": "2x", "desc": "Double reward"},
}

ACHIEVEMENTS = {
    "first_blood": {"name": "🏆 First Blood", "desc": "Survive first game", "reward": 50000000},
    "survivor": {"name": "💀 Survivor", "desc": "Survive 5 games", "reward": 100000000},
    "veteran": {"name": "👑 Veteran", "desc": "Survive 10 games", "reward": 200000000},
    "rich": {"name": "💰 Millionaire", "desc": "Earn ₩1B", "reward": 100000000},
}

async def send_level_up(user_id, first_name, new_level, context):
    """Send level up notification"""
    msg = f"🎉 LEVEL UP!\n\n[{first_name}](tg://user?id={user_id}) is now Level {new_level}!"
    try:
        await context.bot.send_message(chat_id=TARGET_GROUP_ID, text=msg, parse_mode='Markdown')
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
    except Exception:
        pass

def init_player(user_id):
    """Initialize new player"""
    player_data = load_player_from_db(user_id)
    
    if player_data is None:
        player_data = {
            'user_id': user_id,
            'number': random.randint(1, 456),
            'alive': True,
            'games_survived': 0,
            'money': 0,
            'inventory': [],
            'luck_stat': random.randint(3, 8),
            'strength': random.randint(3, 8),
            'intelligence': random.randint(3, 8),
            'achievements': [],
            'death_count': 0,
            'level': 1,
            'exp': 0,
            'reputation': 0,
            'win_streak': 0,
            'highest_streak': 0,
            'vip_status': False,
            'last_daily': None,
            'created_at': datetime.utcnow()
        }
        
        save_player_to_db(user_id, player_data)
        update_global_stats({'total_players': 1})
    else:
        # Ensure reputation exists for existing players
        if 'reputation' not in player_data:
            player_data['reputation'] = 0
            save_player(user_id, player_data)
    
    return player_data

def save_player(user_id, player_data):
    """Save player data"""
    save_player_to_db(user_id, player_data)

async def add_experience(user_id, amount, context, first_name):
    """Add experience to user and check level up"""
    player_data = load_player_from_db(user_id)
    if not player_data:
        return

    if 'level' not in player_data:
        player_data['level'] = 1
    if 'exp' not in player_data:
        player_data['exp'] = 0
    if 'reputation' not in player_data:
        player_data['reputation'] = 0

    if player_data['level'] < 1:
        player_data['level'] = 1

    player_data['exp'] += amount
    old_level = player_data['level']

    # Level calculation: Level n -> n+1 requires 100 * (2^(n-1))
    while player_data['level'] < 200:
        required_exp = 100 * (2 ** (player_data['level'] - 1))
        if player_data['exp'] >= required_exp:
            player_data['level'] += 1
            player_data['exp'] -= required_exp
        else:
            break

    if player_data['level'] > old_level:
        await send_level_up(user_id, first_name, player_data['level'], context)

    save_player(user_id, player_data)

# ==================== BOT HANDLERS ====================
@user_operation
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user_id = update.effective_user.id
    player_data = init_player(user_id)
    
    keyboard = [
        [InlineKeyboardButton("👤 PROFILE", callback_data='profile'),
         InlineKeyboardButton("🏪 SHOP", callback_data='shop')],
        [InlineKeyboardButton("🤝 SOCIAL", callback_data='social'),
         InlineKeyboardButton("💎 VIP", callback_data='vip')],
        [InlineKeyboardButton("🎁 REWARDS", callback_data='daily_rewards'),
         InlineKeyboardButton("📊 STATS", callback_data='stats')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎭 *Squid Game Bot*\n\n"
        f"Welcome, Player #{player_data['number']:03d}.\n"
        f"Level: {player_data['level']}\n"
        f"Status: {'✅ ALIVE' if player_data['alive'] else '💀 DEAD'}\n\n"
        f"💰 Money: ₩{player_data['money']:,}\n"
        f"⚡ Reputation: {player_data['reputation']}\n\n"
        f"Choose your action...",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

@user_operation
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    if not check_button_cooldown(user_id, data):
        await query.answer("⏳ Wait before clicking again!", show_alert=True)
        return
    
    if query.message.chat.id != user_id:
        await query.answer("❌ Not your button!", show_alert=True)
        return
    
    await query.answer()

    # Add experience for interaction
    await add_experience(user_id, 2, context, query.from_user.first_name)

    player_data = init_player(user_id)
    
    # Main Menu
    if data == 'main_menu':
        keyboard = [
            [InlineKeyboardButton("👤 PROFILE", callback_data='profile'),
             InlineKeyboardButton("🏪 SHOP", callback_data='shop')],
            [InlineKeyboardButton("🤝 SOCIAL", callback_data='social'),
             InlineKeyboardButton("💎 VIP", callback_data='vip')],
            [InlineKeyboardButton("🎁 REWARDS", callback_data='daily_rewards'),
             InlineKeyboardButton("📊 STATS", callback_data='stats')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🎭 MENU\n\nPlayer #{player_data['number']:03d}\n💰 ₩{player_data['money']:,}",
            reply_markup=reply_markup
        )
    
    # Profile
    elif data == 'profile':
        keyboard = [
            [InlineKeyboardButton("🏆 Achievements", callback_data='profile_achievements')],
            [InlineKeyboardButton("🎒 Inventory", callback_data='profile_inventory')],
            [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        win_rate = (player_data['games_survived'] / (player_data['games_survived'] + player_data['death_count']) * 100) if (player_data['games_survived'] + player_data['death_count']) > 0 else 0
        
        await query.edit_message_text(
            f"👤 PROFILE\n\n"
            f"Player #{player_data['number']:03d}\n"
            f"Level {player_data['level']}\n"
            f"Reputation: {player_data['reputation']}\n\n"
            f"💰 ₩{player_data['money']:,}\n"
            f"🎮 Wins: {player_data['games_survived']}\n"
            f"💀 Deaths: {player_data['death_count']}\n"
            f"📊 Rate: {win_rate:.1f}%\n"
            f"🔥 Streak: {player_data['win_streak']}\n\n"
            f"⚡ Luck: {player_data['luck_stat']}/10\n"
            f"💪 Str: {player_data['strength']}/10",
            reply_markup=reply_markup
        )
    
    elif data == 'profile_achievements':
        unlocked = len(player_data['achievements'])
        ach_text = f"🏆 ACHIEVEMENTS\n\n{unlocked}/{len(ACHIEVEMENTS)} unlocked\n\n"
        
        for key, ach in ACHIEVEMENTS.items():
            status = "✅" if key in player_data['achievements'] else "🔒"
            ach_text += f"{status} {ach['name']}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='profile')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(ach_text, reply_markup=reply_markup)
    
    elif data == 'profile_inventory':
        if not player_data['inventory']:
            inv_text = "🎒 INVENTORY\n\nEmpty!"
        else:
            inv_text = "🎒 INVENTORY\n\n"
            counts = {}
            for item in player_data['inventory']:
                counts[item] = counts.get(item, 0) + 1
            
            for key, count in counts.items():
                if key in MARKET_ITEMS:
                    inv_text += f"{MARKET_ITEMS[key]['name']} x{count}\n"
        
        keyboard = [
            [InlineKeyboardButton("🏪 Shop", callback_data='shop')],
            [InlineKeyboardButton("🔙 Back", callback_data='profile')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(inv_text, reply_markup=reply_markup)
    
    # Shop
    elif data == 'shop':
        keyboard = [
            [InlineKeyboardButton("💊 Consumables", callback_data='shop_consumables')],
            [InlineKeyboardButton("⚔️ Equipment", callback_data='shop_equipment')],
            [InlineKeyboardButton("💎 Premium", callback_data='shop_premium')],
            [InlineKeyboardButton("💰 ₩" + f"{player_data['money']:,}", callback_data='shop')],
            [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🏪 SHOP\n\nBalance: ₩{player_data['money']:,}",
            reply_markup=reply_markup
        )
    
    elif data == 'shop_consumables':
        keyboard = [
            [InlineKeyboardButton("🍞 Food - ₩10M", callback_data='buy_food')],
            [InlineKeyboardButton("💊 Medicine - ₩50M", callback_data='buy_medicine')],
            [InlineKeyboardButton("🔙 Back", callback_data='shop')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"💊 CONSUMABLES\n\n₩{player_data['money']:,}", reply_markup=reply_markup)
    
    elif data == 'shop_equipment':
        keyboard = [
            [InlineKeyboardButton("🔪 Weapon - ₩100M", callback_data='buy_weapon')],
            [InlineKeyboardButton("🛡️ Armor - ₩200M", callback_data='buy_protection')],
            [InlineKeyboardButton("🎰 Luck - ₩300M", callback_data='buy_luck_charm')],
            [InlineKeyboardButton("🔙 Back", callback_data='shop')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"⚔️ EQUIPMENT\n\n₩{player_data['money']:,}", reply_markup=reply_markup)
    
    elif data == 'shop_premium':
        keyboard = [
            [InlineKeyboardButton("💉 Revive - ₩500M", callback_data='buy_revive_token')],
            [InlineKeyboardButton("🛡️ Shield - ₩450M", callback_data='buy_shield')],
            [InlineKeyboardButton("💎 2x - ₩300M", callback_data='buy_double_reward')],
            [InlineKeyboardButton("🔙 Back", callback_data='shop')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"💎 PREMIUM\n\n₩{player_data['money']:,}", reply_markup=reply_markup)
    
    # Social
    elif data == 'social':
        keyboard = [
            [InlineKeyboardButton("📊 Leaderboards", callback_data='social_leaderboards')],
            [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🤝 SOCIAL", reply_markup=reply_markup)
    
    elif data == 'social_leaderboards':
        keyboard = [
            [InlineKeyboardButton("💰 Richest", callback_data='lb_money')],
            [InlineKeyboardButton("🎮 Wins", callback_data='lb_wins')],
            [InlineKeyboardButton("🔥 Streak", callback_data='lb_streak')],
            [InlineKeyboardButton("🔙 Back", callback_data='social')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📊 LEADERBOARDS", reply_markup=reply_markup)
    
    elif data == 'lb_money':
        players = get_leaderboard('money', 10)
        lb_text = "💰 TOP 10 RICHEST\n\n"
        for i, p in enumerate(players, 1):
            status = "✅" if p.get('alive', True) else "💀"
            lb_text += f"{i}. {status} #{p.get('number', 0):03d} - ₩{p.get('money', 0):,}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='social_leaderboards')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(lb_text, reply_markup=reply_markup)
    
    elif data == 'lb_wins':
        players = get_leaderboard('games_survived', 10)
        lb_text = "🎮 TOP 10 WINNERS\n\n"
        for i, p in enumerate(players, 1):
            status = "✅" if p.get('alive', True) else "💀"
            lb_text += f"{i}. {status} #{p.get('number', 0):03d} - {p.get('games_survived', 0)}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='social_leaderboards')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(lb_text, reply_markup=reply_markup)
    
    elif data == 'lb_streak':
        players = get_leaderboard('highest_streak', 10)
        lb_text = "🔥 TOP 10 STREAKS\n\n"
        for i, p in enumerate(players, 1):
            status = "✅" if p.get('alive', True) else "💀"
            lb_text += f"{i}. {status} #{p.get('number', 0):03d} - {p.get('highest_streak', 0)}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='social_leaderboards')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(lb_text, reply_markup=reply_markup)
    
    # VIP
    elif data == 'vip':
        if not player_data['vip_status']:
            keyboard = [
                [InlineKeyboardButton("💎 Buy VIP (₩2B)", callback_data='buy_vip')],
                [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "💎 VIP LOUNGE\n\n⚠️ ACCESS REQUIRED\n\n"
                "✅ 20% better odds\n✅ 1.5x rewards\n\nCost: ₩2B",
                reply_markup=reply_markup
            )
        else:
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='main_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("💎 VIP LOUNGE\n\n👑 Welcome!", reply_markup=reply_markup)
    
    elif data == 'buy_vip':
        if player_data['money'] >= 2000000000:
            player_data['money'] -= 2000000000
            player_data['vip_status'] = True
            save_player(user_id, player_data)
            await query.answer("👑 VIP Activated!", show_alert=True)
            keyboard = [[InlineKeyboardButton("Enter", callback_data='vip')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("👑 VIP ACTIVATED!", reply_markup=reply_markup)
        else:
            await query.answer("❌ Need ₩2B!", show_alert=True)
    
    # Daily Rewards
    elif data == 'daily_rewards':
        from datetime import date
        today = date.today().isoformat()
        
        if player_data.get('last_daily') == today:
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='main_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("🎁 DAILY\n\nClaimed!\nCome tomorrow.", reply_markup=reply_markup)
        else:
            reward = 50000000
            if player_data['vip_status']:
                reward *= 2
            
            player_data['money'] += reward
            player_data['last_daily'] = today
            save_player(user_id, player_data)
            
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='main_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"🎁 CLAIMED!\n\n+₩{reward:,}\n{'👑 VIP 2x' if player_data['vip_status'] else ''}\n\n"
                f"💰 ₩{player_data['money']:,}",
                reply_markup=reply_markup
            )
    
    # Stats
    elif data == 'stats':
        stats = get_global_stats()
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 GLOBAL STATS\n\n"
            f"👥 Players: {stats.get('total_players', 0):,}\n"
            f"🎮 Games: {stats.get('games_played', 0):,}\n"
            f"💀 Deaths: {stats.get('total_deaths', 0):,}",
            reply_markup=reply_markup
        )
    
    # Purchase
    elif data.startswith('buy_'):
        item_key = data.replace('buy_', '')
        
        if item_key in MARKET_ITEMS:
            item = MARKET_ITEMS[item_key]
            if player_data['money'] >= item['price']:
                player_data['money'] -= item['price']
                player_data['inventory'].append(item_key)
                
                if 'luck+' in item['effect']:
                    player_data['luck_stat'] = min(10, player_data['luck_stat'] + 2)
                elif 'strength+' in item['effect']:
                    player_data['strength'] = min(10, player_data['strength'] + 2)
                
                save_player(user_id, player_data)
                
                await query.answer(f"✅ Purchased!", show_alert=True)
                keyboard = [[InlineKeyboardButton("🔙 Shop", callback_data='shop')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"✅ BOUGHT\n\n{item['name']}\n-₩{item['price']:,}\n\n₩{player_data['money']:,}",
                    reply_markup=reply_markup
                )
            else:
                await query.answer(f"❌ Need ₩{item['price']:,}!", show_alert=True)
    
    # Respawn
    elif data == 'respawn':
        player_data['alive'] = True
        player_data['death_count'] += 1
        player_data['number'] = random.randint(1, 456)
        player_data['win_streak'] = 0
        save_player(user_id, player_data)
        
        keyboard = [[InlineKeyboardButton("👤 Profile", callback_data='profile')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🔄 RESPAWNED\n\n#{player_data['number']:03d}\nLevel {player_data['level']}\n💀 {player_data['death_count']}",
            reply_markup=reply_markup
        )

@user_operation
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages"""
    user_id = update.effective_user.id
    init_player(user_id)
    
    # Add experience for chatting
    xp_amount = 2 if update.effective_chat.id == TARGET_GROUP_ID else 1
    await add_experience(user_id, xp_amount, context, update.effective_user.first_name)

    # Simple response logic
    if random.random() < 0.1:
        await update.message.reply_text("Keep playing...")

# ==================== NEW ADMIN COMMANDS ====================
async def log_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send log file"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    try:
        with open("bot.log", "rb") as f:
            await update.message.reply_document(f, caption="📝 System Log")
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading log: {e}")

# ==================== NEW USER COMMANDS ====================
async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About bot"""
    await update.message.reply_text(
        "🎭 *Squid Game Bot*\n"
        "Version: 2.0 (No Games Edition)\n"
        "Created for fun and stats.",
        parse_mode='Markdown'
    )

async def statistics_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show own details"""
    user_id = update.effective_user.id
    player_data = init_player(user_id)
    
    await update.message.reply_text(
        f"👤 *YOUR STATISTICS*\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"🔢 Player #: {player_data['number']:03d}\n"
        f"⭐ Level: {player_data['level']}\n"
        f"✨ XP: {player_data['exp']}\n"
        f"⚡ Reputation: {player_data['reputation']}\n"
        f"💰 Money: ₩{player_data['money']:,}\n"
        f"🎮 Games Survived: {player_data['games_survived']}\n"
        f"💀 Deaths: {player_data['death_count']}\n"
        f"🔥 Streak: {player_data['win_streak']}",
        parse_mode='Markdown'
    )

async def topxp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top users by XP"""
    players = get_leaderboard('exp', 10)
    msg = "🏆 *TOP 10 XP LEADERS*\n\n"
    for i, p in enumerate(players, 1):
        msg += f"{i}. Level {p.get('level', 1)} | XP: {p.get('exp', 0)} - Player #{p.get('number', 0):03d}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def topcoins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top users by Coins"""
    players = get_leaderboard('money', 10)
    msg = "💰 *TOP 10 RICHEST*\n\n"
    for i, p in enumerate(players, 1):
        msg += f"{i}. ₩{p.get('money', 0):,} - Player #{p.get('number', 0):03d}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def toprep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top users by Reputation"""
    players = get_leaderboard('reputation', 10)
    msg = "⚡ *TOP 10 REPUTATION*\n\n"
    for i, p in enumerate(players, 1):
        msg += f"{i}. Rep: {p.get('reputation', 0)} - Player #{p.get('number', 0):03d}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def getxp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get own XP"""
    user_id = update.effective_user.id
    player_data = init_player(user_id)
    await update.message.reply_text(f"⭐ *Level:* {player_data['level']}\n✨ *XP:* {player_data['exp']}", parse_mode='Markdown')

async def getrep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get own Reputation"""
    user_id = update.effective_user.id
    player_data = init_player(user_id)
    await update.message.reply_text(f"⚡ *Reputation:* {player_data['reputation']}", parse_mode='Markdown')

async def getcoins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get own Coins"""
    user_id = update.effective_user.id
    player_data = init_player(user_id)
    await update.message.reply_text(f"💰 *Money:* ₩{player_data['money']:,}", parse_mode='Markdown')

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎭 *COMMANDS LIST*\n\n"
        "*User Commands:*\n"
        "/start - Start bot\n"
        "/about - About bot\n"
        "/statistics - Your full stats\n"
        "/topxp - Top XP Leaderboard\n"
        "/toplvl - Alias for topxp\n"
        "/topcoins - Top Richest Players\n"
        "/toprep - Top Reputation\n"
        "/getxp - View your XP/Level\n"
        "/getlvl - Alias for getxp\n"
        "/getcoins - View your Money\n"
        "/getrep - View your Reputation\n\n"
        "*Admin Commands:*\n"
        "/log - Get system log\n"
        "/stats - Global stats\n"
        "/send_to_user <id> <amount> - Send money\n"
        "/broadcast - Broadcast message",
        parse_mode='Markdown'
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_global_stats()
    await update.message.reply_text(
        f"📊 *GLOBAL STATS*\n\n"
        f"👥 Total Players: {stats.get('total_players', 0):,}\n"
        f"🎮 Games Played (Legacy): {stats.get('games_played', 0):,}\n"
        f"💀 Total Deaths: {stats.get('total_deaths', 0):,}",
        parse_mode='Markdown'
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    if update.effective_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to broadcast.")
        return

    message = update.message.reply_to_message
    users = get_all_user_ids()

    status_msg = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    count = 0

    for user_id in users:
        try:
            await message.copy(chat_id=user_id)
            count += 1
            if count % 20 == 0:
                await asyncio.sleep(1)
        except Exception:
            pass

    await status_msg.edit_text(f"✅ Broadcast sent to {count} users.")

async def send_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add coins to a user"""
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Usage: /send_to_user <user_id> <amount>")
            return

        target_id = int(args[0])
        amount = int(args[1])

        player = load_player_from_db(target_id)
        if not player:
             await update.message.reply_text("❌ User not found in database.")
             return

        player['money'] += amount
        save_player(target_id, player)

        await update.message.reply_text(f"✅ Added ₩{amount:,} to user {target_id}.")
        try:
            await context.bot.send_message(chat_id=target_id, text=f"💰 Admin sent you ₩{amount:,}!")
        except Exception:
            pass

    except ValueError:
        await update.message.reply_text("❌ Invalid format. Use numbers.")

def main():
    """Start bot with web server"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("log", log_cmd))
    application.add_handler(CommandHandler("about", about_cmd))
    application.add_handler(CommandHandler("statistics", statistics_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("send_to_user", send_to_user))

    # New Commands
    application.add_handler(CommandHandler("topxp", topxp_cmd))
    application.add_handler(CommandHandler("toplvl", topxp_cmd))
    application.add_handler(CommandHandler("topcoins", topcoins_cmd))
    application.add_handler(CommandHandler("toprep", toprep_cmd))
    application.add_handler(CommandHandler("getxp", getxp_cmd))
    application.add_handler(CommandHandler("getlvl", getxp_cmd))
    application.add_handler(CommandHandler("getcoins", getcoins_cmd))
    application.add_handler(CommandHandler("getrep", getrep_cmd))

    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 60)
    print("🎭 SQUID GAME BOT - LITE EDITION")
    print("=" * 60)
    print(f"✅ MongoDB: {'Connected' if mongodb_available else 'Offline'}")
    print(f"✅ Databases: {len(db_connections)}")
    print(f"✅ Web Server: http://0.0.0.0:{WEB_SERVER_PORT}")
    print("=" * 60)
    print("🎮 Bot starting...")
    print("=" * 60)
    
    # Start web server in event loop
    async def start_all():
        await web_server.start()
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Run bot
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
