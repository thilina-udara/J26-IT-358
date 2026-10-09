"""Fictional governance fixtures are software tests, never expert evidence."""
from datetime import datetime,timezone
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.services.expert_reviews import create_case,digest
from tests.test_expert_reviews import assessment

@pytest.fixture
def workflow(tmp_path):
    path=tmp_path/'references.sqlite3'
    client=TestClient(create_app(tmp_path/'plans.sqlite3',{'farmer':'farmer'},['analyst'],admin_tokens=['admin'],
        reviewer_tokens={'one':'one','two':'two','judge':'judge'},reference_database_path=path))
    admin={'Authorization':'Bearer admin'}
    for identity in ('one','two','judge'):
        assert client.post('/api/expert-validation/reviewers',headers=admin,json=dict(reviewer_id=identity,
            credential_evidence='fictional credential fixture',agricultural_role='fixture',organization='fixture',verified=True,
            can_adjudicate=identity=='judge')).status_code==200
    assert client.post('/api/expert-validation/rubrics',headers=admin,json=dict(rubric_version='fixture-v1',rubric_text='fictional test rubric',
        approved=True,approval_evidence='fictional fixture approval')).status_code==200
    case=create_case(assessment());case.scenario.season_verified=True
    manifest=dict(case=case.model_dump(mode='json'),case_version=1,snapshot_id='opaque-fixture',dependence_group='opaque-cohort',
        maximum_input_available_at='2020-01-01T00:00:00Z',provenance='verified_real',provenance_evidence='FICTIONAL test attestation',
        consent_evidence='FICTIONAL',privacy_approval_evidence='FICTIONAL',season_mapping_evidence='FICTIONAL')
    assert client.post('/api/expert-validation/cases',headers=admin,json=manifest).status_code==200
    url='/api/expert-validation/cases/'+case.case_id
    for identity in ('one','two'):
        assert client.post(url+'/assign',headers=admin,params=dict(case_version=1,reviewer_id=identity,rubric_version='fixture-v1')).status_code==200
    return client,case,manifest,url,path

def submit(client,case,url,identity,label,version=1):
    return client.post(url+'/reviews',headers={'Authorization':'Bearer '+identity},json=dict(case_version=version,
        case_digest=digest(case),rubric_version='fixture-v1',label=label,justification='Fictional test rationale',
        reviewed_at=datetime.now(timezone.utc).isoformat()))

def status(client,url):
    return client.get(url+'/status',headers={'Authorization':'Bearer admin'},params=dict(case_version=1,rubric_version='fixture-v1')).json()

def test_authorization_blinding_and_privacy(workflow):
    client,case,_,url,_=workflow
    assert submit(client,case,url,'farmer','High').status_code==403
    assert submit(client,case,url,'judge','High').status_code==403
    assert client.get(url,params=dict(case_version=1,rubric_version='fixture-v1')).status_code==403
    response=client.get(url,headers={'Authorization':'Bearer one'},params=dict(case_version=1,rubric_version='fixture-v1'))
    assert response.status_code==200
    assert 'reviews' not in response.json() and 'sensitive locality' not in response.text
    assert 'provenance_evidence' not in response.text and 'farmer_id' not in response.text
    assert submit(client,case,url,'one','Low').status_code==200
    response=client.get(url,headers={'Authorization':'Bearer two'},params=dict(case_version=1,rubric_version='fixture-v1'))
    assert 'Low' not in response.text

def test_conflicts_adjudication_and_immutability(workflow):
    client,case,_,url,path=workflow
    assert not status(client,url)['training_eligible']
    assert submit(client,case,url,'one','Low').status_code==200
    assert submit(client,case,url,'one','High').status_code==409
    assert submit(client,case,url,'two','High').status_code==200
    result=status(client,url)
    assert result['conflicting'] and result['pairwise_agreement']==0 and result['unresolved']
    packet=client.get(url+'/adjudication-packet',headers={'Authorization':'Bearer judge'},params=dict(case_version=1,rubric_version='fixture-v1'))
    assert packet.status_code==200 and len(packet.json()['reviews'])==2
    assert client.get(url+'/adjudication-packet',headers={'Authorization':'Bearer one'},params=dict(case_version=1,rubric_version='fixture-v1')).status_code==403
    decision=dict(case_version=1,rubric_version='fixture-v1',decision='Medium',justification='Fictional adjudication')
    assert client.post(url+'/adjudicate',headers={'Authorization':'Bearer one'},json=decision).status_code==403
    resolved=client.post(url+'/adjudicate',headers={'Authorization':'Bearer judge'},json=decision)
    assert resolved.status_code==200 and resolved.json()['training_eligible']
    assert client.post(url+'/adjudicate',headers={'Authorization':'Bearer judge'},json=decision).status_code==409
    with sqlite3.connect(path) as db:
        with pytest.raises(sqlite3.IntegrityError):db.execute('DELETE FROM reviews')
        assert 'agreement_before_adjudication' in db.execute('SELECT payload FROM adjudications').fetchone()[0]

def test_version_changes_and_missing_evidence(workflow):
    client,case,manifest,url,_=workflow
    admin={'Authorization':'Bearer admin'}
    assert submit(client,case,url,'one','Uncertain').status_code==200
    assert submit(client,case,url,'two','Uncertain').status_code==200
    decision=dict(case_version=1,rubric_version='fixture-v1',decision='Uncertain',justification='Fictional insufficient evidence')
    result=client.post(url+'/adjudicate',headers={'Authorization':'Bearer judge'},json=decision).json()
    assert not result['training_eligible'] and result['pairwise_agreement']==1
    assert client.post('/api/expert-validation/cases',headers=admin,json=dict(manifest,case_version=2,provenance='fictional')).status_code==422
    assert client.post('/api/expert-validation/cases',headers=admin,json=dict(manifest,case_version=2,consent_evidence=None)).status_code==422
    assert client.post('/api/expert-validation/cases',headers=admin,json=dict(manifest,case_version=2)).status_code==200
    assert submit(client,case,url,'one','High').status_code==409
    assert client.get(url+'/status',headers=admin,params=dict(case_version=2,rubric_version='fixture-v1')).json()['training_eligible'] is False

def test_unapproved_rubric_and_false_reviewer(workflow):
    client,_,_,url,_=workflow;admin={'Authorization':'Bearer admin'}
    assert client.post('/api/expert-validation/rubrics',headers=admin,json=dict(rubric_version='draft',rubric_text='draft')).status_code==200
    assert client.post(url+'/assign',headers=admin,params=dict(case_version=1,reviewer_id='one',rubric_version='draft')).status_code==409
    assert client.post('/api/expert-validation/reviewers',headers=admin,json=dict(reviewer_id='unverified',credential_evidence='unknown',
        agricultural_role='unknown',organization='unknown')).status_code==200
    assert client.post(url+'/assign',headers=admin,params=dict(case_version=1,reviewer_id='unverified',rubric_version='fixture-v1')).status_code==409
