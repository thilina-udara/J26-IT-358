# Historical simulation scientific audit

Current HTTP disclosure policy has been tightened by the
[P0/P1 remediation](security_privacy_blocker_fixes.md). Scenario counts, labels
and feature values below describe retained private retrospective research and
the earlier audited behavior; they are not fields currently released by the
Research Demo API. Frozen models, labels and benchmark metrics remain unchanged.

Reviewed 2026-10-14 on `feature/dasuni/cultivation-concentration-new`.
Existing working-tree work was preserved. No research model was retrained, no
frozen source, label, artifact or metric was edited, and nothing was staged,
committed or pushed.

## Root cause and the two scenarios

The previous evaluator in `app/services/historical_research_evaluator.py` used
the selected planting date for two roles: the farmer's planting input and the
simulated information cutoff. Its peer predicate was:

```text
District == scenario district AND Crop == scenario crop AND Season == scenario season
AND Year == planting calendar year
AND Planting_Date < scenario planting date
AND Expected_Harvest_Date >= scenario planting date
AND abs(Expected_Harvest_Date - scenario harvest date) <= 14 days
```

No submission timestamp or observation availability timestamp was read. The
original CSV's exact columns are Record_ID, District, Year, Season, Crop,
Planting_Date, Land_Size_Acres, Expected_Harvest_Date,
Expected_Yield_kg_per_Acre, Expected_Production_kg. It has 15,090 rows.

For Hambantota/Mung Beans/Yala, 3.5 acres, harvest 2025-08-25, the window is
2025-08-11 through 2025-09-08 inclusive. The original behavior was reproduced:

| Scenario | Planting/default cutoff | Peer records | Peer acres | Acres including scenario | Model overlap count | Proxy | Original probabilities Low/Medium/High |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| A | 2025-06-10 | 83 | 218.5 | 222.0 | 84 | Low | .9136 / .0844 / .0020 |
| B | 2025-06-16 | 214 | 549.0 | 552.5 | 215 | High | .0394 / .0309 / .9298 |

Exactly 131 additional records, totaling 330.5 acres, have planting dates from
June 10 through June 15. Same-day planting is excluded by the strict `<` rule.
All 14 other model inputs were identical; planting month is June in both cases.
**Only Overlap_Plan_Count changed.** The classifier receives counts including
the simulated plan, whereas displayed peer counts exclude it. Window acreage
is a diagnostic and historical label component, not a selected XGBoost feature.

| Newly included planting date | Added records | Added acres |
| --- | ---: | ---: |
| 2025-06-10 | 18 | 43.0 |
| 2025-06-11 | 23 | 48.0 |
| 2025-06-12 | 22 | 63.0 |
| 2025-06-13 | 27 | 71.0 |
| 2025-06-14 | 24 | 60.5 |
| 2025-06-15 | 17 | 45.0 |

This is a changing retrospective cohort, not evidence of a real six-day change
in observed market risk. None of those plans is provably observable at either
cutoff from this dataset. Their availability is **unknown**, not demonstrated
unavailable. Dataset presence and earlier planting cannot establish availability.

The corrected replay retains these counts and Low/High classes. Its historical
production feature now sums recorded production, matching training:
251,552.2222 kg rather than the old 236,932.7778 kg. Own production is missing,
with frozen pipeline missing-value handling, rather than an unsupported yield
estimate. Revised probabilities are .9205/.0777/.0019 and .0541/.0364/.9095.
These are changed scenario inputs, not changed research evaluation metrics.
With explicit `decision_cutoff=2025-06-10`, both June planting dates produce
identical features and proxy predictions. Changing planting month still changes
the Planting_Month feature at the same cutoff.

A read-only application of the existing historical acreage rule gives reference
P33=320.81 and P67=737.97 acres for this cohort. A's 222 acres falls below P33;
B's 552.5 acres lies between the bounds. That retrospective rule would therefore
assign Low and Medium, whereas the classifier predicts Low and High. This is an
ML approximation discrepancy on a hypothetical scenario, not an independent
ground-truth outcome or a newly measured research error rate. It was not used to
change labels, tune thresholds, retrain, alter saved metrics or promote risk.
The model excludes target overlap acreage and can disagree with the direct rule.

## Three separate scientific concepts

1. **Harvest-window concentration:** matching expected harvest anchors within
   inclusive +/-14 days, same district/crop/declared season. This is a 29-day
   window of recorded intentions, not actual harvest intervals or actual supply.
   Historical CSV regions and farmer identities are absent. The dataset-only
   view includes every recorded year matching the full harvest date; for these
   scenarios it contains 414 records and 1,037 acres.
