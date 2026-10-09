"""Historical-only feature ablations with frozen 2025 evaluation."""
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
from ml.training import train_full_original_dataset as orig
from ml.training import train_updated_asc as exp
from ml.training import improve_xgboost_medium_recall as medium
ROOT=exp.ROOT;LABELS=exp.LABELS
FAMILIES={
 'trend':['Last_Completed_Year_Acres','Annual_Acreage_Slope','Last_Annual_Acreage_Change'],
 'previous':['Previous_Year_Window_Mean_Acres','Previous_Year_Window_Median_Acres','Previous_Year_Window_Std_Acres','Previous_Year_Mean_Plan_Acres'],
 'rolling':['Rolling_Two_Years_Window_Mean_Acres','Rolling_Two_Years_Window_Median_Acres','Rolling_Two_Years_Window_Std_Acres'],
 'aligned':['Previous_Year_Aligned_Window_Acres','Rolling_Aligned_Window_Mean_Acres','Aligned_Window_Acreage_Change','Previous_Year_Aligned_Plan_Count'],
 'percentile':['Own_Acres_Historical_Plan_Percentile','Own_Acres_Distance_Historical_Plan_P33','Own_Acres_Distance_Historical_Plan_P67']}

def add_features(raw,features):
    output=features.copy().set_index('Record_ID');updates={}
    for _,g in raw.groupby(base.CAT,sort=False):
        cache={};aligned_cache={}
        for p in g.itertuples(index=False):
            prior=g[(g.Year<p.Year)&(g.Expected_Harvest_Date<p.Planting_Date)];key=(p.Year,len(prior))
            if key not in cache:
                annual={}
                for year,rows in prior.groupby('Year'):
                    ds=rows.Expected_Harvest_Date.to_numpy(dtype='datetime64[D]');acres=rows.Land_Size_Acres.to_numpy();sums=[]
                    for anchor in np.unique(ds):sums.append(float(acres[np.abs((ds-anchor).astype(int))<=14].sum()))
                    annual[int(year)]={'total':float(acres.sum()),'windows':np.array(sums),'mean_plan':float(acres.mean()),'dates':ds,'acres':acres}
                years=sorted(annual);totals=np.array([annual[y]['total'] for y in years]);last=annual.get(p.Year-1)
                recent=[y for y in [p.Year-2,p.Year-1] if y in annual];windows=np.concatenate([annual[y]['windows'] for y in recent]) if recent else np.array([])
                values={c:np.nan for columns in FAMILIES.values() for c in columns}
                if years:
                    values['Last_Completed_Year_Acres']=annual[years[-1]]['total'];values['Annual_Acreage_Slope']=float(np.polyfit(np.array(years)-years[0],totals,1)[0]) if len(years)>1 else np.nan
                    values['Last_Annual_Acreage_Change']=float(totals[-1]-totals[-2]) if len(years)>1 else np.nan
                if last:
                    w=last['windows'];values.update(Previous_Year_Window_Mean_Acres=float(w.mean()),Previous_Year_Window_Median_Acres=float(np.median(w)),Previous_Year_Window_Std_Acres=float(w.std()),Previous_Year_Mean_Plan_Acres=last['mean_plan'])
                if len(windows):values.update(Rolling_Two_Years_Window_Mean_Acres=float(windows.mean()),Rolling_Two_Years_Window_Median_Acres=float(np.median(windows)),Rolling_Two_Years_Window_Std_Acres=float(windows.std()))
                sorted_plan=np.sort(prior.Land_Size_Acres.to_numpy());quantiles=np.percentile(sorted_plan,[33,67],method='linear') if len(sorted_plan) else [np.nan,np.nan]
                cache[key]=(annual,values,sorted_plan,quantiles)
            annual,common,sorted_plan,quantiles=cache[key];values=common.copy()
            # Percentiles of individual HISTORICAL plan sizes, not target window thresholds.
            if len(sorted_plan):
                values['Own_Acres_Historical_Plan_Percentile']=float(np.searchsorted(sorted_plan,p.Land_Size_Acres,side='right')/len(sorted_plan))
                values['Own_Acres_Distance_Historical_Plan_P33']=float(p.Land_Size_Acres-quantiles[0]);values['Own_Acres_Distance_Historical_Plan_P67']=float(p.Land_Size_Acres-quantiles[1])
            align_key=(*key,p.Expected_Harvest_Date.month,p.Expected_Harvest_Date.day,p.Expected_Harvest_Date.year-p.Year)
            if align_key not in aligned_cache:
                aligned={}
                for year,hist in annual.items():
                    calendar_year=year+(p.Expected_Harvest_Date.year-p.Year)
                    anchor=np.datetime64(pd.Timestamp(calendar_year,p.Expected_Harvest_Date.month,min(p.Expected_Harvest_Date.day,28) if p.Expected_Harvest_Date.month==2 else p.Expected_Harvest_Date.day).date(),'D')
                    mask=np.abs((hist['dates']-anchor).astype(int))<=14
                    aligned[year]=(float(hist['acres'][mask].sum()),int(mask.sum()))
                prev=aligned.get(p.Year-1);before=aligned.get(p.Year-2)
                aligned_cache[align_key]={'Previous_Year_Aligned_Window_Acres':prev[0] if prev else np.nan,'Previous_Year_Aligned_Plan_Count':prev[1] if prev else np.nan,
                    'Rolling_Aligned_Window_Mean_Acres':float(np.mean([aligned[y][0] for y in [p.Year-2,p.Year-1] if y in aligned])) if any(y in aligned for y in [p.Year-2,p.Year-1]) else np.nan,
                    'Aligned_Window_Acreage_Change':prev[0]-before[0] if prev and before else np.nan}
            values.update(aligned_cache[align_key]);updates[p.Record_ID]=values
    return output.join(pd.DataFrame.from_dict(updates,orient='index')).reset_index()

