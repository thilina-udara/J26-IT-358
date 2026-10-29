"""Account-session journeys using fictional identities and temporary databases."""
import sqlite3
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.services import farmer_workflow
from tests.test_farmer_auth import account, headers, plan
from tests.test_security_privacy import contains_collective_numbers


def client_for(path):
    return TestClient(create_app(path, {}, [], admin_tokens=[], reviewer_tokens={}))


def test_registered_farmer_complete_journey(tmp_path):
    path=tmp_path/'journey.sqlite3'; client=client_for(path)
    owner, session=account(client); h=headers(session['access_token'])
    other, other_session=account(client, 'fictional-bob'); peer=headers(other_session['access_token'])
    assert client.get('/auth/me',headers=h).json()==owner
    created=client.post('/api/farmer-workflow/plans',headers=h,json=dict(plan(),season='Maha'))
    assert created.status_code==201, created.text
    identifier=created.json()['plan']['plan_id']; base='/api/cultivation-plans/'+identifier
    assert created.json()['plan']['farmer_id']==owner['farmer_id']
    assert client.get(base,headers=h).status_code==200
    assert client.get('/api/cultivation-plans',headers=h).json()['total']==1
    assert client.get('/api/cultivation-plans',headers=peer).json()['total']==0
    report=client.post('/api/farmer-workflow/analyze',headers=h,json=dict(plan_id=identifier,season='Maha')).json()
    assert report['analysis_status']=='completed'
    assert report['status']=='insufficient_evidence' and report['missing_evidence']
    assert report['clustering']['algorithms']==['K-Means','DBSCAN']
    assert report['assessment']['indicators']['status']=='suppressed_or_insufficient'
    assert report['assessment']['risk_level'] is None
    assert not contains_collective_numbers(report)
    assert other['farmer_id'] not in str(report)
    assert client.get(base+'/risk-assessment?season=Maha',headers=h).json()['risk_level'] is None
    assert client.get('/api/cultivation-analysis/clusters?district=Matara',headers=h).status_code==403
    comparison=dict(selected_crop='Corn',replacing_plan_id=identifier,**{k:v for k,v in plan().items() if k!='crop'})
    compared=client.post('/api/cultivation-analysis/alternatives',headers=h,json=comparison)
    assert compared.status_code==200, compared.text
    assert compared.json()['alternatives']==[]
    selection=dict(plan_id=identifier,final_crop='Corn',district='Matara',region='north',land_size_acres=2,
        planting_date='2030-01-01',season='Maha',planting_method='direct_sowing')
    preview=client.post('/api/personalized-cultivation-plans/generate',headers=h,json=selection)
    assert preview.status_code==200 and preview.json()['status']=='partial_plan'
    saved=client.post('/api/farmer-workflow/select',headers=h,json=dict(selection,save=True))
    assert saved.status_code==200 and saved.json()['personalized_plan']['status']=='partial_plan'
    personalized='/api/personalized-cultivation-plans/'+identifier
    assert client.get(personalized,headers=h).json()['stale'] is False
    restarted=client_for(path)
    assert restarted.get('/api/farmer-workflow/plans/'+identifier,headers=h).json()['personalized_plan']['stale'] is False
    for route in [base,personalized,'/api/farmer-workflow/plans/'+identifier,base+'/risk-assessment?season=Maha']:
        assert client.get(route,headers=peer).status_code==404
    for route,value in [('/api/farmer-workflow/analyze',dict(plan_id=identifier)),
                        ('/api/farmer-workflow/select',dict(selection,save=True)),
                        ('/api/cultivation-analysis/alternatives',comparison)]:
        assert client.post(route,headers=peer,json=value).status_code==404
    assert client.put(base,headers=peer,json=plan()).status_code==404
    assert client.delete(base,headers=peer).status_code==404
    assert client.put(base,headers=h,json=plan(land_size_acres=3)).status_code==200
    assert client.get(personalized,headers=h).json()['stale'] is True
    assert client.delete(base,headers=h).json()['plan']['status']=='cancelled'
    assert client.get('/api/cultivation-plans?status=cancelled',headers=h).json()['total']==1
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM cultivation_plan_versions WHERE plan_id=?',(identifier,)).fetchone()[0]>=4
    assert client.post('/auth/logout',headers=h).status_code==204
    assert client.get(base,headers=h).status_code==401
    assert client.post('/api/farmer-workflow/analyze',headers=h,json=dict(plan_id=identifier)).status_code==401


def test_farmer_production_concentration_indicator_is_plan_owned(tmp_path):
    client=client_for(tmp_path/'indicator.sqlite3')
    _,session=account(client); h=headers(session['access_token'])
    _,other_session=account(client, 'fictional-bob'); peer=headers(other_session['access_token'])
    created=client.post('/api/farmer-workflow/plans',headers=h,json=dict(plan(),season='Maha'))
    assert created.status_code==201, created.text
    identifier=created.json()['plan']['plan_id']; base='/api/cultivation-plans/'+identifier
    concentration=client.get(base+'/production-concentration-indicator',headers=h)
    assert concentration.status_code==200, concentration.text
    payload=concentration.json()
    assert payload['plan_id']==identifier
    assert payload['crop']=='Corn' and payload['district']=='Matara' and payload['season']=='Maha'
    assert payload['status'] in ('available','Insufficient Data')
    assert client.get(base+'/production-concentration-indicator',headers=peer).status_code==404


