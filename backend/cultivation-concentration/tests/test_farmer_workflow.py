"""Software fixtures only; no real labels or agricultural approvals."""
from datetime import datetime,timezone
from fastapi.testclient import TestClient
from app.main import create_app
from tests.test_security_privacy import contains_collective_numbers
from tests.test_alternatives import evidence

def body(**changes):
    value=dict(crop='Corn',district='Matara',region='north',land_size_acres=2,
        planting_date='2030-01-01',expected_harvest_date='2030-04-01')
    return dict(value,**changes)

def test_full_original_journey_and_privacy(tmp_path):
    client=TestClient(create_app(tmp_path/'journey.sqlite3',{'owner':'owner','other':'other'}))
    headers={'Authorization':'Bearer owner'}
    assert client.post('/api/farmer-workflow/plans',json=body()).status_code==401
    response=client.post('/api/farmer-workflow/plans',headers=headers,json=body())
    assert response.status_code==201,response.text
    identifier=response.json()['plan']['plan_id']
    workflow=response.json()['workflow']
    assert workflow['historical_prediction']['status']=='insufficient_evidence'
    assert workflow['historical_prediction']['risk_level'] is None
    assert workflow['assessment']['status']=='risk_level_unvalidated'
    assert workflow['assessment']['risk_level'] is None
    assert workflow['recommendations']['alternatives']==[]
    assert not contains_collective_numbers(workflow)
    assert workflow['clustering']['algorithms']==['K-Means','DBSCAN']
    assert 'Season not supplied' in str(workflow['assessment']['missing_evidence'])
    assert client.post('/api/farmer-workflow/analyze',headers={'Authorization':'Bearer other'},json={'plan_id':identifier}).status_code==404
    selection=dict(plan_id=identifier,final_crop='Corn',district='Matara',region='north',land_size_acres=2,
        planting_date='2030-01-01',season='Maha',planting_method='direct_sowing',save=True)
    saved=client.post('/api/farmer-workflow/select',headers=headers,json=selection)
    assert saved.status_code==200 and saved.json()['personalized_plan']['status']=='partial_plan'
    read=client.get('/api/farmer-workflow/plans/'+identifier,headers=headers)
    assert read.json()['personalized_plan']['stale'] is False
    assert client.post('/api/farmer-workflow/select',headers=headers,json=dict(selection,final_crop='Brinjal')).status_code==409

def test_overlap_filters_asof_and_own_once(tmp_path,monkeypatch):
    from app.services import farmer_workflow as module
    from app.services.cultivation_plans import PlanStore
    from app.services.plan_clustering import snapshot
    observed=[];original=module.explain
    def capture(values):observed.append(values);return original(values)
    monkeypatch.setattr(module,'explain',capture)
    path=tmp_path/'overlap.sqlite3'
    client=TestClient(create_app(path,{str(i):str(i) for i in range(6)}))
    identifier=None
    for i,changes in enumerate(({}, {}, {}, {'crop':'Brinjal'}, {'region':'south'}, {'expected_harvest_date':'2030-04-16'})):
        response=client.post('/api/farmer-workflow/plans',headers={'Authorization':'Bearer '+str(i)},json=body(**changes))
        if i==0:identifier=response.json()['plan']['plan_id']
    cutoff=datetime.now(timezone.utc).isoformat()
    result=client.post('/api/farmer-workflow/analyze',headers={'Authorization':'Bearer 0'},json=dict(plan_id=identifier,season='Maha',as_of=cutoff))
    assert result.status_code==200
    assert observed[-1]['overlapping_farmer_count']==3 and observed[-1]['total_planned_acreage']==6
    assert observed[-1]['harvest_overlap_intensity']==.75
    assert len(snapshot(PlanStore(path),datetime.fromisoformat(cutoff)))==6
    assert not contains_collective_numbers(result.json())
    assert client.post('/api/farmer-workflow/analyze',headers={'Authorization':'Bearer 0'},json=dict(plan_id=identifier,as_of='2019-01-01T00:00:00Z')).status_code==404

def test_high_gate_and_eligible_selection_fictional_only(tmp_path,monkeypatch):
    from app.services import farmer_workflow as module
    original=module.explain
    def fixture(values):
        result=original(values)
        result.update(status='risk_level_validated',risk_level='High',classification_evidence={
            'verified':True,'reference':'FICTIONAL software fixture only','available_at':'2020-01-01T00:00:00+00:00'})
        return result
    monkeypatch.setattr(module,'explain',fixture)
    client=TestClient(create_app(tmp_path/'high.sqlite3',{str(i):str(i) for i in range(7)},alternative_evidence=evidence()))
    identifier=None
    for i in range(7):
        response=client.post('/api/farmer-workflow/plans',headers={'Authorization':'Bearer '+str(i)},
            json=body(crop='Corn' if i<4 else 'Brinjal',land_size_acres=5 if i<4 else 2,season='Maha'))
        if i==0:identifier=response.json()['plan']['plan_id']
    result=client.post('/api/farmer-workflow/analyze',headers={'Authorization':'Bearer 0'},json=dict(plan_id=identifier,season='Maha')).json()
    assert [a['crop'] for a in result['recommendations']['alternatives']]==['Brinjal']
    assert not contains_collective_numbers(result)
    selection=dict(plan_id=identifier,final_crop='Brinjal',district='Matara',region='north',land_size_acres=5,
        planting_date='2030-01-01',season='Maha',save=True)
    assert client.post('/api/farmer-workflow/select',headers={'Authorization':'Bearer 0'},json=selection).status_code==200
