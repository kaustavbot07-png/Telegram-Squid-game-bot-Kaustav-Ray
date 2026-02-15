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
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
# Bot Token
BOT_TOKEN = "5966719769:AAEilFOlMwwEUOUFXBmmgQL11NpKMliuXbs"
ADMIN_ID = 5915172170

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

# ==================== GAME DATA ====================
GREETINGS = [
    "Welcome, Player. Your number has been assigned. There is no turning back now.",
    "Another player arrives. How unfortunate for you.",
    "You have entered the game. Leaving is... not an option.",
    "Silence. The games will begin shortly.",
    "So, you've come for the money. Many have tried. Few survive.",
]

THREATS = [
    "You will follow the rules, or you will be eliminated.",
    "Every word you speak could be your last.",
    "The guards are watching. Always watching.",
    "One wrong move and you're out. Permanently.",
]

TAUNTS = [
    "Are you scared? You should be.",
    "Your hands are trembling.",
    "How many of your friends have died already?",
    "The prize is 45.6 billion won. Is your life worth it?",
]

ELIMINATIONS = [
    "💀 ELIMINATED. Remove the body.",
    "💀 Player eliminated. Next.",
    "💀 You have failed. Guards, proceed.",
    "💀 Game over. Forever.",
]

SURVIVAL_MESSAGES = [
    "You survived... this time.",
    "Impressive. But luck runs out eventually.",
    "You live another day.",
]

GAMES = {
    "red_light": {
        "name": "🟢🔴 RED LIGHT, GREEN LIGHT",
        "description": "Run to finish in 5 minutes.\nStop when doll turns.\n🎵 Mugunghwa kkoci pieot seumnida...",
        "difficulty": "Easy",
        "death_rate": 0.35,
        "reward": 100000000,
        "category": "classic"
    },
    "dalgona": {
        "name": "🍬 DALGONA CANDY",
        "description": "Carve shape from honeycomb.\nDon't break it. 10 minutes.",
        "difficulty": "Medium",
        "death_rate": 0.40,
        "reward": 150000000,
        "category": "classic"
    },
    "tug_of_war": {
        "name": "🪢 TUG OF WAR",
        "description": "Two teams. One rope. Deadly drop.",
        "difficulty": "Hard",
        "death_rate": 0.50,
        "reward": 200000000,
        "category": "classic"
    },
    "marbles": {
        "name": "⚪ MARBLES",
        "description": "Win all 10 marbles from partner.\nLoser dies.",
        "difficulty": "Mental",
        "death_rate": 0.50,
        "reward": 250000000,
        "category": "classic"
    },
    "glass_bridge": {
        "name": "🌉 GLASS STEPPING STONES",
        "description": "18 pairs of glass. Tempered vs regular.\nGuess wrong = death.",
        "difficulty": "Extreme",
        "death_rate": 0.65,
        "reward": 300000000,
        "category": "classic"
    },
    "squid_game": {
        "name": "🦑 SQUID GAME",
        "description": "Final game. Two players.\nFight to death.",
        "difficulty": "Final",
        "death_rate": 0.50,
        "reward": 500000000,
        "category": "classic"
    },
    "sniper_dodge": {
        "name": "🎯 SNIPER DODGE",
        "description": "Cross 100m while snipers shoot.\nOne hit = death.",
        "difficulty": "Insane",
        "death_rate": 0.72,
        "reward": 450000000,
        "category": "extreme"
    },
    "fire_walk": {
        "name": "🔥 FIRE WALK",
        "description": "Walk 20m through flames.\n30 seconds max.",
        "difficulty": "Extreme",
        "death_rate": 0.61,
        "reward": 340000000,
        "category": "extreme"
    },
    "electric_maze": {
        "name": "⚡ ELECTRIC MAZE",
        "description": "Metal maze. Random shocks.\n5 minutes.",
        "difficulty": "Deadly",
        "death_rate": 0.58,
        "reward": 320000000,
        "category": "extreme"
    },
    "russian_roulette": {
        "name": "🔫 RUSSIAN ROULETTE",
        "description": "Six chambers. One bullet.\nPure luck.",
        "difficulty": "Extreme",
        "death_rate": 0.17,
        "reward": 350000000,
        "category": "luck"
    },
    "lava_run": {
        "name": "🌋 LAVA RUN",
        "description": "Floor is lava. Literally.\nReach the safe zone.",
        "difficulty": "Extreme",
        "death_rate": 0.85,
        "reward": 600000000,
        "category": "extreme"
    },
    "bomb_defuse": {
        "name": "💣 BOMB DEFUSE",
        "description": "Cut the right wire.\nRed or Blue?",
        "difficulty": "Luck",
        "death_rate": 0.50,
        "reward": 400000000,
        "category": "luck"
    },
    "blind_jump": {
        "name": "🧗 BLIND JUMP",
        "description": "Jump into the abyss.\nHope for a net.",
        "difficulty": "Extreme",
        "death_rate": 0.90,
        "reward": 700000000,
        "category": "extreme"
    },
}

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

