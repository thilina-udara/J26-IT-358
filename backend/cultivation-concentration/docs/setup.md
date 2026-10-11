# Setup and collaborative development

## Fresh clone

Validated on Windows with Python 3.12; other platforms are not yet verified. From the repository root:

```powershell
cd backend/cultivation-concentration
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
```

The lock records the tested development environment, including comparison/test
packages. For a network-isolated machine, obtain the authorized offline wheelhouse
and use `python -m pip install --no-index --find-links <wheelhouse> -r requirements.lock.txt`.
The optional wheelhouse is separate from model inputs and is not part of Git.

## Private artifact inputs

No record-level ASC datasets, live farmer registrations, secrets, model binaries
or local Windows archive paths are distributed through Git. Ask the component
maintainer for authorized access to **pp1_private_artifacts.zip**. Do not upload
this bundle publicly: it includes derived record-level features/predictions and
the 1,450-record historical test reference. No remote hosting URL is currently
configured. An authenticated private transfer is required; a fresh clone alone
cannot run model/data integration checks.

Copy the supplied ZIP to any local location and install it:

```powershell
python scripts/research_artifacts.py --bundle <path-to-pp1_private_artifacts.zip>
python -B -m ml.evaluate_saved
```

The committed `models/artifact_catalog.json` pins the ZIP and each input hash.
Installation validates all payloads before writing, rejects path escapes and
refuses to overwrite differing local files. Never unpickle a model received from
an untrusted source; use only this reviewed bundle/catalog. Installation does not
train or activate predictions. All reconstructed record/model inputs remain ignored.

Full historical reproduction additionally requires authorized original ASC source
and the separately supplied hash-verified `historical_reproduction_private.zip`.
It preserves the complete prior source/evidence bundles and their manifests.
For a full historical reproduction workspace, verify the historical ZIP's SHA-256
against `historical_reproduction_bundle_sha256` in the catalog, then extract only
into a new empty directory. It contains the frozen historical `ml/`, `models/`,
`data/` and old evidence documents. Use the pinned development environment; keep
that workspace private and separate from collaborative backend development.
Archived outputs are not presumed present in Git. Do not rerun old search commands
in the development tree. For future authorized frozen training only:

```powershell
python -m ml.train --dataset <authorized-original-ASC.csv> --output models/local/new_run --model all
```

That command is not part of normal startup/tests and was not executed for cleanup.
It has no hyperparameter search and excludes 2026. Previously exposed 2025 results
remain disclosed. Use a new output directory; never overwrite existing artifacts.

## Backend and configuration

See [optional historical inference provisioning](historical_inference.md) for
trusted artifact loading, availability evidence and the current feature-schema
blocker. Historical saved-model replay does not authorize current farmer risk.

```powershell
$env:CULTIVATION_CORS_ORIGINS = '["http://localhost:5173","http://127.0.0.1:5173"]'
.venv\Scripts\python.exe -B -m app.migrations
.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`GET /health` should return 200. `GET /ready` returns 200 only when the core
database schema, account migration ledger, database write access, authentication
configuration and clustering runtime are available. No real credentials ship with this project.
Use `.env.example` as a key reference; the application reads environment variables,
it does not automatically load that file. Set `CULTIVATION_FARMER_TOKENS`,
`CULTIVATION_ANALYSIS_TOKENS`, `CULTIVATION_ADMIN_TOKENS` and
`CULTIVATION_REVIEWER_TOKENS` with newly generated development-only tokens as needed.
Empty role registries still permit farmer account registration and login. Static
research users remain supported; account sessions do not grant analyst/admin/reviewer roles.
`CULTIVATION_PLAN_DB` and `CULTIVATION_REFERENCE_DB` select new local SQLite files;
default files are under ignored `storage/`. Evidence/approval paths are deployment
inputs, never team member credentials or existing farmer databases.

See [the registered farmer workflow](farmer_workflow.md) for exact requests,
historical-record policy, recoverable submission and end-to-end verification.

The additive account migration uses the same `CULTIVATION_PLAN_DB`. Back up any
existing operational database before deploying. It creates account/session/throttle
tables and a migration ledger, without changing plans, history, or their ownership.
Authentication lazily applies pending migrations for local development; production
should run the explicit migration command before accepting traffic. Health and
OpenAPI checks do not initialize the database.

The migration CLI also reuses the existing `PlanStore` bootstrap to initialize plan
tables and owner-listing indexes. It preserves existing plan data and versioning
semantics, including the existing current-version backfill for pre-versioning rows.
`/ready` never creates a database or applies migrations; its write-access probe is
rolled back without changing rows. A cold, uninitialized database returns 503.

`CULTIVATION_SESSION_TTL_SECONDS` defaults to 3600 (allowed: 60-86400).
`CULTIVATION_LEGACY_FARMER_TOKENS_ENABLED` defaults to `true` for compatibility;
set it to `false` for account-only farmer authentication. Existing analyst/admin/
reviewer tokens are unaffected. See [the authentication API](authentication.md)
for JSON payloads, logout behavior, limits, and deployment requirements.

`CULTIVATION_CORS_ORIGINS` is a JSON array of explicit HTTP(S) origins, default `[]`.
Paths, trailing slashes, wildcard origins and invalid values are rejected at startup.
Restart after changing origins. Allowed headers include Authorization and Content-Type;
GET/POST/PUT/DELETE and preflight OPTIONS are supported. The bearer API does not enable
credential cookies. See [frontend integration examples](frontend_api.md) for pagination,
filtering, response contracts, and error handling.

Optional model artifacts, guideline documents and injected research predictors are
reported separately by `/ready`. Missing optional inputs do not block basic account
and plan operations; ready does not mean risk levels, recommendations or agronomic
guidelines have been validated or activated.

Guidelines preserve checked source URLs and unverified draft claims. Unverified
entries remain inactive. Registered-plan calculations, experimental forecasts and
independent prospective outcomes stay distinct. Matara and Hambantota stay isolated.

## Tests and review gates

```powershell
python -B -m pytest -q -p no:cacheprovider
python -B -c "from app.main import app; from fastapi.testclient import TestClient; assert TestClient(app).get('/health').status_code == 200"
python -B -m ml.evaluate_saved
```

Full tests require the supplied private inputs. They include synthetic small-model
fit/reload regressions; these do not retrain saved research models. K-Means/DBSCAN,
alternative scenarios, planning, ownership/privacy, timestamp integrity, snapshots
and future-registration exclusion are covered. Shared older ML modules remain
because tests/imports depend on their behavior; removing them by filename would
break the retained suite. Backend production risk activation requires separate
approval/evidence and is not part of setup.

Before publishing: inspect staged paths; exclude `data/farmer/`, `data/legacy/`,
private bundles, models, databases and tokens. Previously tracked historical farmer
CSV is removed from the new index only, preserved locally and in the private input
bundle. Its old Git history is not rewritten; removing tracking does not erase
past exposure. Review repository visibility if that history is sensitive.
## Declared-season migration

Apply [migration 002](database_migrations.md) with the existing migration command
before serving traffic. It preserves plans, histories, and timestamps and leaves
legacy seasons NULL. No additional environment variables or private artifacts are
required. After migration, verify with `.venv\Scripts\python.exe -B -m pytest -q`.
