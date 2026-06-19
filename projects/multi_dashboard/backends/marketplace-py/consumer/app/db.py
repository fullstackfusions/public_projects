"""Database module for payment service.

Data contract: Payment service OWNS payment data.
- Payments are stored in local database (not shared with other services)
- Integration happens via events, not shared ORM
"""
import sqlite3
from pathlib import Path


def init_db(db_path: str = "./payments.db") -> sqlite3.Connection:
    """Initialize payment database.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Database connection
    """
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)

    # Create payments table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    print("✅ Payment database initialized")
    return conn
