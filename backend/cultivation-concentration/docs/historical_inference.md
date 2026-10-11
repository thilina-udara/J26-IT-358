# Optional historical inference provisioning

The existing `HistoricalPredictor` and farmer workflow are reused. No historical
HTTP endpoint existed separately: historical context is the `historical_prediction`
field of owned workflow submission and analysis. Existing authentication, role
separation and cross-farmer 404 protection apply. No new endpoint or file-upload API
is introduced. Current concentration/risk and recommendations retain their own
evidence gates, independent of any historical proxy category.

## Available artifact inspection

The selected XGBoost pipeline in
`models/experimental/historical_feature_improvement/v1_20261009` is hash-catalogued,
and existing tests replay saved predictions. Its 15 features include declared land,
planting/harvest months, overlap, expected production and historical window summaries.
The existing operational historical predictor requires 8 different official
district/crop/season features: `Prior_History_Count`, `Historical_Mean_Land_Acres`,
`Historical_Mean_Production_kg`, `Historical_Mean_Yield_kg_per_Acre`, `District`,
`Crop`, `Season`, `Target_Year`. Replay does not establish interchangeability.

Consequently the currently catalogued `selected_xgboost_2024` **cannot be activated
through this predictor**. Provisioning reports an incompatible historical feature
schema before deserialization. No missing window features, observations or calendar
mapping are synthesized. There is no approved runtime observation provider or
planting-to-statistical-year mapping bundled with the application.

## Loading and trust boundary

`create_app` provisions once per application instance when no predictor is explicitly
injected. Empty `CULTIVATION_HISTORICAL_MODEL` disables provisioning. The only
allowlisted alias is `selected_xgboost_2024`; it resolves to a fixed relative model,
schema and environment within Component 02. Absolute paths, other model families,
other years and alternate catalogs are not configurable. Trusted hashes come from
the existing repository-owned `models/artifact_catalog.json`.

The loader reads and verifies model, schema and environment bytes, checks exact
feature order and Python/numpy/pandas/scikit-learn/XGBoost versions, and validates a
hash-pinned server-owned JSON evidence manifest before calling `joblib.load` on the
verified in-memory bytes. It then requires a sklearn Pipeline with XGBClassifier,
matching feature names and class encoding `[0,1,2]`. No pickle is accepted from an
HTTP caller; JSON evidence cannot select executable artifacts. Hash verification
does not sandbox pickle execution: the catalog, component files and deployment
configuration must be controlled by trusted operators. A writable catalog is not
a trusted approval mechanism.

Failure leaves optional inference unavailable and core application startup intact.
Responses contain safe reasons, never local paths or observation data. `/ready`
reports this optional predictor as unavailable without blocking core readiness.
A provisioned predictor remains `configured_not_validated`: readiness is not a
claim of prediction coverage or agricultural validity. Explicit injected predictors
retain the existing test/research integration path.

## Evidence manifest contract

This is a server-only JSON document, not a public request schema. Record its
SHA-256 independently after review; do not compute approval automatically from an
unreviewed file at application startup. Required top-level fields:

| Field | Meaning |
| --- | --- |
| `label_definition` | Exactly `official_equal_weight_cumulative_ratios_0.75_1.25_v1` |
| `trained_through` | 2024 for the allowlisted alias |
| `model_sha256` | Exact trusted pipeline digest from the catalog |
| `model_available_at` | Actual timezone-aware model availability timestamp |
| `coverage_through` | Integer last covered historical year |
| `provenance_verified` | Boolean true after independent review |
| `evidence_reference` | Review/source reference |
| `observations` | Official district/crop/season/year measurements with lineage |
| `season_year_mappings` | Explicit reviewed planting intervals and statistical years |

Each observation requires `district`, `crop`, `season`, integer `year`,
`land_acres`, `production_kg`, `observation_end` (ISO date), `available_at` (aware
ISO timestamp), `provenance_verified` (true), and `evidence_reference`. Observation
completion cannot precede its claimed year or follow actual availability. The
existing predictor validates positive area, finite nonnegative measurements, unique
historical keys, matching district/crop/season, preceding-year coverage and actual
availability at the requested cutoff. Target/future-year observations never enter
features. Do not use a CSV row year as a fabricated publication timestamp.

Each mapping requires `district`, `crop`, `season`, `planting_start`,
`planting_end` (inclusive ISO dates), integer `target_year`, `available_at` (aware
ISO timestamp), `verified` (true), and `reference`. Exactly one entry must match
the plan. Ambiguous or absent entries yield insufficient evidence. For conservative
availability the manifest mapping set is usable only after the latest mapping
availability timestamp; use independently reviewed, coherent mapping vintages.
Calendar planting year is never inferred as the statistical Maha/Yala year.

Prediction cutoffs must be aware, no later than now and before planting. Targets
must be outside model training and have latest prior-year group observations.
Missing or late evidence, invalid outputs and dependency failures return
`insufficient_evidence` with null risk. A compatible result is explicitly
`historical_proxy_prediction`, scoped to district/crop/season, never current overlap,
validated market loss or a regional harvest-window prediction.

## Exact local commands

Use the existing tested environment and an authorized private bundle:

```powershell
Set-Location D:\Research\Rese\J26-IT-358\backend\cultivation-concentration
# On first setup, use Python 3.12.0 and the existing lock file:
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
# Only an authorized local bundle, never an arbitrary downloaded pickle:
.venv\Scripts\python.exe -B -m scripts.research_artifacts --bundle 'D:\authorized-private-handoff\pp1_private_artifacts.zip'
$env:CULTIVATION_HISTORICAL_MODEL = 'selected_xgboost_2024'
# Set these only when an independently reviewed availability manifest exists:
$env:CULTIVATION_HISTORICAL_EVIDENCE = 'D:\authorized-private-handoff\historical-availability.json'
$env:CULTIVATION_HISTORICAL_EVIDENCE_SHA256 = '<independently recorded SHA-256>'
.venv\Scripts\python.exe -B -m app.migrations
.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

These commands configure provisioning, **not successful inference with the current
incompatible bundle**. Leave the model variable unset/empty for ordinary backend
operation. A reviewed compatible artifact would need a separate approved catalog
and feature-contract change; do not relabel the 15-feature model as the 8-feature
model or retrain it as part of this integration. Restart to change provisioning.

Use existing farmer login, then `POST /api/farmer-workflow/analyze` with
`{"plan_id":"<owned ID>","season":"Maha"}`. Inspect `historical_prediction.reason`;
current `assessment.risk_level` remains independently evidence-gated.

```powershell
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_historical_runtime.py
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

New loader tests use fictional pinned bytes and mocked deserialization/model output,
without training or real observations. Existing saved-pipeline replay tests cover
the actual private model, but do not establish compatibility or operational evidence.
No reported metrics, models, datasets, labels, agricultural approvals or current-risk
thresholds change.
