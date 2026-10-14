# Component 02: cultivation concentration research backend

FastAPI backend for cultivation-plan registration, ownership/privacy controls,
district-specific concentration calculations, K-Means/DBSCAN clustering,
evidence-gated alternative-crop scenarios, personalized planning and prospective evaluation.

- [Setup and development](docs/setup.md)
- [Farmer account API and security](docs/authentication.md)
- [Optional historical inference and compatibility gates](docs/historical_inference.md)
- [Frontend API contracts, CORS and readiness](docs/frontend_api.md)
- [Frontend evidence states and privacy](docs/frontend_evidence.md)
- [Methodology and limitations](docs/methodology.md)
- [Model comparison](docs/model_comparison.md)

Selected historical XGBoost: **84.30% pooled accuracy; macro F1 0.7182**.
These are retrospective research-label results, not verified live farmer risk,
market oversupply or crop-profitability accuracy. The API does not automatically
activate the selected experimental model. Matara and Hambantota remain separate.

```text
app/                 FastAPI routes, schemas and backend services
ml/train.py          Frozen training command; no new hyperparameter search
ml/evaluate_saved.py Matched-cohort prediction replay without training
ml/preprocessing/    Shared preprocessing and categorical model dependencies
ml/training/         Retained tested helpers and comparison implementations
models/artifact_catalog.json  Trusted private-bundle hashes, not model binaries
data/guidelines/     Source-traceable guidelines; unverified claims remain inactive
scripts/             Verified private artifact installation
tests/              Full functional and methodological regression suite
docs/               Setup, API contracts, security and research methodology
```

Older helper filenames remain where current imports/tests depend on their behavior.
Unused generated searches and diagnostics are archived outside Git. A fresh clone
has no access to that archive. Obtain the reviewed private artifact bundle through
an authorized handoff before running the complete model/data integration tests.
Never commit farmer data, live databases, tokens or snapshots.

Frontend integration reuses bearer account sessions and existing plan/workflow APIs.
The [registered farmer workflow](docs/farmer_workflow.md) documents the full journey,
historical records, evidence states and analysis-failure recovery.
`GET /api/cultivation-plans` provides a paginated, filtered list of the authenticated
farmer's current plans. Configure the explicit `CULTIVATION_CORS_ORIGINS` JSON array
before startup; cross-origin access defaults to disabled. Run the database migration
command before serving traffic. `/health` remains liveness; `/ready` checks essential
database/authentication/runtime dependencies and reports optional research capabilities
without asserting model or agricultural validation.
## Versioned farmer declarations

Cultivation plans now retain optional `farmer_declared_season` (`Maha`, `Yala`, or
null), including revisions and cancellation. Workflow submission retains its
existing `season` input. Analysis overrides are explicit and do not edit saved
declarations. These are unverified context, not statistical-season evidence or
validated live risk. Run the existing migration command before startup; see
[additive migration details](docs/database_migrations.md) and
[workflow examples](docs/farmer_workflow.md).

## Historical research simulation

The isolated `/api/research-demo/evaluate` workflow returns caller scenario inputs
and previously reported frozen benchmark metadata. It does not read private
historical CSV/model files or operational farmer plans. Enable it locally
with `CULTIVATION_RESEARCH_DEMO_ENABLED=true`. Normal farmer creation still requires
future planting dates. The demo supports planting/cutoff dates from 2025-01-01
through 2026-08-31. `decision_cutoff` is optional and defaults to planting date;
it means the start of that day in Asia/Colombo and cannot follow planting. This
frozen replay currently requires decision and planting in the same calendar year;
verified season/reporting-year mappings are missing.

Example request:

```json
{
  "district": "Hambantota", "crop": "Mung Beans", "season": "Yala",
  "land_size_acres": 3.5, "planting_date": "2025-06-16",
  "expected_harvest_date": "2025-08-25", "decision_cutoff": "2025-06-10",
  "model_name": "XGBoost"
}
```

All peer counts, acreage, derived historical features, coverage, proxy categories
and class probabilities are withheld for every cohort, including zero/singletons.
Publication permission is not established for the historical source. An enable
flag, authentication or historical age does not approve disclosure. Repeated
queries and cutoff/acreage comparisons therefore have no private-data dependency.
Only caller inputs and previously reported frozen metrics are returned; no public
inference is performed. Responses use a closed schema with explicit disclosure
statuses and neutral reason codes. There is no public raw export/comparison API.

The internal evaluator remains available for authorized offline private research.
It separates harvest-window membership from actual observation availability and
the assumed earlier-planted replay cohort. Original submission/observation
timestamps are absent; no zero-leakage claim is justified. It retains frozen
model/feature semantics and never activates current farmer recommendations.
The Research Lab compares caller scenario dates only. Exact 2026 evaluation
metrics are unavailable and are not replaced with 2025 metrics.

See the [research disclosure contract](docs/research_demo_disclosure.md) for
temporal semantics, model boundaries, regression coverage and limitations.

For disposable synthetic storage tests only, the guarded seed command requires
an explicit demo flag and the reserved `research_demo.sqlite3` filename:

```powershell
$env:CULTIVATION_DEMO_DATA_ENABLED = 'true'
..\..\.venv\Scripts\python.exe -B -m app.seed_demo_data `
  --database storage/research_demo.sqlite3 `
  --owner-id fictional-test-owner --from 2026-01-01 --to 2026-03-31 --reset
```

It refuses the configured operational database and existing non-demo records.
Seeded databases carry a synthetic marker and cannot serve operational farmer
workflows, including after renaming. The historical simulation does not consume
these synthetic database records. No normal app startup runs the seeder.

## Explicit frontend CORS configuration

Cross-origin access defaults to disabled. The server uses only the exact configured
origins, without expanding ports or changing behavior under pytest. For Next.js
local development, set this server-side value (also in `.env.example`):

```dotenv
CULTIVATION_CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

Other ports/origins require explicit configuration. Wildcards and credentialed
origin URLs are rejected; browser credentialed CORS and private-network CORS are
disabled. Farmer requests use bearer authorization with `credentials: omit`.

Planning clients must use owned saved details and backend-approved activities.
Absent approval requires a partial/empty state without invented dates or quantities.
