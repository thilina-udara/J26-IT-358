"""Authoritative combined-CSV experiment. No production integration."""
import argparse, hashlib, json, platform
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
from ml.training import train_asc_2020_2026 as base

ROOT=Path(__file__).resolve().parents[2]
LABELS=base.LABELS
FEATURES=base.FEATURES

def save(path, value):
    path.write_text(json.dumps(value,indent=2,default=lambda v: v.item() if isinstance(v,np.generic) else str(v))+'\n',encoding='utf-8')

def engineer(raw):
    d=raw.copy()
    d['Planting_Month']=d.Planting_Date.dt.month
    d['Harvest_Month']=d.Expected_Harvest_Date.dt.month
    rows=[]
    for _,p in d.iterrows():
        g=d[(d.District==p.District)&(d.Crop==p.Crop)&(d.Season==p.Season)]
        peers=g[(g.Planting_Date<p.Planting_Date)&(g.Expected_Harvest_Date>=p.Planting_Date)&((g.Expected_Harvest_Date-p.Expected_Harvest_Date).abs().dt.days<=14)]
        # Every reference record has completed its expected harvest strictly before cutoff.
        past=g[(g.Year<p.Year)&(g.Expected_Harvest_Date<p.Planting_Date)]
        windows=[]; production=[]
        for _,annual in past.groupby('Year'):
            for anchor in sorted(annual.Expected_Harvest_Date.unique()):
                members=annual[(annual.Expected_Harvest_Date-anchor).abs().dt.days<=14]
                windows.append(float(members.Land_Size_Acres.sum()))
                production.append(float(members.Expected_Production_kg.sum()))
        acres=float(peers.Land_Size_Acres.sum()+p.Land_Size_Acres)
        lo=hi=np.nan;label='insufficient_evidence'
        if windows:
            lo,hi=np.percentile(windows,[33,67],method='linear')
            if lo<hi:
                label='Low' if acres<lo and not np.isclose(acres,lo,rtol=1e-12,atol=1e-12) else 'High' if acres>hi and not np.isclose(acres,hi,rtol=1e-12,atol=1e-12) else 'Medium'
        rows.append(dict(**{c:p[c] for c in ['Record_ID','Year',*base.CAT,'Land_Size_Acres','Planting_Month','Harvest_Month']},
            Prediction_Cutoff=p.Planting_Date,Reference_Latest_Harvest=past.Expected_Harvest_Date.max(),
            Overlap_Plan_Count=len(peers)+1,Overlap_Acres=acres,
            Own_Expected_Production_kg=float(p.Expected_Production_kg),
            Past_Window_Count=len(windows),Past_Mean_Window_Acres=float(np.mean(windows)) if windows else np.nan,
            Past_Mean_Window_Production_kg=float(np.mean(production)) if production else np.nan,
            Historical_P33_Acres=lo,Historical_P67_Acres=hi,Risk_Label=label))
    return pd.DataFrame(rows)

