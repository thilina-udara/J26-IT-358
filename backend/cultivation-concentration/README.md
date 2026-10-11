# Component 02: cultivation concentration research backend

FastAPI backend for cultivation-plan registration, ownership/privacy controls,
district-specific concentration calculations, K-Means/DBSCAN clustering,
evidence-gated alternative-crop scenarios, personalized planning and prospective evaluation.

- [Setup and development](docs/setup.md)
- [Farmer account API and security](docs/authentication.md)
- [Optional historical inference and compatibility gates](docs/historical_inference.md)
- [Frontend API contracts, CORS and readiness](docs/frontend_api.md)
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