2. **Decision-time availability:** the exact record version requires an aware
   availability timestamp, source/version evidence and verification. Original
   historical records have no such evidence. The known-at-cutoff view contains
   zero provably available records; this means insufficient evidence, not Low.
   Proven available plans can have future planting dates and remain visible in
   this view, independently of the retrospective planting predicate.
3. **Historical ML proxy:** the frozen classifier predicts an experimental
   acreage-percentile label. The replay explicitly assumes availability for
   unknown records. Its result never supplies a validated current-risk category
   or automatically enables recommendations.

The response uses `historical_proxy_label`; `predicted_risk_level` remains only
a compatibility alias inside the research prediction envelope. Operational
status is always `risk_level_not_yet_validated`.

## Frozen model and feature contract

The exact selected XGBoost order, verified against the joblib pipeline and
`feature_schema.json`, is:

| Position | Feature |
| ---: | --- |
| 1 | District |
| 2 | Crop |
| 3 | Season |
| 4 | Land_Size_Acres |
| 5 | Planting_Month |
| 6 | Harvest_Month |
| 7 | Overlap_Plan_Count |
| 8 | Own_Expected_Production_kg |
| 9 | Past_Window_Count |
| 10 | Past_Mean_Window_Acres |
| 11 | Past_Mean_Window_Production_kg |
| 12 | Previous_Year_Window_Mean_Acres |
| 13 | Previous_Year_Window_Median_Acres |
| 14 | Previous_Year_Window_Std_Acres |
| 15 | Previous_Year_Mean_Plan_Acres |

CatBoost has the same 15 inputs. Random Forest, LinearSVC and RBF SVC use the
first 11. Inference selects and orders the actual saved contract and maps
probabilities through `classes_`, not an assumed universal ordering. Integer
classes 0/1/2 mean Low/Medium/High; SVM class ordering is High/Low/Medium.
SVM pipelines do not supply class probabilities.

This research demo is separate from the optional operational
`historical_prediction.py::HistoricalPredictor`, which expects eight annual
district/crop/season inputs and a different label definition. The existing
`historical_runtime.py` provisioner correctly refuses the selected 15-input
XGBoost artifact for that eight-input contract. No compatible verified
observation provider or season/year manifest is bundled. These contracts were
not merged or relaxed; operational historical inference remains unavailable
under that incompatible configuration. See [historical provisioning](historical_inference.md).

The original retained generator is
`ml/preprocessing/concentration_common.py::engineer_fast`, with selected extra
features in `ml/training/xgboost_concentration.py::add_features`. The original
experiment is retained in `ml/training/improve_historical_features.py`.

- Base historical references select the same district/crop/season, strictly
  earlier **recorded Years**, with expected harvest before the prediction cutoff.
- Each distinct historical harvest date anchors an inclusive +/-14-day window
  inside its recorded year. Acreage and expected production are summed per
  window; overlapping windows are dependent observations.
- Previous-year window mean, median and population standard deviation use the
  same historical windows; previous-year mean plan acreage uses individual
  plan acreage. Windows are not specifically aligned to the target month/day.
- Training peers include earlier-planted, not-yet-harvested matching plans
  across recorded years. The demo's unnecessary same-Year peer restriction was
  removed to preserve cross-year active peers and match training semantics.
- Training own production is the recorded Expected_Production_kg. A new demo
  scenario does not supply that evidence. XGBoost's through-2024 frozen numeric
  imputer uses 1,575 kg for missing own production; this is a global training
  statistic, not a crop-specific yield prediction. CatBoost handles numeric
  missing values natively. This missing-input scenario differs from evaluation
  rows, so historical benchmark accuracy cannot be assigned to this simulation.
- Labels compare scenario-inclusive peer acreage against linear P33/P67 of
  earlier completed historical windows. Below P33 is Low; above P67 is High;
  boundaries are Medium, with existing numerical tolerance. Missing/degenerate
  references are insufficient evidence. These are rule labels, not independent
  oversupply, demand, price-loss or expert outcome labels.
- Risk_Label, target Overlap_Acres, target Historical_P33/P67_Acres, Record_ID
  and Year are excluded from the model inputs. No new threshold was fitted.
- Frozen preprocessing fits training rows only. The selected configuration is
  `base_plus_previous_weight4_boost1.0`: fourfold Medium training weighting,
  no inference probability multiplier. Selection used 2023/2024 development.

| Evaluation Year | Training recorded Years through | Eligible training records | Evaluation records |
| ---: | ---: | ---: | ---: |
| 2023 | 2022 | 4,738 | 1,781 |
| 2024 | 2023 | 6,519 | 2,029 |
| 2025 | 2024 | 8,548 | 2,526 |

