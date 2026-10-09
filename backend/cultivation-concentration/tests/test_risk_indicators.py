from datetime import date,datetime,timezone
import json
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import create_app
from app.schemas.cultivation_plan import Plan
from app.services.cultivation_plans import PlanStore
from app.services.risk_indicators import prepare_indicators
from ml.preprocessing.risk_training_schema import RiskFeatures,LabelEvidence,TrainingRecord,training_projection,FEATURE_NAMES


@pytest.fixture
def store(tmp_path):
    repository=PlanStore(tmp_path/'risk-test.sqlite3')
    with repository.connection() as db:
        for i,harvest in enumerate(('2030-03-18','2030-04-01','2030-04-15','2030-04-16')):
            plan=Plan(plan_id=str(i),farmer_id=f'private-{i}',district='Matara',region='north',crop='Corn',
                land_size_acres=2,planting_date='2030-01-01',expected_harvest_date=harvest,status='active',
                submitted_at='2020-01-01T00:00:00Z',updated_at='2020-01-01T00:00:00Z')
            repository.record_version(db,plan)
    return repository


def test_calculation_boundaries_missing_data_and_privacy(store):
    result=prepare_indicators(store,datetime(2020,6,1,tzinfo=timezone.utc),'Matara',' NORTH ','Corn','Maha',date(2030,4,1))
    assert result['overlapping_farmer_count']==3
    assert result['overlapping_plan_count']==3
    assert result['total_planned_acreage']==6
    assert result['harvest_overlap_intensity']==.75
    assert result['estimated_production_kg'] is None
    assert result['historical_concentration_baseline'] is None
    assert result['label']=={'kind':'unlabeled','value':None}
    assert 'private-' not in json.dumps(result)
    assert 'farmer_id' not in json.dumps(result)
    assert result['cluster_context']['scope'].startswith('district')


def test_asof_and_suppression(store):
    cutoff=datetime(2019,6,1,tzinfo=timezone.utc)
    result=prepare_indicators(store,cutoff,'Matara','north','Corn','Maha',date(2030,4,1))
    assert result['status']=='suppressed_or_insufficient'
    assert 'total_planned_acreage' not in result
    assert 'cluster_context' not in result
    with pytest.raises(ValueError):
        prepare_indicators(store,cutoff,'Matara','north','Corn','Maha',date(2018,4,1))


def features():
    return RiskFeatures(district='Matara',region='north',crop='Corn',season='Maha',overlapping_farmer_count=3,
                        overlapping_plan_count=3,total_planned_acreage=6,harvest_overlap_intensity=.75)


def test_training_no_leaky_fields_or_unlabeled_targets():
    with pytest.raises(ValidationError):
        RiskFeatures(**features().model_dump(),risk_score=1.5)
    record=TrainingRecord(snapshot_id='fictional',forecast_cutoff='2020-01-01T00:00:00Z',
        maximum_input_available_at='2020-01-01T00:00:00Z',features=features())
    with pytest.raises(ValueError):training_projection([record])
    with pytest.raises(ValidationError):
        TrainingRecord(**{**record.model_dump(),'maximum_input_available_at':'2021-01-01T00:00:00Z'})
    with pytest.raises(ValidationError):LabelEvidence(kind='observed_reference',value='High')
    provisional=LabelEvidence(kind='provisional_rule',value='Medium',evidence_reference='fictional rule evidence',definition_version='fixture-v1')
    labeled=record.model_copy(update={'label':provisional})
    with pytest.raises(ValueError):training_projection([labeled])
    x,y=training_projection([labeled],allow_provisional=True)
    assert set(x[0])==set(FEATURE_NAMES) and y==['Medium']
    assert 'value' not in x[0] and 'snapshot_id' not in x[0]


def test_endpoint_permissions_and_metadata(store):
    client=TestClient(create_app(store.path,{'farmer':'private-0'},['analyst']))
    args=dict(district='Matara',region='north',crop='Corn',season='Maha',harvest_date='2030-04-01',as_of='2020-06-01T00:00:00Z')
    endpoint='/api/cultivation-analysis/risk-indicators'
    assert client.get(endpoint,params=args).status_code==403
    response=client.get(endpoint,params=args,headers={'Authorization':'Bearer analyst'})
    assert response.status_code==200
    assert response.json()['label']['kind']=='unlabeled'
    assert client.get(endpoint,params={**args,'as_of':'2099-01-01T00:00:00Z'},headers={'Authorization':'Bearer analyst'}).status_code==422
