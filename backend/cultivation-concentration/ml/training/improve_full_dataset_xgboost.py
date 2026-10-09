"""Select XGBoost on 2023/2024 only, then evaluate frozen choice on 2025."""
import argparse,hashlib,json,platform
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from xgboost import XGBClassifier
from ml.training import train_asc_2020_2026 as base
from ml.training import train_full_original_dataset as original
from ml.training import train_updated_asc as exp
ROOT=exp.ROOT;LABELS=exp.LABELS
EXTRA=['Historical_Mean_Window_Plan_Count','Historical_Mean_Plan_Acres','Overlap_Count_Relative_To_History',
       'Historical_Window_Count_Per_Reference_Year','Planting_Month_Sin','Planting_Month_Cos','Harvest_Month_Sin','Harvest_Month_Cos']

def add_context(raw,features):
    """Historical registration-count context, never label acreage or percentile inputs."""
    out=features.copy().set_index('Record_ID');lookup={}
    for _,g in raw.groupby(base.CAT,sort=False):
        cache={}
        for p in g.itertuples(index=False):
            past=g[(g.Year<p.Year)&(g.Expected_Harvest_Date<p.Planting_Date)]
            key=(p.Year,len(past))
            if key not in cache:
                counts=[]
                for _,annual in past.groupby('Year'):
                    ds=np.sort(annual.Expected_Harvest_Date.to_numpy(dtype='datetime64[D]'));anchors=np.unique(ds)
                    counts.extend((np.searchsorted(ds,anchors+np.timedelta64(14,'D'),side='right')-np.searchsorted(ds,anchors-np.timedelta64(14,'D'),side='left')).tolist())
                cache[key]=(float(np.mean(counts)) if counts else np.nan,float(past.Land_Size_Acres.mean()) if len(past) else np.nan,int(past.Year.nunique()))
            mean_count,mean_acres,years=cache[key];row=out.loc[p.Record_ID]
            lookup[p.Record_ID]=[mean_count,mean_acres,float(row.Overlap_Plan_Count/mean_count) if mean_count>0 else np.nan,
                float(row.Past_Window_Count/years) if years else np.nan,*[v for month in [row.Planting_Month,row.Harvest_Month] for v in [np.sin(2*np.pi*month/12),np.cos(2*np.pi*month/12)]]]
    extra=pd.DataFrame.from_dict(lookup,orient='index',columns=EXTRA)
    return out.join(extra).reset_index()

def specs():
    candidates=[{'id':'baseline','features':'base','balanced':False,'parameters':{}}]
    configs=[('shallow',dict(n_estimators=300,max_depth=2,learning_rate=.04,min_child_weight=8,gamma=.15,reg_alpha=.2,reg_lambda=8,subsample=.85,colsample_bytree=.9)),
        ('moderate',dict(n_estimators=300,max_depth=3,learning_rate=.04,min_child_weight=6,gamma=.1,reg_alpha=.1,reg_lambda=5,subsample=.85,colsample_bytree=.9)),
        ('deeper',dict(n_estimators=250,max_depth=4,learning_rate=.04,min_child_weight=10,gamma=.2,reg_alpha=.3,reg_lambda=10,subsample=.85,colsample_bytree=.9))]
    for name,params in configs:
        for feature in ['base','context']:
            for balanced in [False,True]:candidates.append({'id':f'{name}_{feature}_{"balanced" if balanced else "uniform"}','features':feature,'balanced':balanced,'parameters':params})
    return candidates

def pipeline(spec):
    numeric=base.NUM+(EXTRA if spec['features']=='context' else [])
    processor=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),base.CAT),
        ('num',Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),('scale',StandardScaler())]),numeric)])
    params=dict(n_estimators=200,max_depth=3,learning_rate=.05,objective='multi:softprob',num_class=3,eval_metric='mlogloss',tree_method='hist',random_state=42,n_jobs=1)
    params.update(spec['parameters'])
    return Pipeline([('preprocessing',processor),('classifier',XGBClassifier(**params))])

