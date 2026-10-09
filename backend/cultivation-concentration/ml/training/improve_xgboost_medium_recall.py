"""Medium recall search using earlier folds, then one frozen 2025 evaluation."""
import argparse,hashlib,json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from ml.training import train_asc_2020_2026 as base
from ml.training import train_updated_asc as exp
from ml.training import train_full_original_dataset as orig
from ml.training import improve_full_dataset_xgboost as previous
ROOT=exp.ROOT;LABELS=exp.LABELS
WEIGHTS=['uniform','balanced','sqrt_balanced','medium_2','medium_4'];BOOSTS=[1.,1.5,2.,3.]

def fit_model(data,end,weight,spec):
    train=data[(data.Year<=end)&data.Risk_Label.isin(LABELS)];model=previous.pipeline(spec);y=train.Risk_Label.map(dict(zip(LABELS,range(3))));counts=y.value_counts()
    if weight=='uniform':w=np.ones(len(train))
    elif weight in ['balanced','sqrt_balanced']:
        w=y.map({k:len(y)/(3*v) for k,v in counts.items()}).to_numpy();w=np.sqrt(w) if weight=='sqrt_balanced' else w
    else:w=np.where(y==1,2. if weight=='medium_2' else 4.,1.)
    w=w/w.mean();model.fit(train[base.FEATURES],y,classifier__sample_weight=w)
    assert np.allclose(model.named_steps['preprocessing'].named_transformers_['num'].named_steps['impute'].statistics_,train[base.NUM].median())
    return model

def probabilities(data,year,weight,spec):
    model=fit_model(data,year-1,weight,spec);test=data[(data.Year==year)&data.Risk_Label.isin(LABELS)]
    train=data[(data.Year<year)&data.Risk_Label.isin(LABELS)]
    assert train.Prediction_Cutoff.max()<test.Prediction_Cutoff.min()
    # Independent earlier model forecasts immediately preceding year to fit calibration.
    earlier=fit_model(data,year-2,weight,spec);calrows=data[(data.Year==year-1)&data.Risk_Label.isin(LABELS)]
    cp=earlier.predict_proba(calrows[base.FEATURES]);cy=calrows.Risk_Label.map(dict(zip(LABELS,range(3))))
    calibrator=LogisticRegression(C=1.,max_iter=2000,random_state=42);calibrator.fit(np.log(np.clip(cp,1e-8,1)),cy)
    raw=model.predict_proba(test[base.FEATURES]);cal=calibrator.predict_proba(np.log(np.clip(raw,1e-8,1)))
    return model,calibrator,test,raw,cal

def decision(prob,boost):
    score=prob.copy();score[:,1]*=boost
    return np.array(LABELS)[score.argmax(axis=1)]

