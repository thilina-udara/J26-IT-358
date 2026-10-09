"""No training: spy model and fictional boundary evidence only."""
from datetime import datetime,timezone
from app.services.historical_prediction import HistoricalPredictor,predict_context

class SpyModel:
    def __init__(self):self.inputs=[]
    def predict(self,frame):self.inputs.append(frame.to_dict('records')[0]);return [1]

def fixture():
    model=SpyModel()
    observed=[dict(district='Matara',crop='Corn',season='Maha',year=year,land_acres=area,production_kg=area*10,
        provenance_verified=True,evidence_reference='FICTIONAL vintage',available_at=datetime(2022,1,1,tzinfo=timezone.utc))
        for year,area in [(2020,10),(2021,20)]]
    service=HistoricalPredictor(model,observed,'spy-not-real-model',datetime(2022,1,1,tzinfo=timezone.utc),2021,2021)
    service.season_year_mapping_evidence=dict(verified=True,reference='FICTIONAL mapping, not a Sri Lankan calendar',
        available_at=datetime(2022,1,1,tzinfo=timezone.utc))
    # One explicitly bounded fictional case; no universal month/day rule.
    service.season_year_mapper=lambda plan,season:2022 if (plan['district'],plan['crop'],season,plan['planting_date'])==('Matara','Corn','Maha','2022-09-01') else None
    plan=dict(district='Matara',crop='Corn',planting_date='2022-09-01',expected_harvest_date='2023-01-01')
    return service,model,plan

def test_verified_prior_features_and_no_future_observations():
    service,model,plan=fixture();cutoff=datetime(2022,8,31,tzinfo=timezone.utc)
    service.observations.append(dict(service.observations[0],year=2022,land_acres=99999))
    assert predict_context(service,plan,'Maha',cutoff)['risk_level']=='Medium'
    features=model.inputs[0]
    assert features['Prior_History_Count']==2 and features['Historical_Mean_Land_Acres']==15
    assert features['Historical_Mean_Production_kg']==150 and features['Target_Year']==2022

def test_boundaries_and_missing_mapping():
    service,model,plan=fixture()
    for day in (1,2):
        assert predict_context(service,plan,'Maha',datetime(2022,9,day,tzinfo=timezone.utc))['status']=='insufficient_evidence'
    cutoff=datetime(2022,8,31,tzinfo=timezone.utc)
    for changed in ('2022-08-31','2022-09-02'):
        assert predict_context(service,dict(plan,planting_date=changed),'Maha',cutoff)['risk_level'] is None
    assert predict_context(service,plan,'Yala',cutoff)['risk_level'] is None
    assert predict_context(service,dict(plan,crop='Brinjal'),'Maha',cutoff)['risk_level'] is None
    service.season_year_mapping_evidence['verified']=False
    assert predict_context(service,plan,'Maha',cutoff)['risk_level'] is None
    assert model.inputs==[]

def test_missing_or_late_publication_availability():
    service,model,plan=fixture();cutoff=datetime(2022,8,31,tzinfo=timezone.utc)
    for available in (None,datetime(2022,9,2,tzinfo=timezone.utc)):
        service.observations[0]['available_at']=available
        assert predict_context(service,plan,'Maha',cutoff)['status']=='insufficient_evidence'
    assert model.inputs==[]
