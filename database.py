import sqlite3

conn = sqlite3.connect("app.db", check_same_thread=False)
cursor = conn.cursor()

# ---------- USERS TABLE ----------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

# ---------- USER CONFIG TABLE ----------
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_config (
    user_id INTEGER UNIQUE,
    chat_id TEXT,
    messages TEXT,
    delay INTEGER
)
""")
conn.commit()

# ---------- REGISTER USER ----------
def register_user(username, password):
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        conn.commit()
        return True
    except:
        return False

# ---------- LOGIN VERIFY ----------
def verify_user(username, password):
    cursor.execute(
        "SELECT id FROM users WHERE username=? AND password=?",
        (username, password)
    )
    row = cursor.fetchone()
    return row[0] if row else None

# ---------- GET USER CONFIG ----------
def get_user_config(user_id):
    cursor.execute(
        "SELECT chat_id, messages, delay FROM user_config WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    if row:
        return {"chat_id": row[0], "messages": row[1], "delay": row[2]}
    return None

# ---------- SAVE USER CONFIG ----------
def save_user_config(user_id, chat_id, messages, delay):
    cursor.execute("DELETE FROM user_config WHERE user_id=?", (user_id,))
    cursor.execute(
        "INSERT INTO user_config (user_id, chat_id, messages, delay) VALUES (?, ?, ?, ?)",
        (user_id, chat_id, messages, delay)
    )
    conn.commit()