@pytest.mark.parametrize('malformed',[False,True])
def test_analysis_failure_preserves_discoverable_plan_and_retry(tmp_path,monkeypatch,malformed):
    path=tmp_path/'recovery.sqlite3'; client=client_for(path)
    _,session=account(client); h=headers(session['access_token']); original=farmer_workflow.run
    def fail(*args,**kwargs):
        if malformed:return {'private':'fictional-private-error'}
        raise RuntimeError('fictional-private-error')
    monkeypatch.setattr(farmer_workflow,'run',fail)
    result=client.post('/api/farmer-workflow/plans',headers=h,json=dict(plan(),season='Maha'))
    assert result.status_code==201,result.text
    value=result.json(); identifier=value['plan']['plan_id']; report=value['workflow']
    assert report['analysis_status']=='failed' and report['assessment']['risk_level'] is None
    assert report['recovery']['plan_saved'] and report['recovery']['retryable']
    assert 'fictional-private-error' not in result.text
    assert client.post('/api/farmer-workflow/plans',headers=h,json=plan()).status_code==409
    restarted=client_for(path)
    assert restarted.get('/api/cultivation-plans',headers=h).json()['items'][0]['plan_id']==identifier
    monkeypatch.setattr(farmer_workflow,'run',original)
    retry=restarted.post(report['recovery']['endpoint'],headers=h,json=report['recovery']['request'])
    assert retry.status_code==200 and retry.json()['analysis_status']=='completed'
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM cultivation_plan_versions').fetchone()[0]==1


@pytest.mark.parametrize('planting',['2020-01-01',datetime.now(timezone.utc).date().isoformat()])
def test_historical_records_explicitly_ineligible_preserved(tmp_path,planting):
    client=client_for(tmp_path/'historical.sqlite3'); _,session=account(client); h=headers(session['access_token'])
    historical=plan(planting_date=planting)
    assert client.post('/api/farmer-workflow/plans',headers=h,json=historical).status_code==422
    created=client.post('/api/cultivation-plans',headers=h,json=historical)
    assert created.status_code==201; identifier=created.json()['plan']['plan_id']
    report=client.post('/api/farmer-workflow/analyze',headers=h,json=dict(plan_id=identifier)).json()
    assert report['analysis_status']=='not_applicable' and report['status']=='insufficient_evidence'
    assert report['assessment']['risk_level'] is None
    risk=client.get('/api/cultivation-plans/'+identifier+'/risk-assessment?season=Maha',headers=h)
    assert risk.status_code==200 and risk.json()['status']=='insufficient_evidence'
    assert client.get('/api/cultivation-plans',headers=h).json()['total']==1


def test_configuration_failure_before_write(tmp_path):
    path=tmp_path/'preflight.sqlite3'
    client=TestClient(create_app(path,{},[],alternative_evidence={'unknown':True}))
    _,session=account(client); h=headers(session['access_token'])
    assert client.post('/api/farmer-workflow/plans',headers=h,json=plan()).status_code==503
    assert client.get('/api/cultivation-plans',headers=h).json()['total']==0


def test_account_cohort_runs_existing_clustering_without_peer_disclosure(tmp_path,monkeypatch):
    from app.services import risk_indicators
    path=tmp_path/'cohort.sqlite3'; client=client_for(path); observed=[]
    original=risk_indicators.analyze
    def capture(*args,**kwargs):
        result=original(*args,**kwargs); observed.append(result); return result
    monkeypatch.setattr(risk_indicators,'analyze',capture)
    identities=[]
    for i in range(6):
        profile,session=account(client,'fictional-cohort-'+str(i)); h=headers(session['access_token'])
        identities.append(profile['farmer_id'])
        result=client.post('/api/cultivation-plans',headers=h,json=plan(crop='Corn' if i<3 else 'Brinjal'))
        assert result.status_code==201
        if i==0:owner_headers=h; identifier=result.json()['plan']['plan_id']
    response=client.post('/api/farmer-workflow/analyze',headers=owner_headers,json=dict(plan_id=identifier,season='Maha'))
    assert response.status_code==200
    assert observed[-1]['status']=='available' and observed[-1]['kmeans'] and observed[-1]['dbscan']
    assert response.json()['assessment']['indicators']['status']=='available'
    assert response.json()['assessment']['risk_level'] is None
    assert not contains_collective_numbers(response.json())
    assert all(identity not in response.text for identity in identities[1:])
    with sqlite3.connect(path) as db:db.execute('UPDATE farmer_sessions SET created_at=0, expires_at=1')
    assert client.post('/api/farmer-workflow/analyze',headers=owner_headers,json=dict(plan_id=identifier)).status_code==401


def test_history_update_retains_previous_available_version(tmp_path):
    client=client_for(tmp_path/'history.sqlite3'); _,session=account(client); h=headers(session['access_token'])
    created=client.post('/api/cultivation-plans',headers=h,json=plan()).json()
    identifier=created['plan']['plan_id']; cutoff=datetime.now(timezone.utc).isoformat()
    assert client.put('/api/cultivation-plans/'+identifier,headers=h,json=plan(planting_date='2020-01-01')).status_code==200
    current=client.post('/api/farmer-workflow/analyze',headers=h,json=dict(plan_id=identifier)).json()
    assert current['analysis_status']=='not_applicable'
    previous=client.post('/api/farmer-workflow/analyze',headers=h,json=dict(plan_id=identifier,as_of=cutoff)).json()
    assert previous['analysis_status']=='completed'
    assert client.get('/api/cultivation-plans/'+identifier,headers=h).json()['plan']['planting_date']=='2020-01-01'