# ==================== GAME ANIMATIONS ====================
GAME_ANIMATIONS = {
    "red_light": [
        "🟢 GREEN LIGHT! You run...",
        "🔴 RED LIGHT! FREEZE!",
        "🟢 GREEN! Sprinting...",
        "🔴 STOP! The doll turns...",
        "🟢 Almost there...",
    ],
    "dalgona": [
        "🍬 You start carving the honeycomb...",
        "🔨 Tapping gently...",
        "⏳ Shape is forming...",
        "😬 Don't break it...",
        "🎨 Almost done...",
    ],
    "tug_of_war": [
        "🪢 Teams take positions...",
        "💪 Pulling with all strength...",
        "⚖️ Rope tightens...",
        "🔥 Sweat and strain...",
        "😱 Edge of the platform...",
    ],
    "marbles": [
        "⚪ You face your partner...",
        "🤝 You bet 1 marble...",
        "🎲 Your partner guesses...",
        "😨 One marble lost...",
        "⚪ Final round...",
    ],
    "glass_bridge": [
        "🌉 First step onto glass...",
        "⚡ You tap the first pane...",
        "😰 It holds! Jump to next...",
        "💎 Tempered glass?",
        "👣 One wrong step...",
    ],
    "squid_game": [
        "🦑 Enter the squid court...",
        "⚔️ Approach your opponent...",
        "💢 Attack!",
        "🛡️ Defend!",
        "😤 Final blow...",
    ],
    "sniper_dodge": [
        "🎯 Snipers aim...",
        "🏃 Run!",
        "💥 Bullet whizzes past...",
        "😅 Dive behind cover...",
        "🎯 Final stretch...",
    ],
    "fire_walk": [
        "🔥 Flames roar...",
        "👣 First step on coals...",
        "😖 Searing heat...",
        "🏃 Keep moving...",
        "🏁 Almost through...",
    ],
    "electric_maze": [
        "⚡ Maze of metal...",
        "🤖 Shocks pulse randomly...",
        "😬 Avoid the live wires...",
        "💡 Find the path...",
        "🏃 Exit in sight...",
    ],
    "russian_roulette": [
        "🔫 Six chambers... one bullet.",
        "🔄 Spin the cylinder...",
        "😰 Put the gun to your head...",
        "👆 Click.",
        "💀 Final trigger...",
    ],
    "lava_run": [
        "🌋 The ground shakes...",
        "🔥 Lava starts rising!",
        "🏃 Jump to the first rock...",
        "😰 It's getting hot...",
        "🏁 The safe zone is near...",
    ],
    "bomb_defuse": [
        "💣 Timer ticking down...",
        "✂️ Pliers in hand...",
        "😰 Red or Blue?",
        "💥 3... 2... 1...",
        "✂️ CUT!",
    ],
    "blind_jump": [
        "🌑 Darkness below...",
        "😨 Toes on the edge...",
        "🌬️ Wind howling...",
        "🦶 You leap!",
        "⏳ Falling...",
    ],
}

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
            'win_streak': 0,
            'highest_streak': 0,
            'vip_status': False,
            'last_daily': None,
            'created_at': datetime.utcnow()
        }
        
        save_player_to_db(user_id, player_data)
        update_global_stats({'total_players': 1})
    
    return player_data

def save_player(user_id, player_data):
    """Save player data"""
    save_player_to_db(user_id, player_data)

async def add_experience(user_id, amount, update):
    """Add experience to user and check level up"""
    player_data = load_player_from_db(user_id)
    if not player_data:
        return

    if 'level' not in player_data:
        player_data['level'] = 1
    if 'exp' not in player_data:
        player_data['exp'] = 0

    player_data['exp'] += amount

    # Level calculation: Level * 1000 required for next level
    required_exp = player_data['level'] * 1000

    if player_data['exp'] >= required_exp:
        player_data['level'] += 1
        player_data['exp'] = 0 # Reset exp as per existing logic
        save_player(user_id, player_data)

        msg = f"🎉 LEVEL UP! You are now Level {player_data['level']}!"
        try:
            if update.callback_query:
                # Use message from callback query
                await update.callback_query.message.reply_text(msg)
            elif update.message:
                await update.message.reply_text(msg)
        except Exception as e:
            logger.error(f"Error sending level up message: {e}")
    else:
        save_player(user_id, player_data)

