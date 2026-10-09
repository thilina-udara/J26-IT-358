"""Matched chronological CatBoost experiment; 2025 evaluated only after selection."""
import argparse
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import catboost
import joblib
import numpy as np
import pandas as pd
import sklearn
from catboost import CatBoostClassifier
from sklearn.pipeline import Pipeline
from ml.preprocessing.catboost_inputs import CatBoostInputs
from ml.preprocessing import concentration_common as base
from ml.training import xgboost_concentration as historical
original = base  # Shared metric and label calculation, not legacy model implementations.


def save(path, value):
    path.write_text(json.dumps(value, indent=2, default=lambda v: v.item() if isinstance(v, np.generic) else str(v))+'\n', encoding='utf-8')
LABELS = base.LABELS
# Fixed before examining any new CatBoost 2025 outcomes.
CANDIDATES = [
    dict(name='depth4_l2_3_weight1', depth=4, l2_leaf_reg=3, medium_weight=1),
    dict(name='depth4_l2_10_weight1', depth=4, l2_leaf_reg=10, medium_weight=1),
    dict(name='depth6_l2_10_weight1', depth=6, l2_leaf_reg=10, medium_weight=1),
    dict(name='depth4_l2_10_weight2', depth=4, l2_leaf_reg=10, medium_weight=2),
    dict(name='depth4_l2_10_weight4', depth=4, l2_leaf_reg=10, medium_weight=4),
    dict(name='depth6_l2_10_weight2', depth=6, l2_leaf_reg=10, medium_weight=2),
]
COMMON = dict(iterations=400, learning_rate=.04, random_strength=1,
              bootstrap_type='Bayesian', bagging_temperature=1, loss_function='MultiClass',
              random_seed=42, thread_count=2, task_type='CPU', has_time=True,
              one_hot_max_size=2, nan_mode='Min', allow_writing_files=False, verbose=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cohort(frame, year):
    eligible = frame.Risk_Label.isin(LABELS)
    train = frame[eligible & (frame.Year < year)].sort_values(['Prediction_Cutoff', 'Record_ID'])
    test = frame[eligible & (frame.Year == year)].copy()
    assert not set(train.Record_ID) & set(test.Record_ID)
    assert train.Prediction_Cutoff.max() < test.Prediction_Cutoff.min()
    return train, test


def fitted(frame, year, features, candidate):
    train, test = cohort(frame, year)
    model = Pipeline([
        ('preprocessing', CatBoostInputs(features, base.CAT)),
        ('classifier', CatBoostClassifier(**COMMON, depth=candidate['depth'], l2_leaf_reg=candidate['l2_leaf_reg'],
             class_weights=[1, candidate['medium_weight'], 1], cat_features=base.CAT)),
    ])
    start = time.perf_counter()
    model.fit(train[features], train.Risk_Label.map(dict(zip(LABELS, range(3)))))
    elapsed = time.perf_counter() - start
    prediction = np.array(LABELS)[model.predict(test[features]).astype(int).ravel()]
    result = original.metric(test, prediction)
    result.update(training_seconds=elapsed, training_records=len(train),
                  training_accuracy=float(np.mean(np.array(LABELS)[model.predict(train[features]).astype(int).ravel()] == train.Risk_Label)),
                  training_majority_class=train.Risk_Label.value_counts().idxmax(),
                  training_majority_baseline=float(test.Risk_Label.eq(train.Risk_Label.value_counts().idxmax()).mean()),
                  retrospective_majority_prevalence=float(test.Risk_Label.value_counts(normalize=True).max()))
    predictions = test[['Record_ID', 'Year', 'District', 'Crop', 'Season', 'Risk_Label']].copy()
    predictions['Prediction'] = prediction
    return model, predictions, result


def verify_frame(generated, saved, columns):
    left = generated.set_index('Record_ID').sort_index()[columns]
    right = saved.set_index('Record_ID').sort_index()[columns]
    pd.testing.assert_frame_equal(left, right, check_dtype=False, atol=1e-8, rtol=1e-9)


def run(out, source, feature_path, baseline_prediction_path):
    """Original six-candidate development selection with explicit authorized inputs."""
    if sha(source) != historical.SOURCE_SHA256:
        raise ValueError('Expected the unchanged original ASC dataset, not sampled CSVs')
    protected = [source, feature_path, baseline_prediction_path]
    hashes = {str(p): sha(p) for p in protected}
    features = historical.FEATURES
    schema = {'features': features, 'excluded': ['Risk_Label', 'Overlap_Acres', 'Historical_P33_Acres',
                                               'Historical_P67_Acres', 'Record_ID', 'Year']}
    assert not set(features) & set(schema['excluded'])
    assert features == base.FEATURES + historical.EXTRA
    raw = pd.read_csv(source)
    assert len(raw) == 15090 and not raw.Record_ID.duplicated().any()
    raw = raw[raw.Year <= 2025].copy()  # 2026 is never engineered, trained, predicted or scored.
    for column in ['Planting_Date', 'Expected_Harvest_Date']:
        raw[column] = pd.to_datetime(raw[column], format='%m/%d/%Y')
    saved = pd.read_csv(feature_path)
    for column in ['Prediction_Cutoff', 'Reference_Latest_Harvest']:
        saved[column] = pd.to_datetime(saved[column])
    development_raw = raw[raw.Year <= 2024].copy()
    development = historical.add_features(development_raw, original.engineer_fast(development_raw))
    references = development.Reference_Latest_Harvest.notna()
    assert (development.loc[references, 'Reference_Latest_Harvest'] < development.loc[references, 'Prediction_Cutoff']).all()
    verify_frame(development, saved[saved.Year <= 2024], features+['Year', 'Risk_Label', 'Prediction_Cutoff', 'Historical_P33_Acres', 'Historical_P67_Acres', 'Overlap_Acres'])
    # Check both the labels and derived features remain district-specific.
    changed = development_raw.copy()
    changed.loc[changed.District == 'Hambantota', ['Land_Size_Acres', 'Expected_Production_kg']] *= 7
    isolated = historical.add_features(changed, original.engineer_fast(changed))
    verify_frame(isolated[isolated.District == 'Matara'], development[development.District == 'Matara'], features+['Risk_Label', 'Overlap_Acres', 'Historical_P33_Acres', 'Historical_P67_Acres'])
    out.mkdir(parents=True, exist_ok=False)
    save(out/'search_specification.json', dict(candidates=CANDIDATES, common_parameters=COMMON,
        development_years=[2023, 2024], final_year=2025, excluded_year=2026,
        selection='Max pooled development macro F1, then accuracy, then Medium recall; accuracy within 2pp of best candidate and each fold within 3pp of matched XGBoost. If none feasible, max development accuracy.',
        decision_rule='Unmodified argmax; no probability/threshold tuning', features=features,
        prior_exposure='2025 and 2026 already examined in earlier research; not pristine project holdouts.'))
    save(out/'input_hashes.json', hashes)
    baseline_predictions = pd.read_csv(baseline_prediction_path)
    baseline_development = {}
    for year in [2023, 2024]:
        _, test = cohort(development, year)
        matched = test.merge(baseline_predictions[baseline_predictions.Year == year], on=['Record_ID', 'Year', 'Risk_Label'], validate='one_to_one')
        assert len(matched) == len(test)
        baseline_development[str(year)] = original.metric(matched, matched.Prediction)
    metrics, cache, development_predictions = {}, {}, []
    for candidate in CANDIDATES:
        yearly, predictions = {}, []
        for year in [2023, 2024]:
            model, pred, result = fitted(development, year, features, candidate)
            cache[(candidate['name'], year)] = model
            yearly[str(year)] = result
            pred['Candidate'] = candidate['name']; predictions.append(pred)
            print(candidate['name'], year, 'accuracy', round(result['accuracy'], 5), 'macro_f1', round(result['macro_f1'], 5), flush=True)
        pooled = pd.concat(predictions, ignore_index=True)
        development_predictions.append(pooled)
        metrics[candidate['name']] = dict(parameters=candidate, folds=yearly, pooled=original.metric(pooled, pooled.Prediction))
    best_accuracy = max(m['pooled']['accuracy'] for m in metrics.values())
    feasible = {name:m for name,m in metrics.items() if m['pooled']['accuracy'] >= best_accuracy-.02
                and all(m['folds'][str(y)]['accuracy'] >= baseline_development[str(y)]['accuracy']-.03 for y in [2023, 2024])}
    if feasible:
        selected = max(feasible, key=lambda name:(feasible[name]['pooled']['macro_f1'], feasible[name]['pooled']['accuracy'], feasible[name]['pooled']['per_class']['Medium']['recall'], name))
    else:
        selected = max(metrics, key=lambda name:(metrics[name]['pooled']['accuracy'], metrics[name]['pooled']['macro_f1'], name))
    save(out/'development_metrics.json', metrics)
    pd.concat(development_predictions, ignore_index=True).to_csv(out/'development_predictions.csv', index=False)
    save(out/'selection_frozen_before_2025.json', dict(selected=selected, parameters=metrics[selected]['parameters'],
        frozen_at=datetime.now(timezone.utc).isoformat(), feasible_candidates=list(feasible), fallback_used=not bool(feasible),
        final_year_used_for_selection=False, year_2026_used=False))
    print('Frozen selected configuration:', selected, flush=True)
    context = historical.add_features(raw, original.engineer_fast(raw))
    verify_frame(context, saved, features+['Year', 'Risk_Label', 'Prediction_Cutoff', 'Historical_P33_Acres', 'Historical_P67_Acres', 'Overlap_Acres'])
    verify_frame(context[context.Year <= 2024], development, features+['Risk_Label'])
    modified = raw.copy()
    modified.loc[modified.Year == 2025, ['Land_Size_Acres', 'Expected_Production_kg']] *= 100
    perturbation = historical.add_features(modified, original.engineer_fast(modified))
    verify_frame(perturbation[perturbation.Year <= 2024], development, features+['Risk_Label', 'Historical_P33_Acres', 'Historical_P67_Acres', 'Overlap_Acres'])
    model, final_predictions, final = fitted(context, 2025, features, metrics[selected]['parameters'])
    final_predictions.to_csv(out/'final_2025_predictions.csv', index=False)
    selected_dev = pd.concat(development_predictions, ignore_index=True)
    selected_dev = selected_dev[selected_dev.Candidate == selected].drop(columns='Candidate')
    pool = pd.concat([selected_dev, final_predictions], ignore_index=True)
    pool.to_csv(out/'selected_historical_predictions.csv', index=False)
    matched = pool.merge(baseline_predictions.rename(columns={'Prediction':'XGBoost_Prediction'}),
                         on=['Record_ID', 'Year', 'Risk_Label'], validate='one_to_one')
    assert len(matched) == len(pool) == len(baseline_predictions)
    matched.to_csv(out/'matched_predictions.csv', index=False)
    xgb_metrics = {str(y):original.metric(g, g.XGBoost_Prediction) for y,g in matched.groupby('Year')}
    xgb_metrics['pooled'] = original.metric(matched, matched.XGBoost_Prediction)
    cb_metrics = dict(metrics[selected]['folds'], **{'2025':final, 'pooled':original.metric(pool, pool.Prediction)})
    detailed = {}
    for year, group in matched.groupby('Year'):
        detailed[str(year)] = {f'{district}/{season}':dict(records=len(g), catboost=original.metric(g,g.Prediction), xgboost=original.metric(g,g.XGBoost_Prediction))
                              for (district,season),g in group.groupby(['District','Season'])}
    for year in [2023, 2024, 2025]:
        selected_model = model if year == 2025 else cache[(selected,year)]
        joblib.dump(selected_model, out/f'catboost_pipeline_through_{year-1}.joblib')
        joblib.dump(selected_model.named_steps['preprocessing'], out/f'preprocessing_through_{year-1}.joblib')
        selected_model.named_steps['classifier'].save_model(str(out/f'catboost_through_{year-1}.cbm'))
        for family, values in [('catboost',cb_metrics),('xgboost',xgb_metrics)]:
            pd.DataFrame(values[str(year)]['confusion_matrix'], index=LABELS, columns=LABELS).to_csv(out/f'{family}_{year}_confusion_matrix.csv')
    for family, values in [('catboost',cb_metrics),('xgboost',xgb_metrics)]:
        pd.DataFrame(values['pooled']['confusion_matrix'], index=LABELS, columns=LABELS).to_csv(out/f'{family}_pooled_confusion_matrix.csv')
    # Verify the final artifact can be loaded and reproduces its held-year predictions.
    _, test = cohort(context, 2025)
    loaded = joblib.load(out/'catboost_pipeline_through_2024.joblib')
    assert np.array_equal(np.array(LABELS)[loaded.predict(test[features]).astype(int).ravel()], final_predictions.Prediction)
    assert all(sha(Path(p)) == h for p,h in hashes.items())
    save(out/'verification.json', dict(saved_features_labels_identical=True, matching_record_ids=True,
        strict_cutoff_order=True, district_perturbation_passed=True, future_2025_perturbation_passed=True,
        preprocessing_training_only=True, categorical_target_statistics_training_only=True,
        target_components_excluded=schema['excluded'], original_files_unchanged=True, model_reload_predictions_identical=True,
        historical_availability_verified=False))
    save(out/'feature_schema.json', dict(features=features, categorical=base.CAT, label_order=LABELS,
        preprocessing='Fixed missing category sentinel; numeric NaNs native; training-only CatBoost category statistics and quantization',
        excluded=schema['excluded']))
    save(out/'metrics.json', dict(selected=selected, catboost=cb_metrics, xgboost=xgb_metrics, district_season=detailed,
        excluded_by_year=context[~context.Risk_Label.isin(LABELS)].Year.value_counts().sort_index().to_dict(),
        source_records=15090, records_2026_used=0, source_sha256=hashes[str(source)]))
    save(out/'environment.json', dict(python=platform.python_version(), catboost=catboost.__version__,
        sklearn=sklearn.__version__, pandas=pd.__version__, numpy=np.__version__, joblib=joblib.__version__))
    command = 'python -m ml.training.compare_catboost train --source <authorized-original-ASC.csv> --features <authorized-features.csv> --baseline-predictions <matched-XGBoost-predictions.csv> --output-dir <new-private-directory>'
    (out/'reproduce.txt').write_text(command+'\nUse a new nonexistent output directory; install the recorded environment versions.\n', encoding='utf-8')
    save(out/'artifact_manifest.json', {p.name:sha(p) for p in out.iterdir() if p.is_file()})
    print(json.dumps(dict(selected=selected, catboost=cb_metrics['pooled'], xgboost=xgb_metrics['pooled'])), flush=True)


def evaluate(folder, feature_path, baseline_prediction_path=None):
    """Replay three reviewed private pipelines; no fitting, selection or tuning."""
    schema = json.loads((folder/'feature_schema.json').read_text())
    if schema['features'] != historical.FEATURES or schema['label_order'] != LABELS:
        raise ValueError('Saved feature/label definitions differ from historical CatBoost')
    frozen = json.loads((folder/'selection_frozen_before_2025.json').read_text())
    if frozen['selected'] != 'depth4_l2_10_weight2':
        raise ValueError('Unexpected frozen CatBoost selection')
    data = pd.read_csv(feature_path); data = data[data.Year <= 2025].copy()
    data['Prediction_Cutoff'] = pd.to_datetime(data.Prediction_Cutoff)
    saved = pd.read_csv(folder/'selected_historical_predictions.csv')
    saved = saved[saved.Year.isin([2023, 2024, 2025])]
    if data.Record_ID.duplicated().any() or saved.Record_ID.duplicated().any():
        raise ValueError('Duplicate evaluation identifiers')
    folds, baselines = {}, {}
    for year, count in [(2023, 1781), (2024, 2029), (2025, 2526)]:
        train, test = cohort(data, year)
        rows = saved[saved.Year == year]
        if len(rows) != count or set(rows.Record_ID) != set(test.Record_ID):
            raise ValueError(f'Historical eligible cohort changed for {year}')
        inputs = data.set_index('Record_ID').loc[rows.Record_ID]
        if not np.array_equal(inputs.Risk_Label.to_numpy(), rows.Risk_Label.to_numpy()):
            raise ValueError('Historical target labels differ')
        model = joblib.load(folder/f'catboost_pipeline_through_{year-1}.joblib')
        parameters = model.named_steps['classifier'].get_params()
        expected = dict(COMMON, depth=4, l2_leaf_reg=10, class_weights=[1, 2, 1], cat_features=base.CAT)
        if any(parameters.get(k) != v for k,v in expected.items()):
            raise ValueError('Saved CatBoost parameters differ from original selected configuration')
        prediction = np.array(LABELS)[model.predict(inputs[historical.FEATURES]).astype(int).ravel()]
        if not np.array_equal(prediction, rows.Prediction.to_numpy()):
            raise ValueError(f'{year} saved CatBoost predictions differ')
        folds[str(year)] = base.metric(rows, prediction)
        baselines[str(year)] = base.metric(rows, [train.Risk_Label.value_counts().idxmax()]*len(rows))
    result = {'folds': folds, 'pooled': base.metric(saved, saved.Prediction), 'majority_baselines': baselines}
    if baseline_prediction_path is not None:
        baseline = pd.read_csv(baseline_prediction_path)
        baseline = baseline[baseline.Year.isin([2023, 2024, 2025])]
        matched = saved.merge(baseline[['Record_ID','Year','Risk_Label','Prediction']],
                             on=['Record_ID','Year','Risk_Label'], validate='one_to_one', suffixes=('', '_XGBoost'))
        if len(matched) != len(saved) or len(baseline) != len(saved):
            raise ValueError('XGBoost comparison cohorts/labels differ')
        result['matched_xgboost'] = base.metric(matched, matched.Prediction_XGBoost)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    training = commands.add_parser('train', help='Explicit future original-protocol reproduction only')
    training.add_argument('--source', type=Path, required=True)
    training.add_argument('--features', type=Path, required=True)
    training.add_argument('--baseline-predictions', type=Path, required=True,
                          help='Private matched XGBoost predictions required by original development feasibility rule')
    training.add_argument('--output-dir', type=Path, required=True)
    replay = commands.add_parser('evaluate', help='Verify saved private CatBoost pipelines without training')
    replay.add_argument('--artifacts', type=Path, required=True)
    replay.add_argument('--features', type=Path, required=True)
    replay.add_argument('--baseline-predictions', type=Path)
    a = parser.parse_args()
    if a.command == 'train':
        run(a.output_dir.resolve(), a.source.resolve(), a.features.resolve(), a.baseline_predictions.resolve())
    else:
        print(json.dumps(evaluate(a.artifacts.resolve(), a.features.resolve(), a.baseline_predictions), indent=2))
