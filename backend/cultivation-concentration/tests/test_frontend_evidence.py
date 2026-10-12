"""Presentation contracts over fictional plans and temporary SQLite only."""
import json
import sqlite3
from fastapi.testclient import TestClient
from app.main import create_app
from app.schemas.api_responses import RiskAssessmentResponse, PersonalizedPlanResponse
from app.schemas.cultivation_plan import PlanInput
from app.services.cultivation_plans import PlanStore
from app.services.privacy import farmer_view
from tests.test_farmer_auth import account, headers, plan
from tests.test_security_privacy import contains_collective_numbers
from tests.test_alternatives import path, call, evidence
from tests.test_personalized_planning import setup, post


def test_computed_but_withheld_and_repeated_edit_privacy(tmp_path):
    database=tmp_path/'evidence.sqlite3'; store=PlanStore(database)
    client=TestClient(create_app(database,{},[])); _,session=account(client)
    h=headers(session['access_token'])
    created=client.post('/api/cultivation-plans',headers=h,json=plan()).json()['plan']
    for name in ('fictional-peer-a','fictional-peer-b','fictional-peer-c'):
        store.save(PlanInput(**plan(),farmer_id=name),name)
    route='/api/cultivation-plans/'+created['plan_id']
    for acreage in (2,10,3):
        assert client.put(route,headers=h,json=plan(land_size_acres=acreage)).status_code==200
        result=client.get(route+'/risk-assessment',headers=h,params={'season':'Maha'}).json()
        assert result['indicators']['status']=='available'
        assert result['disclosure_status']=='collective_values_withheld'
        assert 'collective_values_protected' in result['reason_codes']
        assert result['status']=='risk_level_unvalidated' and result['risk_level'] is None
        assert not contains_collective_numbers(result)
        assert 'cluster_context' not in result['indicators']
        assert 'fictional-peer' not in json.dumps(result)
        RiskAssessmentResponse.model_validate(result)
    _,peer=account(client,'fictional-other-account')
    assert client.get(route+'/risk-assessment?season=Maha',headers=headers(peer['access_token'])).status_code==404
    assert client.get(route+'/risk-assessment?season=Maha').status_code==401
    assert client.get('/api/cultivation-analysis/clusters?district=Matara',headers=h).status_code==403


def test_missing_evidence_and_model_unavailable_workflow(tmp_path):
    client=TestClient(create_app(tmp_path/'missing.sqlite3',{},[])); _,s=account(client); h=headers(s['access_token'])
    result=client.post('/api/farmer-workflow/plans',headers=h,json=dict(plan(),season='Maha')).json()
    report=result['workflow']
    assert report['analysis_status']=='completed' and report['status']=='insufficient_evidence'
    risk=report['assessment']
    assert risk['indicators']['status']=='suppressed_or_insufficient'
    assert risk['disclosure_status']=='collective_values_withheld'
    assert 'classification_reference_missing' in risk['reason_codes']
    assert 'coverage_or_privacy_limited' in risk['reason_codes']
    assert risk['missing_evidence'] and risk['risk_level'] is None
    historical=report['historical_prediction']
    assert historical['status']=='insufficient_evidence'
    assert historical['reason_codes']==['historical_prediction_unavailable']
    assert historical['scope']=='historical_district_crop_season_proxy'
    assert report['recommendations']['status']=='blocked_unvalidated_risk'
    assert report['recommendations']['alternatives']==[]
    assert not contains_collective_numbers(report)


def test_unapproved_comparison_has_separate_approval_and_coverage(path):
    result=call(path,{}).json()
    assert result['status']=='insufficient_evidence' and result['alternatives']==[]
    assert result['disclosure_status']=='collective_values_withheld'
    for comparison in result['comparisons']:
        assert comparison['approval_status']=='applicable_suitability_unavailable'
        assert 'suitability_approval_unavailable' in comparison['reason_codes']
        assert 'comparable_coverage_unavailable' in comparison['reason_codes']
    assert not contains_collective_numbers(result)


def test_approved_conditional_alternative_stays_unvalidated(path):
    result=call(path,evidence()).json()
    alternative=result['alternatives'][0]
    assert alternative['status']=='eligible_alternative'
    assert alternative['approval_status']=='applicable_suitability_approved'
    assert alternative['reason_codes']==['risk_classification_unvalidated']
    assert alternative['risk_level']=='unknown_unvalidated'
    assert not contains_collective_numbers(result)


