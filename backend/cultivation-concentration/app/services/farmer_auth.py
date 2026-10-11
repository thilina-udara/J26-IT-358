"""Persistent accounts and revocable opaque sessions. No raw credentials at rest."""
import hashlib
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import BoundedSemaphore
from uuid import uuid4
from fastapi import HTTPException
from app.migrations import migrate

SESSION_PREFIX = 'cc_session_'
SESSION_PATTERN = re.compile(r'cc_session_[A-Za-z0-9_-]{43}\Z')
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**17, 8, 1
THROTTLE_WINDOW = 900
PASSWORD_WORK = BoundedSemaphore(2)


def now_seconds():
    return int(datetime.now(timezone.utc).timestamp())


def utc_datetime(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc)


def session_ttl():
    try:
        value = int(os.getenv('CULTIVATION_SESSION_TTL_SECONDS', '3600'))
        if not 60 <= value <= 86400:
            raise ValueError('Out of range')
        return value
    except ValueError as exc:
        raise HTTPException(503, 'Farmer session configuration unavailable') from exc


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def derive_password(password, salt):
    # Bound the memory cost of untrusted concurrent password requests per process.
    if not PASSWORD_WORK.acquire(blocking=False):
        raise HTTPException(503, 'Farmer authentication busy; retry later', headers={'Retry-After': '1'})
    try:
        return hashlib.scrypt(password.encode('utf-8'), salt=salt, n=SCRYPT_N,
                              r=SCRYPT_R, p=SCRYPT_P, dklen=32, maxmem=256 * 1024 * 1024)
    except (ValueError, MemoryError) as exc:
        raise HTTPException(503, 'Farmer authentication unavailable') from exc
    finally:
        PASSWORD_WORK.release()


def hash_password(password):
    salt = secrets.token_bytes(16)
    return f'scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${derive_password(password, salt).hex()}'


def verify_password(password, encoded):
    if encoded is None:
        # Spend the same work for unknown identifiers without creating an account.
        secrets.compare_digest(derive_password(password, b'component02dummy'), bytes(32))
        return False
    try:
        algorithm, n, r, p, salt, expected = encoded.split('$')
        if (algorithm, int(n), int(r), int(p)) != ('scrypt', SCRYPT_N, SCRYPT_R, SCRYPT_P):
            raise ValueError('Unsupported password hash')
        salt, expected = bytes.fromhex(salt), bytes.fromhex(expected)
        if len(salt) != 16 or len(expected) != 32:
            raise ValueError('Invalid password hash')
        return secrets.compare_digest(derive_password(password, salt), expected)
    except (ValueError, TypeError) as exc:
        raise HTTPException(503, 'Farmer authentication unavailable') from exc


def unauthorized():
    return HTTPException(401, 'Valid farmer credentials required',
                         headers={'WWW-Authenticate': 'Bearer'})


class AuthStore:
    def __init__(self, path):
        self.path = Path(path)
        migrate(self.path)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def profile(row):
        return dict(farmer_id=row['farmer_id'], login_identifier=row['login_identifier'],
                    authentication_method='session', created_at=utc_datetime(row['created_at']))

    def reserve_attempt(self, scope, key, limit):
        """Persistent fixed-window throttle shared by workers; keys stored as digests."""
        stamp = now_seconds()
        bucket = digest(scope + ':' + key)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM farmer_auth_throttles WHERE window_started_at<=?',
                       (stamp - THROTTLE_WINDOW,))
            row = db.execute('SELECT * FROM farmer_auth_throttles WHERE bucket_digest=?',
                             (bucket,)).fetchone()
            if row and row['attempts'] >= limit:
                raise HTTPException(429, 'Too many authentication attempts; try again later',
                                    headers={'Retry-After': str(max(1, row['window_started_at'] + THROTTLE_WINDOW - stamp))})
            db.execute('''INSERT INTO farmer_auth_throttles VALUES(?,?,1)
                ON CONFLICT(bucket_digest) DO UPDATE SET attempts=attempts+1''', (bucket, stamp))

    def register(self, value, reserved_ids=()):
        password_hash = hash_password(value.password.get_secret_value())
        identity = 'farmer-' + str(uuid4())
        # Never claim a pre-existing research identity or its records.
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            while identity in reserved_ids or ('cultivation_plans' in tables and db.execute(
                'SELECT 1 FROM cultivation_plans WHERE farmer_id=?', (identity,)
            ).fetchone()):
                identity = 'farmer-' + str(uuid4())
            try:
                db.execute('INSERT INTO farmer_accounts(farmer_id,login_identifier,password_hash,created_at) VALUES(?,?,?,?)',
                           (identity, value.login_identifier, password_hash, now_seconds()))
            except sqlite3.IntegrityError as exc:
                raise HTTPException(409, 'Login identifier is unavailable') from exc
            row = db.execute('SELECT * FROM farmer_accounts WHERE farmer_id=?', (identity,)).fetchone()
        return self.profile(row)

    def login(self, value):
        ttl = session_ttl()
        self.reserve_attempt('login', value.login_identifier, 5)
        with self.connection() as db:
            row = db.execute('SELECT * FROM farmer_accounts WHERE login_identifier=?',
                             (value.login_identifier,)).fetchone()
        valid = verify_password(value.password.get_secret_value(), row['password_hash'] if row else None)
        if not valid or row['disabled']:
            raise unauthorized()
        token = SESSION_PREFIX + secrets.token_urlsafe(32)
        stamp = now_seconds()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            # Recheck account status in the transaction that creates the session.
            current = db.execute('SELECT * FROM farmer_accounts WHERE farmer_id=?', (row['farmer_id'],)).fetchone()
            if current is None or current['disabled'] or current['password_hash'] != row['password_hash']:
                raise unauthorized()
            db.execute('DELETE FROM farmer_sessions WHERE expires_at<=?', (stamp,))
            db.execute('INSERT INTO farmer_sessions(token_digest,farmer_id,created_at,expires_at) VALUES(?,?,?,?)',
                       (digest(token), row['farmer_id'], stamp, stamp + ttl))
            db.execute('DELETE FROM farmer_auth_throttles WHERE bucket_digest=?',
                       (digest('login:' + value.login_identifier),))
        return dict(access_token=token, token_type='bearer', expires_in=ttl,
                    expires_at=utc_datetime(stamp + ttl), farmer=self.profile(row))

    def authenticate(self, token):
        if not SESSION_PATTERN.fullmatch(token):
            raise unauthorized()
        with self.connection() as db:
            row = db.execute('''SELECT a.* FROM farmer_sessions s
                JOIN farmer_accounts a ON a.farmer_id=s.farmer_id
                WHERE s.token_digest=? AND s.expires_at>? AND s.revoked_at IS NULL AND a.disabled=0''',
                             (digest(token), now_seconds())).fetchone()
        if row is None:
            raise unauthorized()
        return self.profile(row)

    def logout(self, token):
        if not SESSION_PATTERN.fullmatch(token):
            raise unauthorized()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            stamp = now_seconds()
            row = db.execute('''SELECT s.token_digest FROM farmer_sessions s
                JOIN farmer_accounts a ON a.farmer_id=s.farmer_id
                WHERE s.token_digest=? AND s.expires_at>? AND s.revoked_at IS NULL AND a.disabled=0''',
                             (digest(token), stamp)).fetchone()
            if row is None:
                raise unauthorized()
            db.execute('UPDATE farmer_sessions SET revoked_at=? WHERE token_digest=?', (stamp, digest(token)))
