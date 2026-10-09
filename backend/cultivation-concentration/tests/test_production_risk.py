"""Fictional fixture evidence, not activated agronomic guidelines."""
from datetime import datetime,timezone
from app.schemas.production_risk import ProductionRegistry
from app.services.production_risk import evaluate,farmer_response,alternatives
from app.schemas.alternatives import EvidenceRegistry
from tests.test_alternatives import evidence
from fastapi.testclient import TestClient
from app.main import create_app

def test_district_only_workflow_defaults_to_missing_evidence(tmp_path):
    client=TestClient(create_app(tmp_path/'district.sqlite3',{'owner':'owner'}))
    result=client.post('/api/farmer-workflow/plans',headers={'Authorization':'Bearer owner'},json=dict(crop='Corn',
        district='Matara',land_size_acres=2,planting_date='2030-01-01',expected_harvest_date='2030-04-01',season='Maha'))
    assert result.status_code==201
    assert result.json()['plan']['region']=='unspecified'
    assessment=result.json()['workflow']['experimental_production_assessment']
    assert assessment['validation_status']=='insufficient_evidence'
    assert assessment['experimental_risk_level'] is None and assessment['overlapping_acres'] is None
    assert result.json()['workflow']['experimental_alternatives']==[]

def fixture():
    plans=[dict(plan_id=str(i),farmer_id=str(i),district='Matara',region='north' if i<2 else 'south',crop='Corn',
        land_size_acres=2,planting_date='2030-01-01',expected_harvest_date='2030-04-01',updated_at='2020-01-01T00:00:00+00:00') for i in range(3)]
    entry=dict(crop='Corn',district='Matara',season='Maha',reference='FICTIONAL verified evidence',verified=True,
        available_at='2020-01-01T00:00:00Z',verified_at='2020-01-01T00:00:00Z',valid_from='2029-01-01',valid_to='2031-12-31',
        applicable_without_variety_or_product=True,yield_kg_per_acre=100,reference_window_production_kg=[100,200,300,400],
        historical_observation_end='2019-01-01',reference_definition='FICTIONAL comparable registration reference',
        comparable_coverage_verified=True,quantile_method_approved_for_experiment=True)
    assignments=[dict(plan_id=p['plan_id'],updated_at=p['updated_at'],season='Maha',verified=True,
        reference='FICTIONAL season proof',available_at='2020-01-01T00:00:00Z') for p in plans]
    return plans,entry,assignments,datetime(2026,1,1,tzinfo=timezone.utc)

def test_production_once_district_scope_and_privacy():
    plans,entry,assignments,cutoff=fixture()
    registry=ProductionRegistry(evidence=[entry],season_assignments=assignments)
    result=evaluate(plans,plans[0],'Maha',cutoff,registry)
    assert result['expected_total_production_kg']==600 and result['new_farmer_production_kg']==200
    assert result['overlapping_plan_count']==3 and result['overlapping_acres']==6
    assert result['historical_reference_production_kg']==250 and result['production_ratio']==2.4
    assert result['experimental_risk_level']=='High'
    assert farmer_response(result)['expected_total_production_kg'] is None
    assert farmer_response(result)['new_farmer_production_kg']==200
    # An existing estimate is ignored instead of added a second time.
    plans[0]['expected_production_kg']=9999
    assert evaluate(plans,plans[0],'Maha',cutoff,registry)['expected_total_production_kg']==600

def test_missing_late_sparse_and_revision_evidence():
    plans,entry,assignments,cutoff=fixture()
    for changed in ({'verified':False},{'available_at':'2027-01-01T00:00:00Z'}, {'comparable_coverage_verified':False}):
        assert evaluate(plans,plans[0],'Maha',cutoff,ProductionRegistry(evidence=[dict(entry,**changed)],season_assignments=assignments))['experimental_risk_level'] is None
    assert evaluate(plans,plans[0],'Yala',cutoff,ProductionRegistry(evidence=[entry],season_assignments=assignments))['validation_status']=='insufficient_evidence'
    registry=ProductionRegistry(evidence=[entry],season_assignments=assignments)
    assert evaluate(plans[:1],plans[0],'Maha',cutoff,registry)['experimental_risk_level'] is None
    plans[1]['updated_at']='2021-01-01T00:00:00Z'
    assert evaluate(plans,plans[0],'Maha',cutoff,registry)['experimental_risk_level'] is None

def test_experimental_alternatives_separate_and_verified():
    plans,entry,assignments,cutoff=fixture()
    for i in range(3,6):
        p=dict(plans[0],plan_id=str(i),farmer_id=str(i),crop='Brinjal');plans.append(p)
        assignments.append(dict(assignments[0],plan_id=str(i)))
    candidate=dict(entry,crop='Brinjal',reference_window_production_kg=[1000,1200,1400,1600])
    registry=ProductionRegistry(evidence=[entry,candidate],season_assignments=assignments)
    current=evaluate(plans,plans[0],'Maha',cutoff,registry)
    values=alternatives(plans,plans[0],'Maha',cutoff,registry,EvidenceRegistry.model_validate(evidence()),current)
    assert len(values)==1 and values[0]['crop']=='Brinjal'
    assert values[0]['status']=='experimental_candidate_not_approved_recommendation'
    assert alternatives(plans,plans[0],'Maha',cutoff,registry,EvidenceRegistry(),current)==[]