def fit_predict(spec,train,test):
    features=base.FEATURES+(EXTRA if spec['features']=='context' else [])
    model=pipeline(spec);y=train.Risk_Label.map(dict(zip(LABELS,range(3))));kwargs={}
    if spec['balanced']:
        counts=y.value_counts();kwargs['classifier__sample_weight']=y.map({k:len(y)/(3*v) for k,v in counts.items()}).to_numpy()
    model.fit(train[features],y,**kwargs)
    assert np.allclose(model.named_steps['preprocessing'].named_transformers_['num'].named_steps['impute'].statistics_,train[base.NUM+(EXTRA if spec['features']=='context' else [])].median())
    pred=np.array(LABELS)[model.predict(test[features]).astype(int)]
    return model,pred

def run(out):
    md=ROOT/'models/experimental/full_original_dataset/v1_20261009';source=ROOT/'data/legacy/official_farmer_cultivation_2020_2026.csv'
    watched=[source,*[p for p in md.iterdir() if p.is_file()]];hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    raw=pd.read_csv(source);raw=raw[raw.Year<=2025].copy()
    for c in ['Planting_Date','Expected_Harvest_Date']:raw[c]=pd.to_datetime(raw[c],format='%m/%d/%Y')
    saved=pd.read_csv(md/'features_and_labels.csv');saved=saved[saved.Year<=2025].copy()
    assert hashes[str(source)]==json.loads((md/'metrics.json').read_text())['original_validation']['sha256']
    for c in ['Prediction_Cutoff','Reference_Latest_Harvest']:saved[c]=pd.to_datetime(saved[c])
    # Build development context without exposing 2025 data to selection.
    development=add_context(raw[raw.Year<=2024],saved[saved.Year<=2024])
    out.mkdir(parents=True,exist_ok=False)
    candidate_specs=specs();exp.save(out/'preregistered_candidates.json',{'selection_folds':[2023,2024],'final_year':2025,'selection_rule':'maximize pooled 2023/2024 accuracy; tie-break pooled macro F1, then stable candidate ID','candidates':candidate_specs,'excluded_year':2026})
    all_results={};dev_predictions=[]
    for spec in candidate_specs:
        candidate_frames=[];folds={}
        for year in [2023,2024]:
            train=development[(development.Year<year)&development.Risk_Label.isin(LABELS)];test=development[(development.Year==year)&development.Risk_Label.isin(LABELS)]
            assert train.Prediction_Cutoff.max()<test.Prediction_Cutoff.min()
            assert not set(train.Record_ID)&set(test.Record_ID)
            model,pred=fit_predict(spec,train,test);m=original.metric(test,pred);majority=train.Risk_Label.value_counts().idxmax();m['baseline']=original.metric(test,[majority]*len(test));folds[str(year)]=m
            frame=test[['Record_ID','Year','Risk_Label']].copy();frame['Prediction']=pred;frame['Candidate']=spec['id'];candidate_frames.append(frame)
        pooled=pd.concat(candidate_frames,ignore_index=True);all_results[spec['id']]={'folds':folds,'pooled':original.metric(pooled,pooled.Prediction),'specification':spec};dev_predictions.append(pooled)
        print(json.dumps({'candidate':spec['id'],'development_accuracy':all_results[spec['id']]['pooled']['accuracy'],'development_macro_f1':all_results[spec['id']]['pooled']['macro_f1']}),flush=True)
    selected=max(all_results,key=lambda name:(all_results[name]['pooled']['accuracy'],all_results[name]['pooled']['macro_f1'],name))
    exp.save(out/'development_metrics.json',all_results)
    pd.concat(dev_predictions,ignore_index=True).to_csv(out/'development_predictions.csv',index=False)
    # Persist an immutable selection record before making any 2025 predictions.
    exp.save(out/'selection_frozen_before_2025.json',{'selected':selected,'specification':all_results[selected]['specification'],'selected_using':[2023,2024],'selection_rule':'pooled accuracy, then macro F1','2025_used_for_selection':False,'2026_used':False})
    print('Frozen selection:',selected,flush=True)
    context=add_context(raw,saved)
    pd.testing.assert_frame_equal(development.reset_index(drop=True),context[context.Year<=2024].reset_index(drop=True))
    train=context[(context.Year<=2024)&context.Risk_Label.isin(LABELS)];test=context[(context.Year==2025)&context.Risk_Label.isin(LABELS)]
    assert train.Prediction_Cutoff.max()<test.Prediction_Cutoff.min()
    model,pred=fit_predict(all_results[selected]['specification'],train,test)
    joblib.dump(model,out/'selected_xgboost_through_2024.joblib');joblib.dump(model.named_steps['preprocessing'],out/'selected_preprocessing.joblib')
    baseline=original.metric(test,[train.Risk_Label.value_counts().idxmax()]*len(test));final=original.metric(test,pred);final['baseline']=baseline
    final['seasons']={s:original.metric(test[test.Season==s],pred[test.Season.eq(s)]) for s in ['Maha','Yala']}
    frame=test[['Record_ID','Year','District','Crop','Season','Risk_Label']].copy();frame['Prediction']=pred;frame.to_csv(out/'final_2025_predictions.csv',index=False)
    # Refit the already-selected fixed specification on each earlier fold to save its artifacts.
    for year in [2023,2024]:
        tr=development[(development.Year<year)&development.Risk_Label.isin(LABELS)];te=development[(development.Year==year)&development.Risk_Label.isin(LABELS)]
        fitted,check=fit_predict(all_results[selected]['specification'],tr,te)
        expected=pd.concat(dev_predictions).query('Candidate == @selected and Year == @year')
        assert np.array_equal(check,expected.Prediction)
        joblib.dump(fitted,out/f'selected_xgboost_through_{year-1}.joblib');joblib.dump(fitted.named_steps['preprocessing'],out/f'selected_preprocessing_through_{year-1}.joblib')
    pooled=pd.concat([pd.concat(dev_predictions).query('Candidate == @selected')[['Record_ID','Year','Risk_Label','Prediction']],frame[['Record_ID','Year','Risk_Label','Prediction']]],ignore_index=True)
    pooled.to_csv(out/'selected_historical_predictions.csv',index=False)
    old=json.loads((md/'metrics.json').read_text())
    result={'selected':selected,'development':all_results[selected],'final_2025':final,'pooled_selected':original.metric(pooled,pooled.Prediction),
        'prior_baseline':{'folds':{y:v['models']['XGBoost'] for y,v in old['folds'].items()},'pooled':old['pooled']['XGBoost']},
        'source_sha256':hashes[str(source)],'insufficient_by_year':saved[saved.Risk_Label=='insufficient_evidence'].Year.value_counts().sort_index().to_dict(),
        'disclosure':'2025 and 2026 already examined in prior research; 2025 held out from THIS search only. Pooled result includes selection folds and is not a pristine validation estimate.'}
    exp.save(out/'metrics.json',result);exp.save(out/'input_hashes.json',hashes)
    features=base.FEATURES+(EXTRA if all_results[selected]['specification']['features']=='context' else [])
    exp.save(out/'feature_schema.json',{'features':features,'extra_feature_definitions':{'Historical_Mean_Window_Plan_Count':'mean count in completed historical +/-14-day windows, same anchors/groups/cutoff as acreage history','Historical_Mean_Plan_Acres':'mean individual historical acres before cutoff, same group','Overlap_Count_Relative_To_History':'current overlap plan count / historical mean window plan count','Historical_Window_Count_Per_Reference_Year':'number of historical anchors / number of eligible reference years','cyclic_months':'sin/cos 2*pi*month/12'},'forbidden':['Risk_Label','Overlap_Acres','Historical_P33_Acres','Historical_P67_Acres','Record_ID','Year']})
    context.to_csv(out/'features_and_labels_2020_2025.csv',index=False)
    for title,m in [('final_2025',final),('pooled',result['pooled_selected']),*[(y,m) for y,m in all_results[selected]['folds'].items()]]:
        pd.DataFrame(m['confusion_matrix'],index=LABELS,columns=LABELS).to_csv(out/f'{title}_confusion_matrix.csv')
    import sklearn,xgboost
    exp.save(out/'environment.json',{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'xgboost':xgboost.__version__,'selected_model_parameters':model.named_steps['classifier'].get_params()})
    (out/'reproduce.txt').write_text('.venv\\Scripts\\python.exe -m ml.training.improve_full_dataset_xgboost --output-dir models/experimental/full_dataset_improvement/v2_reproduction\nUse a fresh output directory.\n',encoding='utf-8')
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    exp.save(out/'artifact_manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
    print(json.dumps({'selected':selected,'final_2025':final,'pooled':result['pooled_selected']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();run(a.output_dir.resolve())
