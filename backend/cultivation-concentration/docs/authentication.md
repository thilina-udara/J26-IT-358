> PP1 working copy: use the isolated launcher and URLs in [PP1_RUN.md](../../../PP1_RUN.md).

# Farmer accounts and authentication

Farmer accounts extend the existing Component 02 application. They use the same
SQLite file as cultivation plans; they do not replace plan services or research
role registries. `/docs` exposes the updated OpenAPI contracts.

## Endpoints

| Endpoint | Request | Success |
| --- | --- | --- |
| `POST /auth/register` | JSON `login_identifier`, `password` | 201, stable `farmer_id` and public account metadata |
| `POST /auth/login` | JSON `login_identifier`, `password` | 200, `access_token`, `token_type`, `expires_in`, UTC `expires_at`, public farmer metadata |
| `GET /auth/me` | `Authorization: Bearer <access_token>` | 200, verified farmer metadata |
| `POST /auth/logout` | `Authorization: Bearer <access_token>` | 204, current session revoked |

Registration does not automatically log in. Example fictional registration body:

```json
{
  "login_identifier": "fictional-demo-farmer",
  "password": "A fictional development passphrase!"
}
```

Use the same fields to log in, then send the returned credential only in the
Authorization header. Never place it in a URL, logs, committed configuration, or
analytics. Auth responses, including errors, have `Cache-Control: no-store`.
Validation errors omit supplied field values so passwords are not echoed.

Login identifiers are 3-100 ASCII letters, digits, or `. _ @ + -`. The server
trims their surrounding whitespace and lowercases them. Identifiers are unique
after normalization. They are usernames; an email-looking identifier does not
establish email ownership. Registration rejects duplicate identifiers with 409.
Invalid bodies return 422; extra fields such as `farmer_id` or `role` are forbidden.

Registration passwords must be 15-128 characters. Spaces and Unicode are allowed;
passwords are never trimmed, normalized, or truncated. Unknown accounts, incorrect
passwords, and disabled accounts return the same 401 message. Missing, malformed,
expired, revoked, or disabled-account credentials also return 401.

## Passwords and sessions