The demo's 2025/2026 scenarios use the through-2024 artifact. The displayed
2024-12-31 training cutoff is the **recorded Year upper bound**, not a verified
publication date, observation-end date or model release date. The saved training
features' latest planting cutoff through 2024 is 2024-06-22. Of 15,090 raw
records, 6,241 have a Year different from planting calendar year. No trustworthy
season/reporting-year mapping is available. Do not silently interpret Year as
the planting year. The frozen models were built retrospectively in October 2026;
availability of the trained model at the historical decision cutoff is unverified.

## Historical evaluation and limits of validation

Read-only `ml.evaluate_saved.evaluate()` reproduced all five models' stored
predictions exactly over identical cohorts, without fitting a research model.
Frozen results, not new performance claims:

| Model | Pooled records | Pooled accuracy | Pooled macro F1 |
| --- | ---: | ---: | ---: |
| XGBoost | 6,336 | .84296086 | .71819222 |
| CatBoost | 6,336 | .84406566 | .70878211 |
| Random Forest | 6,336 | .77667298 | .60117216 |
| LinearSVC | 6,336 | .79040404 | .60637685 |
| RBF SVC | 6,336 | .79434975 | .62004099 |

| XGBoost Year | Accuracy | Macro F1 | Medium recall | High recall |
| ---: | ---: | ---: | ---: | ---: |
| 2023 | .91240876 | .80348152 | .92957746 | .49696970 |
| 2024 | .89058650 | .76202002 | .39051095 | .90033223 |
| 2025 | .75574030 | .62951719 | .22385862 | .95408163 |

2025 High precision is .43538999: High recall alone overstates discrimination.
The 2023/2024 folds were used for selection, and 2025/2026 were inspected in
earlier project research. Pooled scores include development records and are
not pristine external validation. There are no supported 2026 metrics for this
selected workflow; the old UI's fallback to 2025 scores was removed. Class
probabilities are not established as calibrated probabilities of financial loss.

Chronological splits and training-only preprocessing prevent specific leakage
paths, but do **not** establish historical observability. Unknown publication lag,
later revisions, uncertain reporting-year mappings and unverified individual
source provenance remain. The original code's full-cohort median yield included
target/future years and had no approved agricultural source; it has been removed.
Historical mean production now uses original record-wise production sums rather
than mean acreage multiplied by a pooled yield. Verified late observations are
excluded from replay peers and history. Unknown versions remain an explicit
assumption, so the workflow must not claim “zero temporal leakage.”

