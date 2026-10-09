# Methodology

## Backend workflow

Authenticated farmers register and version their own cultivation plans. Ownership
checks restrict access to individual plans. Analyst/administrator/reviewer roles
have separate permissions. Authentication is configured through deployment-local
tokens; this is not a claim of a complete external identity-provider integration.

Known concentration uses registered plans available at the assessment cutoff,
within the same district and crop and an inclusive ?14-day harvest window.
K-Means and DBSCAN describe patterns in registered plans; cluster IDs are not
Low/Medium/High labels. Matara and Hambantota never share concentration aggregates.
Alternative-crop scenarios and personalized schedules are evidence-gated.
Guideline source checking does not activate unverified quantities or timing claims.

Prospective assessments preserve immutable timestamps, own-plan inputs, peer plan
versions/statuses, available overlap, reference/model versions and outputs.
Later registrations cannot retroactively change an assessment. Farmers do not
receive peer identities. Independently defined later outcomes must be evaluated
separately; replaying the concentration formula is agreement, not independent accuracy.

## Historical research target

The original ASC dataset contains 15,090 records for 2020?2026. It is not published
with this implementation. SHA-256:
`4397ddae6a3fabde06f1b9dc6fd42d40b3f0cc5a5275754621011e4cfcbb2bab`.
Do not combine it with sampled farmer CSVs or modify it.

Historical labels use earlier-year reference harvests completed before each
simulated planting cutoff, grouped separately by district, crop and season.
Reference harvest-window acreage uses inclusive ?14-day windows. Existing linear
P33/P67 rules classify overlap acreage below P33 as Low, above P67 as High and
between the bounds as Medium, preserving the existing numerical boundary tolerance.
Labels require at least one historical window and P33 < P67. Missing or degenerate
references are `insufficient_evidence` and excluded, not relabeled.
Target overlap includes own acreage plus same-group peers planted strictly earlier
than cutoff, not yet harvested at cutoff, with expected harvest within ?14 days.
Same-day peer planting is excluded. These proxies do not prove registration availability.
The retained implementation is `ml/preprocessing/concentration_common.py`
(`engineer_fast`); the selected XGBoost entry point reuses these rules.

ASC records have no registration timestamps. A planting-date proxy cannot prove
that historical peer plans were registered at prediction time. These results are
retrospective experimental classification, not demonstrated submission-time accuracy.
The target is cultivation concentration, not independently verified oversupply or
price-loss risk. Historical threshold shifts and identical inputs with differing
labels limit Medium-class predictability.

## Selected XGBoost inputs and protocol

Categorical inputs: District, Crop, Season. Numerical inputs: own acreage,
planting/harvest month, permitted overlap-plan count, own expected production,
historical window count/mean acreage/mean expected production, and previous-year
window mean/median/standard-deviation acreage and mean plan acreage.

Current target overlap acreage, target P33/P67 thresholds, label, record ID and year
are excluded from classifier inputs. Historical reference thresholds remain part
of label generation, not leaked target features. Retrospective availability of
peer counts remains an explicit limitation rather than verified submission evidence.

Train through 2022 ? test 2023 (1,781 eligible records); through 2023 ? test 2024
(2,029); through 2024 ? test 2025 (2,526). Preprocessing fits training rows only.
Pooled accuracy uses 6,336 predictions, not an average of annual percentages.
Earlier 2023?2024 folds selected the frozen specification. Both 2025 and 2026 were
examined in prior research, so neither is a pristine holdout for the overall project.
2026 is excluded from this historical evaluation and new model selection.

Selected configuration: `base_plus_previous_weight4_boost1.0`, XGBoost depth 2,
300 estimators, learning rate .04, minimum child weight 8, gamma .15, alpha .2,
lambda 8, subsample .85, column subsample .9, seed 42; 4? Medium training weight,
no Medium probability multiplier. These are frozen prior results, not new tuning.
The retained model-specific training entry points under `ml/training/` use the
shared historical rules and require authorized private inputs. The selected
XGBoost entry point is `ml/training/xgboost_concentration.py`.
No training is needed to run the backend or verify saved predictions.

## Evidence and reproducibility

`ml/evaluate_saved.py` loads all 15 chronological pipelines, verifies identical
record cohorts/labels, reproduces exact stored predictions and computes per-class
precision/recall/F1, confusion matrices and pooled metrics. SVM classes are strings;
XGBoost classes use Low/Medium/High = 0/1/2. Do not mix probability class orderings.
Full historical source, evidence, search outputs and old manifests are preserved
in a private frozen archive, outside Git. The minimal artifact catalog provides
new checksums for retained inputs; old manifests describing larger bundles are
kept with those complete archived bundles, not misrepresented as minimal manifests.

A future genuine predictive study needs timestamped registrations, frozen
assessment snapshots and independent outcomes. Historical 84.30% is not a live
performance guarantee. Backend/API features and tests do not establish agronomic
or market effectiveness; planning remains subject to evidence and approval gates.