def run(out):
    md=ROOT/'models/experimental/full_dataset_improvement/v1_20261009';od=ROOT/'models/experimental/full_original_dataset/v1_20261009';source=ROOT/'data/legacy/official_farmer_cultivation_2020_2026.csv'
    watched=[source,*[p for directory in [md,od] for p in directory.iterdir() if p.is_file()]];hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    data=pd.read_csv(od/'features_and_labels.csv');data=data[data.Year<=2025].copy();data['Prediction_Cutoff']=pd.to_datetime(data.Prediction_Cutoff)
    spec=json.loads((md/'selection_frozen_before_2025.json').read_text())['specification'];development=data[data.Year<=2024].copy();out.mkdir(parents=True,exist_ok=False)
    search_rule={'weights':WEIGHTS,'calibration':['none','multiclass_log_probability_logistic_C1'],'medium_probability_multipliers':BOOSTS,
        'selection':'max pooled development macro F1, tie-break Medium recall then accuracy; pooled accuracy >= baseline minus 2pp AND each fold accuracy >= baseline minus 3pp',
        'selection_years':[2023,2024],'final_year':2025,'calibration':'each fold fits logistic map on previous-year out-of-time predictions of a model trained through the year before that; never calibrate on evaluation fold','2026_excluded':True}
    exp.save(out/'search_specification.json',search_rule)
    metrics={};frames=[];cache={}
    for weight in WEIGHTS:
        for year in [2023,2024]:
            model,calibrator,test,raw,cal=probabilities(development,year,weight,spec);cache[(weight,year)]=(model,calibrator,test,raw,cal)
        for calibrated in [False,True]:
            for boost in BOOSTS:
                name=f'{weight}_{"calibrated" if calibrated else "raw"}_medium{boost}';folds={};pooled=[]
                for year in [2023,2024]:
                    model,calibrator,test,raw,cal=cache[(weight,year)];prob=cal if calibrated else raw;pred=decision(prob,boost)
                    m=orig.metric(test,pred);m['log_loss']=float(log_loss(test.Risk_Label.map(dict(zip(LABELS,range(3)))),prob,labels=[0,1,2]));folds[str(year)]=m
                    frame=test[['Record_ID','Year','Risk_Label']].copy();frame['Prediction']=pred;frame['Candidate']=name;pooled.append(frame)
                p=pd.concat(pooled,ignore_index=True);frames.append(p);metrics[name]={'configuration':{'weight':weight,'calibrated':calibrated,'medium_multiplier':boost},'folds':folds,'pooled':orig.metric(p,p.Prediction)}
        print('Finished development weight',weight,flush=True)
    baseline_name='uniform_raw_medium1.0';baseline=metrics[baseline_name]
    # Assert reproducibility against previous saved development predictions.
    oldpred=pd.read_csv(md/'selected_historical_predictions.csv');p=pd.concat(frames);control=p[p.Candidate==baseline_name]
    joined=control.merge(oldpred[['Record_ID','Prediction']],on='Record_ID',suffixes=('_new','_old'),validate='one_to_one');assert joined.Prediction_new.eq(joined.Prediction_old).all()
    feasible={name:m for name,m in metrics.items() if m['pooled']['accuracy']>=baseline['pooled']['accuracy']-.02 and all(m['folds'][str(y)]['accuracy']>=baseline['folds'][str(y)]['accuracy']-.03 for y in [2023,2024])}
    selected=max(feasible,key=lambda name:(feasible[name]['pooled']['macro_f1'],feasible[name]['pooled']['per_class']['Medium']['recall'],feasible[name]['pooled']['accuracy'],name))
    exp.save(out/'development_metrics.json',metrics);p.to_csv(out/'development_predictions.csv',index=False)
    chosen=metrics[selected]['configuration'];exp.save(out/'selection_frozen_before_2025.json',{'selected':selected,'configuration':chosen,'selection_rule':search_rule,'2025_used_for_selection':False})
    print('Frozen choice',selected,flush=True)
    # Evaluate only the selected configuration on 2025; final calibrator uses 2024 OOT predictions.
    model,calibrator,test,raw,cal=probabilities(data,2025,chosen['weight'],spec);pred=decision(cal if chosen['calibrated'] else raw,chosen['medium_multiplier'])
    final=orig.metric(test,pred);frame=test[['Record_ID','Year','District','Crop','Season','Risk_Label']].copy();frame['Prediction']=pred
    frame.to_csv(out/'final_2025_predictions.csv',index=False);pd.DataFrame({'Record_ID':test.Record_ID,**{f'raw_{c}':raw[:,i] for i,c in enumerate(LABELS)},**{f'calibrated_{c}':cal[:,i] for i,c in enumerate(LABELS)}}).to_csv(out/'final_2025_probabilities.csv',index=False)
    joblib.dump(model,out/'selected_xgboost_through_2024.joblib');joblib.dump(model.named_steps['preprocessing'],out/'selected_preprocessing.joblib');joblib.dump(calibrator,out/'chronological_multiclass_calibrator.joblib')
    for year in [2023,2024]:
        fitted,calibrator,_,_,_=cache[(chosen['weight'],year)];joblib.dump(fitted,out/f'selected_xgboost_through_{year-1}.joblib');joblib.dump(calibrator,out/f'calibrator_for_{year}.joblib')
    selecteddev=p[p.Candidate==selected].drop(columns='Candidate');pooled=pd.concat([selecteddev,frame[['Record_ID','Year','Risk_Label','Prediction']]],ignore_index=True);pooled.to_csv(out/'selected_historical_predictions.csv',index=False)
    previous_metrics=json.loads((md/'metrics.json').read_text());result={'selected':selected,'configuration':chosen,'development':metrics[selected],'baseline_development':baseline,
        'final_2025':final,'pooled':orig.metric(pooled,pooled.Prediction),'baseline_final_2025':previous_metrics['final_2025'],'baseline_pooled':previous_metrics['pooled_selected'],'dataset_sha256':hashes[str(source)]}
    result['majority_baselines']={str(y):orig.metric(g,['Low']*len(g)) for y,g in pooled.groupby('Year')};result['majority_baselines']['pooled']=orig.metric(pooled,['Low']*len(pooled))
    exp.save(out/'metrics.json',result);exp.save(out/'input_hashes.json',hashes);exp.save(out/'feature_schema.json',{'features':base.FEATURES,'labels':LABELS,'same_labels_and_ids':True,'decision':chosen,'calibration_application':'softmax logistic mapping of log clipped base probabilities, then Medium multiplier and argmax'})
    for title,m in [('2023',metrics[selected]['folds']['2023']),('2024',metrics[selected]['folds']['2024']),('2025',final),('pooled',result['pooled'])]:pd.DataFrame(m['confusion_matrix'],index=LABELS,columns=LABELS).to_csv(out/f'{title}_confusion_matrix.csv')
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    exp.save(out/'artifact_manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True);a=parser.parse_args();run(a.output_dir.resolve())
