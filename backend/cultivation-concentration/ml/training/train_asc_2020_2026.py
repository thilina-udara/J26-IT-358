"""New retrospective ASC research model; never activates production gates."""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.cluster import KMeans, DBSCAN
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, balanced_accuracy_score, silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

ROOT=Path(__file__).resolve().parents[2]
LABELS=['Low','Medium','High']
CAT=['District','Crop','Season']
NUM=['Land_Size_Acres','Planting_Month','Harvest_Month','Overlap_Plan_Count','Own_Expected_Production_kg',
     'Past_Window_Count','Past_Mean_Window_Acres','Past_Mean_Window_Production_kg']
FEATURES=CAT+NUM
REQUIRED=['Record_ID',*CAT,'Year','Planting_Date','Expected_Harvest_Date','Land_Size_Acres',
          'Expected_Yield_kg_per_Acre','Expected_Production_kg']
ASSUMPTIONS=[
 'EXPERIMENTAL rule-derived acreage labels, not observed oversupply or price loss.',
 'Provenance is unverified: the existing project designates 2020–2025 farmer data synthetic prototype; owner reports ASC. Neither file has verified individual origins.',
 'Original submission/publication timestamps missing: hindsight replay assumes submission immediately before planting; same-date peers excluded.',
 'Historical observations assumed usable after expected harvest and before target-year January 1, with unknown publication lag.',
 'Current progressive registration is compared with completed historical windows; lead-time mismatch can bias Low counts.',
 'Recorded Maha/Yala and month/day/year dates are dataset conventions, not independently verified agricultural calendars.',
 'Overlapping cases are dependent; plan IDs do not establish unique farmer identities.',
 '2026 was evaluated once after selection, then included in the all-data refit: no untouched 2026 holdout remains.'
]


def load(paths):
    frames=[];metadata=[]
    for path in paths:
        raw=pd.read_csv(path)
        if not set(REQUIRED)<=set(raw):raise ValueError('Missing required columns')
        metadata.append(dict(path=str(path),rows=len(raw),headers=list(raw),types=raw.dtypes.astype(str).to_dict(),
            missing_values=int(raw.isna().sum().sum()),sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest()))
        frames.append(raw[REQUIRED])
    data=pd.concat(frames,ignore_index=True)
    raw_count=len(data);data=data.drop_duplicates().copy()
    for c in CAT:
        allowed={'District':['Matara','Hambantota'],'Crop':['Bandakka','Brinjal','Pumpkin','Corn','Mung Beans','Chillies'],'Season':['Maha','Yala']}[c]
        lookup={v.casefold():v for v in allowed}
        if c=='Crop':lookup.update({'okra':'Bandakka','mung bean':'Mung Beans','maize':'Corn'})
        data[c]=data[c].astype('string').str.strip().str.casefold().map(lookup)
    data['Record_ID']=data.Record_ID.astype('string').str.strip()
    before=len(data);data=data.drop_duplicates()
    if data.Record_ID.isna().any() or data.Record_ID.eq('').any() or data.Record_ID.duplicated().any():
        raise ValueError('Missing/conflicting duplicate plan ID; do not rename or silently merge')
    for c in ['Planting_Date','Expected_Harvest_Date']:
        data[c]=pd.to_datetime(data[c],format='%m/%d/%Y',errors='raise')
    for c in ['Year','Land_Size_Acres','Expected_Yield_kg_per_Acre','Expected_Production_kg']:
        data[c]=pd.to_numeric(data[c],errors='raise')
        if not np.isfinite(data[c]).all():raise ValueError('Invalid numeric values')
    if data.isna().any().any() or not data.Year.between(2020,2026).all() or (data.Year%1!=0).any():raise ValueError('Invalid required fields/year')
    if (data.Year!=data.Planting_Date.dt.year).any():raise ValueError('Recorded/planting year mismatch')
    if (data.Expected_Harvest_Date<data.Planting_Date).any() or (data.Land_Size_Acres<=0).any() or (data.Expected_Yield_kg_per_Acre<=0).any() or (data.Expected_Production_kg<0).any():raise ValueError('Invalid dates/acres/expected production')
    mismatch=~np.isclose(data.Land_Size_Acres*data.Expected_Yield_kg_per_Acre,data.Expected_Production_kg,rtol=1e-9,atol=1e-6)
    return data.sort_values(['Planting_Date','Record_ID']).reset_index(drop=True),dict(inputs=metadata,raw_rows=raw_count,
        exact_duplicates_removed=raw_count-before,normalized_duplicates_removed=before-len(data),unique_rows=len(data),
        year_counts={str(k):int(v) for k,v in data.Year.value_counts().sort_index().items()},production_formula_mismatch_count=int(mismatch.sum()))


