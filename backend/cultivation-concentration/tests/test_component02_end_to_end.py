"""Integration audit only: temporary SQLite and explicitly fictional evidence."""
import json
from datetime import datetime, timezone
from time import perf_counter
from fastapi.testclient import TestClient
from app.main import create_app
from app.services.cultivation_plans import PlanStore
from app.services.plan_clustering import snapshot
from tests.test_alternatives import evidence


def test_farmer_journey_and_persistence(tmp_path):
    path=tmp_path/'integration.sqlite3'
    tokens={f'token-{i}':f'fictional-{i}' for i in range(7)}
    client=TestClient(create_app(path,tokens,['analyst'],alternative_evidence=evidence()))
    timings={}
    def call(name,method,url,token='token-0',**kwargs):
        start=perf_counter()
        response=client.request(method,url,headers={'Authorization':'Bearer '+token},**kwargs)
        timings.setdefault(name,[]).append(1000*(perf_counter()-start))
        return response
    original=None
    body=dict(farmer_id='fictional-0',district='Matara',region='north',crop='Corn',
        land_size_acres=5,planting_date='2030-01-01',expected_harvest_date='2030-04-01')
    assert call('authentication','POST','/api/cultivation-plans',token='invalid',json=body).status_code==401
    for i in range(7):
        row=dict(body,farmer_id=f'fictional-{i}',crop='Corn' if i<4 else 'Brinjal',land_size_acres=5 if i<4 else 2)
        response=call('submit','POST','/api/cultivation-plans',token=f'token-{i}',json=row)
        assert response.status_code==201
        if i==0:original=response.json()['plan']['plan_id']
    cutoff=datetime.now(timezone.utc)
    params=dict(district='Matara',region='north',crop='Corn',season='Maha',harvest_date='2030-04-01',as_of=cutoff.isoformat())
    # Current authorization boundary: farmer cannot request risk/clustering directly.
    assert call('farmer_analysis_denied','GET','/api/cultivation-analysis/risk-assessment',params=params).status_code==403
    for _ in range(3):
        clusters=call('clusters','GET','/api/cultivation-analysis/clusters',token='analyst',params=dict(district='Matara',as_of=cutoff.isoformat()))
        assert clusters.status_code==200 and clusters.json()['status']=='available'
        indicators=call('indicators','GET','/api/cultivation-analysis/risk-indicators',token='analyst',params=params)
        assert indicators.json()['total_planned_acreage']==20
        assert indicators.json()['overlapping_farmer_count']==4
        assessment=call('assessment','GET','/api/cultivation-analysis/risk-assessment',token='analyst',params=params)
        assert assessment.json()['risk_level'] is None
        assert assessment.json()['missing_evidence']
        assert 'fictional-' not in json.dumps(assessment.json())
    alternative=dict(selected_crop='Corn',district='Matara',region='north',land_size_acres=5,
        planting_date='2030-01-01',expected_harvest_date='2030-04-01',replacing_plan_id=original)
    result=call('alternatives','POST','/api/cultivation-analysis/alternatives',json=alternative)
    assert result.status_code==200 and result.json()['alternatives'][0]['crop']=='Brinjal'
    planning=dict(plan_id=original,final_crop='Corn',district='Matara',region='north',land_size_acres=5,
        planting_date='2030-01-01',expected_harvest_date='2030-04-01',season='Maha',planting_method='direct_sowing')
    preview=call('generate_original','POST','/api/personalized-cultivation-plans/generate',json=planning)
    assert preview.status_code==200 and preview.json()['activities']==[]
    assert preview.json()['status']=='partial_plan'
    assert call('save_original','POST','/api/personalized-cultivation-plans/save',json=planning).status_code==200
    assert call('save_alternative','POST','/api/personalized-cultivation-plans/save',json=dict(planning,final_crop='Brinjal')).status_code==200
    assert call('owner_denial','GET','/api/personalized-cultivation-plans/'+original,token='token-1').status_code==404
    # A fresh application instance reads the same persistent database.
    reopened=TestClient(create_app(path,tokens))
    saved=reopened.get('/api/personalized-cultivation-plans/'+original,headers={'Authorization':'Bearer token-0'})
    assert saved.status_code==200 and len(saved.json()['revisions'])==2
    assert saved.json()['personalized_plan']['final_crop']=='Brinjal' and not saved.json()['stale']
    with PlanStore(path).connection() as db:
        assert db.execute("SELECT COUNT(*),SUM(land_size_acres) FROM cultivation_plans WHERE status='active'").fetchone()[:]==(7,26)
    before=snapshot(PlanStore(path),cutoff)
    after=snapshot(PlanStore(path),datetime.now(timezone.utc))
    assert next(p for p in before if p['plan_id']==original)['crop']=='Corn'
    assert next(p for p in after if p['plan_id']==original)['crop']=='Brinjal'
    print('AUDIT_TIMINGS_MS',json.dumps({k:{'n':len(v),'min':round(min(v),2),'mean':round(sum(v)/len(v),2),'max':round(max(v),2)} for k,v in timings.items()},sort_keys=True))


def test_missing_evidence_and_response_boundary(tmp_path):
    client=TestClient(create_app(tmp_path/'missing.sqlite3',{'owner':'owner'},['analyst']))
    headers={'Authorization':'Bearer owner'}
    value=dict(farmer_id='owner',district='Matara',region='north',crop='Corn',land_size_acres=2,
        planting_date='2030-01-01',expected_harvest_date='2030-04-01')
    created=client.post('/api/cultivation-plans',headers=headers,json=value)
    assert created.status_code==201
    assert created.json()['concentration']['plan_count'] is None
    assert client.post('/api/cultivation-plans',headers=headers,json=value).status_code==409
    assert client.post('/api/cultivation-plans',headers=headers,json=dict(value,land_size_acres=-1)).status_code==422
    response=client.post('/api/cultivation-analysis/alternatives',headers=headers,json=dict(
        selected_crop='Corn',district='Matara',region='north',land_size_acres=2,planting_date='2030-01-01',expected_harvest_date='2030-04-01'))
    assert response.json()['status']=='insufficient_evidence' and not response.json()['alternatives']
    response=client.get('/api/cultivation-analysis/risk-indicators',headers={'Authorization':'Bearer analyst'},params=dict(
        district='Matara',region='north',crop='Corn',season='Maha',harvest_date='2030-04-01'))
    assert response.json()['status']=='suppressed_or_insufficient'
    assert 'total_planned_acreage' not in response.json()
