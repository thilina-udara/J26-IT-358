"""RF-only chronological ASC baseline. No training occurs on import or evaluation.

Historical RF: 77.67% pooled accuracy, macro F1 0.6012, 6,336 eligible
2023/2024/2025 records. Previously exposed evaluation years are not pristine
holdouts. Authorized original data and saved artifacts are external inputs.

Examples (run from component root; original records must remain private):
  python -m ml.training.random_forest_baseline evaluate --artifacts <RF-directory> --features <private-historical-features.csv>
  python -m ml.training.random_forest_baseline train --dataset <original-ASC.csv> --output <new-directory>
The train command is only for explicitly authorized future reproduction.
"""
import argparse
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from ml.preprocessing.concentration_common import LABELS, FEATURES, CAT, NUM, load, engineer_fast, metric, preprocessing

SOURCE_SHA256 = '4397ddae6a3fabde06f1b9dc6fd42d40b3f0cc5a5275754621011e4cfcbb2bab'
YEARS = (2023, 2024, 2025)


def pipeline():
    return Pipeline([('preprocessing', preprocessing()),
                     ('classifier', RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=1))])


def save(path, value):
    path.write_text(json.dumps(value, indent=2, default=lambda v: v.item() if isinstance(v, np.generic) else str(v)) + '\n', encoding='utf-8')


def train(dataset, output):
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Use the unchanged authorized original ASC source; do not combine sampled CSVs')
    raw, audit = load(dataset, '%m/%d/%Y')
    # 2026 is excluded from all fitting, label construction and evaluation here.
    features = engineer_fast(raw[raw.Year <= 2025].copy())
    output.mkdir(parents=True, exist_ok=False)
    folds, predictions = {}, []
    for year in YEARS:
        training = features[(features.Year < year) & features.Risk_Label.isin(LABELS)]
        test = features[(features.Year == year) & features.Risk_Label.isin(LABELS)]
        if len(training) == 0 or len(test) == 0 or training.Risk_Label.nunique() < 3:
            raise ValueError(f'Insufficient historical class evidence for {year}')
        assert not set(training.Record_ID) & set(test.Record_ID)
        assert training.Prediction_Cutoff.max() < test.Prediction_Cutoff.min()
        model = pipeline()
        model.fit(training[FEATURES], training.Risk_Label.map(dict(zip(LABELS, range(3)))))
        prediction = np.asarray(LABELS)[model.predict(test[FEATURES]).astype(int)]
        majority = training.Risk_Label.value_counts().idxmax()
        folds[str(year)] = {'test': metric(test, prediction), 'baseline': metric(test, [majority] * len(test)),
                            'eligible_train': len(training), 'baseline_class': majority,
                            'seasons': {s: metric(test[test.Season == s], prediction[test.Season.eq(s)])
                                        for s in ['Maha', 'Yala'] if test.Season.eq(s).any()}}
        rows = test[['Record_ID', 'Year', *CAT, 'Risk_Label']].copy()
        rows['Model'] = 'Random Forest'
        rows['Prediction'] = prediction
        rows['Baseline_Prediction'] = majority
        predictions.append(rows)
        joblib.dump(model, output / f'random_forest_through_{year-1}.joblib')
        joblib.dump(model.named_steps['preprocessing'], output / f'random_forest_preprocessing_through_{year-1}.joblib')
    pooled = pd.concat(predictions, ignore_index=True)
    result = {'folds': folds, 'pooled': metric(pooled, pooled.Prediction),
              'majority_baseline': metric(pooled, pooled.Baseline_Prediction), 'source_sha256': SOURCE_SHA256,
              'insufficient_by_year': features[~features.Risk_Label.isin(LABELS)].Year.value_counts().to_dict(),
              'validation': audit, 'previously_exposed_years': [2025, 2026]}
    pooled.to_csv(output / 'historical_out_of_time_predictions.csv', index=False)
    features.to_csv(output / 'features_and_labels.csv', index=False)
    save(output / 'feature_schema.json', {'features': FEATURES, 'categorical': CAT, 'numeric': NUM, 'labels': LABELS})
    save(output / 'metrics.json', result)
    save(output / 'artifact_manifest.json', {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()})
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source dataset changed during execution')
    return result


def evaluate(folder, features_path=None):
    # Load only reviewed private artifacts: joblib is unsafe for untrusted files.
    schema = json.loads((folder / 'feature_schema.json').read_text())['features']
    if schema != FEATURES:
        raise ValueError('Feature schema differs from the historical RF baseline')
    context = pd.read_csv(features_path if features_path is not None else folder / 'features_and_labels.csv')
    saved = pd.read_csv(folder / 'historical_out_of_time_predictions.csv')
    saved = saved[(saved.Model == 'Random Forest') & saved.Year.isin(YEARS)]
    assert not saved.Record_ID.duplicated().any()
    frames, folds = [], {}
    for year in YEARS:
        expected = context[(context.Year == year) & context.Risk_Label.isin(LABELS)]
        rows = saved[saved.Year == year].merge(context[['Record_ID', 'Year', 'Risk_Label', *FEATURES]],
                    on=['Record_ID', 'Year', 'Risk_Label'], suffixes=('', '_context'), validate='one_to_one')
        assert set(rows.Record_ID) == set(expected.Record_ID)
        model = joblib.load(folder / f'random_forest_through_{year-1}.joblib')
        prediction = np.asarray(LABELS)[model.predict(rows[FEATURES]).astype(int)]
        assert np.array_equal(prediction, rows.Prediction.to_numpy()), f'Saved {year} predictions differ'
        folds[str(year)] = metric(rows, prediction)
        frames.append(rows)
    pooled = pd.concat(frames, ignore_index=True)
    return {'folds': folds, 'pooled': metric(pooled, pooled.Prediction),
            'majority_baseline': metric(pooled, pooled.Baseline_Prediction)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    fitting = sub.add_parser('train')
    fitting.add_argument('--dataset', type=Path, required=True)
    fitting.add_argument('--output', type=Path, required=True)
    replay = sub.add_parser('evaluate')
    replay.add_argument('--artifacts', type=Path, required=True)
    replay.add_argument('--features', type=Path, help='Authorized historical features CSV; defaults to features_and_labels.csv in artifact directory')
    a = p.parse_args()
    result = train(a.dataset, a.output) if a.command == 'train' else evaluate(a.artifacts, a.features)
    print(json.dumps(result, indent=2))
