from datetime import datetime,timezone
import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.schemas.cultivation_plan import Plan
from app.services.cultivation_plans import PlanStore


def evidence():
    base=dict(district='Matara',region='north',source_reference='fictional-fixture-evidence',verified_by='fictional-reviewer',
        verified_at='2020-01-01T00:00:00Z',available_at='2020-01-01T00:00:00Z',valid_from='2029-01-01',valid_to='2031-12-31',verified=True)
    return dict(suitability=[dict(base,evidence_id='s-fixture',crop='Brinjal',min_land_acres=1,max_land_acres=10,
        min_harvest_days=80,max_harvest_days=100,applicable_without_additional_inputs=True,applicability_statement='Fictional test applicability, not agronomic guidance')],
        coverage=[dict(base,evidence_id='c-'+crop,crop=crop,comparable_registration_scope=True,
            registration_scope_id='fictional-scope',coverage_statement='Fictional fixture coverage') for crop in ('Corn','Brinjal')])


def body(**changes):
    value=dict(selected_crop='Corn',district='Matara',region='north',land_size_acres=2,
               planting_date='2030-01-01',expected_harvest_date='2030-04-01',as_of='2020-06-01T00:00:00Z')
    value.update(changes);return value


@pytest.fixture
def path(tmp_path):
    path=tmp_path/'alternatives.sqlite3';store=PlanStore(path)
    with store.connection() as db:
        for crop,acreage in (('Corn',5),('Brinjal',2)):
            for i,harvest in enumerate(('2030-03-18','2030-04-01','2030-04-15')):
                store.record_version(db,Plan(plan_id=crop+str(i),farmer_id='private-'+str(i),district='Matara',region='north',crop=crop,
                    land_size_acres=acreage,planting_date='2030-01-01',expected_harvest_date=harvest,status='active',
                    submitted_at='2020-01-01T00:00:00Z',updated_at='2020-01-01T00:00:00Z'))
    return path


def call(path,registry,value=None):
    client=TestClient(create_app(path,{'token':'requester'},alternative_evidence=registry))
    return client.post('/api/cultivation-analysis/alternatives',json=value or body(),headers={'Authorization':'Bearer token'})


def test_conditional_comparison_original_exclusion_and_privacy(path):
    response=call(path,evidence());assert response.status_code==200
    result=response.json();alternative=result['alternatives'][0]
    assert alternative['crop']=='Brinjal'
    assert 'planned_acreage' not in alternative['planned_concentration']
    assert 'scenario_inclusive_acreage' not in alternative['planned_concentration']
    assert 'overlapping_farmer_count' not in alternative['planned_concentration']
    assert 'scenario_inclusive_acreage' not in result['selected_concentration']
    assert all(c['crop']!='Corn' for c in result['comparisons'])
    assert 'private-' not in json.dumps(result) and 'farmer_id' not in json.dumps(result)
    assert alternative['risk_level']=='unknown_unvalidated'


def test_missing_guidelines_and_coverage(path):
    result=call(path,{}).json()
    assert result['status']=='insufficient_evidence' and result['alternatives']==[]
    registry=evidence();registry['coverage']=[]
    assert call(path,registry).json()['alternatives']==[]
    registry=evidence();registry['suitability'][0]['applicable_without_additional_inputs']=False
    assert call(path,registry).json()['alternatives']==[]


def test_sparse_regions_and_window_privacy(path):
    for changes in ({'region':'south'},{'district':'Hambantota'},{'expected_harvest_date':'2030-04-02'}):
        result=call(path,evidence(),body(**changes)).json()
        assert result['alternatives']==[]
        brinjal=next(c for c in result['comparisons'] if c['crop']=='Brinjal')
        assert brinjal['planned_concentration']['status']=='suppressed_or_insufficient'
        assert 'planned_acreage' not in brinjal['planned_concentration']


def test_asof_evidence_and_plan_availability(path):
    assert call(path,evidence(),body(as_of='2019-01-01T00:00:00Z')).json()['alternatives']==[]
    registry=evidence();registry['suitability'][0]['verified_at']='2021-01-01T00:00:00Z'
    assert call(path,registry).json()['alternatives']==[]
    assert call(path,evidence(),body(as_of='2099-01-01T00:00:00Z')).status_code==422
    assert call(path,evidence(),body(as_of='2020-01-01T00:00:00')).status_code==422


def test_auth_bounds_and_replacement_ownership(path):
    client=TestClient(create_app(path,{'token':'requester'},alternative_evidence=evidence()))
    assert client.post('/api/cultivation-analysis/alternatives',json=body()).status_code==401
    assert call(path,evidence(),body(land_size_acres=0)).status_code==422
    assert call(path,evidence(),body(replacing_plan_id='Corn0')).status_code==404
    assert call(path,evidence(),body(selected_crop='unsupported')).status_code==422


def test_coverage_scope_mismatch(path):
    registry=evidence();registry['coverage'][1]['registration_scope_id']='other'
    assert call(path,registry).json()['alternatives']==[]
