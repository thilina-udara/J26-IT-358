# Cultivation database migrations

From `backend/cultivation-concentration`, after backing up the operational database:

```powershell
.venv\Scripts\python.exe -B -m app.migrations --database <path-to-cultivation.sqlite3>
```

The CLI uses `CULTIVATION_PLAN_DB` when `--database` is omitted. Run it before
serving traffic. Local account initialization applies all pending migrations;
plan initialization applies only independent season migration 002. A plan-only
database does not become authentication-ready merely by creating a repository.
Readiness never applies migrations and requires the new column and migration ledger.

Migration 001 creates persistent farmer authentication tables. Migration 002
(`002_farmer_declared_season.sql`) adds a nullable `farmer_declared_season` TEXT
column with a database CHECK allowing only `Maha`, `Yala`, or NULL. On a fresh
database it creates the original plan table before adding the column. The migration
runner executes pending DDL and ledger writes in one `BEGIN IMMEDIATE` transaction;
repeat execution skips versions already recorded.

There is no season backfill, timestamp change, or rewrite of existing JSON history.
Legacy version payloads without the field reconstruct as unknown. Existing
pre-versioning bootstrap still records only the current row at its actual
`updated_at`, never a fabricated historical submission snapshot. New revisions
include the declaration, with actual server receipt/revision timestamps. Cancellation
retains it. Omitted declarations on updates preserve the previous value; explicit
NULL clears it. These changes use the existing plan/version transaction and
optimistic personalized-plan revision check.

The column is a farmer declaration, not a statistical mapping or evidence approval.
It neither adds a model feature provider nor enables historical inference.