The terminology follows the primary [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage):
information unavailable at prediction time can bias validation, even with a
pipeline. [Clustering documentation](https://scikit-learn.org/stable/modules/clustering.html)
describes unlabeled similarity/density grouping; interpreting those groups as
agricultural risk requires separate reference evidence.

## Research objective coverage

Software regression tests establish implemented behavior, not scientific or
agronomic effectiveness. No current production assessor supplies an independently
validated concentration-risk category. All eight capabilities have software
support or explicit gates, but the full research objective is not scientifically
validated end to end.

| Capability | Implemented evidence | What is validated | Missing scientific evidence |
| --- | --- | --- | --- |
| A. Farmer cultivation registration | `cultivation_plans.py`, `farmer_auth.py`, versioned SQLite plans, ownership, declared season and future creation dates | Auth/date/version behavior covered by software tests | Independently verified real farmer intentions, participation coverage, accuracy of declared dates/acreage |
| B. Same-crop/region harvest concentration | `risk_indicators.py` uses version/submission cutoff snapshot, same district/region/crop, inclusive +/-14 days; farmer numbers withheld | Deterministic grouping/own-plan-once/cutoff/privacy behavior tested | Crop duration/harvest interval validity, season mapping, representative coverage, actual supply; historical CSV has no region |
| C. K-Means | `plan_clustering.py`: separate districts, one-hot crop/region, standardized log acreage and elapsed harvest days, seeded K-Means | Reproducible algorithm and disclosure behavior tested | Domain-approved distance/weights/k, cluster stability, target membership interpretation, independent risk references |
| D. DBSCAN | Same service: eps/min_samples density groups and noise, suppressed small groups | Algorithm/noise interpretation/privacy behavior tested | Evidence-based parameter selection and density interpretation; noise is not High risk |
| E. Evidence-based risk | `risk_assessment.py` and `current_plan_risk.py` expose descriptive indicators and missing evidence; production/reference research layers have availability/applicability gates | Fail-closed software gates; historical classifier agreement with experimental rules | Representative real snapshots, independent expert labels/approved category definitions, prospective construct/outcome validation; oversupply also needs demand/market outcomes |
| F. Conditional alternatives | `farmer_workflow.py::defensible_high` requires independently verified High; `alternatives.py` requires approved suitability, comparable scope/coverage and releasable peers | Gate/comparison behavior tested with fictional attestations | Genuine classification, suitability and coverage approvals, comparable registration participation and realized benefit |
| G. Farmer final selection | `personalized_planning.py::save_choice`, authenticated selection routes, versioned choice; switching crops rechecks comparison eligibility | Ownership, stale revision checks and selection persistence tested | Real farmer use/usability and defensible approved alternative evidence |
| H. Personalized planning | `personalized_planning.py::generate`: source-checked guideline entries plus explicit availability/applicability approval overlay, actual date anchors and unit conversion | Approval/anchor/unit/privacy/version behavior tested | Region/season/variety/method/product approvals, soil/water context, complete verified activity coverage and field validation |

The descriptive comparison endpoint can return conditional lower-concentration
candidates with suitability/coverage approvals even when risk remains unvalidated;
it does not assert they are automatic farmer recommendations. Final selection
rechecks that comparison eligibility. Automatic workflow recommendations remain
behind the separate verified-current-High gate. Experimental production candidates
remain explicitly experimental. A historical High is never passed to those gates.
Keeping the original crop may produce only a partial plan without approved
guidance. Empty or partial schedules are preferable to invented activities,
yield/profit estimates or unsupported agronomic approval.

## Changes and regression evidence

- Optional decision cutoff is separate from selected planting date. It defaults
  to planting for compatibility and uses start-of-day Asia/Colombo; it must not
  follow planting. The currently frozen replay limits planting and cutoff to
  the same calendar year rather than inventing a season/year mapping.
- Added distinct dataset-window, proven-availability and replay indicators;
  absent timestamps are unknown. Trusted server-side observation evidence
  fields cannot be injected through the request schema.
- Verified reviewed model bytes against the existing artifact catalog before
  deserialization, checked saved feature ordering, and used actual class ordering.
- Removed unsupported yield estimation and future-cohort yield access; corrected
  historical production aggregation and cross-year peer eligibility.
- Sparse/zero replay cohorts abstain; small peer aggregates are withheld. Three
  records is a conservative disclosure policy, not a scientifically validated
  risk/sample-size threshold or a verified count of distinct farmers.
- Removed ranked demo alternatives. No farmer-level IDs, individual records or
  source rows are returned. Aggregate suppression is not differential privacy;
  repeated queries can still permit inference.
- Research UI shows cutoff, planting, harvest, recorded-Year training cutoff,
  model availability caveat, proxy/probabilities, observation status, concentration
  views, missing own production, and changes compared with the preceding scenario.
- Seeder targets only reserved `research_demo.sqlite3`, rejects configured
  operational paths and non-demo records, and marks synthetic databases. The
  operational application refuses the reserved filename and marked databases
  even after renaming. Evaluation never reads the seeded database.
- Operational farmer creation date rules, risk validation, suitability, coverage,
  guideline, ownership and disclosure gates remain unchanged.

Regression coverage includes independent cutoff/planting changes, verified late
observations, missing/ambiguous/unattested timestamps, future planted-but-known
plans, unknown availability, record-wise production/training semantics,
cross-year peers, future-data/label/yield mutations, sparse/zero coverage, actual
model contracts, probability ordering, current-risk separation, blocked
recommendations, forbidden request evidence, database byte-level isolation,
synthetic markers/renames and existing non-demo record preservation. Frontend
tests cover distinct evidence views, abstention, previous-scenario explanation
and cutoff request serialization alongside existing privacy/approval tests.

## Validation results

- Full Component 02 backend suite: `python -m pytest tests -q` — **440 passed**
  in 190.86 seconds, one existing Starlette/httpx deprecation warning. All backend
  test files in this workspace are in this component. Tests that fit small
  fictional classifiers do not retrain or overwrite any research artifact.
- Dedicated temporal regression file: **22 passed**, including saved-artifact
  contracts and the real reported scenario counts. Other existing tests cover
  operational ownership/privacy, recommendation, suitability and planning gates.
- Frontend `npm run test:crop-planning`: **32 passed**.
- Frontend `npm run typecheck`, `npm run lint`, and `npm run build`: **passed**;
  existing image optimization and hook dependency warnings remain outside the
  modified research UI. Build includes `/crop-planning/research-demo`.
- Read-only saved-prediction replay: all five models' three chronological folds
  reproduced exactly, with identical 6,336-record cohorts.
- Integrity check: **all 63 catalogued files present, zero hash changes**;
  original historical CSV SHA-256 remains
  `4397ddae6a3fabde06f1b9dc6fd42d40b3f0cc5a5275754621011e4cfcbb2bab`.
- `git diff --check`: passed. No staging, commits or pushes.

Remaining limitations are observation/model availability, source provenance,
season/reporting-year and regional compatibility, dependent historical windows,
global missing-input handling, probability calibration, independent current-risk
labels, representative comparable coverage, approved agronomic applicability and
prospective field/market validation. Passing software tests does not resolve them.