def run(output):
    source=ROOT/'data/farmer/farmer_cultivation_2020_2026.csv'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    raw=pd.read_csv(source)
    audit={'source':str(source),'sha256':digest,'records':len(raw),'columns_and_types':raw.dtypes.astype(str).to_dict(),
        'missing_values':raw.isna().sum().to_dict(),'exact_duplicate_rows':int(raw.duplicated().sum()),
        'duplicate_ids':int(raw.Record_ID.duplicated().sum()),
        'year_counts':raw.Year.value_counts().sort_index().to_dict(),
        'district_counts':raw.District.value_counts().to_dict(),'crop_counts':raw.Crop.value_counts().to_dict(),
        'season_counts':raw.Season.value_counts().to_dict()}
    d=raw.copy()
    for c in ['Planting_Date','Expected_Harvest_Date']:d[c]=pd.to_datetime(d[c],format='%Y-%m-%d',errors='coerce')
    num=['Year','Land_Size_Acres','Expected_Yield_kg_per_Acre','Expected_Production_kg']
    audit.update(invalid_dates=int(d[['Planting_Date','Expected_Harvest_Date']].isna().any(axis=1).sum()),
        harvest_before_planting=int((d.Expected_Harvest_Date<d.Planting_Date).sum()),
        year_vs_planting_mismatches=int((d.Year!=d.Planting_Date.dt.year).sum()),
        year_planting_cross_table=pd.crosstab(d.Year,d.Planting_Date.dt.year).to_dict(),
        acreage_invalid=int((~np.isfinite(d.Land_Size_Acres)|(d.Land_Size_Acres<=0)).sum()),
        production_invalid=int((~np.isfinite(d.Expected_Production_kg)|(d.Expected_Production_kg<=0)).sum()),
        yield_invalid=int((~np.isfinite(d.Expected_Yield_kg_per_Acre)|(d.Expected_Yield_kg_per_Acre<=0)).sum()),
        production_formula_mismatch=int((~np.isclose(d.Land_Size_Acres*d.Expected_Yield_kg_per_Acre,d.Expected_Production_kg,atol=.011,rtol=0)).sum()),
        numeric_ranges={c:{'min':float(d[c].min()),'max':float(d[c].max())} for c in num},
        date_ranges={c:{'min':str(d[c].min()),'max':str(d[c].max())} for c in ['Planting_Date','Expected_Harvest_Date']},
        duration_days={'min':int((d.Expected_Harvest_Date-d.Planting_Date).dt.days.min()),'max':int((d.Expected_Harvest_Date-d.Planting_Date).dt.days.max())})
    if raw.isna().any().any() or any(audit[k] for k in ['exact_duplicate_rows','duplicate_ids','invalid_dates','harvest_before_planting','acreage_invalid','production_invalid','yield_invalid']):raise ValueError(audit)
    output.mkdir(parents=True,exist_ok=False)
    save(output/'data_validation.json',audit)
    f=engineer(d);train,val,test=base.split(f)
    assert train.Prediction_Cutoff.max()<val.Prediction_Cutoff.min()<test.Prediction_Cutoff.min()
    assert (f.Reference_Latest_Harvest.dropna()<f.loc[f.Reference_Latest_Harvest.notna(),'Prediction_Cutoff']).all()
    # Perturb future acreage: earlier feature and label values must be identical.
    changed=d.copy();changed.loc[changed.Year>=2025,'Land_Size_Acres']*=100
    earlier=engineer(changed)
    pd.testing.assert_frame_equal(f[f.Year<=2024].reset_index(drop=True),earlier[earlier.Year<=2024].reset_index(drop=True))
    models=base.models();results={};majority=train.Risk_Label.value_counts().idxmax()
    for name,model in models.items():
        model.fit(base.inputs(train),train.Risk_Label.map(dict(zip(LABELS,range(3)))))
        results[name]={s:base.metrics(model,frame) for s,frame in [('training',train),('validation',val)]}
    selected=max(results,key=lambda n:results[n]['validation']['macro_f1'])
    # Fixed configs, features and validation selection; final evaluation now occurs once.
    for name,model in models.items():
        results[name]['test_2026']=base.metrics(model,test)
        stem='random_forest' if name=='Random Forest' else 'xgboost'
        joblib.dump(model,output/f'{stem}.joblib')
        joblib.dump(model.named_steps['preprocessing'],output/f'{stem}_preprocessing.joblib')
        for split,metrics in results[name].items():
            pd.DataFrame(metrics['confusion_matrix'],index=LABELS,columns=LABELS).to_csv(output/f'{stem}_{split}_confusion_matrix.csv')
    clusters={}
    for district,rows in f[f.Year<=2024].groupby('District'):
        processor=base.preprocessing();x=processor.fit_transform(base.inputs(rows));clusters[district]={}
        joblib.dump(processor,output/f'{district.lower()}_clustering_preprocessing.joblib')
        for name,model in [('kmeans',KMeans(n_clusters=3,n_init=10,random_state=42)),('dbscan',DBSCAN(eps=1,min_samples=5))]:
            labels=model.fit_predict(x);valid=labels!=-1;n=len(set(labels[valid]));score=None
            if 1<n<valid.sum():score=float(silhouette_score(x[valid],labels[valid]))
            profiles={str(int(k)):{'count':int((labels==k).sum()),'crop_counts':rows.loc[labels==k,'Crop'].value_counts().to_dict(),
                'season_counts':rows.loc[labels==k,'Season'].value_counts().to_dict(),
                'numeric_means':rows.loc[labels==k,base.NUM].mean().to_dict()} for k in sorted(set(labels))}
            clusters[district][name]={'clusters':n,'noise_count':int((labels==-1).sum()),'silhouette_excluding_noise':score,'profiles':profiles}
            joblib.dump(model,output/f'{district.lower()}_{name}.joblib')
            pd.DataFrame({'Record_ID':rows.Record_ID,'cluster':labels}).to_csv(output/f'{district.lower()}_{name}_assignments.csv',index=False)
    splits={s:{'rows':len(frame),'classes':frame.Risk_Label.value_counts().to_dict(),
        'planting_min':str(frame.Prediction_Cutoff.min()),'planting_max':str(frame.Prediction_Cutoff.max()),
        'training_majority_baseline_accuracy':float(frame.Risk_Label.eq(majority).mean()),
        'split_majority_prevalence':float(frame.Risk_Label.value_counts(normalize=True).max())}
        for s,frame in [('training',train),('validation',val),('test_2026',test)]}
    result={'validation':audit,'models':results,'splits':splits,'training_majority_class':majority,'selected_by_validation_macro_f1':selected,
        'insufficient_evidence_by_year':f[f.Risk_Label=='insufficient_evidence'].Year.value_counts().sort_index().to_dict(),
        'all_labels_by_year':pd.crosstab(f.Year,f.Risk_Label).to_dict(),'clustering':clusters,
        'leakage_checks':{'future_perturbation_passed':True,'strict_prediction_cutoff_order_passed':True,'historical_harvest_before_cutoff_passed':True}}
    save(output/'metrics.json',result)
    save(output/'feature_schema.json',{'features':FEATURES,'categorical':base.CAT,'numeric':base.NUM,'labels':LABELS,
        'excluded_label_components':['Overlap_Acres','Historical_P33_Acres','Historical_P67_Acres','Risk_Label'],
        'cutoff':'immediately before planting; own proposed plan available; strictly earlier planted peers only'})
    save(output/'label_definition.json',{'percentiles':[33,67],'method':'linear','reference':'same district, crop, season; earlier Year; expected harvest strictly before planting cutoff; unique observed harvest-date anchors within each historical year; inclusive +/-14 days',
        'rules':'Low below P33; High above P67; Medium including boundaries; missing history or coincident quantiles = insufficient_evidence',
        'caveats':['Research concentration only, not verified oversupply or price-loss risk.','Submission/publication timestamps absent: assumed availability at planting/expected harvest, not proven operational availability.','Historical windows overlap and are dependent; anchor-weighted percentiles are not independent annual samples.','Progressive registrations compared to completed historical windows may bias Low.','Year interpreted as season cohort; previous-October planting retained.','2026 remains excluded from all model and preprocessing fits.']})
    f.to_csv(output/'features_and_labels.csv',index=False)
    command=f'.venv\\Scripts\\python.exe -m ml.training.train_updated_asc --output-dir {output.relative_to(ROOT).as_posix()}'
    (output/'reproduce.txt').write_text(command+'\nUse a fresh output directory (existing directories are refused).\n',encoding='utf-8')
    import sklearn,xgboost
    save(output/'environment.json',{'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__,'sklearn':sklearn.__version__,'xgboost':xgboost.__version__,'joblib':joblib.__version__,
        'model_parameters':{n:m.named_steps['classifier'].get_params() for n,m in models.items()}})
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    save(output/'artifact_manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()})
    print(json.dumps({'output':str(output),'models':results,'splits':splits}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();run(args.output_dir.resolve())