# ==================== BOT HANDLERS ====================
@user_operation
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user_id = update.effective_user.id
    player_data = init_player(user_id)
    
    response = random.choice(GREETINGS)
    
    keyboard = [
        [InlineKeyboardButton("🎮 GAMES", callback_data='games_hub'),
         InlineKeyboardButton("👤 PROFILE", callback_data='profile')],
        [InlineKeyboardButton("🏪 SHOP", callback_data='shop'),
         InlineKeyboardButton("🤝 SOCIAL", callback_data='social')],
        [InlineKeyboardButton("🎪 CASINO", callback_data='casino'),
         InlineKeyboardButton("💎 VIP", callback_data='vip')],
        [InlineKeyboardButton("🎁 REWARDS", callback_data='daily_rewards'),
         InlineKeyboardButton("📊 STATS", callback_data='stats')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎭 {response}\n\n"
        f"╔═══════════════════════╗\n"
        f"   Player #{player_data['number']:03d}\n"
        f"   Level: {player_data['level']}\n"
        f"   Status: {'✅ ALIVE' if player_data['alive'] else '💀 DEAD'}\n"
        f"╚═══════════════════════╝\n\n"
        f"💰 Money: ₩{player_data['money']:,}\n"
        f"🎮 Wins: {player_data['games_survived']}\n"
        f"🔥 Streak: {player_data['win_streak']}\n\n"
        f"Choose your path...",
        reply_markup=reply_markup
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
    await add_experience(user_id, 2, update)

    player_data = init_player(user_id)
    
    # Main Menu
    if data == 'main_menu':
        keyboard = [
            [InlineKeyboardButton("🎮 GAMES", callback_data='games_hub'),
             InlineKeyboardButton("👤 PROFILE", callback_data='profile')],
            [InlineKeyboardButton("🏪 SHOP", callback_data='shop'),
             InlineKeyboardButton("🤝 SOCIAL", callback_data='social')],
            [InlineKeyboardButton("🎪 CASINO", callback_data='casino'),
             InlineKeyboardButton("💎 VIP", callback_data='vip')],
            [InlineKeyboardButton("🎁 REWARDS", callback_data='daily_rewards'),
             InlineKeyboardButton("📊 STATS", callback_data='stats')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🎭 MENU\n\nPlayer #{player_data['number']:03d}\n💰 ₩{player_data['money']:,}",
            reply_markup=reply_markup
        )
    
    # Games Hub
    elif data == 'games_hub':
        keyboard = [
            [InlineKeyboardButton("🎯 Classic", callback_data='games_classic')],
            [InlineKeyboardButton("🕹️ Arcade", callback_data='games_arcade')],
            [InlineKeyboardButton("💀 Extreme", callback_data='games_extreme')],
            [InlineKeyboardButton("🎰 Luck", callback_data='games_luck')],
            [InlineKeyboardButton("🎲 Random", callback_data='random_game')],
            [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🎮 GAMES HUB\n\nChoose category:", reply_markup=reply_markup)
    
    elif data == 'games_arcade':
        keyboard = [
            [InlineKeyboardButton("❌⭕ Tic Tac Toe", callback_data='game_ttt')],
            [InlineKeyboardButton("👊✋✌️ RPS", callback_data='game_rps')],
            [InlineKeyboardButton("🔙 Back", callback_data='games_hub')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🕹️ ARCADE GAMES", reply_markup=reply_markup)

    elif data == 'game_ttt':
        await tictactoe_cmd(update, context)

    elif data == 'game_rps':
        await rps_cmd(update, context)

    elif data == 'games_classic':
        keyboard = [
            [InlineKeyboardButton("🟢 Red Light", callback_data='game_red_light')],
            [InlineKeyboardButton("🍬 Dalgona", callback_data='game_dalgona')],
            [InlineKeyboardButton("🪢 Tug War", callback_data='game_tug_of_war')],
            [InlineKeyboardButton("⚪ Marbles", callback_data='game_marbles')],
            [InlineKeyboardButton("🌉 Glass", callback_data='game_glass_bridge')],
            [InlineKeyboardButton("🦑 Squid", callback_data='game_squid_game')],
            [InlineKeyboardButton("🔙 Back", callback_data='games_hub')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🎯 CLASSIC GAMES", reply_markup=reply_markup)
    
    elif data == 'games_extreme':
        keyboard = [
            [InlineKeyboardButton("🎯 Sniper (72%)", callback_data='game_sniper_dodge')],
            [InlineKeyboardButton("🔥 Fire (61%)", callback_data='game_fire_walk')],
            [InlineKeyboardButton("⚡ Electric (58%)", callback_data='game_electric_maze')],
            [InlineKeyboardButton("🌋 Lava (85%)", callback_data='game_lava_run')],
            [InlineKeyboardButton("🧗 Blind Jump (90%)", callback_data='game_blind_jump')],
            [InlineKeyboardButton("🔙 Back", callback_data='games_hub')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("💀 EXTREME GAMES", reply_markup=reply_markup)
    
    elif data == 'games_luck':
        keyboard = [
            [InlineKeyboardButton("🔫 Roulette (17%)", callback_data='game_russian_roulette')],
            [InlineKeyboardButton("💣 Bomb Defuse (50%)", callback_data='game_bomb_defuse')],
            [InlineKeyboardButton("🔙 Back", callback_data='games_hub')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🎰 LUCK GAMES", reply_markup=reply_markup)
    
    elif data == 'random_game':
        if not player_data['alive']:
            await query.answer("💀 Dead!", show_alert=True)
            return
        game_key = random.choice(list(GAMES.keys()))
        await play_game(query, game_key, user_id, player_data)
    
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
            f"Level {player_data['level']}\n\n"
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
    
    # Casino
    elif data == 'casino':
        keyboard = [
            [InlineKeyboardButton("🎰 Slots (₩50M)", callback_data='casino_slots')],
            [InlineKeyboardButton("🃏 Blackjack (₩50M)", callback_data='casino_blackjack')],
            [InlineKeyboardButton("🔴⚫ Roulette (₩50M)", callback_data='casino_roulette')],
            [InlineKeyboardButton("🪙 Coin (₩50M)", callback_data='casino_coin')],
            [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"🎪 CASINO\n\n₩{player_data['money']:,}", reply_markup=reply_markup)
    
    elif data == 'casino_blackjack':
        await blackjack_cmd(update, context)

    elif data == 'casino_roulette':
        await roulette_cmd(update, context)

    elif data == 'casino_slots':
        if player_data['money'] < 50000000:
            await query.answer("❌ Need ₩50M!", show_alert=True)
            return
        
        player_data['money'] -= 50000000
        symbols = ['🍒', '🍋', '⭐', '💎', '7️⃣']
        result = [random.choice(symbols) for _ in range(3)]
        
        win = False
        prize = 0
        
        if result[0] == result[1] == result[2]:
            if result[0] == '7️⃣':
                prize = 500000000
            elif result[0] == '💎':
                prize = 300000000
            else:
                prize = 100000000
            win = True
            player_data['money'] += prize
        
        save_player(user_id, player_data)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Again", callback_data='casino_slots')],
            [InlineKeyboardButton("🔙 Back", callback_data='casino')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎰 SLOTS\n\n[ {result[0]} | {result[1]} | {result[2]} ]\n\n"
            f"{'🎉 WIN +₩' + f'{prize:,}' if win else '❌ LOSE -₩50M'}\n\n"
            f"💰 ₩{player_data['money']:,}",
            reply_markup=reply_markup
        )
    
    elif data == 'casino_coin':
        keyboard = [
            [InlineKeyboardButton("⬆️ Heads", callback_data='coin_heads')],
            [InlineKeyboardButton("⬇️ Tails", callback_data='coin_tails')],
            [InlineKeyboardButton("🔙 Back", callback_data='casino')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🪙 COIN\n\nBet: ₩50M\nWin: ₩100M", reply_markup=reply_markup)
    
    elif data.startswith('coin_'):
        if player_data['money'] < 50000000:
            await query.answer("❌ Need ₩50M!", show_alert=True)
            return
        
        player_data['money'] -= 50000000
        choice = 'heads' if data == 'coin_heads' else 'tails'
        result = random.choice(['heads', 'tails'])
        won = choice == result
        
        if won:
            player_data['money'] += 100000000
        
        save_player(user_id, player_data)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Again", callback_data='casino_coin')],
            [InlineKeyboardButton("🔙 Back", callback_data='casino')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🪙 COIN\n\n{choice.upper()} → {result.upper()}\n\n"
            f"{'✅ WIN +₩100M' if won else '❌ LOSE -₩50M'}\n\n"
            f"💰 ₩{player_data['money']:,}",
            reply_markup=reply_markup
        )
    
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
    
    # Game Play
    elif data.startswith('game_'):
        if not player_data['alive']:
            keyboard = [[InlineKeyboardButton("🔄 Respawn", callback_data='respawn')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("💀 DEAD\n\nRespawn?", reply_markup=reply_markup)
            return
        
        game_key = data.replace('game_', '')
        if game_key in GAMES:
            await play_game(query, game_key, user_id, player_data)
    
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
        
        keyboard = [[InlineKeyboardButton("🎮 Play", callback_data='games_hub')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🔄 RESPAWNED\n\n#{player_data['number']:03d}\nLevel {player_data['level']}\n💀 {player_data['death_count']}",
            reply_markup=reply_markup
        )

async def play_game(query, game_key, user_id, player_data):
    """Play game with animations"""
    game = GAMES[game_key]
    
    # Initial message
    await query.edit_message_text(
        f"🎭 {game['name']}\n\n{game['description']}\n\n"
        f"⚠️ {game['difficulty']}\n💀 {int(game['death_rate']*100)}%\n"
        f"💰 ₩{game['reward']:,}\n\n⏳ Starting..."
    )
    
    messages_to_cleanup = []

    # Countdown
    await asyncio.sleep(1)
    msg = await query.message.reply_text("3...")
    messages_to_cleanup.append(msg)
    await asyncio.sleep(1)
    msg = await query.message.reply_text("2...")
    messages_to_cleanup.append(msg)
    await asyncio.sleep(1)
    msg = await query.message.reply_text("1...")
    messages_to_cleanup.append(msg)
    await asyncio.sleep(1)
    msg = await query.message.reply_text("🎮 GO!")
    messages_to_cleanup.append(msg)
    await asyncio.sleep(1)
    
    # Game animation
    animation_steps = GAME_ANIMATIONS.get(game_key, [
        "🎲 The game unfolds...",
        "⏳ Tension builds...",
        "😰 Your heart races...",
        "💫 Fate hangs in the balance...",
    ])
    
    for step in animation_steps:
        msg = await query.message.reply_text(step)
        messages_to_cleanup.append(msg)
        await asyncio.sleep(1.5)  # 1.5 seconds between steps
    
    # Cleanup past gameplay record (intermediate messages)
    for msg in messages_to_cleanup:
        try:
            await msg.delete()
        except Exception:
            pass

    # Calculate survival
    # base = 1 - game['death_rate']
    # luck = player_data['luck_stat'] * 0.02
    # items = 0.05 if 'luck_charm' in player_data['inventory'] else 0
    # items += 0.10 if 'protection' in player_data['inventory'] else 0
    # vip = 0.20 if player_data['vip_status'] else 0
    
    # chance = min(0.95, base + luck + items + vip)
    chance = 0.000000001  # 0.0000001% win chance
    survived = random.random() < chance
    
    update_global_stats({'games_played': 1})
    
    if survived:
        reward = game['reward']
        if 'double_reward' in player_data['inventory']:
            reward *= 2
            player_data['inventory'].remove('double_reward')
        if player_data['vip_status']:
            reward = int(reward * 1.5)
        
        player_data['games_survived'] += 1
        player_data['money'] += reward
        player_data['win_streak'] += 1
        
        if player_data['win_streak'] > player_data['highest_streak']:
            player_data['highest_streak'] = player_data['win_streak']
        
        player_data['exp'] += 100
        if player_data['exp'] >= player_data['level'] * 1000:
            player_data['level'] += 1
            player_data['exp'] = 0
            await query.message.reply_text(f"🎉 LEVEL {player_data['level']}!")
        
        if player_data['games_survived'] == 1 and 'first_blood' not in player_data['achievements']:
            player_data['achievements'].append('first_blood')
            player_data['money'] += 50000000
        
        save_player(user_id, player_data)
        
        keyboard = [
            [InlineKeyboardButton("🎮 Again", callback_data='games_hub')],
            [InlineKeyboardButton("👤 Profile", callback_data='profile')],
            [InlineKeyboardButton("🏪 Shop", callback_data='shop')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"✅ {random.choice(SURVIVAL_MESSAGES)}\n\n"
            f"💰 +₩{reward:,}\n🎮 {player_data['games_survived']}\n"
            f"🔥 {player_data['win_streak']}\n💵 ₩{player_data['money']:,}",
            reply_markup=reply_markup
        )
    else:
        if 'revive_token' in player_data['inventory']:
            player_data['inventory'].remove('revive_token')
            save_player(user_id, player_data)
            keyboard = [[InlineKeyboardButton("Continue", callback_data='games_hub')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("💉 REVIVED!", reply_markup=reply_markup)
            return
        
        player_data['alive'] = False
        player_data['death_count'] += 1
        player_data['win_streak'] = 0
        
        update_global_stats({'total_deaths': 1})
        save_player(user_id, player_data)
        
        keyboard = [
            [InlineKeyboardButton("📊 Stats", callback_data='profile')],
            [InlineKeyboardButton("🔄 Respawn", callback_data='respawn')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"{random.choice(ELIMINATIONS)}\n\n#{player_data['number']:03d}\n\n"
            f"🎮 {player_data['games_survived']}\n💰 ₩{player_data['money']:,}\n💀 {player_data['death_count']}",
            reply_markup=reply_markup
        )

@user_operation
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages"""
    user_id = update.effective_user.id
    init_player(user_id)
    
    # Add experience for chatting
    await add_experience(user_id, 5, update)

    msg = update.message.text.lower()
    
    if 'help' in msg or 'save' in msg:
        response = "No help. Only survival."
    elif 'die' in msg or 'death' in msg:
        response = "Death is inevitable."
    else:
        response = random.choice(THREATS + TAUNTS)
    
    if random.random() < 0.3:
        keyboard = [
            [InlineKeyboardButton("🎮 Play", callback_data='games_hub')],
            [InlineKeyboardButton("📊 Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"🎭 {response}", reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"🎭 {response}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎭 SQUID GAME BOT\n\n"
        "/start - Enter\n"
        "/help - Commands\n"
        "/stats - Stats\n\n"
        "💀 Begin..."
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_global_stats()
    await update.message.reply_text(
        f"📊 STATS\n\n"
        f"👥 {stats.get('total_players', 0):,}\n"
        f"🎮 {stats.get('games_played', 0):,}\n"
        f"💀 {stats.get('total_deaths', 0):,}"
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
             # Try initializing if not exists locally but maybe user exists in Telegram?
             # We can only credit if they are in our DB.
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

# ==================== LUDO SYSTEM ====================
ludo_games = {}

class LudoGame:
    def __init__(self, user_id):
        self.user_id = user_id
        self.p_tokens = [0] * 4
        self.b_tokens = [0] * 4
        self.turn = 'player'
        self.last_roll = 0
        self.waiting_move = False
        self.log = "🎮 Game Started!"
        self.winner = None

    def to_abs(self, side, pos):
        if not (1 <= pos <= 51): return -1
        if side == 'player': return pos
        return (pos + 26 - 1) % 52 + 1

    def is_safe(self, abs_pos):
        return abs_pos in [1, 9, 14, 22, 27, 35, 40, 48]

    def move(self, side, idx, roll):
        tokens = self.p_tokens if side == 'player' else self.b_tokens
        opp_tokens = self.b_tokens if side == 'player' else self.p_tokens
        pos = tokens[idx]

        if pos == 0:
            if roll == 6:
                tokens[idx] = 1
                self.log = f"{'🟢' if side=='player' else '🔴'} Token {idx+1} -> START"
                return True
            return False

        new_pos = pos + roll
        if new_pos > 57: return False

        tokens[idx] = new_pos
        self.log = f"{'🟢' if side=='player' else '🔴'} Token {idx+1} -> {new_pos}"

        if new_pos == 57:
            self.log += " (HOME!)"

        # Capture logic
        if 1 <= new_pos <= 51:
            abs_pos = self.to_abs(side, new_pos)
            if not self.is_safe(abs_pos):
                for i, opp_pos in enumerate(opp_tokens):
                    if self.to_abs('bot' if side=='player' else 'player', opp_pos) == abs_pos:
                        opp_tokens[i] = 0
                        self.log += f"\n⚔️ CAPTURE! {'Bot' if side=='player' else 'Player'} sent home!"
                        return True
        return True

    def get_valid_moves(self, side, roll):
        tokens = self.p_tokens if side == 'player' else self.b_tokens
        moves = []
        for i, pos in enumerate(tokens):
            if pos == 0:
                if roll == 6: moves.append(i)
            elif pos < 57 and pos + roll <= 57:
                moves.append(i)
        return moves

    def check_win(self):
        if all(t == 57 for t in self.p_tokens): return 'player'
        if all(t == 57 for t in self.b_tokens): return 'bot'
        return None

    def bot_turn(self):
        roll = random.randint(1, 6)
        moves = self.get_valid_moves('bot', roll)

        if not moves:
            self.log = f"🔴 Bot rolled {roll}. No moves."
            self.turn = 'player'
            return

        # AI Logic
        best_move = random.choice(moves)

        # Simple Heuristics
        for m in moves:
            pos = self.b_tokens[m]
            if pos + roll == 57: # Enter home
                best_move = m
                break
            if pos == 0: # Leave base
                best_move = m
                break

        self.move('bot', best_move, roll)

        if self.check_win() == 'bot':
            self.winner = 'bot'
            self.log += "\n🔴 BOT WINS!"
            return

        if roll == 6:
            self.log += "\n🔴 Bot rolled 6! Again!"
            self.bot_turn()
        else:
            self.turn = 'player'

    def render_status(self):
        status = f"🎲 LUDO vs ROBOT\n\n"
        status += f"🟢 YOU (Green)\n"
        for i, p in enumerate(self.p_tokens):
            pos = "🏠 Base" if p == 0 else ("🏁 HOME" if p == 57 else f"Step {p}")
            status += f"{i+1}: {pos}\n"
        status += "\n"

        status += f"🔴 BOT (Red)\n"
        for i, p in enumerate(self.b_tokens):
            pos = "🏠 Base" if p == 0 else ("🏁 HOME" if p == 57 else f"Step {p}")
            status += f"{i+1}: {pos}\n"
        status += "\n"

        status += f"📜 {self.log}"
        return status

@user_operation
async def ludo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start Ludo game"""
    user_id = update.effective_user.id
    ludo_games[user_id] = LudoGame(user_id)
    game = ludo_games[user_id]

    keyboard = [[InlineKeyboardButton("🎲 ROLL DICE", callback_data='ludo_roll')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(game.render_status(), reply_markup=reply_markup)

async def ludo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Ludo callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if user_id not in ludo_games:
        if data == 'ludo_play_again':
             await ludo_cmd(update, context)
             return
        await query.answer("❌ No game found! /ludo to start", show_alert=True)
        return

    game = ludo_games[user_id]

    if data == 'ludo_roll':
        if game.turn != 'player':
            await query.answer("❌ Not your turn!", show_alert=True)
            return

        roll = random.randint(1, 6)
        game.last_roll = roll
        moves = game.get_valid_moves('player', roll)

        if not moves:
            game.log = f"🟢 You rolled {roll}. No moves."
            game.turn = 'bot'
            game.bot_turn()

            if game.winner:
                del ludo_games[user_id]
                keyboard = [[InlineKeyboardButton("🎮 Play Again", callback_data='ludo_play_again')]]
            else:
                keyboard = [[InlineKeyboardButton("🎲 ROLL DICE", callback_data='ludo_roll')]]

        elif len(moves) == 1:
            game.move('player', moves[0], roll)
            if game.check_win() == 'player':
                game.winner = 'player'
                player_data = load_player_from_db(user_id)
                if player_data:
                    player_data['money'] += 100000000
                    save_player(user_id, player_data)
                game.log += "\n🎉 YOU WIN! +₩100M"
                del ludo_games[user_id]
                keyboard = [[InlineKeyboardButton("🎮 Play Again", callback_data='ludo_play_again')]]
            else:
                if roll == 6:
                    game.log += "\n🟢 Rolled 6! Roll again!"
                    keyboard = [[InlineKeyboardButton("🎲 ROLL DICE", callback_data='ludo_roll')]]
                else:
                    game.turn = 'bot'
                    game.bot_turn()
                    if game.winner:
                        del ludo_games[user_id]
                        keyboard = [[InlineKeyboardButton("🎮 Play Again", callback_data='ludo_play_again')]]
                    else:
                        keyboard = [[InlineKeyboardButton("🎲 ROLL DICE", callback_data='ludo_roll')]]
        else:
            game.waiting_move = True
            game.log = f"🟢 You rolled {roll}. Choose token:"
            keyboard = []
            row = []
            for m in moves:
                row.append(InlineKeyboardButton(f"Token {m+1}", callback_data=f'ludo_move_{m}'))
            keyboard.append(row)

        await query.edit_message_text(game.render_status(), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith('ludo_move_'):
        if not game.waiting_move:
             await query.answer("❌ Roll first!", show_alert=True)
             return

        idx = int(data.split('_')[2])
        game.move('player', idx, game.last_roll)
        game.waiting_move = False

        if game.check_win() == 'player':
             game.winner = 'player'
             player_data = load_player_from_db(user_id)
             if player_data:
                 player_data['money'] += 100000000
                 save_player(user_id, player_data)
             game.log += "\n🎉 YOU WIN! +₩100M"
             del ludo_games[user_id]
             keyboard = [[InlineKeyboardButton("🎮 Play Again", callback_data='ludo_play_again')]]
        else:
            if game.last_roll == 6:
                game.log += "\n🟢 Rolled 6! Roll again!"
                keyboard = [[InlineKeyboardButton("🎲 ROLL DICE", callback_data='ludo_roll')]]
            else:
                game.turn = 'bot'
                game.bot_turn()
                if game.winner:
                     del ludo_games[user_id]
                     keyboard = [[InlineKeyboardButton("🎮 Play Again", callback_data='ludo_play_again')]]
                else:
                     keyboard = [[InlineKeyboardButton("🎲 ROLL DICE", callback_data='ludo_roll')]]

        await query.edit_message_text(game.render_status(), reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== TIC TAC TOE SYSTEM ====================
tictactoe_games = {}

class TicTacToeGame:
    def __init__(self, user_id):
        self.user_id = user_id
        self.board = [' '] * 9
        self.turn = 'X'
        self.winner = None
        self.game_over = False
        self.log = "🎮 Tic Tac Toe vs Bot"

    def make_move(self, position):
        if self.board[position] == ' ':
            self.board[position] = 'X'
            if self.check_win('X'):
                self.winner = 'X'
                self.game_over = True
                self.log = "🎉 YOU WIN!"
            elif ' ' not in self.board:
                self.game_over = True
                self.log = "🤝 DRAW!"
            else:
                self.turn = 'O'
                self.bot_move()
            return True
        return False

    def bot_move(self):
        if self.game_over: return
        available = [i for i, x in enumerate(self.board) if x == ' ']
        if not available: return

        move = -1
        # Try to win
        for m in available:
            self.board[m] = 'O'
            if self.check_win('O'):
                move = m
                break
            self.board[m] = ' '

        if move == -1: # Block
            for m in available:
                self.board[m] = 'X'
                if self.check_win('X'):
                    move = m
                    self.board[m] = ' '
                    break
                self.board[m] = ' '

        if move == -1:
            move = random.choice(available)

        self.board[move] = 'O'
        if self.check_win('O'):
            self.winner = 'O'
            self.game_over = True
            self.log = "💀 BOT WINS!"
        elif ' ' not in self.board:
            self.game_over = True
            self.log = "🤝 DRAW!"
        else:
            self.turn = 'X'

    def check_win(self, mark):
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        return any(all(self.board[i] == mark for i in line) for line in wins)

    def render_board(self):
        key = {'X': '❌', 'O': '⭕', ' ': '⬜'}
        display = f"{self.log}\n\n"
        for i in range(0, 9, 3):
            row = [key[self.board[i+j]] for j in range(3)]
            display += "".join(row) + "\n"
        return display

async def send_tictactoe_board(update, user_id):
    game = tictactoe_games[user_id]
    keyboard = []
    if not game.game_over:
        for i in range(0, 9, 3):
            row = []
            for j in range(3):
                idx = i+j
                text = " " if game.board[idx] == ' ' else game.board[idx]
                row.append(InlineKeyboardButton(text, callback_data=f'ttt_move_{idx}'))
            keyboard.append(row)
    else:
        keyboard.append([InlineKeyboardButton("🔄 Play Again", callback_data='ttt_new')])

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='games_arcade')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(game.render_board(), reply_markup=reply_markup)
    else:
        await update.message.reply_text(game.render_board(), reply_markup=reply_markup)

@user_operation
async def tictactoe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == 'ttt_new':
        tictactoe_games[user_id] = TicTacToeGame(user_id)
        await send_tictactoe_board(update, user_id)
        return

    if user_id not in tictactoe_games:
        tictactoe_games[user_id] = TicTacToeGame(user_id)

    game = tictactoe_games[user_id]

    if data.startswith('ttt_move_'):
        idx = int(data.split('_')[2])
        if not game.game_over and game.board[idx] == ' ':
            game.make_move(idx)
            if game.winner == 'X':
                p = load_player_from_db(user_id)
                if p:
                    p['money'] += 50000000
                    save_player(user_id, p)
                    game.log += "\n💰 +₩50,000,000"
            await send_tictactoe_board(update, user_id)
            if game.game_over:
                del tictactoe_games[user_id]
        else:
            await query.answer("❌ Invalid move!", show_alert=True)
    else:
        await send_tictactoe_board(update, user_id)

async def tictactoe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tictactoe_games[user_id] = TicTacToeGame(user_id)
    await send_tictactoe_board(update, user_id)


# ==================== ROCK PAPER SCISSORS SYSTEM ====================
async def rps_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👊 ROCK", callback_data='rps_rock'),
         InlineKeyboardButton("✋ PAPER", callback_data='rps_paper'),
         InlineKeyboardButton("✌️ SCISSORS", callback_data='rps_scissors')],
        [InlineKeyboardButton("🔙 Back", callback_data='games_arcade')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "🎮 ROCK PAPER SCISSORS\n\nChoose your weapon!"
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup)

@user_operation
async def rps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    choice = query.data.split('_')[1]

    # Animation
    await query.edit_message_text("👊 ROCK...", reply_markup=None)
    await asyncio.sleep(0.8)
    await query.edit_message_text("✋ PAPER...", reply_markup=None)
    await asyncio.sleep(0.8)
    await query.edit_message_text("✌️ SCISSORS...", reply_markup=None)
    await asyncio.sleep(0.8)
    await query.edit_message_text("🔫 SHOOT!", reply_markup=None)
    await asyncio.sleep(0.5)

    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    emoji = {'rock': '👊', 'paper': '✋', 'scissors': '✌️'}

    result = "🤝 DRAW!"
    win = False

    if choice == bot_choice:
        result = "🤝 DRAW!"
    elif (choice == 'rock' and bot_choice == 'scissors') or \
         (choice == 'paper' and bot_choice == 'rock') or \
         (choice == 'scissors' and bot_choice == 'paper'):
        result = "🎉 YOU WIN!"
        win = True
    else:
        result = "💀 YOU LOSE!"

    msg = f"🎮 RESULTS\n\nYou: {emoji[choice]}\nBot: {emoji[bot_choice]}\n\n{result}"

    if win:
        p = load_player_from_db(user_id)
        if p:
            p['money'] += 30000000
            save_player(user_id, p)
            msg += "\n💰 +₩30,000,000"

    keyboard = [
        [InlineKeyboardButton("🔄 Again", callback_data='game_rps')],
        [InlineKeyboardButton("🔙 Back", callback_data='games_arcade')]
    ]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== BLACKJACK SYSTEM ====================
blackjack_games = {}

class BlackjackGame:
    def __init__(self, user_id):
        self.user_id = user_id
        self.deck = []
        self.player_hand = []
        self.dealer_hand = []
        self.game_over = False
        self.status = "Playing"
        self.create_deck()
        self.deal_initial()

    def create_deck(self):
        suits = ['♠️', '♥️', '♦️', '♣️']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = [{'rank': r, 'suit': s, 'value': self.get_value(r)} for s in suits for r in ranks]
        random.shuffle(self.deck)

    def get_value(self, rank):
        if rank in ['J', 'Q', 'K']: return 10
        if rank == 'A': return 11
        return int(rank)

    def deal_initial(self):
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]

    def calculate_score(self, hand):
        score = sum(card['value'] for card in hand)
        aces = sum(1 for card in hand if card['rank'] == 'A')
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    def hit(self):
        self.player_hand.append(self.deck.pop())
        if self.calculate_score(self.player_hand) > 21:
            self.game_over = True
            self.status = "BUST"

    def stand(self):
        self.game_over = True
        while self.calculate_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

        p_score = self.calculate_score(self.player_hand)
        d_score = self.calculate_score(self.dealer_hand)

        if d_score > 21:
            self.status = "WIN"
        elif p_score > d_score:
            self.status = "WIN"
        elif p_score < d_score:
            self.status = "LOSE"
        else:
            self.status = "PUSH"

    def render(self, reveal=False):
        p_score = self.calculate_score(self.player_hand)

        cards_str = " ".join([f"{c['rank']}{c['suit']}" for c in self.player_hand])
        txt = f"🃏 BLACKJACK\n\n👤 YOU ({p_score})\n{cards_str}\n\n"

        if reveal or self.game_over:
            d_score = self.calculate_score(self.dealer_hand)
            d_cards = " ".join([f"{c['rank']}{c['suit']}" for c in self.dealer_hand])
            txt += f"🕴️ DEALER ({d_score})\n{d_cards}\n\n"
        else:
            c = self.dealer_hand[0]
            txt += f"🕴️ DEALER (?)\n{c['rank']}{c['suit']} 🂠\n\n"

        if self.game_over:
            if self.status == "WIN": txt += "🎉 YOU WIN! +₩100M"
            elif self.status == "LOSE": txt += "💀 YOU LOSE!"
            elif self.status == "BUST": txt += "💥 BUST!"
            elif self.status == "PUSH": txt += "🤝 PUSH (Money returned)"

        return txt

async def blackjack_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    p = load_player_from_db(user_id)
    if not p or p['money'] < 50000000:
        if update.callback_query:
            await update.callback_query.answer("❌ Need ₩50M!", show_alert=True)
        else:
            await update.message.reply_text("❌ Need ₩50M to play!")
        return

    p['money'] -= 50000000
    save_player(user_id, p)

    game = BlackjackGame(user_id)
    blackjack_games[user_id] = game

    keyboard = [
        [InlineKeyboardButton("👊 HIT", callback_data='bj_hit'),
         InlineKeyboardButton("✋ STAND", callback_data='bj_stand')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(game.render(), reply_markup=reply_markup)
    else:
        await update.message.reply_text(game.render(), reply_markup=reply_markup)

@user_operation
async def blackjack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if user_id not in blackjack_games:
        await query.answer("❌ Game expired.", show_alert=True)
        return

    game = blackjack_games[user_id]

    if data == 'bj_hit':
        game.hit()
        if game.game_over:
            del blackjack_games[user_id]
            keyboard = [[InlineKeyboardButton("🔄 Again", callback_data='casino_blackjack'),
                         InlineKeyboardButton("🔙 Back", callback_data='casino')]]
            await query.edit_message_text(game.render(reveal=True), reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            keyboard = [
                [InlineKeyboardButton("👊 HIT", callback_data='bj_hit'),
                 InlineKeyboardButton("✋ STAND", callback_data='bj_stand')]
            ]
            await query.edit_message_text(game.render(), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'bj_stand':
        game.stand()
        p = load_player_from_db(user_id)
        if game.status == "WIN":
            p['money'] += 100000000
        elif game.status == "PUSH":
            p['money'] += 50000000
        save_player(user_id, p)

        del blackjack_games[user_id]
        keyboard = [[InlineKeyboardButton("🔄 Again", callback_data='casino_blackjack'),
                     InlineKeyboardButton("🔙 Back", callback_data='casino')]]
        await query.edit_message_text(game.render(reveal=True), reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== ROULETTE SYSTEM ====================
async def roulette_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔴 RED (2x)", callback_data='roulette_red'),
         InlineKeyboardButton("⚫ BLACK (2x)", callback_data='roulette_black')],
        [InlineKeyboardButton("1-12 (3x)", callback_data='roulette_1-12'),
         InlineKeyboardButton("13-24 (3x)", callback_data='roulette_13-24'),
         InlineKeyboardButton("25-36 (3x)", callback_data='roulette_25-36')],
        [InlineKeyboardButton("🟢 GREEN (35x)", callback_data='roulette_green')],
        [InlineKeyboardButton("🔙 Back", callback_data='casino')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "🎡 ROULETTE\n\nBet: ₩50M\nChoose your bet:"
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup)

@user_operation
async def roulette_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    bet_type = query.data.split('_')[1]

    p = load_player_from_db(user_id)
    if not p or p['money'] < 50000000:
        await query.answer("❌ Need ₩50M!", show_alert=True)
        return

    p['money'] -= 50000000
    save_player(user_id, p)

    # Animation
    await query.edit_message_text("🎡 Spinning... 🔴", reply_markup=None)
    await asyncio.sleep(0.5)
    await query.edit_message_text("🎡 Spinning... ⚫", reply_markup=None)
    await asyncio.sleep(0.5)
    await query.edit_message_text("🎡 Spinning... 🟢", reply_markup=None)
    await asyncio.sleep(0.5)
    await query.edit_message_text("🎡 Ball bouncing...", reply_markup=None)
    await asyncio.sleep(0.5)

    result_num = random.randint(0, 36)
    color = "green" if result_num == 0 else ("red" if result_num in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else "black")
    emoji = {'red': '🔴', 'black': '⚫', 'green': '🟢'}

    win = False
    multiplier = 0

    if bet_type == 'red' and color == 'red': win = True; multiplier = 2
    elif bet_type == 'black' and color == 'black': win = True; multiplier = 2
    elif bet_type == 'green' and color == 'green': win = True; multiplier = 35
    elif bet_type == '1-12' and 1 <= result_num <= 12: win = True; multiplier = 3
    elif bet_type == '13-24' and 13 <= result_num <= 24: win = True; multiplier = 3
    elif bet_type == '25-36' and 25 <= result_num <= 36: win = True; multiplier = 3

    msg = f"🎡 RESULT: {emoji[color]} {result_num}\n\n"
    if win:
        p['money'] += 50000000 * multiplier
        save_player(user_id, p)
        msg += f"🎉 YOU WIN! +₩{50000000 * multiplier:,}"
    else:
        msg += "💀 YOU LOSE!"

    msg += f"\n💰 ₩{p['money']:,}"

    keyboard = [[InlineKeyboardButton("🔄 Again", callback_data='casino_roulette'),
                 InlineKeyboardButton("🔙 Back", callback_data='casino')]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
def main():
    """Start bot with web server"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("send_to_user", send_to_user))
    application.add_handler(CommandHandler("ludo", ludo_cmd))

    # New Game Handlers
    application.add_handler(CallbackQueryHandler(tictactoe_callback, pattern='^ttt_'))
    application.add_handler(CallbackQueryHandler(rps_callback, pattern='^rps_'))
    application.add_handler(CallbackQueryHandler(blackjack_callback, pattern='^bj_'))
    application.add_handler(CallbackQueryHandler(roulette_callback, pattern='^roulette_'))

    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 60)
    print("🎭 SQUID GAME BOT - PRODUCTION")
    print("=" * 60)
    print(f"✅ MongoDB: {'Connected' if mongodb_available else 'Offline'}")
    print(f"✅ Databases: {len(db_connections)}")
    print(f"✅ Web Server: http://0.0.0.0:{WEB_SERVER_PORT}")
    print("✅ Multi-user: Protected")
    print("✅ Button spam: Blocked")
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