def feature_sets():
    sets={'base':[]}
    for family,columns in FAMILIES.items():sets['base_plus_'+family]=columns
    allcols=[c for columns in FAMILIES.values() for c in columns];sets['all']=allcols
    for family,columns in FAMILIES.items():sets['all_minus_'+family]=[c for c in allcols if c not in columns]
    return sets

def fit(raw_features,year,extra,weight,params):
    train=raw_features[(raw_features.Year<year)&raw_features.Risk_Label.isin(LABELS)];test=raw_features[(raw_features.Year==year)&raw_features.Risk_Label.isin(LABELS)]
    assert train.Prediction_Cutoff.max()<test.Prediction_Cutoff.min();assert not set(train.Record_ID)&set(test.Record_ID)
    numeric=base.NUM+extra;features=base.FEATURES+extra
    prep=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),base.CAT),('num',Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),('scale',StandardScaler())]),numeric)])
    kwargs=dict(n_estimators=300,max_depth=2,learning_rate=.04,min_child_weight=8,gamma=.15,reg_alpha=.2,reg_lambda=8,subsample=.85,colsample_bytree=.9,objective='multi:softprob',num_class=3,eval_metric='mlogloss',tree_method='hist',random_state=42,n_jobs=1);kwargs.update(params)
    model=Pipeline([('preprocessing',prep),('classifier',XGBClassifier(**kwargs))]);y=train.Risk_Label.map(dict(zip(LABELS,range(3))))
    w=np.where(y==1,float(weight),1.);w/=w.mean();model.fit(train[features],y,classifier__sample_weight=w)
    imputer=model.named_steps['preprocessing'].named_transformers_['num'].named_steps['impute']
    assert np.allclose(imputer.statistics_,train[numeric].median().fillna(0),equal_nan=True)
    return model,test,model.predict_proba(test[features])

