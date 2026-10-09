"""Reproduce saved chronological predictions without fitting any model."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from ml.preprocessing.concentration_common import metric

ROOT = Path(__file__).resolve().parents[1]
LABELS = ['Low', 'Medium', 'High']
FAMILIES = {
    'XGBoost': ('historical_feature_improvement', 'selected_xgboost', 'selected_historical_predictions.csv', None),
    'Random Forest': ('full_original_dataset', 'random_forest', 'historical_out_of_time_predictions.csv', 'Random Forest'),
    'CatBoost': ('catboost_comparison', 'catboost_pipeline', 'selected_historical_predictions.csv', None),
    'LinearSVC': ('svm_full_dataset', 'linear_svc', 'svm_out_of_time_predictions.csv', 'LinearSVC'),
    'RBF SVC': ('svm_full_dataset', 'rbf_svc', 'svm_out_of_time_predictions.csv', 'RBF SVC'),
}


def evaluate():
    base = ROOT / 'models/experimental'
    context = pd.read_csv(base / 'historical_feature_improvement/v1_20261009/features_and_labels_2020_2025.csv')
    results = {}
    expected_ids = None
    for name, (family, prefix, filename, model_name) in FAMILIES.items():
        folder = base / family / 'v1_20261009'
        saved = pd.read_csv(folder / filename)
        if model_name:
            saved = saved[saved.Model == model_name]
        saved = saved[saved.Year.isin([2023, 2024, 2025])]
        assert not saved.Record_ID.duplicated().any()
        ids = set(saved.Record_ID)
        if expected_ids is None:
            expected_ids = ids
        assert ids == expected_ids, 'Evaluation cohorts differ'
        features = json.loads((folder / 'feature_schema.json').read_text())['features']
        folds = {}
        frames = []
        for year in [2023, 2024, 2025]:
            rows = saved[saved.Year == year].merge(context, on=['Record_ID', 'Year', 'Risk_Label'], suffixes=('', '_context'), validate='one_to_one')
            assert len(rows) == int((saved.Year == year).sum())
            model = joblib.load(folder / f'{prefix}_through_{year-1}.joblib')
            prediction = np.asarray(model.predict(rows[features])).reshape(-1)
            if prediction.dtype.kind in 'iuf':
                prediction = np.asarray(LABELS)[prediction.astype(int)]
            assert np.array_equal(prediction, rows.Prediction.to_numpy()), f'{name} {year} prediction mismatch'
            folds[str(year)] = metric(rows, prediction)
            frames.append(rows)
        pooled = pd.concat(frames, ignore_index=True)
        results[name] = {'folds': folds, 'pooled': metric(pooled, pooled.Prediction)}
    return results


if __name__ == '__main__':
    print(json.dumps(evaluate(), indent=2))
