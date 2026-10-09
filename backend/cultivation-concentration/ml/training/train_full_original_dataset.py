"""Exclusive original-dataset research experiment; no production integration."""
import argparse, hashlib, json, platform
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report,confusion_matrix,accuracy_score
from ml.training import train_updated_asc as existing
from ml.training import train_asc_2020_2026 as base
ROOT=existing.ROOT;LABELS=base.LABELS

def engineer_fast(raw):
    """Same cutoffs/anchors/percentiles as existing.engineer, using sorted prefix sums."""
    result=[]
    for _,g in raw.groupby(base.CAT,sort=False):
        g=g.copy();dates=g.Expected_Harvest_Date.to_numpy(dtype='datetime64[D]');plants=g.Planting_Date.to_numpy(dtype='datetime64[D]')
        years=g.Year.to_numpy();areas=g.Land_Size_Acres.to_numpy();productions=g.Expected_Production_kg.to_numpy();cache={}
        for i,p in enumerate(g.itertuples(index=False)):
            cutoff=plants[i];harvest=dates[i]
            peers=(plants<cutoff)&(dates>=cutoff)&(np.abs((dates-harvest).astype(int))<=14)
            past=(years<p.Year)&(dates<cutoff);key=(int(p.Year),int(past.sum()))
            if key not in cache:
                windows=[];production=[]
                for year in np.unique(years[past]):
                    mask=past&(years==year);order=np.argsort(dates[mask]);ds=dates[mask][order]
                    acres=areas[mask][order];prod=productions[mask][order];anchors=np.unique(ds)
                    low=np.searchsorted(ds,anchors-np.timedelta64(14,'D'),side='left');high=np.searchsorted(ds,anchors+np.timedelta64(14,'D'),side='right')
                    ap=np.concatenate([[0],np.cumsum(acres)]);pp=np.concatenate([[0],np.cumsum(prod)])
                    windows.extend((ap[high]-ap[low]).tolist());production.extend((pp[high]-pp[low]).tolist())
                lo=hi=np.nan
                if windows:lo,hi=np.percentile(windows,[33,67],method='linear')
                cache[key]=(len(windows),float(np.mean(windows)) if windows else np.nan,float(np.mean(production)) if production else np.nan,lo,hi)
            count,mean_area,mean_prod,lo,hi=cache[key]
            overlap=float(areas[peers].sum()+p.Land_Size_Acres);label='insufficient_evidence'
            if count and lo<hi:
                label='Low' if overlap<lo and not np.isclose(overlap,lo,atol=1e-12,rtol=1e-12) else 'High' if overlap>hi and not np.isclose(overlap,hi,atol=1e-12,rtol=1e-12) else 'Medium'
            result.append(dict(Record_ID=p.Record_ID,Year=p.Year,District=p.District,Crop=p.Crop,Season=p.Season,
                Land_Size_Acres=p.Land_Size_Acres,Planting_Month=p.Planting_Date.month,Harvest_Month=p.Expected_Harvest_Date.month,
                Prediction_Cutoff=p.Planting_Date,Reference_Latest_Harvest=g.loc[past,'Expected_Harvest_Date'].max(),
                Overlap_Plan_Count=int(peers.sum())+1,Overlap_Acres=overlap,Own_Expected_Production_kg=float(p.Expected_Production_kg),
                Past_Window_Count=count,Past_Mean_Window_Acres=mean_area,Past_Mean_Window_Production_kg=mean_prod,
                Historical_P33_Acres=lo,Historical_P67_Acres=hi,Risk_Label=label))
    return pd.DataFrame(result).set_index('Record_ID').loc[raw.Record_ID].reset_index()