def run(out):
    source=ROOT/'data/legacy/official_farmer_cultivation_2020_2026.csv';od=ROOT/'models/experimental/full_original_dataset/v1_20261009';md=ROOT/'models/experimental/xgboost_medium_recall/v1_20261009'
    watched=[source,*[p for directory in [od,md] for p in directory.iterdir() if p.is_file()]];hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    raw=pd.read_csv(source);raw=raw[raw.Year<=2025].copy()
    for c in ['Planting_Date','Expected_Harvest_Date']:raw[c]=pd.to_datetime(raw[c],format='%m/%d/%Y')
    saved=pd.read_csv(od/'features_and_labels.csv');saved=saved[saved.Year<=2025].copy();saved['Prediction_Cutoff']=pd.to_datetime(saved.Prediction_Cutoff)
    development=add_features(raw[raw.Year<=2024],saved[saved.Year<=2024]);out.mkdir(parents=True,exist_ok=False)
    sets=feature_sets();exp.save(out/'search_specification.json',{'feature_families':FAMILIES,'feature_sets':sets,'medium_weights':[2,4],'medium_multipliers':[1.,1.5,2.],
        'selection':'max development pooled macro F1, then Medium recall, accuracy; pooled accuracy >= control minus 2pp; each year >= control minus 3pp','development':[2023,2024],'final':2025,'2026_excluded':True})
    metrics={};frames=[];cache={}
    for name,extra in sets.items():
        for weight in [2,4]:
            for year in [2023,2024]:
                model,test,prob=fit(development,year,extra,weight,{});cache[(name,weight,year)]=(model,test,prob)
            for boost in [1.,1.5,2.]:
                candidate=f'{name}_weight{weight}_boost{boost}';folds={};candidate_frames=[]
                for year in [2023,2024]:
                    model,test,prob=cache[(name,weight,year)];pred=medium.decision(prob,boost);folds[str(year)]=orig.metric(test,pred)
                    p=test[['Record_ID','Year','Risk_Label']].copy();p['Prediction']=pred;p['Candidate']=candidate;candidate_frames.append(p)
                pooled=pd.concat(candidate_frames,ignore_index=True);frames.append(pooled);metrics[candidate]={'features':name,'weight':weight,'boost':boost,'folds':folds,'pooled':orig.metric(pooled,pooled.Prediction)}
        print('Finished feature ablation',name,flush=True)
    control=metrics['base_weight2_boost1.5'];predictions=pd.concat(frames,ignore_index=True)
    oldpred=pd.read_csv(md/'selected_historical_predictions.csv');check=predictions[predictions.Candidate=='base_weight2_boost1.5'].merge(oldpred[['Record_ID','Prediction']],on='Record_ID',suffixes=('_new','_old'),validate='one_to_one');assert check.Prediction_new.eq(check.Prediction_old).all()
    feasible={n:m for n,m in metrics.items() if m['pooled']['accuracy']>=control['pooled']['accuracy']-.02 and all(m['folds'][str(y)]['accuracy']>=control['folds'][str(y)]['accuracy']-.03 for y in [2023,2024])}
    selected=max(feasible,key=lambda n:(feasible[n]['pooled']['macro_f1'],feasible[n]['pooled']['per_class']['Medium']['recall'],feasible[n]['pooled']['accuracy'],n));chosen=metrics[selected]
    exp.save(out/'development_metrics.json',metrics);predictions.to_csv(out/'development_predictions.csv',index=False)
    exp.save(out/'selection_frozen_before_2025.json',{'selected':selected,'features':chosen['features'],'weight':chosen['weight'],'boost':chosen['boost'],'2025_used_for_selection':False});print('Frozen choice',selected,flush=True)
    context=add_features(raw,saved);pd.testing.assert_frame_equal(development.reset_index(drop=True),context[context.Year<=2024].reset_index(drop=True))
    extra=sets[chosen['features']];model,test,prob=fit(context,2025,extra,chosen['weight'],{});pred=medium.decision(prob,chosen['boost']);final=orig.metric(test,pred)
    p=test[['Record_ID','Year','District','Crop','Season','Risk_Label']].copy();p['Prediction']=pred;p.to_csv(out/'final_2025_predictions.csv',index=False)
    joblib.dump(model,out/'selected_xgboost_through_2024.joblib');joblib.dump(model.named_steps['preprocessing'],out/'selected_preprocessing.joblib')
    for year in [2023,2024]:joblib.dump(cache[(chosen['features'],chosen['weight'],year)][0],out/f'selected_xgboost_through_{year-1}.joblib')
    pool=pd.concat([predictions[predictions.Candidate==selected][['Record_ID','Year','Risk_Label','Prediction']],p[['Record_ID','Year','Risk_Label','Prediction']]],ignore_index=True);pool.to_csv(out/'selected_historical_predictions.csv',index=False)
    prior=json.loads((md/'metrics.json').read_text());result={'selected':selected,'development':chosen,'final_2025':final,'pooled':orig.metric(pool,pool.Prediction),'baseline':prior,'source_sha256':hashes[str(source)]}
    result['majority_baselines']={str(y):orig.metric(g,['Low']*len(g)) for y,g in pool.groupby('Year')};result['majority_baselines']['pooled']=orig.metric(pool,['Low']*len(pool))
    exp.save(out/'metrics.json',result);exp.save(out/'input_hashes.json',hashes);exp.save(out/'feature_schema.json',{'features':base.FEATURES+extra,'families':FAMILIES,'selected_feature_set':chosen['features'],'weight':chosen['weight'],'medium_probability_multiplier':chosen['boost'],'excluded':['Risk_Label','Overlap_Acres','Historical_P33_Acres','Historical_P67_Acres','Record_ID','Year']})
    context.to_csv(out/'features_and_labels_2020_2025.csv',index=False)
    for title,m in [('2023',chosen['folds']['2023']),('2024',chosen['folds']['2024']),('2025',final),('pooled',result['pooled'])]:pd.DataFrame(m['confusion_matrix'],index=LABELS,columns=LABELS).to_csv(out/f'{title}_confusion_matrix.csv')
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    exp.save(out/'artifact_manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
    print(json.dumps({'selected':selected,'final_2025':final,'pooled':result['pooled']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();run(a.output_dir.resolve())