def engineer(data):
    data=data.copy();data['Planting_Month']=data.Planting_Date.dt.month;data['Harvest_Month']=data.Expected_Harvest_Date.dt.month
    results=[];history_cache={}
    for _,p in data.iterrows():
        group=data.loc[(data.District==p.District)&(data.Crop==p.Crop)&(data.Season==p.Season)]
        # Earlier-year plans are eligible in the current window only if still active.
        peers=group.loc[(group.Planting_Date<p.Planting_Date)&(group.Expected_Harvest_Date>=p.Planting_Date)
             &((group.Expected_Harvest_Date-p.Expected_Harvest_Date).abs().dt.days<=14)]
        acres=float(peers.Land_Size_Acres.sum()+p.Land_Size_Acres)
        key=(int(p.Year),p.District,p.Crop,p.Season)
        if key not in history_cache:
            past=group.loc[(group.Year<p.Year)&(group.Expected_Harvest_Date<pd.Timestamp(int(p.Year),1,1))]
            windows=[];production=[]
            for _,annual in past.groupby('Year'):
                for anchor in sorted(annual.Expected_Harvest_Date.unique()):
                    members=annual.loc[(annual.Expected_Harvest_Date-anchor).abs().dt.days<=14]
                    windows.append(float(members.Land_Size_Acres.sum()));production.append(float(members.Expected_Production_kg.sum()))
            history_cache[key]=(windows,production)
        windows,production=history_cache[key]
        lower=upper=np.nan;label='insufficient_evidence'
        if windows:
            lower,upper=np.percentile(windows,[33,67],method='linear')
            if lower<upper:
                label='Low' if acres<lower and not np.isclose(acres,lower,rtol=1e-12,atol=1e-12) else 'High' if acres>upper and not np.isclose(acres,upper,rtol=1e-12,atol=1e-12) else 'Medium'
        results.append(dict(**{c:p[c] for c in ['Record_ID','Year',*CAT,'Land_Size_Acres','Planting_Month','Harvest_Month']},
            Overlap_Plan_Count=len(peers)+1,Overlap_Acres=acres,Overlap_Expected_Production_kg=float(peers.Expected_Production_kg.sum()+p.Expected_Production_kg),
            Own_Expected_Production_kg=float(p.Expected_Production_kg),Past_Window_Count=len(windows),
            Past_Mean_Window_Acres=float(np.mean(windows)) if windows else np.nan,
            Past_Mean_Window_Production_kg=float(np.mean(production)) if production else np.nan,
            Historical_P33_Acres=lower,Historical_P67_Acres=upper,Risk_Label=label))
    return pd.DataFrame(results)


def split(data):
    eligible=data.loc[data.Risk_Label.isin(LABELS)]
    return tuple(eligible.loc[eligible.Year.between(a,b)].copy() for a,b in [(2020,2024),(2025,2025),(2026,2026)])


def inputs(data):
    return data.loc[:,FEATURES]


def preprocessing():
    return ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),CAT),
        ('num',Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),('scale',StandardScaler())]),NUM)])


def models():
    return {'Random Forest':Pipeline([('preprocessing',preprocessing()),('classifier',RandomForestClassifier(n_estimators=300,random_state=42,n_jobs=1))]),
        'XGBoost':Pipeline([('preprocessing',preprocessing()),('classifier',XGBClassifier(n_estimators=200,max_depth=3,learning_rate=.05,objective='multi:softprob',num_class=3,eval_metric='mlogloss',tree_method='hist',random_state=42,n_jobs=1))])}


def metrics(model,data):
    y=data.Risk_Label.map({v:i for i,v in enumerate(LABELS)});pred=model.predict(inputs(data))
    report=classification_report(y,pred,labels=[0,1,2],target_names=LABELS,output_dict=True,zero_division=0)
    return dict(accuracy=accuracy_score(y,pred),balanced_accuracy=balanced_accuracy_score(y,pred),macro_precision=report['macro avg']['precision'],
        macro_recall=report['macro avg']['recall'],macro_f1=report['macro avg']['f1-score'],per_class={c:report[c] for c in LABELS},
        confusion_matrix=confusion_matrix(y,pred,labels=[0,1,2]).tolist())


