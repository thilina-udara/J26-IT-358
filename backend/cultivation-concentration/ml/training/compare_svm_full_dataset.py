"""Chronological SVM comparison; select on 2023/2024, evaluate 2025 once."""
import argparse,hashlib,json,time,warnings,platform
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.svm import LinearSVC,SVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
from sklearn.exceptions import ConvergenceWarning
from ml.preprocessing import concentration_common as base
LABELS=base.LABELS
SOURCE_SHA256='4397ddae6a3fabde06f1b9dc6fd42d40b3f0cc5a5275754621011e4cfcbb2bab'


def save(path,value):
    path.write_text(json.dumps(value,indent=2,default=lambda v: v.item() if isinstance(v,np.generic) else str(v))+'\n',encoding='utf-8')


def historical_inputs(source,features):
    """Explicit authorized inputs; verify unchanged source, labels and row order."""
    if hashlib.sha256(source.read_bytes()).hexdigest()!=SOURCE_SHA256:
        raise ValueError('Expected the unchanged full original ASC dataset, not sampled records')
    # The pinned bytes establish the original validated source. Parse dates
    # locally; do not couple SVM to legacy loaders or modify RF/shared code.
    raw=pd.read_csv(source)
    for column in ['Planting_Date','Expected_Harvest_Date']:
        raw[column]=pd.to_datetime(raw[column],format='%m/%d/%Y',errors='raise')
    expected=base.engineer_fast(raw[raw.Year<=2025].copy())
    data=pd.read_csv(features);data=data[data.Year<=2025].copy()
    data['Prediction_Cutoff']=pd.to_datetime(data.Prediction_Cutoff)
    expected['Prediction_Cutoff']=pd.to_datetime(expected.Prediction_Cutoff)
    columns=['Record_ID','Year','Risk_Label','Prediction_Cutoff',*base.FEATURES]
    pd.testing.assert_frame_equal(data[columns].reset_index(drop=True),expected[columns].reset_index(drop=True),
                                  check_dtype=False,rtol=1e-10,atol=1e-8)
    return data

def metric(rows,pred):
    m=base.metric(rows,pred);r=classification_report(rows.Risk_Label,pred,labels=LABELS,output_dict=True,zero_division=0)
    m.update(macro_precision=r['macro avg']['precision'],macro_recall=r['macro avg']['recall'])
    return m

def specs():
    out=[]
    for family in ['LinearSVC','RBF SVC']:
        for c in [.1,1.,10.]:
            for weight in [None,'balanced']:
                for gamma in ([None] if family=='LinearSVC' else ['scale',.01,.1]):
                    out.append({'id':f'{family.replace(" ","_")}_C{c}_gamma{gamma}_weight{weight}','family':family,'C':c,'gamma':gamma,'class_weight':weight})
    return out

def fit(spec,train,test):
    classifier=LinearSVC(C=spec['C'],class_weight=spec['class_weight'],dual='auto',max_iter=20000,random_state=42) if spec['family']=='LinearSVC' else SVC(C=spec['C'],gamma=spec['gamma'],class_weight=spec['class_weight'],kernel='rbf',cache_size=512)
    model=Pipeline([('preprocessing',base.preprocessing()),('classifier',classifier)])
    start=time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning);model.fit(train[base.FEATURES],train.Risk_Label)
    seconds=time.perf_counter()-start
    convergence=[str(w.message) for w in caught if issubclass(w.category,ConvergenceWarning)]
    assert np.allclose(model.named_steps['preprocessing'].named_transformers_['num'].named_steps['impute'].statistics_,train[base.NUM].median())
    scaler=model.named_steps['preprocessing'].named_transformers_['num'].named_steps['scale']
    assert np.allclose(scaler.mean_,train[base.NUM].mean())
    return model,model.predict(test[base.FEATURES]),seconds,convergence

