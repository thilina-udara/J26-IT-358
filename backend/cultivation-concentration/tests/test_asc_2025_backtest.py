"""Fictional backtest fixtures only; never opens ASC or sealed datasets."""
import pytest
from ml.asc_2025_backtest import replay
from tests.test_production_reference import row


def test_access_gate_and_year_isolation():
    with pytest.raises(PermissionError):replay([],[])
    with pytest.raises(ValueError):replay([{'Year':'2025'}],[],access_authorized=True)
    with pytest.raises(ValueError):replay([], [{'Year':'2026'}],access_authorized=True)


def test_retrospective_separation_order_and_missing_evidence():
    history=[row('history'+district, District=district, Year='2024', Planting_Date='1/1/2024',Expected_Harvest_Date='4/1/2024')
             for district in ('Matara','Hambantota')]
    current=[row('a',Year='2025',Planting_Date='1/1/2025',Expected_Harvest_Date='4/1/2025'),
             row('b',Year='2025',Planting_Date='1/2/2025',Expected_Harvest_Date='4/15/2025'),
             row('other',District='Hambantota',Year='2025',Planting_Date='1/2/2025',Expected_Harvest_Date='4/1/2025')]
    result=replay(history,list(reversed(current))+current[:1],access_authorized=True)
    assert result['reference']['permitted_years']==list(range(2020,2025))
    assert result['category_counts']=={'insufficient_evidence':3}
    assert [r['plan_count'] for r in result['results']]==[1,2,1]
    assert result['results'][1]['recorded_expected_production_kg']==400
    assert result['results'][2]['planned_acres']==2
    assert replay(history,current,access_authorized=True)==result


def test_same_date_batch_and_harvest_spillover():
    history=[row('past',Year='2024',Planting_Date='1/1/2024',Expected_Harvest_Date='4/1/2024'),
             row('spillover',Year='2024',Planting_Date='12/1/2024',Expected_Harvest_Date='2/1/2025',Expected_Production_kg='999999')]
    current=[row(identity,Year='2025',Planting_Date='1/1/2025',Expected_Harvest_Date='4/1/2025') for identity in ('a','b')]
    result=replay(history,current,access_authorized=True)
    assert all(r['plan_count']==1 for r in result['results'])
    assert all(w['expected_kg']==200 for w in result['reference']['windows'])
    assert all(r['assessment']['experimental_risk_level'] is None for r in result['results'])
