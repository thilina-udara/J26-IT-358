# Model comparison

All models below use the original 15,090-record ASC dataset and the same eligible
historical labels/cohorts: 6,336 out-of-time records across 2023, 2024 and 2025.
These are frozen retrospective results, with prior exposure to 2025/2026 disclosed.
No retraining or tuning was performed during repository simplification.

| Model | Pooled accuracy | Pooled macro F1 | Artifact family |
| --- | ---: | ---: | --- |
| Selected XGBoost | 84.30% | 0.7182 | historical_feature_improvement |
| Random Forest | 77.67% | 0.6012 | full_original_dataset |
| CatBoost | 84.41% | 0.7088 | catboost_comparison |
| LinearSVC | 79.04% | 0.6064 | svm_full_dataset |
| RBF SVC | 79.43% | 0.6200 | svm_full_dataset |

CatBoost has slightly higher accuracy; XGBoost has stronger macro F1 and Medium
recall, supporting its research selection. This does not imply XGBoost dominates
every metric. The tested probability ensemble reached 84.42% / macro F1 0.7161,
with lower Medium recall than selected XGBoost; it was not selected. No model
supports a claimed 88% pooled historical accuracy.

Selected XGBoost annual accuracy: 2023 **91.24%**, 2024 **89.06%**, 2025 **75.57%**.
2025 Medium recall is **22.39%**. Pooled Medium recall is about **42.28%** versus
CatBoost **36.05%**. Threshold drift and incomplete prediction-time information
remain limitations; the labels are not independent verified market outcomes.

Artifacts live under `models/experimental/<family>/v1_20261009/` after private
bundle installation. For training-end years 2022, 2023 and 2024, pipeline prefixes
are `selected_xgboost`, `random_forest`, `catboost_pipeline`, `linear_svc`, `rbf_svc`;
each filename is `<prefix>_through_<year>.joblib`. Preprocessing and feature schemas
are supplied with them. CatBoost loading requires `ml/preprocessing/catboost_inputs.py`.

Run `python -B -m ml.evaluate_saved` to verify all saved predictions and print full
per-year/pooled precision, recall, F1 and confusion matrices. Exact saved metrics
remain in the private bundle; the original detailed reports and chronological
selection records remain in the immutable external historical archive. That archive
is not available from a fresh clone unless separately provided through authorized access.
The classifier is not automatically activated by production API routes.

## Exact chronological results

Rows use identical eligible records. Recall values below are percentages.

| Model | Test year | Records | Accuracy | Macro F1 | Medium recall | High recall | Majority baseline accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| XGBoost | 2023 | 1781 | 91.24% | 0.8035 | 92.96% | 49.70% | 74.79% |
| XGBoost | 2024 | 2029 | 89.06% | 0.7620 | 39.05% | 90.03% | 71.66% |
| XGBoost | 2025 | 2526 | 75.57% | 0.6295 | 22.39% | 95.41% | 57.60% |
| XGBoost | pooled | 6336 | 84.30% | 0.7182 | 42.28% | 84.73% | 66.93% |
| Random Forest | 2023 | 1781 | 86.24% | 0.5585 | 83.80% | 1.82% | 74.79% |
| Random Forest | 2024 | 2029 | 73.09% | 0.4218 | 43.07% | 2.33% | 71.66% |
| Random Forest | 2025 | 2526 | 75.30% | 0.6198 | 19.88% | 95.66% | 57.60% |
| Random Forest | pooled | 6336 | 77.67% | 0.6012 | 39.69% | 44.87% | 66.93% |
| CatBoost | 2023 | 1781 | 91.69% | 0.8313 | 84.86% | 60.00% | 74.79% |
| CatBoost | 2024 | 2029 | 88.27% | 0.7207 | 26.64% | 90.03% | 71.66% |
| CatBoost | 2025 | 2526 | 76.17% | 0.6228 | 19.44% | 94.90% | 57.60% |
| CatBoost | pooled | 6336 | 84.41% | 0.7088 | 36.05% | 86.48% | 66.93% |
| LinearSVC | 2023 | 1781 | 90.96% | 0.8283 | 54.93% | 80.00% | 74.79% |
| LinearSVC | 2024 | 2029 | 74.22% | 0.3974 | 33.94% | 0.00% | 71.66% |
| LinearSVC | 2025 | 2526 | 74.51% | 0.5810 | 11.63% | 95.41% | 57.60% |
| LinearSVC | pooled | 6336 | 79.04% | 0.6064 | 26.52% | 58.97% | 66.93% |
| RBF SVC | 2023 | 1781 | 85.12% | 0.5245 | 67.96% | 0.00% | 74.79% |
| RBF SVC | 2024 | 2029 | 83.39% | 0.6359 | 7.30% | 85.38% | 71.66% |
| RBF SVC | 2025 | 2526 | 72.25% | 0.5543 | 8.25% | 95.41% | 57.60% |
| RBF SVC | pooled | 6336 | 79.43% | 0.6200 | 21.75% | 73.54% | 66.93% |

The training-period majority class is Low in all three folds (verified from training labels only).

## Confusion matrices

Rows = actual; columns = predicted; order Low, Medium, High.

| Model | Year | Low row | Medium row | High row |
| --- | --- | --- | --- | --- |
| XGBoost | 2023 | [1279, 53, 0] | [20, 264, 0] | [3, 80, 82] |
| XGBoost | 2024 | [1429, 25, 0] | [79, 107, 88] | [11, 19, 271] |
| XGBoost | 2025 | [1383, 72, 0] | [42, 152, 485] | [5, 13, 374] |
| XGBoost | pooled | [4091, 150, 0] | [141, 523, 573] | [19, 112, 727] |
| Random Forest | 2023 | [1295, 36, 1] | [46, 238, 0] | [17, 145, 3] |
| Random Forest | 2024 | [1358, 94, 2] | [149, 118, 7] | [16, 278, 7] |
| Random Forest | 2025 | [1392, 63, 0] | [61, 135, 483] | [9, 8, 375] |
| Random Forest | pooled | [4045, 193, 3] | [256, 491, 490] | [42, 431, 385] |
| CatBoost | 2023 | [1293, 39, 0] | [43, 241, 0] | [11, 55, 99] |
| CatBoost | 2024 | [1447, 7, 0] | [106, 73, 95] | [10, 20, 271] |
| CatBoost | 2025 | [1420, 35, 0] | [67, 132, 480] | [7, 13, 372] |
| CatBoost | pooled | [4160, 81, 0] | [216, 446, 575] | [28, 88, 742] |
| LinearSVC | 2023 | [1332, 0, 0] | [105, 156, 23] | [33, 0, 132] |
| LinearSVC | 2024 | [1413, 41, 0] | [181, 93, 0] | [30, 271, 0] |
| LinearSVC | 2025 | [1429, 26, 0] | [90, 79, 510] | [18, 0, 374] |
| LinearSVC | pooled | [4174, 67, 0] | [376, 328, 533] | [81, 271, 506] |
| RBF SVC | 2023 | [1323, 9, 0] | [91, 193, 0] | [28, 137, 0] |
| RBF SVC | 2024 | [1415, 36, 3] | [236, 20, 18] | [44, 0, 257] |
| RBF SVC | 2025 | [1395, 60, 0] | [110, 56, 513] | [16, 2, 374] |
| RBF SVC | pooled | [4133, 105, 3] | [437, 269, 531] | [88, 139, 631] |
