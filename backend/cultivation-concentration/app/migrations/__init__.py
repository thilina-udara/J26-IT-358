"""Additive, transactional Component 02 migrations; never rewrite research plans."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS = ((1, '001_farmer_accounts.sql'), (2, '002_farmer_declared_season.sql'))


def migrate(database_path, *, versions=None):
    """Apply all migrations, or an independent subset for repository bootstrap."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    try:
        db.execute('PRAGMA foreign_keys = ON')
        with db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('''CREATE TABLE IF NOT EXISTS component02_schema_migrations (
                version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL
            )''')
            for version, name in MIGRATIONS:
                if versions is not None and version not in versions:
                    continue
                existing = db.execute(
                    'SELECT name FROM component02_schema_migrations WHERE version=?', (version,)
                ).fetchone()
                if existing:
                    if existing[0] != name:
                        raise RuntimeError('Component 02 migration version conflict')
                    continue
                # These migrations contain plain DDL, without triggers or embedded semicolons.
                # executescript would implicitly commit; execute each statement in this transaction.
                script = (Path(__file__).parent / name).read_text(encoding='utf-8')
                for statement in script.split(';'):
                    if statement.strip():
                        db.execute(statement)
                db.execute('INSERT INTO component02_schema_migrations VALUES(?,?,?)',
                           (version, name, datetime.now(timezone.utc).isoformat()))
    finally:
        db.close()