def report(out,result):
    lines=['# Linear and RBF SVM: matched chronological comparison','',
        'Only the full original ASC dataset defines the features and research labels. This report describes a completed explicitly requested SVM run; previous models, datasets and production code remain unchanged.','',
        '**Holdout disclosure:** 2025 and 2026 were examined in earlier research. This search selects hyperparameters using 2023/2024 only and freezes both SVM choices before any new 2025 evaluation. 2025 is held out from this search, but is not a pristine unseen cohort for the overall project. 2026 is excluded entirely. Pooled scores include development selection folds and are not independent validation estimates.','',
        '## Pipeline and search','',
        'The unchanged 11 historical baseline features are used: '+', '.join(base.FEATURES)+'. OneHotEncoder(handle_unknown=ignore) handles District/Crop/Season; numeric median imputation and StandardScaler are fitted on each training fold only. One-hot blocks are left unscaled, matching the existing classifier preprocessing. No label ingredients (overlap acreage/P33/P67), IDs or year enter the models.','',
        'Labels and eligible IDs are reused unchanged from the original experiment: historical district/crop/season-specific +/-14-day acreage windows, prior recorded years with expected harvest before planting cutoff, linear historical P33/P67, Low below P33, High above P67, Medium including boundaries. Missing history or coincident quantiles remains insufficient_evidence and is excluded explicitly. Matara and Hambantota calculations remain separate. Registration/publication availability is assumed because actual timestamps are absent.','',
        'Development folds: train through 2022 -> test 2023 and train through 2023 -> test 2024. Search: C in {0.1, 1, 10}, class_weight in {None, balanced}; RBF gamma in {scale, 0.01, 0.1}. Six linear and eighteen RBF candidates. Select each family by pooled development accuracy, tie-break macro F1 and stable ID; candidates with convergence warnings are ineligible. LinearSVC uses dual=auto, max_iter=20000, seed 42. RBF SVC uses cache_size=512 MB and no iteration cap. No early stopping or search uses 2025/2026.','']
    def table(headers,rows):
        lines.append('| '+' | '.join(headers)+' |');lines.append('| '+' | '.join(['---']*len(headers))+' |');lines.extend('| '+' | '.join(map(str,row))+' |' for row in rows);lines.append('')
    table(['Candidate','Development accuracy','Development macro F1','Fit seconds (two folds)','Convergence warnings'],[(name,f"{m['pooled']['accuracy']:.2%}",f"{m['pooled']['macro_f1']:.4f}",f"{m['total_fit_seconds']:.2f}",len(m['convergence_warnings'])) for name,m in result['search'].items()])
    lines.extend(['## Frozen choices',''])
    for family,spec in result['selected'].items():lines.extend([f"{family}: `{json.dumps(spec,sort_keys=True)}`.",''])
    lines.extend(['## Matched measured results',''])
    table(['Year','Model','n','Accuracy','Macro precision','Macro recall','Macro F1','Low recall','Medium recall','High recall'],[(year,name,m['records'],f"{m['accuracy']:.2%}",*[f"{m[k]:.4f}" for k in ['macro_precision','macro_recall','macro_f1']],*[f"{m['per_class'][c]['recall']:.4f}" for c in LABELS]) for year,models in result['comparison'].items() for name,m in models.items()])
    lines.extend(['The majority baseline predicts the training-majority class Low for each fold. All methods have exactly the same IDs and target labels: 1,781 in 2023, 2,029 in 2024, 2,526 in 2025; pooled 6,336. Pooled metrics are recalculated from row-level predictions rather than averaged across percentages.','', '## Training times',''])
    table(['Family','2023 fold fit seconds','2024 fold fit seconds','Final through-2024 fit seconds','Entire development search fit seconds'],[(family,*[f"{result['fit_times'][family][str(y)]:.2f}" for y in [2023,2024,2025]],f"{sum(m['total_fit_seconds'] for m in result['search'].values() if m['spec']['family']==family):.2f}") for family in result['selected']])
    lines.extend(['Times include preprocessing and classifier fitting; they exclude feature loading, prediction and reporting. Selected development fits are refitted to save artifacts, and their times are recorded separately from search totals. Timing is machine-dependent.','', '## Interpretation',''])
    for family in result['selected']:
        pooled=result['comparison']['pooled'][family];final=result['comparison']['2025'][family]
        lines.extend([f"{family}: pooled accuracy **{pooled['accuracy']:.2%}**, macro F1 **{pooled['macro_f1']:.4f}**; final 2025 accuracy **{final['accuracy']:.2%}**, Medium recall **{final['per_class']['Medium']['recall']:.2%}**.",''])
    lines.extend(['A higher pooled score alone cannot establish superior future generalization because it includes model-selection folds. Consider 2025 accuracy, macro F1 and minority-category recall together. These scores concern rule-derived concentration, not independent economic outcomes or future unknown registrations. Do not switch candidates or tune after inspecting 2025; a new future cohort is needed for prospective verification.','', '## Confusion matrices','', 'Rows actual; columns predicted Low, Medium, High.',''])
    for year,models in result['comparison'].items():
        for name,m in models.items():
            lines.extend([f'### {year}: {name}','']);table(['Actual/predicted',*LABELS],[(c,*row) for c,row in zip(LABELS,m['confusion_matrix'])])
    lines.extend(['## Artifacts and verification','',f'New directory: `{out}`. Saves six SVM pipelines and six preprocessing artifacts (two families x three folds), candidate specifications, development predictions/metrics, frozen selection before 2025, matched final/pooled predictions, evaluation metrics and confusion matrices, fit times, dataset hash, exact environment and preprocessing schema, reproduction instructions and artifact manifest. Saved model predictions reproduce, preprocessing statistics use training rows only, and all previous inputs are hash-checked unchanged.','',
        'Reproduce from backend root with a fresh output directory:','', '```powershell', 'python -m ml.training.compare_svm_full_dataset train --source <authorized-original-ASC.csv> --features <authorized-historical-features.csv> --output-dir <new-directory>','```','', 'Backend regression results are recorded after the run.',''])
    (out/'svm_comparison.md').write_text('\n'.join(lines),encoding='utf-8')

