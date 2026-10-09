"""Unchanged shared ASC historical rules isolated from other model implementations.

Retrospective planting-date cutoffs cannot verify registration availability.
Research concentration labels are not independently verified market outcomes.
"""
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

LABELS = ['Low', 'Medium', 'High']
CAT = ['District', 'Crop', 'Season']
NUM = ['Land_Size_Acres', 'Planting_Month', 'Harvest_Month', 'Overlap_Plan_Count', 'Own_Expected_Production_kg', 'Past_Window_Count', 'Past_Mean_Window_Acres', 'Past_Mean_Window_Production_kg']
FEATURES = CAT + NUM

def engineer_fast(raw):
    """Same cutoffs/anchors/percentiles as existing.engineer, using sorted prefix sums."""
    result=[]
    for _,g in raw.groupby(CAT,sort=False):
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

def preprocessing():
    return ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),CAT),
        ('num',Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),('scale',StandardScaler())]),NUM)])
