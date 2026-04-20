import sqlite3
from pathlib import Path
import os
import contextlib

DB_PATH = Path(__file__).parent.parent / "projects" / "ada.db"

def init_db():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jules_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                api_key TEXT UNIQUE NOT NULL,
                concurrent_sessions_limit INTEGER,
                total_sessions_limit INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

@contextlib.contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_all_accounts():
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM jules_accounts ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def add_account(api_key, name=None, concurrent_limit=None, total_limit=None):
    with get_db() as conn:
        try:
            cursor = conn.execute("""
                INSERT INTO jules_accounts (api_key, name, concurrent_sessions_limit, total_sessions_limit)
                VALUES (?, ?, ?, ?)
            """, (api_key, name, concurrent_limit, total_limit))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None # API key already exists

def update_account(account_id, api_key, name=None, concurrent_limit=None, total_limit=None):
    with get_db() as conn:
        conn.execute("""
            UPDATE jules_accounts
            SET api_key = ?, name = ?, concurrent_sessions_limit = ?, total_sessions_limit = ?
            WHERE id = ?
        """, (api_key, name, concurrent_limit, total_limit, account_id))
        conn.commit()
        return True

def delete_account(account_id):
    with get_db() as conn:
        conn.execute("DELETE FROM jules_accounts WHERE id = ?", (account_id,))
        conn.commit()
        return True

if __name__ == '__main__':
    init_db()
    print(f"Database initialized at {DB_PATH}")
