"""All approval and agronomic values in these fixtures are fictional."""
import json
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.services.cultivation_plans import PlanStore
from app.schemas.cultivation_plan import Plan
from tests.test_alternatives import evidence


@pytest.fixture
def setup(tmp_path):
    directory=tmp_path/'guidelines';directory.mkdir()
    entry=dict(entry_id='fixture',crop_name='Bandakka',verification_status='source_checked',
        source_url='https://example.invalid/fictional',district_applicability=['Matara'],season=['Maha'],
        variety=None,guideline_category='harvest',activity_name='Fictional harvest',notes='Fictional only',
        timing_reference='direct_sowing',days_offset={'min':50,'max':56},repeat_interval_days=2,
        max_occurrences=4,rate_per_hectare={'min':10,'max':20},unit='kg/ha')
    (directory/'verified_entries.json').write_text(json.dumps({'entries':[entry]}))
    approval=dict(entry_id='fixture',claim_verified=True,approved_by='fictional officer',
        evidence_reference='fictional approval',available_at='2020-01-01T00:00:00Z',
        approved_at='2020-01-01T00:00:00Z',district='Matara',region='north',season='Maha',
        variety=None,planting_method='direct_sowing')
    path=tmp_path/'test.sqlite3'
    client=TestClient(create_app(path,{'owner':'owner','other':'other'},alternative_evidence=evidence(),
        planning_approvals=[approval],planning_guideline_dir=directory))
    response=client.post('/api/cultivation-plans',headers={'Authorization':'Bearer owner'},json=dict(
        farmer_id='owner',district='Matara',region='north',crop='Bandakka',land_size_acres=2.4710538147,
        planting_date='2030-01-01',expected_harvest_date='2030-04-01'))
    assert response.status_code==201
    request=dict(plan_id=response.json()['plan']['plan_id'],final_crop='Bandakka',district='Matara',
        region='north',land_size_acres=2.4710538147,planting_date='2030-01-01',season='Maha',planting_method='direct_sowing')
    return client,request,path,directory,approval


def post(client,request,operation='generate',token='owner'):
    return client.post('/api/personalized-cultivation-plans/'+operation,json=request,headers={'Authorization':'Bearer '+token})


def test_original_units_and_multiple_harvests(setup):
    client,request,*_=setup
    result=post(client,request).json()
    assert result['status']=='partial_plan'
    activity=result['activities'][0]
    assert activity['quantity']['min']==pytest.approx(10)
    assert len(activity['date_windows'])==4
    assert activity['date_windows'][0]['earliest']=='2030-02-20'
    assert activity['source_url'].endswith('fictional')
    assert 'farmer_id' not in json.dumps(result)


@pytest.mark.parametrize('changes',[{'region':'south'},{'variety':'other'},{'season':'Yala'},
    {'planting_method':'transplanting'}])
def test_inapplicability(setup,changes):
    client,request,*_=setup
    assert post(client,dict(request,**changes)).json()['activities']==[]


def test_missing_real_guidelines_and_no_implicit_activation(setup):
    _,request,path,_,_=setup
    client=TestClient(create_app(path,{'owner':'owner'}))
    for crop in ('Bandakka','Brinjal','Pumpkin','Corn','Mung Beans','Chillies'):
        # Original crop allowed; no fabricated alternative eligibility.
        if crop=='Bandakka':
            assert post(client,request).json()['activities']==[]
        else:assert post(client,dict(request,final_crop=crop)).status_code==409


def test_owner_revisions_and_no_double_count(setup):
    client,request,path,*_=setup
    assert post(client,request,token='other').status_code==404
    assert client.post('/api/personalized-cultivation-plans/generate',json=request).status_code==401
    for _ in range(2):assert post(client,request,'save').status_code==200
    result=client.get('/api/personalized-cultivation-plans/'+request['plan_id'],headers={'Authorization':'Bearer owner'}).json()
    assert len(result['revisions'])==2 and not result['stale']
    with PlanStore(path).connection() as db:
        assert db.execute("SELECT count(*) FROM cultivation_plans WHERE status='active'").fetchone()[0]==1
    assert client.get('/api/personalized-cultivation-plans/'+request['plan_id'],headers={'Authorization':'Bearer other'}).status_code==404
    client.delete('/api/cultivation-plans/'+request['plan_id'],headers={'Authorization':'Bearer owner'})
    assert post(client,request,'save').status_code==409


def test_asof_and_unverified_claim(setup):
    client,request,path,directory,approval=setup
    assert post(client,dict(request,as_of='2019-01-01T00:00:00Z')).status_code==409
    assert post(client,dict(request,as_of='2099-01-01T00:00:00Z')).status_code==422
    client=TestClient(create_app(path,{'owner':'owner'},planning_guideline_dir=directory,
        planning_approvals=[dict(approval,claim_verified=False)]))
    assert post(client,request).json()['activities']==[]


def test_transplant_anchor_and_incompatible_unit(setup):
    _,request,path,directory,approval=setup
    data=json.loads((directory/'verified_entries.json').read_text())
    data['entries'][0].update(timing_reference='transplanting',unit='unknown',crop_name='Bandakka')
    (directory/'verified_entries.json').write_text(json.dumps(data))
    client=TestClient(create_app(path,{'owner':'owner'},planning_guideline_dir=directory,
        planning_approvals=[dict(approval,planting_method='transplanting')]))
    result=post(client,dict(request,planting_method='transplanting',nursery_sowing_date='2029-12-01')).json()
    assert result['activities'][0]['date_windows'][0]['earliest']=='2030-02-20'
    assert result['activities'][0]['quantity'] is None


def test_eligible_alternative_updates_same_plan(setup):
    client,request,path,*_=setup
    client.put('/api/cultivation-plans/'+request['plan_id'],headers={'Authorization':'Bearer owner'},json=dict(
        farmer_id='owner',district='Matara',region='north',crop='Corn',land_size_acres=2.4710538147,
        planting_date='2030-01-01',expected_harvest_date='2030-04-01'))
    store=PlanStore(path)
    with store.connection() as db:
        for crop,area in [('Corn',5),('Brinjal',2)]:
            for i in range(3):
                store.record_version(db,Plan(plan_id=crop+str(i),farmer_id='fictional-'+str(i),district='Matara',
                    region='north',crop=crop,land_size_acres=area,planting_date='2030-01-01',
                    expected_harvest_date='2030-04-01',status='active',submitted_at='2020-01-01T00:00:00Z',
                    updated_at='2020-01-01T00:00:00Z'))
    response=post(client,dict(request,final_crop='Brinjal'),'save')
    assert response.status_code==200,response.text
    assert response.json()['personalized_plan']['final_crop']=='Brinjal'
    assert client.get('/api/cultivation-plans/'+request['plan_id'],headers={'Authorization':'Bearer owner'}).json()['plan']['crop']=='Brinjal'
