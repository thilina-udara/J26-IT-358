# Component 02: cultivation concentration research backend

FastAPI backend for cultivation-plan registration, ownership/privacy controls,
district-specific concentration calculations, K-Means/DBSCAN clustering,
evidence-gated alternative-crop scenarios, personalized planning and prospective evaluation.

- [Setup and development](docs/setup.md)
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
docs/               Three focused guides
```

Older helper filenames remain where current imports/tests depend on their behavior.
Unused generated searches and diagnostics are archived outside Git. A fresh clone
has no access to that archive. Obtain the reviewed private artifact bundle through
an authorized handoff before running the complete model/data integration tests.
Never commit farmer data, live databases, tokens or snapshots.
