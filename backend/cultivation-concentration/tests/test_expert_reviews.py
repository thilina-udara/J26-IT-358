from datetime import datetime,timezone
import json
import pytest
from pydantic import ValidationError
from app.services.risk_assessment import explain
from app.services.expert_reviews import create_case,template,digest,export_cases,validate_reviews,import_reviews
from tests.test_risk_indicators import store
from fastapi.testclient import TestClient
from app.main import create_app


def assessment():
    return explain(dict(status='available',as_of='2020-01-01T00:00:00Z',district='Matara',region='sensitive locality',crop='Corn',season='Maha',
        harvest_window_start='2030-03-18',overlapping_farmer_count=3,overlapping_plan_count=4,total_planned_acreage=8,
        harvest_overlap_intensity=.8,estimated_production_kg=None,historical_concentration_baseline=None,
        cluster_context={'kmeans':[],'dbscan':[]}))


def review(case,**changes):
    value=dict(case_id=case.case_id,case_digest=digest(case),reference_label='Uncertain',reason='Fictional test response, not an actual officer review',
        reviewer_id='fixture-reviewer',reviewer_role='fixture',reviewer_organization='fixture',reviewed_at='2021-01-01T00:00:00Z',rubric_version='fixture-v1')
    value.update(changes)
    return value


def test_explanations_export_privacy_and_empty_targets(tmp_path):
    value=assessment()
    assert value['risk_level'] is None and value['status']=='risk_level_unvalidated'
    assert len(value['missing_evidence'])>=4
    output=tmp_path/'cases.json'
    case=export_cases([value],output)[0]
    content=output.read_text()
    assert 'sensitive locality' not in content and 'farmer_id' not in content and 'plan_id' not in content
    assert case.reference_label is None and case.provisional_rule_label is None
    assert template(case)['reference_label'] is None
    assert case.scenario.harvest_month=='2030-04'
    with pytest.raises(FileExistsError):export_cases([value],output)


def test_reference_integrity_and_chronology():
    case=create_case(assessment())
    accepted=validate_reviews([case],[review(case)])
    assert accepted[0]['training_eligible'] is False
    assert accepted[0]['reviewer_identity_verified'] is False
    assert accepted[0]['review']['reference_label']=='Uncertain'
    for changes in ({'case_id':'unknown'},{'case_digest':'0'*64},{'reviewed_at':'2019-01-01T00:00:00Z'},
                    {'reviewed_at':'2099-01-01T00:00:00Z'},{'label_kind':'provisional_rule'},
                    {'reference_label':'SyntheticHigh'},{'reason':''},{'reviewer_id':''}):
        with pytest.raises(ValueError):validate_reviews([case],[review(case,**changes)])
    with pytest.raises(ValueError):validate_reviews([case],[review(case),review(case)])
    with pytest.raises(ValueError):validate_reviews([case],[template(case)])


def test_separate_import_and_suppression(tmp_path):
    cases_path=tmp_path/'cases.json'
    case=export_cases([assessment()],cases_path)[0]
    before=cases_path.read_bytes()
    reviews=tmp_path/'reviews.json';reviews.write_text(json.dumps([review(case)]))
    output=tmp_path/'validated.json'
    assert len(import_reviews(cases_path,reviews,output))==1
    assert cases_path.read_bytes()==before
    assert json.loads(output.read_text())['provisional_rule_reviews']==[]
    with pytest.raises(FileExistsError):import_reviews(cases_path,reviews,output)
    private=assessment();private['indicators']['status']='suppressed_or_insufficient'
    with pytest.raises(ValueError):create_case(private)


def test_assessment_api_asof_and_privacy(store):
    client=TestClient(create_app(store.path,analysis_tokens=['analyst']))
    args=dict(district='Matara',region='north',crop='Corn',season='Maha',harvest_date='2030-04-01',as_of='2020-06-01T00:00:00Z')
    endpoint='/api/cultivation-analysis/risk-assessment'
    assert client.get(endpoint,params=args).status_code==403
    headers={'Authorization':'Bearer analyst'}
    result=client.get(endpoint,params=args,headers=headers)
    assert result.status_code==200
    body=result.json()
    assert body['status']=='risk_level_unvalidated' and body['risk_level'] is None
    assert body['indicators']['total_planned_acreage']==6
    assert 'private-' not in json.dumps(body)
    earlier=client.get(endpoint,params={**args,'as_of':'2019-06-01T00:00:00Z'},headers=headers).json()
    assert earlier['indicators']['status']=='suppressed_or_insufficient'
    assert 'total_planned_acreage' not in earlier['indicators']