def run(out,source,features):
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,features]}
    data=historical_inputs(source,features)
    development=data[data.Year<=2024].copy();out.mkdir(parents=True,exist_ok=False);candidates=specs()
    save(out/'search_specification.json',{'candidates':candidates,'selection_years':[2023,2024],'final_year':2025,'selection_rule':'pooled accuracy, macro F1 tie-break; no convergence warnings'})
    result={'search':{},'selected':{},'comparison':{},'fit_times':{},'dataset_sha256':hashes[str(source)]};devframes=[]
    for spec in candidates:
        frames=[];folds={};total=0.;warn=[]
        for year in [2023,2024]:
            train=development[(development.Year<year)&development.Risk_Label.isin(LABELS)];test=development[(development.Year==year)&development.Risk_Label.isin(LABELS)]
            assert train.Prediction_Cutoff.max()<test.Prediction_Cutoff.min();assert not set(train.Record_ID)&set(test.Record_ID)
            model,pred,seconds,caught=fit(spec,train,test);m=metric(test,pred);m['fit_seconds']=seconds;folds[str(year)]=m;total+=seconds;warn.extend(caught)
            frame=test[['Record_ID','Year','Risk_Label']].copy();frame['Prediction']=pred;frame['Candidate']=spec['id'];frames.append(frame)
        pooled=pd.concat(frames,ignore_index=True);devframes.append(pooled)
        result['search'][spec['id']]={'spec':spec,'folds':folds,'pooled':metric(pooled,pooled.Prediction),'total_fit_seconds':total,'convergence_warnings':warn}
        print(json.dumps({'candidate':spec['id'],'development_accuracy':result['search'][spec['id']]['pooled']['accuracy'],'fit_seconds':total,'convergence_warnings':len(warn)}),flush=True)
    for family in ['LinearSVC','RBF SVC']:
        eligible={name:m for name,m in result['search'].items() if m['spec']['family']==family and not m['convergence_warnings']}
        if not eligible:raise ValueError(f'No converged candidate for {family}')
        winner=max(eligible,key=lambda name:(eligible[name]['pooled']['accuracy'],eligible[name]['pooled']['macro_f1'],name));result['selected'][family]=eligible[winner]['spec']
    save(out/'selection_frozen_before_2025.json',result['selected']);save(out/'development_metrics.json',result['search']);pd.concat(devframes,ignore_index=True).to_csv(out/'development_predictions.csv',index=False)
    print('Frozen selections',json.dumps(result['selected']),flush=True)
    svmframes=[]
    for family,spec in result['selected'].items():
        result['fit_times'][family]={}
        for year in [2023,2024,2025]:
            train=data[(data.Year<year)&data.Risk_Label.isin(LABELS)];test=data[(data.Year==year)&data.Risk_Label.isin(LABELS)]
            assert train.Prediction_Cutoff.max()<test.Prediction_Cutoff.min()
            model,pred,seconds,caught=fit(spec,train,test);assert not caught
            if year<2025:
                previous=pd.concat(devframes)
                previous=previous[(previous.Candidate==spec['id'])&(previous.Year==year)];assert np.array_equal(pred,previous.Prediction)
            result['fit_times'][family][str(year)]=seconds;stem='linear_svc' if family=='LinearSVC' else 'rbf_svc'
            joblib.dump(model,out/f'{stem}_through_{year-1}.joblib');joblib.dump(model.named_steps['preprocessing'],out/f'{stem}_preprocessing_through_{year-1}.joblib')
            frame=test[['Record_ID','Year','District','Crop','Season','Risk_Label']].copy();frame['Prediction']=pred;frame['Model']=family;svmframes.append(frame)
    svm=pd.concat(svmframes,ignore_index=True);svm.to_csv(out/'svm_out_of_time_predictions.csv',index=False)
    common=svm[svm.Model=='LinearSVC'][['Record_ID','Year','Risk_Label']]
    assert set(common.Record_ID)==set(svm[svm.Model=='RBF SVC'].Record_ID)
    majority_frames=[]
    for year in [2023,2024,2025]:
        training=data[(data.Year<year)&data.Risk_Label.isin(LABELS)]
        majority_class=training.Risk_Label.value_counts().idxmax()
        if majority_class!='Low':
            raise ValueError('Historical majority baseline changed; expected training-majority Low')
        frame=common[common.Year==year].copy();frame['Prediction']=majority_class;frame['Model']='Majority baseline'
        majority_frames.append(frame)
    comparison=pd.concat([svm,*majority_frames],ignore_index=True);comparison.to_csv(out/'matched_predictions.csv',index=False)
    for year in [2023,2024,2025]:result['comparison'][str(year)]={name:metric(g,g.Prediction) for name,g in comparison[comparison.Year==year].groupby('Model')}
    result['comparison']['pooled']={name:metric(g,g.Prediction) for name,g in comparison.groupby('Model')}
    for family in result['selected']:
        assert not svm[svm.Model==family].Record_ID.duplicated().any()
    save(out/'metrics.json',result);save(out/'feature_schema.json',{'features':base.FEATURES,'categorical':base.CAT,'numeric':base.NUM,'labels':LABELS,'historical_labels_and_cohorts_unchanged':True});save(out/'input_hashes.json',hashes)
    import sklearn
    save(out/'environment.json',{'python':platform.python_version(),'sklearn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__,'joblib':joblib.__version__})
    for year,models in result['comparison'].items():
        for name,m in models.items():pd.DataFrame(m['confusion_matrix'],index=LABELS,columns=LABELS).to_csv(out/f'{year}_{name.replace(" ","_")}_confusion_matrix.csv')
    (out/'reproduce.txt').write_text('python -m ml.training.compare_svm_full_dataset train --source <authorized-original-ASC.csv> --features <authorized-historical-features.csv> --output-dir <new-directory>\nFresh directory required.\n',encoding='utf-8')
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    report(out,result);save(out/'artifact_manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
    print(json.dumps({'selected':result['selected'],'final_2025':result['comparison']['2025'],'pooled':result['comparison']['pooled']}),flush=True)

def evaluate(folder,features):
    """Replay all six reviewed private SVM pipelines; never fit or select models."""
    if json.loads((folder/'feature_schema.json').read_text())['features']!=base.FEATURES:
        raise ValueError('Saved SVM feature schema differs from historical baseline')
    data=pd.read_csv(features);data=data[data.Year<=2025].copy()
    if data.Record_ID.duplicated().any():raise ValueError('Duplicate feature IDs')
    saved=pd.read_csv(folder/'svm_out_of_time_predictions.csv')
    result={};cohorts=[]
    for family,stem in [('LinearSVC','linear_svc'),('RBF SVC','rbf_svc')]:
        selected=saved[(saved.Model==family)&saved.Year.isin([2023,2024,2025])].copy()
        if selected.Record_ID.duplicated().any():raise ValueError('Duplicate prediction IDs')
        cohorts.append(set(selected.Record_ID));folds={}
        for year,count in [(2023,1781),(2024,2029),(2025,2526)]:
            rows=selected[selected.Year==year]
            expected=data[(data.Year==year)&data.Risk_Label.isin(LABELS)]
            if len(rows)!=count or set(rows.Record_ID)!=set(expected.Record_ID):
                raise ValueError(f'Historical eligible cohort changed for {year}')
            inputs=data.set_index('Record_ID').loc[rows.Record_ID]
            if not np.array_equal(inputs.Risk_Label.to_numpy(),rows.Risk_Label.to_numpy()):
                raise ValueError('Historical target labels differ')
            model=joblib.load(folder/f'{stem}_through_{year-1}.joblib')
            prediction=model.predict(inputs[base.FEATURES])
            if not np.array_equal(prediction,rows.Prediction.to_numpy()):
                raise ValueError(f'{family} {year} saved predictions differ')
            folds[str(year)]=metric(rows,prediction)
        result[family]={'folds':folds,'pooled':metric(selected,selected.Prediction)}
    if cohorts[0]!=cohorts[1]:raise ValueError('SVM evaluation cohorts differ')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    commands=p.add_subparsers(dest='command',required=True)
    training=commands.add_parser('train',help='Explicit future reproduction only; never required for saved evaluation')
    training.add_argument('--source',type=Path,required=True,help='Authorized unchanged original ASC CSV')
    training.add_argument('--features',type=Path,required=True,help='Authorized original historical features/labels CSV')
    training.add_argument('--output-dir',type=Path,required=True,help='New nonexistent private output directory')
    replay=commands.add_parser('evaluate',help='Replay reviewed private saved pipelines without training')
    replay.add_argument('--artifacts',type=Path,required=True)
    replay.add_argument('--features',type=Path,required=True)
    a=p.parse_args()
    if a.command=='train':run(a.output_dir.resolve(),a.source.resolve(),a.features.resolve())
    else:print(json.dumps(evaluate(a.artifacts.resolve(),a.features.resolve()),indent=2))
