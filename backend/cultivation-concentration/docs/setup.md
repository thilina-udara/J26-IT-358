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

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`GET /health` should return 200. No real credentials ship with this project.
Use `.env.example` as a key reference; the application reads environment variables,
it does not automatically load that file. Set `CULTIVATION_FARMER_TOKENS`,
`CULTIVATION_ANALYSIS_TOKENS`, `CULTIVATION_ADMIN_TOKENS` and
`CULTIVATION_REVIEWER_TOKENS` with newly generated development-only tokens as needed.
An empty token configuration permits health checks but not authenticated operations.
`CULTIVATION_PLAN_DB` and `CULTIVATION_REFERENCE_DB` select new local SQLite files;
default files are under ignored `storage/`. Evidence/approval paths are deployment
inputs, never team member credentials or existing farmer databases.

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
