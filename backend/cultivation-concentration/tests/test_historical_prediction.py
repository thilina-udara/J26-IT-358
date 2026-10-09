from datetime import datetime,timezone
import pandas as pd
from app.services.historical_prediction import HistoricalPredictor,FEATURES,predict_context
from ml.training.compare_models import make_models

def predictor():
    model=make_models()['Random Forest']
    rows=[]
    for i in range(9):
        rows.append(dict(Prior_History_Count=i+1,Historical_Mean_Land_Acres=10+i,
            Historical_Mean_Production_kg=100+i,Historical_Mean_Yield_kg_per_Acre=10,
            District='Matara',Crop='Corn',Season='Maha',Target_Year=2010+i))
    model.fit(pd.DataFrame(rows,columns=FEATURES),[0,1,2]*3)
    observations=[dict(district='Matara',crop='Corn',season='Maha',year=year,land_acres=10,production_kg=100,
        provenance_verified=True,evidence_reference='FICTIONAL source fixture',available_at=datetime(2022,1,1,tzinfo=timezone.utc)) for year in (2020,2021)]
    return HistoricalPredictor(model,observations,'Random Forest',datetime(2022,1,1,tzinfo=timezone.utc),2021,2022)

def test_real_pipeline_inference_and_future_exclusion():
    service=predictor();cutoff=datetime(2022,6,1,tzinfo=timezone.utc)
    # Target-year data with huge values cannot influence features.
    baseline=service.predict('Matara','Corn','Maha',2022,cutoff)
    service.observations.append(dict(service.observations[0],year=2022,land_acres=1e9))
    assert service.predict('Matara','Corn','Maha',2022,cutoff)==baseline
    assert baseline['risk_level'] in ('Low','Medium','High')
    assert service.predict('Matara','Unknown','Maha',2022,cutoff)['status']=='insufficient_evidence'
    assert service.predict('Hambantota','Corn','Maha',2022,cutoff)['status']=='insufficient_evidence'
    service.observations[0]['provenance_verified']=False
    assert service.predict('Matara','Corn','Maha',2022,cutoff)['risk_level'] is None

def test_availability_model_and_calendar_mapping_gates():
    service=predictor();cutoff=datetime(2022,6,1,tzinfo=timezone.utc)
    owned=dict(district='Matara',crop='Corn',planting_date='2022-09-01')
    assert predict_context(service,owned,'Maha',cutoff)['risk_level'] is None
    service.season_year_mapper=lambda plan,season:2022
    service.season_year_mapping_evidence=dict(verified=True,reference='FICTIONAL mapping evidence',available_at=datetime(2022,1,1,tzinfo=timezone.utc))
    assert predict_context(service,owned,'Maha',cutoff)['status']=='historical_proxy_prediction'
    service.observations[0]['available_at']=datetime(2023,1,1,tzinfo=timezone.utc)
    assert service.predict('Matara','Corn','Maha',2022,cutoff)['status']=='insufficient_evidence'
    assert service.predict('Matara','Corn','Maha',2021,cutoff)['status']=='insufficient_evidence'
    assert service.predict('Matara','Corn','Maha',2026,cutoff)['status']=='insufficient_evidence'