def test_partial_planning_approval_does_not_mean_complete(setup):
    client,request,*_=setup
    approved=post(client,request).json()
    assert approved['status']=='partial_plan'
    assert approved['approval_status']=='approved_activities_only'
    assert approved['reason_codes']==['schedule_incomplete']
    assert approved['activities'] and approved['missing_categories']
    unavailable=post(client,dict(request,season='Yala')).json()
    assert unavailable['approval_status']=='no_approved_applicable_activities'
    assert 'applicable_guidance_unavailable' in unavailable['reason_codes']
    assert unavailable['activities']==[]
    PersonalizedPlanResponse.model_validate(unavailable)


def test_legacy_saved_plan_metadata_does_not_rewrite_history(setup):
    client,request,path,*_=setup
    saved=post(client,request,'save').json()
    with sqlite3.connect(path) as db:
        payload=json.loads(db.execute('SELECT payload FROM personalized_plan_versions').fetchone()[0])
        payload.pop('approval_status');payload.pop('reason_codes')
        serialized=json.dumps(payload)
        db.execute('UPDATE personalized_plan_versions SET payload=?',(serialized,))
    result=client.get('/api/personalized-cultivation-plans/'+request['plan_id'],headers=headers('owner')).json()
    assert result['personalized_plan']['approval_status']=='approved_activities_only'
    assert result['revision_id']==saved['revision_id'] and result['stale'] is False
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT payload FROM personalized_plan_versions').fetchone()[0]==serialized


def test_unrecorded_legacy_approval_is_not_inferred():
    from app.services.personalized_planning import evidence_metadata
    result=evidence_metadata(dict(activities=[dict(activity_name='fictional legacy activity')]))
    assert result['approval_status']=='approval_not_recorded'


def test_workflow_partial_success_and_retry(tmp_path,monkeypatch):
    from app.services import farmer_workflow
    client=TestClient(create_app(tmp_path/'recovery.sqlite3',{},[])); _,s=account(client); h=headers(s['access_token'])
    original=farmer_workflow.run
    def fail(*args,**kwargs):raise RuntimeError('fictional private diagnostic')
    monkeypatch.setattr(farmer_workflow,'run',fail)
    response=client.post('/api/farmer-workflow/plans',headers=h,json=plan())
    assert response.status_code==201
    report=response.json()['workflow']
    assert report['analysis_status']=='failed' and report['status']=='analysis_unavailable'
    assert report['reason_codes']==['analysis_unavailable']
    assert report['assessment']['reason_codes']==['analysis_not_evaluated','collective_values_protected']
    assert report['recovery']['plan_saved'] and report['recovery']['retryable']
    assert 'fictional private diagnostic' not in response.text
    monkeypatch.setattr(farmer_workflow,'run',original)
    retry=client.post(report['recovery']['endpoint'],headers=h,json=report['recovery']['request'])
    assert retry.status_code==200 and retry.json()['analysis_status']=='completed'


def test_filter_preserves_original_fields_without_mutating_input():
    original=dict(status='available',total_planned_acreage=123,privacy_policy='old',
                  nested=dict(kmeans=[dict(farmer_id='fictional-peer')],reason='Existing explanation'),
                  missing_evidence=['Existing evidence requirement'])
    filtered=farmer_view(original)
    assert original['total_planned_acreage']==123
    assert filtered['status']=='available'
    assert filtered['missing_evidence']==original['missing_evidence']
    assert filtered['nested']['reason']=='Existing explanation'
    assert 'kmeans' not in filtered['nested']
    assert not contains_collective_numbers(filtered)


def test_historical_records_are_not_computation_success(tmp_path):
    client=TestClient(create_app(tmp_path/'historical.sqlite3',{},[])); _,s=account(client); h=headers(s['access_token'])
    saved=client.post('/api/cultivation-plans',headers=h,json=plan(planting_date='2020-01-01',expected_harvest_date='2020-04-01')).json()['plan']
    result=client.post('/api/farmer-workflow/analyze',headers=h,json=dict(plan_id=saved['plan_id'])).json()
    assert result['analysis_status']=='not_applicable'
    assert result['reason_codes']==['analysis_not_applicable']
    assert result['assessment']['risk_level'] is None