def load(path,date_format):
    raw=pd.read_csv(path);d=raw.copy()
    audit={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'records':len(raw),'columns_and_types':raw.dtypes.astype(str).to_dict(),
        'missing_values':raw.isna().sum().to_dict(),'duplicate_ids':int(raw.Record_ID.duplicated().sum()),'duplicate_records':int(raw.duplicated().sum()),
        'year_counts':raw.Year.value_counts().sort_index().to_dict(),'district_counts':raw.District.value_counts().to_dict(),
        'season_counts':raw.Season.value_counts().to_dict(),'crop_counts':raw.Crop.value_counts().to_dict(),
        'year_season_counts':pd.crosstab(raw.Year,raw.Season).to_dict(),'district_crop_counts':raw.groupby(['District','Crop']).size().to_dict(),'date_format':date_format}
    # JSON-safe joint group keys.
    audit['district_crop_counts']={f'{a} / {b}':int(n) for (a,b),n in audit['district_crop_counts'].items()}
    for c in ['Planting_Date','Expected_Harvest_Date']:d[c]=pd.to_datetime(d[c],format=date_format,errors='coerce')
    audit['invalid_dates']={c:int(d[c].isna().sum()) for c in ['Planting_Date','Expected_Harvest_Date']}
    audit['harvest_before_planting']=int((d.Expected_Harvest_Date<d.Planting_Date).sum())
    audit['year_planting_mismatch']=int(d.Year.ne(d.Planting_Date.dt.year).sum())
    audit['date_ranges']={c:[str(d[c].min()),str(d[c].max())] for c in ['Planting_Date','Expected_Harvest_Date']}
    audit['duration_days']=[int((d.Expected_Harvest_Date-d.Planting_Date).dt.days.min()),int((d.Expected_Harvest_Date-d.Planting_Date).dt.days.max())]
    audit['numeric_ranges']={c:[float(d[c].min()),float(d[c].max())] for c in ['Land_Size_Acres','Expected_Yield_kg_per_Acre','Expected_Production_kg']}
    audit['invalid_numeric']={c:int((~np.isfinite(d[c])|d[c].le(0)).sum()) for c in audit['numeric_ranges']}
    audit['production_formula_mismatches']=int((~np.isclose(d.Land_Size_Acres*d.Expected_Yield_kg_per_Acre,d.Expected_Production_kg,atol=.011,rtol=0)).sum())
    if raw.isna().any().any() or audit['duplicate_ids'] or audit['duplicate_records'] or any(audit['invalid_dates'].values()) or any(audit['invalid_numeric'].values()) or audit['harvest_before_planting']:raise ValueError(audit)
    assert d.Year.between(2020,2026).all() and (d.Year%1==0).all()
    return d,audit

def metric(frame,pred):
    r=classification_report(frame.Risk_Label,pred,labels=LABELS,output_dict=True,zero_division=0)
    return {'records':len(frame),'correct':int(np.sum(np.asarray(frame.Risk_Label)==np.asarray(pred))),
        'accuracy':float(accuracy_score(frame.Risk_Label,pred)),'macro_f1':r['macro avg']['f1-score'],
        'per_class':{c:r[c] for c in LABELS},'confusion_matrix':confusion_matrix(frame.Risk_Label,pred,labels=LABELS).tolist(),
        'classes':frame.Risk_Label.value_counts().to_dict()}

def distribution_compare(new,old):
    result={}
    for field in ['Year','District','Season','Crop']:
        result[field]={str(v):{'original_count':int(new[field].eq(v).sum()),'smaller_count':int(old[field].eq(v).sum()),
            'original_share':float(new[field].eq(v).mean()),'smaller_share':float(old[field].eq(v).mean())} for v in sorted(set(new[field])|set(old[field]))}
    shared=new.merge(old,on='Record_ID',suffixes=('_original','_smaller'))
    result['shared_ids']=len(shared)
    result['shared_id_equal_fields']={c:int(shared[c+'_original'].eq(shared[c+'_smaller']).sum()) for c in new.columns if c!='Record_ID'}
    cols=[c for c in new.columns if c!='Record_ID']
    result['exact_semantic_matches_excluding_id']=int(len(new[cols].merge(old[cols].drop_duplicates(),on=cols,how='inner')))
    return result

