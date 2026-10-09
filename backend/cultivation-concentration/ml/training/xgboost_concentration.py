"""Selected historical XGBoost: 84.30% accuracy / 0.7182 macro F1, 6,336 rows.

Frozen selection: base_plus_previous_weight4_boost1.0, selected on 2023/2024.
This reproduces the selected configuration, not the original ablation search.
2025/2026 were previously exposed; pooled results include development folds.
ASC has no registration timestamps: planting-cutoff proxies do not demonstrate
submission-time availability. Research concentration is not verified market risk.
Matara/Hambantota histories remain separate. No production activation occurs.

Explicit private inputs; no training on import or in evaluate mode:
  python -m ml.training.xgboost_concentration evaluate --artifacts <reviewed-folder> --features <private-features.csv>
  python -m ml.training.xgboost_concentration train --source <original-ASC.csv> --output <new-private-folder>
Only run train for separately authorized future reproduction. Never load untrusted joblib.
"""
import argparse
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier
from ml.preprocessing import concentration_common as common

SOURCE_SHA256 = '4397ddae6a3fabde06f1b9dc6fd42d40b3f0cc5a5275754621011e4cfcbb2bab'
EXTRA = ['Previous_Year_Window_Mean_Acres', 'Previous_Year_Window_Median_Acres',
         'Previous_Year_Window_Std_Acres', 'Previous_Year_Mean_Plan_Acres']
FEATURES = common.FEATURES + EXTRA
NUMERIC = common.NUM + EXTRA
PARAMETERS = dict(n_estimators=300, max_depth=2, learning_rate=.04, min_child_weight=8,
                  gamma=.15, reg_alpha=.2, reg_lambda=8, subsample=.85, colsample_bytree=.9,
                  objective='multi:softprob', num_class=3, eval_metric='mlogloss',
                  tree_method='hist', random_state=42, n_jobs=1)
SELECTION = dict(selected='base_plus_previous_weight4_boost1.0', features='base_plus_previous',
                 weight=4, boost=1.0, **{'2025_used_for_selection': False})


def add_features(raw, features):
    """Exactly the four selected previous-year statistics; earlier completed harvests only."""
    output = features.copy().set_index('Record_ID')
    updates = {}
    for _, group in raw.groupby(common.CAT, sort=False):
        cache = {}
        for plan in group.itertuples(index=False):
            prior = group[(group.Year < plan.Year) & (group.Expected_Harvest_Date < plan.Planting_Date)]
            key = (plan.Year, len(prior))
            if key not in cache:
                previous = prior[prior.Year == plan.Year - 1]
                values = {column: np.nan for column in EXTRA}
                if len(previous):
                    dates = previous.Expected_Harvest_Date.to_numpy(dtype='datetime64[D]')
                    acres = previous.Land_Size_Acres.to_numpy()
                    windows = np.array([float(acres[np.abs((dates-anchor).astype(int)) <= 14].sum())
                                        for anchor in np.unique(dates)])
                    values.update(zip(EXTRA, [float(windows.mean()), float(np.median(windows)),
                                             float(windows.std()), float(previous.Land_Size_Acres.mean())]))
                cache[key] = values
            updates[plan.Record_ID] = cache[key].copy()
    return output.join(pd.DataFrame.from_dict(updates, orient='index')).reset_index()


def pipeline():
    prep = ColumnTransformer([
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), common.CAT),
        ('num', Pipeline([('impute', SimpleImputer(strategy='median', keep_empty_features=True)),
                          ('scale', StandardScaler())]), NUMERIC)])
    return Pipeline([('preprocessing', prep), ('classifier', XGBClassifier(**PARAMETERS))])


def historical_inputs(source):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Use the unchanged authorized original ASC source, not sampled datasets')
    raw, _ = common.load(source, '%m/%d/%Y')
    raw = raw[raw.Year <= 2025].copy()
    return add_features(raw, common.engineer_fast(raw))


def save(path, value):
    path.write_text(json.dumps(value, indent=2, default=lambda v: v.item() if isinstance(v, np.generic) else str(v)) + '\n', encoding='utf-8')


