"""Inference-only matched ensemble search; freeze before final 2025 evaluation."""
import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from ml.ensemble_decisions import LABELS, combine, error_overlap, validate
from ml.training.train_updated_asc import ROOT, save
from ml.training.train_full_original_dataset import metric
from ml.training.compare_catboost import cohort

XGB = ROOT/'models/experimental/historical_feature_improvement/v1_20261009'
CB = ROOT/'models/experimental/catboost_comparison/v1_20261009'
CANDIDATES = {
    'equal_average':dict(method='average', xgboost_weight=.5),
    'average_xgb25':dict(method='average', xgboost_weight=.25),
    'average_xgb75':dict(method='average', xgboost_weight=.75),
    **{f'disagree_{rule}':dict(method='disagreement',rule=rule) for rule in
       ['prefer_xgboost','prefer_catboost','higher_confidence','prefer_medium']},
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probabilities(model, test, features):
    classes = list(model.classes_)
    assert sorted(classes) == [0,1,2]
    values = np.asarray(model.predict_proba(test[features]))[:, [classes.index(i) for i in range(3)]]
    return validate(values), dict(saved_class_order=[int(c) for c in classes], aligned_labels=LABELS.tolist())


def infer(context, years, features):
    frames, cache, ordering, majority = [], {}, {}, {}
    for year in years:
        train, test = cohort(context, year)
        xmodel = joblib.load(XGB/f'selected_xgboost_through_{year-1}.joblib')
        cmodel = joblib.load(CB/f'catboost_pipeline_through_{year-1}.joblib')
        xp, xo = probabilities(xmodel, test, features)
        cp, co = probabilities(cmodel, test, features)
        ordering[str(year)] = dict(xgboost=xo,catboost=co)
        # Latest XGBoost has no post-probability Medium multiplier.
        assert json.loads((XGB/'feature_schema.json').read_text())['medium_probability_multiplier'] == 1
        for directory, values in [(XGB,xp),(CB,cp)]:
            saved = pd.read_csv(directory/'selected_historical_predictions.csv')
            saved = saved[saved.Year==year]
            reproduced=test[['Record_ID','Year','Risk_Label']].copy()
            reproduced['Reproduced']=LABELS[values.argmax(axis=1)]
            check=reproduced.merge(saved,on=['Record_ID','Year','Risk_Label'],validate='one_to_one')
            assert len(check)==len(test)==len(saved) and check.Reproduced.eq(check.Prediction).all()
        frame = test[['Record_ID','Year','District','Crop','Season','Risk_Label']].copy()
        for prefix,values in [('XGBoost',xp),('CatBoost',cp)]:
            for index,label in enumerate(LABELS): frame[f'{prefix}_P_{label}']=values[:,index]
        frames.append(frame)
        cache[year]=(test,xp,cp)
        major=train.Risk_Label.value_counts().idxmax()
        majority[str(year)]=dict(class_selected_from_training=major,records=len(test),
            accuracy=float(test.Risk_Label.eq(major).mean()),retrospective_majority_prevalence=float(test.Risk_Label.value_counts(normalize=True).max()))
    return pd.concat(frames,ignore_index=True),cache,ordering,majority


def evaluate_candidates(cache):
    results, frames = {}, []
    for name,spec in CANDIDATES.items():
        folds, pieces = {}, []
        for year,(test,xp,cp) in cache.items():
            pred=combine(xp,cp,spec);folds[str(year)]=metric(test,pred)
            frame=test[['Record_ID','Year','Risk_Label']].copy();frame['Prediction']=pred;frame['Candidate']=name
            pieces.append(frame)
        pool=pd.concat(pieces,ignore_index=True);frames.append(pool)
        results[name]=dict(specification=spec,folds=folds,pooled=metric(pool,pool.Prediction))
    return results,pd.concat(frames,ignore_index=True)


def best(names,results,control):
    feasible=[name for name in names if results[name]['pooled']['accuracy']>=control['pooled']['accuracy']-.02
              and all(results[name]['folds'][year]['accuracy']>=control['folds'][year]['accuracy']-.03 for year in ['2023','2024'])]
    choices=feasible or list(names)
    return max(choices,key=lambda name:(results[name]['pooled']['macro_f1'],results[name]['pooled']['accuracy'],results[name]['pooled']['per_class']['Medium']['recall'],name))


def run(out):
    protected=[ROOT/'data/legacy/official_farmer_cultivation_2020_2026.csv',ROOT/'data/farmer/farmer_cultivation_2020_2026.csv',
        *[p for directory in [XGB,CB] for p in directory.rglob('*') if p.is_file()],
        *[p for p in (ROOT/'app').rglob('*.py')],ROOT/'ml/prospective_evaluation.py']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in protected}
    assert sha(ROOT/'data/legacy/official_farmer_cultivation_2020_2026.csv')==json.loads((XGB/'metrics.json').read_text())['source_sha256']
    for directory in [XGB,CB]:
        assert all(sha(directory/name)==value for name,value in json.loads((directory/'artifact_manifest.json').read_text()).items())
    schema=json.loads((XGB/'feature_schema.json').read_text()); features=schema['features']
    assert features==json.loads((CB/'feature_schema.json').read_text())['features']
    assert not set(features)&set(schema['excluded'])
    context=pd.read_csv(XGB/'features_and_labels_2020_2025.csv')
    assert context.Year.max()==2025 and not context.Record_ID.duplicated().any()
    context['Prediction_Cutoff']=pd.to_datetime(context.Prediction_Cutoff)
    out.mkdir(parents=True,exist_ok=False)
    save(out/'search_specification.json',dict(candidates=CANDIDATES,development=[2023,2024],final=2025,excluded=2026,
        selection='Max pooled development macro F1, then accuracy, Medium recall; pooled accuracy >= XGBoost minus 2pp and each fold >= XGBoost minus 3pp. If none feasible in a method family, rank all by the same development criteria.',
        confidence_note='Class-weighted raw probability maxima are not independently calibrated confidence estimates.',
        prior_exposure='2025 and 2026 already exposed in earlier experiments; not pristine project holdouts.'))
    save(out/'input_hashes.json',hashes)
    devprob,cache,ordering,majority=infer(context[context.Year<=2024],[2023,2024],features)
    results,devpred=evaluate_candidates(cache)
    control=results['disagree_prefer_xgboost']
    choices=dict(equal_average='equal_average', weighted_average=best(['equal_average','average_xgb25','average_xgb75'],results,control),
                 disagreement=best([name for name in CANDIDATES if name.startswith('disagree_')],results,control))
    selected=best(CANDIDATES,results,control)
    save(out/'development_metrics.json',results);devpred.to_csv(out/'development_predictions.csv',index=False)
    devprob.to_csv(out/'development_probabilities.csv',index=False)
    save(out/'selection_frozen_before_2025.json',dict(selected=selected,selected_methods=choices,
        specifications={name:CANDIDATES[name] for name in set([selected,*choices.values()])},
        frozen_at=datetime.now(timezone.utc).isoformat(),year_2025_used_for_selection=False,year_2026_used=False))
    print('Frozen selections:',json.dumps(dict(selected=selected,methods=choices)),flush=True)
    finalprob,finalcache,finalordering,finalmajority=infer(context,[2025],features)
    finalprob.to_csv(out/'final_2025_probabilities.csv',index=False)
    ordering.update(finalordering);majority.update(finalmajority);cache.update(finalcache)
    poolprob=pd.concat([devprob,finalprob],ignore_index=True);poolprob.to_csv(out/'matched_probabilities.csv',index=False)
    report_models={'XGBoost':dict(method='disagreement',rule='prefer_xgboost'),
                   'CatBoost':dict(method='disagreement',rule='prefer_catboost'),
                   **{label:CANDIDATES[name] for label,name in choices.items()},'selected_ensemble':CANDIDATES[selected]}
    metrics,overlap,frames={}, {},[]
    for label,spec in report_models.items():
        folds,pieces={},[]
        for year,(test,xp,cp) in cache.items():
            pred=combine(xp,cp,spec);folds[str(year)]=metric(test,pred)
            frame=test[['Record_ID','Year','District','Crop','Season','Risk_Label']].copy();frame['Prediction']=pred;frame['Model']=label;pieces.append(frame)
            pd.DataFrame(folds[str(year)]['confusion_matrix'],index=LABELS,columns=LABELS).to_csv(out/f'{label}_{year}_confusion_matrix.csv')
        pool=pd.concat(pieces,ignore_index=True);folds['pooled']=metric(pool,pool.Prediction);frames.append(pool);metrics[label]=folds
        pd.DataFrame(folds['pooled']['confusion_matrix'],index=LABELS,columns=LABELS).to_csv(out/f'{label}_pooled_confusion_matrix.csv')
    pd.concat(frames,ignore_index=True).to_csv(out/'evaluation_predictions.csv',index=False)
    for name,frame in [(str(y),poolprob[poolprob.Year==y]) for y in [2023,2024,2025]]+[('pooled',poolprob)]:
        xp=frame[[f'XGBoost_P_{label}' for label in LABELS]].to_numpy();cp=frame[[f'CatBoost_P_{label}' for label in LABELS]].to_numpy()
        overlap[name]=dict(overall=error_overlap(frame.Risk_Label,xp,cp),by_class={})
        for label in LABELS:
            mask=frame.Risk_Label.eq(label).to_numpy();overlap[name]['by_class'][label]=error_overlap(frame.loc[mask,'Risk_Label'],xp[mask],cp[mask])
    save(out/'metrics.json',dict(models=metrics,selected=selected,selected_methods=choices,error_overlap=overlap,majority_baselines=majority,records_2026_used=0))
    save(out/'class_ordering.json',ordering)
    save(out/'ensemble_specification.json',dict(features=features,label_order=LABELS.tolist(),decision=CANDIDATES[selected],
        base_artifacts={str(y):dict(xgboost=str((XGB/f'selected_xgboost_through_{y-1}.joblib').relative_to(ROOT)),
                                    catboost=str((CB/f'catboost_pipeline_through_{y-1}.joblib').relative_to(ROOT))) for y in [2023,2024,2025]},
        original_model_hashes=hashes))
    assert all(sha(ROOT/p)==value for p,value in hashes.items())
    save(out/'verification.json',dict(cohort_labels_exact_match=True,standalone_predictions_reproduced=True,
        aligned_probability_classes=True,probabilities_finite_normalized=True,strict_training_cutoff_order=True,
        model_fits_performed=0,source_features_unchanged=True,protected_inputs_unchanged=True,
        historical_registration_availability_verified=False))
    save(out/'environment.json',dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,joblib=joblib.__version__))
    (out/'reproduce.txt').write_text(f'.\\.venv\\Scripts\\python.exe -m ml.training.evaluate_xgboost_catboost_ensemble --output-dir {out.relative_to(ROOT).as_posix()}\nUse a new nonexistent directory for reruns.\n',encoding='utf-8')
    save(out/'artifact_manifest.json',{p.name:sha(p) for p in out.iterdir() if p.is_file()})
    print(json.dumps(dict(selected=selected,metrics=metrics['selected_ensemble'],error_overlap=overlap['pooled'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    run(parser.parse_args().output_dir.resolve())
