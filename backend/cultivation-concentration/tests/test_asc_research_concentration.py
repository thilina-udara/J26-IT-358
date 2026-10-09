"""Fictional software checks only; no actual source access or model fitting."""
from copy import deepcopy
import pytest
from ml.asc_2025_research_concentration import analyze,classify
from ml.preprocessing.build_production_reference import build
from tests.test_production_reference import row


def history():
    return [row(str(i),Land_Size_Acres=str(acres),Expected_Harvest_Date=f'{4+i}/1/2020')
            for i,acres in enumerate((1,2,4))]


def current(identity='own',**changes):
    return row(identity,**dict(dict(Year='2025',Planting_Date='1/1/2025',Expected_Harvest_Date='4/1/2025'),**changes))


@pytest.mark.parametrize('acres,label',[(1,'Low'),(1.66,'Medium'),(2,'Medium'),(2.68,'Medium'),(3,'High')])
def test_documented_categories_and_boundaries(acres,label):
    reference=build(history())
    result=classify(acres,'Matara','Corn','Maha',reference)
    assert result['research_concentration_category']==label
    assert result['validation_status']=='experimental'
    assert 'HINDSIGHT' in result['limitations'][0]
    assert result['reference_sample_size']==3


def test_exact_matching_overlap_and_determinism():
    rows=[current('a'),current('b',Planting_Date='1/2/2025',Expected_Harvest_Date='4/15/2025'),
          current('other',District='Hambantota'),current('crop',Crop='Brinjal'),current('season',Season='Yala')]
    result=analyze(history(),rows+[rows[0]])
    assert len(result['results'])==5
    last=result['results'][-1]
    assert last['overlapping_plan_count']==2 and last['current_overlap_acres']==4
    assert analyze(history(),list(reversed(rows)))==result
    changed=deepcopy(rows);changed[1]['Expected_Harvest_Date']='4/16/2025'
    assert analyze(history(),changed)['results'][-1]['overlapping_plan_count']==1
    production=deepcopy(rows)
    for r in production:r['Expected_Production_kg']='999999'
    assert [r['research_concentration_category'] for r in analyze(history(),production)['results']]==[r['research_concentration_category'] for r in result['results']]


@pytest.mark.parametrize('damage',['empty','invalid','window','year','flat'])
def test_invalid_references_do_not_get_fallback_labels(damage):
    reference=build(history())
    if damage=='empty':reference['reference_distributions']=[]
    elif damage=='flat':reference=build([row('one')])
    else:
        for w in reference['windows']:
            if w['scope']=='descriptive_development_2020_2023' and w['half_window_days']==14:
                if damage=='invalid':w['acres']=float('nan')
                elif damage=='window':w['window_end']=w['harvest_anchor']
                else:w['recorded_year']=2025
    assert classify(2,'Matara','Corn','Maha',reference)['research_concentration_category']=='insufficient_evidence'


def test_no_protected_or_future_cohort():
    with pytest.raises(ValueError):analyze([dict(Year='2024')],[current()])
    with pytest.raises(ValueError):analyze(history(),[dict(Year='2026')])