def train(source, output):
    data = historical_inputs(source)
    output.mkdir(parents=True, exist_ok=False)
    save(output / 'frozen_selection.json', SELECTION)
    frames, folds = [], {}
    for year in [2023, 2024, 2025]:
        training = data[(data.Year < year) & data.Risk_Label.isin(common.LABELS)]
        test = data[(data.Year == year) & data.Risk_Label.isin(common.LABELS)]
        if not len(test) or training.Risk_Label.nunique() != 3:
            raise ValueError(f'Insufficient historical class evidence for {year}')
        assert training.Prediction_Cutoff.max() < test.Prediction_Cutoff.min()
        assert not set(training.Record_ID) & set(test.Record_ID)
        target = training.Risk_Label.map(dict(zip(common.LABELS, range(3))))
        weight = np.where(target == 1, 4., 1.)
        weight /= weight.mean()
        model = pipeline()
        model.fit(training[FEATURES], target, classifier__sample_weight=weight)
        prediction = np.asarray(common.LABELS)[np.argmax(model.predict_proba(test[FEATURES]), axis=1)]
        folds[str(year)] = common.metric(test, prediction)
        rows = test[['Record_ID', 'Year', *common.CAT, 'Risk_Label']].copy()
        rows['Prediction'] = prediction
        rows['Baseline_Prediction'] = training.Risk_Label.value_counts().idxmax()
        frames.append(rows)
        joblib.dump(model, output / f'selected_xgboost_through_{year-1}.joblib')
    pooled = pd.concat(frames, ignore_index=True)
    result = {'folds': folds, 'pooled': common.metric(pooled, pooled.Prediction),
              'majority_baseline': common.metric(pooled, pooled.Baseline_Prediction),
              'source_sha256': SOURCE_SHA256, 'selection': SELECTION,
              'insufficient_by_year': data[~data.Risk_Label.isin(common.LABELS)].Year.value_counts().to_dict()}
    pooled.to_csv(output / 'selected_historical_predictions.csv', index=False)
    data.to_csv(output / 'features_and_labels_2020_2025.csv', index=False)
    save(output / 'feature_schema.json', {'features': FEATURES, 'weight': 4, 'medium_probability_multiplier': 1.0})
    save(output / 'metrics.json', result)
    save(output / 'artifact_manifest.json', {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()})
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256
    return result


def evaluate(folder, features):
    """Replay reviewed saved pipelines; no fitting, feature selection or threshold tuning."""
    schema = json.loads((folder / 'feature_schema.json').read_text())
    if schema['features'] != FEATURES or schema['weight'] != 4 or schema['medium_probability_multiplier'] != 1.0:
        raise ValueError('Saved feature/decision specification differs from the frozen selection')
    data = pd.read_csv(features)
    data = data[data.Year <= 2025].copy()
    data['Prediction_Cutoff'] = pd.to_datetime(data.Prediction_Cutoff)
    saved = pd.read_csv(folder / 'selected_historical_predictions.csv')
    saved = saved[saved.Year.isin([2023, 2024, 2025])]
    if data.Record_ID.duplicated().any() or saved.Record_ID.duplicated().any():
        raise ValueError('Duplicate record identifiers')
    folds = {}
    for year, count in [(2023, 1781), (2024, 2029), (2025, 2526)]:
        rows = saved[saved.Year == year]
        expected = data[(data.Year == year) & data.Risk_Label.isin(common.LABELS)]
        if len(rows) != count or set(rows.Record_ID) != set(expected.Record_ID):
            raise ValueError(f'Historical eligible cohort changed for {year}')
        inputs = data.set_index('Record_ID').loc[rows.Record_ID]
        if not np.array_equal(inputs.Risk_Label.to_numpy(), rows.Risk_Label.to_numpy()):
            raise ValueError('Historical target labels differ')
        model = joblib.load(folder / f'selected_xgboost_through_{year-1}.joblib')
        if any(model.named_steps['classifier'].get_params()[k] != v for k, v in PARAMETERS.items()):
            raise ValueError('Saved classifier parameters differ from the frozen configuration')
        training = data[(data.Year < year) & data.Risk_Label.isin(common.LABELS)]
        imputer = model.named_steps['preprocessing'].named_transformers_['num'].named_steps['impute']
        assert np.allclose(imputer.statistics_, training[NUMERIC].median().fillna(0), equal_nan=True)
        prediction = np.asarray(common.LABELS)[np.argmax(model.predict_proba(inputs[FEATURES]), axis=1)]
        if not np.array_equal(prediction, rows.Prediction.to_numpy()):
            raise ValueError(f'{year} saved predictions differ')
        folds[str(year)] = common.metric(rows, prediction)
    return {'folds': folds, 'pooled': common.metric(saved, saved.Prediction)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    fitting = commands.add_parser('train', help='Explicit future frozen reproduction only')
    fitting.add_argument('--source', type=Path, required=True)
    fitting.add_argument('--output', type=Path, required=True)
    replay = commands.add_parser('evaluate', help='Verify saved pipelines without training')
    replay.add_argument('--artifacts', type=Path, required=True)
    replay.add_argument('--features', type=Path, required=True)
    a = p.parse_args()
    result = train(a.source, a.output) if a.command == 'train' else evaluate(a.artifacts, a.features)
    print(json.dumps(result, indent=2))
