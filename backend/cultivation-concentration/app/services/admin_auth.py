"""Admin & Agricultural Officer authentication service and data store."""
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException

from app.services.farmer_auth import (
    digest,
    hash_password,
    verify_password,
    now_seconds,
    utc_datetime,
    session_ttl,
    unauthorized,
)
from app.migrations import migrate

ADMIN_SESSION_PREFIX = "cc_admin_session_"
ADMIN_SESSION_PATTERN = re.compile(r"cc_admin_session_[A-Za-z0-9_-]{43}\Z")


def unauthorized_admin():
    return HTTPException(
        401,
        "Valid administrative or officer credentials required",
        headers={"WWW-Authenticate": "Bearer"},
    )


class AdminStore:
    def __init__(self, path):
        self.path = Path(path)
        migrate(self.path)
        self._ensure_default_officer()

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def _ensure_default_officer(self):
        """Seed a default agricultural officer account if none exists."""
        with self.connection() as db:
            row = db.execute("SELECT 1 FROM admin_accounts LIMIT 1").fetchone()
            if not row:
                # Default administrative officer account for local development/demonstration
                admin_id = "admin-" + str(uuid4())
                pwd_hash = hash_password("AgriOfficer@2026")
                db.execute(
                    """INSERT INTO admin_accounts(admin_id, login_identifier, password_hash, full_name, role, created_at, disabled)
                       VALUES (?, ?, ?, ?, ?, ?, 0)""",
                    (admin_id, "agriofficer", pwd_hash, "District Agriculture Officer", "officer", now_seconds()),
                )
                admin_root_id = "admin-" + str(uuid4())
                admin_root_hash = hash_password("AdminRoot@2026!")
                db.execute(
                    """INSERT INTO admin_accounts(admin_id, login_identifier, password_hash, full_name, role, created_at, disabled)
                       VALUES (?, ?, ?, ?, ?, ?, 0)""",
                    (admin_root_id, "systemadmin", admin_root_hash, "Senior Research Administrator", "admin", now_seconds()),
                )

    @staticmethod
    def profile(row):
        return {
            "admin_id": row["admin_id"],
            "login_identifier": row["login_identifier"],
            "full_name": row["full_name"],
            "role": row["role"],
            "authentication_method": "admin_session",
            "created_at": utc_datetime(row["created_at"]),
        }

    def login(self, identifier: str, password_raw: str):
        ttl = session_ttl()
        norm_id = identifier.strip().lower()
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM admin_accounts WHERE login_identifier=?",
                (norm_id,),
            ).fetchone()

        valid = verify_password(password_raw, row["password_hash"] if row else None)
        if not valid or (row and row["disabled"]):
            raise unauthorized_admin()

        token = ADMIN_SESSION_PREFIX + secrets.token_urlsafe(32)
        stamp = now_seconds()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT * FROM admin_accounts WHERE admin_id=?", (row["admin_id"],)
            ).fetchone()
            if not current or current["disabled"]:
                raise unauthorized_admin()
            db.execute("DELETE FROM admin_sessions WHERE expires_at<=?", (stamp,))
            db.execute(
                "INSERT INTO admin_sessions(token_digest, admin_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (digest(token), row["admin_id"], stamp, stamp + ttl),
            )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": ttl,
            "expires_at": utc_datetime(stamp + ttl),
            "admin": self.profile(row),
        }

    def authenticate(self, token: str):
        if not ADMIN_SESSION_PATTERN.fullmatch(token):
            raise unauthorized_admin()
        with self.connection() as db:
            row = db.execute(
                """SELECT a.* FROM admin_sessions s
                   JOIN admin_accounts a ON a.admin_id = s.admin_id
                   WHERE s.token_digest = ? AND s.expires_at > ? AND s.revoked_at IS NULL AND a.disabled = 0""",
                (digest(token), now_seconds()),
            ).fetchone()
        if not row:
            raise unauthorized_admin()
        return self.profile(row)

    def logout(self, token: str):
        if not ADMIN_SESSION_PATTERN.fullmatch(token):
            raise unauthorized_admin()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            stamp = now_seconds()
            db.execute(
                "UPDATE admin_sessions SET revoked_at=? WHERE token_digest=?",
                (stamp, digest(token)),
            )
