"""SQLite Database Manager for Farmer Transport Tracking & Barcode Stickers.
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = BASE_DIR / "storage" / "transport_tracking.sqlite3"
MIGRATION_PATH = BASE_DIR / "app" / "migrations" / "001_transport_tracking.sql"


def get_db_path() -> Path:
    env_path = os.getenv("TRANSPORT_TRACKING_DB")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def init_transport_db() -> None:
    """Initialize the transport SQLite database and apply migrations."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        if MIGRATION_PATH.exists():
            sql = MIGRATION_PATH.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.commit()


def get_db_connection() -> sqlite3.Connection:
    """Return a configured SQLite connection."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