Passwords use Python/OpenSSL `hashlib.scrypt`, with N=131072, r=8, p=1, a fresh
16-byte random salt, and a 32-byte derived key. Only the versioned hash, parameters,
and salt are stored. This follows OWASP's recommended scrypt fallback configuration:
[OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
No additional Python dependencies or token-signing secrets are required.

Credentials are opaque `cc_session_` bearer tokens containing 32 random bytes
(256 bits). The database stores only SHA-256 token digests. Every authenticated
request checks persisted expiry, revocation, and account status. Default lifetime
is one hour; there is no sliding expiry or refresh token. Re-login after expiry.
Database compromise does not expose raw sessions, but database write access is
still privileged and must be protected.

Logout revokes the supplied session immediately for subsequent requests, including
after application restart. Other sessions remain valid. Repeated logout of a revoked
session returns 401. Already-authorized in-flight operations can complete.
Sessions remain valid across restarts until their original expiry or revocation.
Expired rows are removed on successful login. Disabling an account in the database
blocks its sessions; an account-management API is outside this change.

The `cc_session_` prefix is reserved for account sessions. Credentials with this
prefix never fall back to legacy tokens, preventing expired/revoked sessions from
being accepted through the compatibility registry. Do not provision static research
tokens using that prefix.

## Plan identity and research compatibility

`POST /api/cultivation-plans` and `PUT /api/cultivation-plans/{plan_id}` now accept
bodies without `farmer_id`. The server constructs the persisted identity from verified
credentials. Existing clients may still submit it as an assertion; a mismatched value
returns 403. Plan IDs, historical versions, cancellation, ownership checks, and
privacy suppression are unchanged. Cross-farmer reads/updates/deletes remain 404.
The existing farmer-workflow submission already derives its farmer ID server-side.

The default compatibility setting accepts `CULTIVATION_FARMER_TOKENS` alongside
account sessions. `/auth/me` identifies these users with
`authentication_method: legacy_research_token`, null login identifier and creation
time. Static research tokens cannot log in or be revoked by `/auth/logout`; remove
them from their registry to revoke them. Set
`CULTIVATION_LEGACY_FARMER_TOKENS_ENABLED=false` for account-only deployment.

Accounts receive generated `farmer-<UUID>` IDs. Registration never links an account
to historical plans by username or submitted ID. Existing research identities and
their records retain their ownership; any future account linking needs a separate,
verified administrative workflow. Analyst, administrator and reviewer authentication
continues to use the existing registries. Account sessions grant none of those roles.
Malformed or ambiguous research role configuration continues to fail closed with 503.

## Database migration and startup

From the repository root, run:

```powershell
Set-Location D:\meeting\J26-IT-358\backend\cultivation-concentration
$env:CULTIVATION_PLAN_DB = 'storage/pp1/cultivation_plans.sqlite3'
$env:CULTIVATION_SESSION_TTL_SECONDS = '3600'
$env:CULTIVATION_LEGACY_FARMER_TOKENS_ENABLED = 'false'
.venv\Scripts\python.exe -B -m app.migrations
.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

To select a database explicitly: `python -B -m app.migrations --database <path>`.
The application reads process environment variables; copying `.env.example` alone
does not load them. The migration and application must target the same database.
Set legacy mode to `true` if pre-provisioned research farmers must remain active.
For browser integration, configure `CULTIVATION_CORS_ORIGINS` before startup and
use the [existing cultivation endpoints and listing API](frontend_api.md).

Migration `001_farmer_accounts.sql` adds:

- `farmer_accounts`: generated ID, unique normalized identifier, password hash,
  creation timestamp, disabled flag.
- `farmer_sessions`: token digest, account foreign key, creation/expiry/revocation
  timestamps, owner and expiry indexes.
- `farmer_auth_throttles`: digested rate-limit bucket keys and window counters.
- Runner ledger `component02_schema_migrations`: applied version/name/timestamp.

The runner applies DDL and records its version in one `BEGIN IMMEDIATE` transaction.
It is idempotent, serializes concurrent migration attempts, and rolls back on schema
conflicts. The account migration does not modify cultivation, personalized,
expert-governance or prospective records. The CLI also invokes the existing plan
bootstrap to initialize missing plan tables, owner-listing indexes and the existing
current-version backfill for pre-versioning rows. Existing plans have no new farmer-account foreign key because
pre-provisioned research identities must remain valid. Take a consistent database
backup before production deployment. Do not drop authentication tables to roll back;
old plan data does not require reverting this additive migration.

## Abuse controls and deployment limits

Login attempts are limited to five per normalized identifier in a 15-minute fixed
window. Successful login clears that identifier's counter. Both known and unknown
identifiers use the same check and password-hashing work. Registration and login
also share a limit of 40 requests per client IP per 15 minutes, checked before
password hashing. Counters persist across application restarts and are shared by
workers using the same database. A 429 response supplies `Retry-After`.

At most two password hashes run concurrently per process (approximately 128 MiB
per hash). Saturated hashing returns 503 with `Retry-After: 1`. Allow appropriate
memory per worker. This bounds local hashing work; it is not a substitute for
deployment-level request limits.

Client addresses come from the ASGI request, not directly from user-supplied
`X-Forwarded-For`. Configure Uvicorn/reverse-proxy trust for actual proxy addresses
only. Shared NAT/proxy addresses may share the IP limit. Distributed abuse and
identifier lockout attacks need edge controls and monitoring. Malformed requests
rejected during validation do not consume these application counters.

Public deployments require HTTPS and protection/redaction of Authorization headers,
request bodies, SQLite files, and backups. The local startup command binds loopback;
it does not provide TLS. Browser clients should avoid persistent bearer-token storage
accessible to injected scripts. This API does not issue cookies.

Legacy role credentials remain externally configured static secrets with their
existing lifecycle. Password recovery, verified email/phone ownership, breached-
password screening, MFA, security-event monitoring, and global session revocation
are not implemented here. SQLite storage is not encrypted at rest by this application.

## Verification

```powershell
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_farmer_auth.py
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Tests use fictional identities and temporary SQLite databases. The complete existing
suite still requires the authorized private research artifacts described in setup.