def run(output):
    new,na=load(ROOT/'data/legacy/official_farmer_cultivation_2020_2026.csv','%m/%d/%Y')
    old,oa=load(ROOT/'data/farmer/farmer_cultivation_2020_2026.csv','%Y-%m-%d')
    output.mkdir(parents=True,exist_ok=False)
    comparison=distribution_compare(new,old)
    print('Engineering original dataset only',len(new),flush=True)
    f=engineer_fast(new)
    # Verify optimized implementation against untouched existing generator on a full small group.
    small_group=min((g for _,g in new.groupby(base.CAT)),key=len)
    fast=engineer_fast(small_group).set_index('Record_ID').sort_index();reference=existing.engineer(small_group).set_index('Record_ID').sort_index()
    pd.testing.assert_frame_equal(fast[reference.columns],reference,check_dtype=False,atol=1e-8,rtol=1e-10)
    # Existing smaller feature table remains comparison-only and never enters a fit.
    old_saved=pd.read_csv(ROOT/'models/reproducibility/legacy_comparison/smaller_dataset_features.csv')
    old_fast=engineer_fast(old)
    pd.testing.assert_frame_equal(old_fast.set_index('Record_ID').sort_index()[old_saved.columns.drop('Record_ID').drop(['Prediction_Cutoff','Reference_Latest_Harvest'])],
        old_saved.set_index('Record_ID').sort_index().drop(columns=['Prediction_Cutoff','Reference_Latest_Harvest']),check_dtype=False,atol=1e-8,rtol=1e-10)
    changed=new[new.Year<=2024].copy()
    pd.testing.assert_frame_equal(engineer_fast(changed).reset_index(drop=True),f[f.Year<=2024].reset_index(drop=True))
    assert (f.Reference_Latest_Harvest.dropna()<f.loc[f.Reference_Latest_Harvest.notna(),'Prediction_Cutoff']).all()
    comparison['overlap_by_year']={str(y):{name:{c:{'mean':float(g[c].mean()),'median':float(g[c].median())} for c in ['Overlap_Plan_Count','Overlap_Acres']} for name,g in [('original',f[f.Year==y]),('smaller',old_fast[old_fast.Year==y])]} for y in range(2020,2027)}
    result={'original_validation':na,'smaller_validation':oa,'comparison':comparison,'insufficient_by_year':f[f.Risk_Label=='insufficient_evidence'].Year.value_counts().sort_index().to_dict(),
        'folds':{},'pooled':{},'diagnostic_2026':{},'checks':{'existing_generator_equivalence':True,'smaller_saved_feature_equivalence':True,'future_year_exclusion_equivalence':True,'cutoff_availability':True}}
    f.to_csv(output/'features_and_labels.csv',index=False)
    predictions=[];frozen={}
    for year in [2023,2024,2025]:
        train=f[(f.Year<year)&f.Risk_Label.isin(LABELS)];test=f[(f.Year==year)&f.Risk_Label.isin(LABELS)]
        missing_test=int(((f.Year==year)&~f.Risk_Label.isin(LABELS)).sum())
        if train.empty or test.empty or set(train.Risk_Label)!=set(LABELS):
            result['folds'][str(year)]={'status':'insufficient training/test class evidence','eligible_train':len(train),'eligible_test':len(test)};continue
        assert train.Prediction_Cutoff.max()<test.Prediction_Cutoff.min()
        assert not set(train.Record_ID)&set(test.Record_ID)
        majority=train.Risk_Label.value_counts().idxmax()
        fold={'eligible_train':len(train),'eligible_test':len(test),'insufficient_test':missing_test,'train_classes':train.Risk_Label.value_counts().to_dict(),
            'baseline_class':majority,'baseline':metric(test,[majority]*len(test)),'models':{}}
        for name,model in base.models().items():
            model.fit(base.inputs(train),train.Risk_Label.map(dict(zip(LABELS,range(3)))))
            medians=model.named_steps['preprocessing'].named_transformers_['num'].named_steps['impute'].statistics_
            assert np.allclose(medians,train[base.NUM].median().to_numpy())
            pred=np.array(LABELS)[model.predict(base.inputs(test)).astype(int)]
            m=metric(test,pred);m['seasons']={s:metric(test[test.Season==s],pred[test.Season.eq(s)]) for s in ['Maha','Yala'] if test.Season.eq(s).any()}
            fold['models'][name]=m
            stem='random_forest' if name=='Random Forest' else 'xgboost'
            joblib.dump(model,output/f'{stem}_through_{year-1}.joblib');joblib.dump(model.named_steps['preprocessing'],output/f'{stem}_preprocessing_through_{year-1}.joblib')
            pd.DataFrame(m['confusion_matrix'],index=LABELS,columns=LABELS).to_csv(output/f'{stem}_test_{year}_confusion_matrix.csv')
            p=test[['Record_ID','Year','District','Crop','Season','Risk_Label']].copy();p['Model']=name;p['Prediction']=pred;p['Baseline_Prediction']=majority;predictions.append(p)
            if year==2025:frozen[name]=(model,majority)
        result['folds'][str(year)]=fold
        print(json.dumps({'fold':year,'models':{n:{k:m[k] for k in ['accuracy','macro_f1','records']} for n,m in fold['models'].items()}}),flush=True)
    historical=pd.concat(predictions,ignore_index=True)
    for name,g in historical.groupby('Model'):result['pooled'][name]=metric(g,g.Prediction)
    unique=historical.drop_duplicates('Record_ID');result['pooled']['Majority baseline']=metric(unique,unique.Baseline_Prediction)
    historical.to_csv(output/'historical_out_of_time_predictions.csv',index=False)
    # Freeze all decisions before diagnostic 2026. Use through-2024 fits, no test-based selection.
    diagnostic=f[(f.Year==2026)&f.Risk_Label.isin(LABELS)];diag_predictions=[]
    for name,(model,majority) in frozen.items():
        pred=np.array(LABELS)[model.predict(base.inputs(diagnostic)).astype(int)];m=metric(diagnostic,pred)
        m['seasons']={s:metric(diagnostic[diagnostic.Season==s],pred[diagnostic.Season.eq(s)]) for s in ['Maha','Yala']}
        m['baseline']=metric(diagnostic,[majority]*len(diagnostic));result['diagnostic_2026'][name]=m
        stem='random_forest' if name=='Random Forest' else 'xgboost'
        pd.DataFrame(m['confusion_matrix'],index=LABELS,columns=LABELS).to_csv(output/f'{stem}_diagnostic_2026_confusion_matrix.csv')
        p=diagnostic[['Record_ID','Year','District','Crop','Season','Risk_Label']].copy();p['Model']=name;p['Prediction']=pred;diag_predictions.append(p)
    pd.concat(diag_predictions,ignore_index=True).to_csv(output/'diagnostic_2026_predictions.csv',index=False)
    existing.save(output/'metrics.json',result)
    existing.save(output/'feature_schema.json',{'features':base.FEATURES,'categorical':base.CAT,'numeric':base.NUM,'labels':LABELS})
    import sklearn,xgboost
    existing.save(output/'environment.json',{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'xgboost':xgboost.__version__,
        'parameters':{n:m.named_steps['classifier'].get_params() for n,m in base.models().items()}})
    (output/'reproduce.txt').write_text('.venv\\Scripts\\python.exe -m ml.training.train_full_original_dataset --output-dir models/experimental/full_original_dataset/v2_reproduction\nRun from backend root; fresh output directory required.\n',encoding='utf-8')
    for path,audit in [(ROOT/'data/legacy/official_farmer_cultivation_2020_2026.csv',na),(ROOT/'data/farmer/farmer_cultivation_2020_2026.csv',oa)]:assert hashlib.sha256(path.read_bytes()).hexdigest()==audit['sha256']
    existing.save(output/'artifact_manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()})
    print(json.dumps({'output':str(output),'pooled':result['pooled'],'diagnostic_2026':result['diagnostic_2026']}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args();run(args.output_dir.resolve())
