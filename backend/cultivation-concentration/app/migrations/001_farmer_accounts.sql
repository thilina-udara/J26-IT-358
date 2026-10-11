CREATE TABLE farmer_accounts (
    farmer_id TEXT PRIMARY KEY,
    login_identifier TEXT NOT NULL UNIQUE CHECK(login_identifier = lower(trim(login_identifier))),
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    disabled INTEGER NOT NULL DEFAULT 0 CHECK(disabled IN (0, 1))
);

CREATE TABLE farmer_sessions (
    token_digest TEXT PRIMARY KEY,
    farmer_id TEXT NOT NULL REFERENCES farmer_accounts(farmer_id),
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL CHECK(expires_at > created_at),
    revoked_at INTEGER
);
CREATE INDEX farmer_sessions_owner ON farmer_sessions(farmer_id);
CREATE INDEX farmer_sessions_expiry ON farmer_sessions(expires_at);

CREATE TABLE farmer_auth_throttles (
    bucket_digest TEXT PRIMARY KEY,
    window_started_at INTEGER NOT NULL,
    attempts INTEGER NOT NULL CHECK(attempts > 0)
);
