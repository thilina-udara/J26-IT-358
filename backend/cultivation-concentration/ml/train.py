"""One frozen-configuration training entry point; no search or model selection.

Not needed to run the backend. Requires authorized ASC data and the private
artifact bundle. Prior 2025/2026 exposure prevents claiming a pristine holdout.
"""
import argparse
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from ml.evaluate_saved import ROOT, FAMILIES, LABELS
from ml.training.train_full_original_dataset import load, engineer_fast, metric
from ml.training.improve_historical_features import add_features


def run(dataset, output, chosen):
    catalog = json.loads((ROOT / 'models/artifact_catalog.json').read_text())
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != catalog['original_dataset_sha256']:
        raise ValueError('Dataset differs from the frozen original ASC source')
    raw, _ = load(dataset, '%m/%d/%Y')
    raw = raw[raw.Year <= 2025].copy()
    context = add_features(raw, engineer_fast(raw))
    output.mkdir(parents=True, exist_ok=False)
    results = {}
    for name, (family, prefix, _, _) in FAMILIES.items():
        if chosen != 'all' and chosen != name:
            continue
        folder = ROOT / 'models/experimental' / family / 'v1_20261009'
        schema = json.loads((folder / 'feature_schema.json').read_text())
        features = schema['features']
        folds = []
        for year in [2023, 2024, 2025]:
            training = context[(context.Year < year) & context.Risk_Label.isin(LABELS)]
            test = context[(context.Year == year) & context.Risk_Label.isin(LABELS)]
            pipeline = clone(joblib.load(folder / f'{prefix}_through_{year-1}.joblib'))
            numeric = name in ['XGBoost', 'Random Forest', 'CatBoost']
            target = training.Risk_Label.map(dict(zip(LABELS, range(3)))) if numeric else training.Risk_Label
            kwargs = {}
            if name in ['XGBoost', 'CatBoost']:
                weight = np.where(training.Risk_Label == 'Medium', 4. if name == 'XGBoost' else 2., 1.)
                kwargs['classifier__sample_weight'] = weight / weight.mean()
            pipeline.fit(training[features], target, **kwargs)
            prediction = np.asarray(pipeline.predict(test[features])).reshape(-1)
            if numeric:
                prediction = np.asarray(LABELS)[prediction.astype(int)]
            record = test[['Record_ID', 'Year', 'Risk_Label']].copy()
            record['Prediction'] = prediction
            folds.append(record)
            joblib.dump(pipeline, output / f'{prefix}_through_{year-1}.joblib')
        pooled = pd.concat(folds, ignore_index=True)
        results[name] = metric(pooled, pooled.Prediction)
        pooled.to_csv(output / f'{prefix}_predictions.csv', index=False)
    (output / 'metrics.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--model', choices=['all', *FAMILIES], default='all')
    a = p.parse_args()
    run(a.dataset, a.output, a.model)
