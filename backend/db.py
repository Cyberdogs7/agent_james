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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS oauth_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT UNIQUE NOT NULL,
                credentials TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def store_oauth_credential(provider, credentials):
    """Store OAuth credentials for a provider. Updates if exists."""
    import json
    with get_db() as conn:
        conn.execute("""
            INSERT INTO oauth_credentials (provider, credentials, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(provider) DO UPDATE SET 
                credentials = excluded.credentials,
                updated_at = CURRENT_TIMESTAMP
        """, (provider, json.dumps(credentials)))
        conn.commit()
        return True


def get_oauth_credential(provider):
    """Get OAuth credentials for a provider. Returns dict or None."""
    import json
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT credentials FROM oauth_credentials WHERE provider = ?",
            (provider,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row["credentials"])
        return None


def delete_oauth_credential(provider):
    """Delete OAuth credentials for a provider."""
    with get_db() as conn:
        conn.execute("DELETE FROM oauth_credentials WHERE provider = ?", (provider,))
        conn.commit()
        return True


def list_oauth_credentials():
    """List all stored OAuth credentials (provider names only)."""
    with get_db() as conn:
        cursor = conn.execute("SELECT provider, created_at, updated_at FROM oauth_credentials")
        return [dict(row) for row in cursor.fetchall()]


if __name__ == '__main__':
    init_db()
    print(f"Database initialized at {DB_PATH}")
