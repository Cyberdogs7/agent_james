import sqlite3
from pathlib import Path
import os
import contextlib

DB_PATH = Path(__file__).parent.parent / "projects" / "ada.db"

def init_db():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    with get_db() as conn:
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
