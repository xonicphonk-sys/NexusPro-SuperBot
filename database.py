import sqlite3

DB_NAME = "nexus_pro.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        # Users Table (VIP & Coins tracking)
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            first_name TEXT, 
            joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_vip INTEGER DEFAULT 0,
            coins INTEGER DEFAULT 10
        )''')
        # Stats Table
        conn.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER DEFAULT 0)")
        # Insert Default Stats
        stats_keys = ['total_downloads', 'total_ai_chats', 'total_files_converted']
        for key in stats_keys:
            conn.execute("INSERT OR IGNORE INTO stats (key, value) VALUES (?, 0)", (key,))
        conn.commit()

def save_user(user_id, first_name):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))
        conn.commit()

def get_user_data(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT is_vip, coins FROM users WHERE user_id = ?", (user_id,)).fetchone()

def update_stat(key):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(f"UPDATE stats SET value = value + 1 WHERE key = '{key}'")
        conn.commit()
