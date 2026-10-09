"""Fictional engineering checks, not threshold validation."""
from datetime import datetime,date,timezone
from app.schemas.cultivation_plan import Plan
from app.services.cultivation_plans import PlanStore
from app.services.plan_clustering import snapshot
from app.services.risk_indicators import prepare_indicators
from app.services.current_plan_risk import evaluate
from app.services.privacy import farmer_view
from tests.test_security_privacy import contains_collective_numbers

def test_overlap_regions_crops_and_regional_share(tmp_path):
    store=PlanStore(tmp_path/'fictional.sqlite3')
    with store.connection() as db:
        for i in range(9):
            store.record_version(db,Plan(plan_id=str(i),farmer_id='fixture-'+str(i),district='Matara',
                region='south' if i==8 else 'north',crop='Brinjal' if 4<=i<=6 else 'Corn',
                land_size_acres=2,planting_date='2030-01-01',expected_harvest_date=(
                    ['2030-03-18','2030-04-01','2030-04-15','2030-04-16'][i] if i<4 else '2030-04-01'),
                status='active',submitted_at='2020-01-01T00:00:00Z',updated_at=('2021-01-01T00:00:00Z' if i==7 else '2020-01-01T00:00:00Z')))
    cutoff=datetime(2020,6,1,tzinfo=timezone.utc)
    indicators=prepare_indicators(store,cutoff,'Matara','north','Corn','Maha',date(2030,4,1))
    assert indicators['overlapping_farmer_count']==3 and indicators['total_planned_acreage']==6
    assert indicators['harvest_overlap_intensity']==.75
    assert indicators['regional_crop_context']['crop_share_of_regional_window_acreage']==.5
    assert evaluate(indicators)['risk_level'] is None
    assert not contains_collective_numbers(farmer_view(evaluate(indicators)))
    assert 'fixture-' not in str(evaluate(indicators))
    # Revised requester replaces its own contribution in the latest snapshot.
    owned=Plan.model_validate(next(p for p in snapshot(store,cutoff) if p['plan_id']=='1'))
    with store.connection() as db:store.record_version(db,owned.model_copy(update={'land_size_acres':5,'updated_at':datetime(2021,1,1,tzinfo=timezone.utc)}))
    assert prepare_indicators(store,cutoff,'Matara','north','Corn','Maha',date(2030,4,1))['total_planned_acreage']==6
    assert prepare_indicators(store,datetime(2021,6,1,tzinfo=timezone.utc),'Matara','north','Corn','Maha',date(2030,4,1))['total_planned_acreage']==11

def test_single_farmer_never_implies_low_and_complement_private(tmp_path):
    store=PlanStore(tmp_path/'single.sqlite3')
    with store.connection() as db:
        for i in range(3):
            store.record_version(db,Plan(plan_id=str(i),farmer_id='same-farmer',district='Matara',region='north',crop='Corn',
                land_size_acres=2,planting_date='2030-01-01',expected_harvest_date='2030-04-01',status='active',
                submitted_at='2020-01-01T00:00:00Z',updated_at='2020-01-01T00:00:00Z'))
    indicators=prepare_indicators(store,datetime(2020,6,1,tzinfo=timezone.utc),'Matara','north','Corn','Maha',date(2030,4,1))
    assert indicators['status']=='suppressed_or_insufficient'
    assert evaluate(indicators)['status']=='insufficient_evidence' and evaluate(indicators)['risk_level'] is None
    assert 'total_planned_acreage' not in indicators