def clustering(data):
    out={}
    for district,rows in data.loc[data.Year<=2024].groupby('District'):
        processor=preprocessing();x=processor.fit_transform(inputs(rows));reports={}
        for name,model in [('K-Means',KMeans(n_clusters=3,n_init=10,random_state=42)),('DBSCAN',DBSCAN(eps=1,min_samples=5))]:
            labels=model.fit_predict(x);valid=labels!=-1;unique=set(labels[valid]);score=None
            if len(unique)>1 and valid.sum()>len(unique):score=float(silhouette_score(x[valid],labels[valid]))
            profiles={}
            for label in sorted(set(labels)):
                group=rows.loc[labels==label]
                profiles[str(int(label))]=dict(size=len(group),crops=group.Crop.value_counts().to_dict(),
                    mean_own_acres=float(group.Land_Size_Acres.mean()),mean_overlap_plan_count=float(group.Overlap_Plan_Count.mean()),
                    mean_overlap_acres=float(group.Overlap_Acres.mean()),harvest_months=group.Harvest_Month.value_counts().sort_index().to_dict())
            reports[name]=dict(cluster_count=len(unique),silhouette=score,noise_percentage=float((labels==-1).mean()*100),profiles=profiles)
        out[district]=reports
    return out


def manifest(output):
    output=Path(output)
    value=dict(environment=dict(python=platform.python_version(),sklearn=sklearn.__version__,xgboost=xgboost.__version__,
        pandas=pd.__version__,numpy=np.__version__,joblib=joblib.__version__),
        config={name:model.named_steps['classifier'].get_params() for name,model in models().items()},
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file() and p.name!='artifact_manifest.json'})
    with (output/'artifact_manifest.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,sort_keys=True)


def run(paths,output):
    # Exclusive version directory: no existing artifacts are overwritten.
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    raw,audit=load(paths);data=engineer(raw);train,validation,test=split(data)
    if any(frame.empty for frame in (train,validation,test)) or set(train.Risk_Label)!=set(LABELS):raise ValueError('Inadequate chronological coverage')
    fitted=models();validation_metrics={}
    for name,model in fitted.items():
        model.fit(inputs(train),train.Risk_Label.map({v:i for i,v in enumerate(LABELS)}))
        validation_metrics[name]=metrics(model,validation)
    selected=max(validation_metrics,key=lambda n:(validation_metrics[n]['macro_f1'],validation_metrics[n]['balanced_accuracy']))
    # Configuration/selection is fixed above; only now evaluate held-out 2026.
    test_metrics={name:metrics(model,test) for name,model in fitted.items()}
    importance={name:dict(sorted(zip(model.named_steps['preprocessing'].get_feature_names_out(),
        map(float,model.named_steps['classifier'].feature_importances_)),key=lambda pair:pair[1],reverse=True)) for name,model in fitted.items()}
    all_eligible=data.loc[data.Risk_Label.isin(LABELS)]
    final=models();artifacts={}
    for name,model in final.items():
        stem='random_forest' if name=='Random Forest' else 'xgboost'
        joblib.dump(fitted[name],output/f'{stem}_development_evaluated.joblib')
        model.fit(inputs(all_eligible),all_eligible.Risk_Label.map({v:i for i,v in enumerate(LABELS)}))
        joblib.dump(model,output/f'{stem}_all_data.joblib');joblib.dump(model.named_steps['preprocessing'],output/f'{stem}_preprocessing.joblib')
        artifacts[name]=dict(all_data_model=str(output/f'{stem}_all_data.joblib'),evaluated_development_model=str(output/f'{stem}_development_evaluated.joblib'))
    result=dict(audit=audit,assumptions=ASSUMPTIONS,selected_by_validation=selected,validation=validation_metrics,test_2026=test_metrics,
        clustering=clustering(data),feature_importance=importance,artifacts=artifacts,
        splits={name:dict(rows=len(frame),classes=frame.Risk_Label.value_counts().to_dict(),years=sorted(map(int,frame.Year.unique())))
                for name,frame in [('train',train),('validation',validation),('test',test),('all_data_refit',all_eligible)]},
        excluded_by_year={str(k):int(v) for k,v in data.loc[data.Risk_Label=='insufficient_evidence'].Year.value_counts().sort_index().items()},
        schema=dict(features=FEATURES,categorical=CAT,numeric=NUM,label_order=LABELS,forbidden=['Overlap_Acres','Overlap_Expected_Production_kg','Historical_P33_Acres','Historical_P67_Acres','Risk_Label','Record_ID','Year']),
        label_definition=dict(window_days=14,percentiles=[33,67],method='linear',reference='same district/crop/season, earlier recorded years, harvest before target-year Jan 1',validation_status='experimental'))
    data.to_csv(output/'research_features_and_targets.csv',index=False)
    for name,value in [('metadata',result),('feature_schema',result['schema']),('label_definition',result['label_definition'])]:
        (output/f'{name}.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    for item in audit['inputs']:
        if hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Source changed during run')
    manifest(output)
    print(json.dumps(dict(selected=selected,splits=result['splits'],validation=validation_metrics,test_2026=test_metrics,output=str(output))))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    run([ROOT/'data/farmer/cultivation_data_2020_2025.csv',ROOT/'data/farmer/cultivation_data_2026.csv'],args.output_dir)


if __name__=='__main__':main()
