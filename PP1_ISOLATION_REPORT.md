PP1 isolation preparation ? 2026-10-21 (Asia/Colombo)

The new copy is prepared and both development services are running. It is safe to
implement historical trend-based risk analysis in this copy using the PP1
launcher and local resources. That analysis has not been implemented by this setup.

| Item | Verified configuration |
|---|---|
| Working copy | `D:\meeting\J26-IT-358` |
| Python interpreter | `D:\meeting\J26-IT-358\.venv\Scripts\python.exe` |
| Operational SQLite | `D:\meeting\J26-IT-358\backend\cultivation-concentration\storage\pp1\cultivation_plans.sqlite3` |
| Frontend | http://127.0.0.1:3001/crop-planning |
| Backend | http://127.0.0.1:8001 |
| Backend health | `/health`: HTTP 200, healthy |
| Backend readiness | `/ready`: HTTP 200, ready |
| Research demo status | HTTP 200, enabled; reports `storage/pp1/research_demo.sqlite3` |
| Frontend HTTP checks | Home, crop planning, research demo, admin login, admin dashboard: HTTP 200 |
| CORS | Only explicit localhost/127.0.0.1 port 3001 origins allowed; port 3000 rejected |
| Compiled frontend | API is `http://127.0.0.1:8001`; previous port 8000 API absent from checked app chunks |
| Dependency checks | 51 exact lockfile versions installed; `pip check` passed |
| TypeScript | `tsc --noEmit --incremental false` passed |
| Git whitespace check | `git diff --check` passed |

The operational SQLite database is a new independent file, not a hardlink or
alias of the copied or original database. Migrations 1, 2 and 3 are applied.
It starts with zero farmer accounts: register a new presentation account.
Existing copied SQLite files and backups remain preserved. Reference and optional
seeded demo database paths are also restricted to this copy's `storage/pp1`.
The research evaluator itself reads copied datasets/model artifacts; no training
or inference request was needed for these health checks. The optional operational
historical/prospective predictors remain unconfigured.

The copied virtual environment was moved under
`scratch/pp1-isolation/copied-venv-DO-NOT-USE`. A new environment was created from
the system Python, without executing copied launchers. An online dependency
attempt stalled and was stopped. All 51 locked distributions were available in
the quarantined local copy. Package files were checked against their installed
RECORD hashes, repackaged into local wheels, and reinstalled with the new
interpreter's pip. Old executable launchers were omitted and regenerated.
The new launchers contain no original-project path. The local wheels and their
verification manifest are retained for offline recovery.

Active environment files no longer select shared infrastructure. The launcher
clears inherited database/API/Python overrides and fixes SQLite paths, CORS, and
ports. PostgreSQL, Redis, Celery and Docker were not started or connected to for
PP1. The process-tree audit found no PP1 connections to ports 5432, 6379, 55433,
or 56380. The original PostgreSQL service was left alone.

If optional infrastructure is needed later, Compose is isolated as `j26_pp1`:
containers `j26_pp1_postgis` and `j26_pp1_redis`; volumes
`j26_pp1_postgres_data` and `j26_pp1_redis_data`; loopback host ports 55433 and
56380. This configuration was checked as data; Docker was never invoked.

Only this copy's `.next` and `.next-dev` generated frontend caches were removed.
The dev cache was regenerated successfully. Old original-project references
remain only in preserved provenance/backup metadata and archived scratch or
environment files; they are not active PP1 execution paths. Copied setup commands
were updated to this copy and the PP1 ports. The demo-status route now reflects
the configured PP1 database label rather than a stale fixed label.

Windows background reload did not complete reliably in testing, so the final
backend uses explicit restart. Frontend development reloads source changes.
Both start and stop helpers were exercised against PP1 processes. Use
[PP1_RUN.md](PP1_RUN.md) for foreground/background commands and restart steps.

The original `D:\Research\Rese\J26-IT-358` was never targeted for writes.
All 3,255 fingerprinted original files, including its Git metadata, remain
unchanged. All 55 files under this copy's models directory (including 31 model
binaries), all 26 checked dataset files and the preserved copied operational
database are unchanged. No model was overwritten or retrained. No Git commit or
push was made.

Files created or modified (relative to the new working copy):

- `.env`
- `backend/cultivation-concentration/.env`
- `frontend/.env.local`
- `docker-compose.yml`
- `frontend/.env.example`
- `frontend/package.json`
- `frontend/next.config.mjs`
- `frontend/src/app/crop-planning/components/session.tsx`
- `frontend/src/app/crop-planning/lib/admin-session.tsx`
- `frontend/src/app/crop-planning/admin/dashboard/page.tsx`
- `backend/cultivation-concentration/app/research_demo_routes.py`
- `backend/cultivation-concentration/docs/authentication.md`
- `backend/cultivation-concentration/docs/farmer_workflow.md`
- `backend/cultivation-concentration/docs/frontend_api.md`
- `backend/cultivation-concentration/docs/historical_inference.md`
- `scripts/pp1.py`
- `scripts/pp1_local_wheels.py`
- `scripts/start-pp1.ps1`
- `scripts/stop-pp1.ps1`
- `PP1_RUN.md`
- `PP1_ISOLATION_REPORT.md`

Generated local resources also include the fresh `.venv`, the new PP1 SQLite
file, regenerated frontend caches, and logs/backups/wheels/audit JSON files under
`scratch/pp1-isolation/`. Full check evidence is in `health-results.json`,
`service-audit.json`, `integrity-results.json`, `final-integrity-results.json`, and
`local-wheel-manifest.json` there. Original paths in integrity evidence are used
only for read-only verification.
