CREATE TABLE IF NOT EXISTS admin_accounts (
    admin_id TEXT PRIMARY KEY,
    login_identifier TEXT NOT NULL UNIQUE CHECK(login_identifier = lower(trim(login_identifier))),
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'officer')),
    created_at INTEGER NOT NULL,
    disabled INTEGER NOT NULL DEFAULT 0 CHECK(disabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS admin_sessions (
    token_digest TEXT PRIMARY KEY,
    admin_id TEXT NOT NULL REFERENCES admin_accounts(admin_id),
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL CHECK(expires_at > created_at),
    revoked_at INTEGER
);

CREATE INDEX IF NOT EXISTS admin_sessions_owner ON admin_sessions(admin_id);
CREATE INDEX IF NOT EXISTS admin_sessions_expiry ON admin_sessions(expires_at);
