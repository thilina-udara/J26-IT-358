"""Prospective contract tests with fictional forecasts/outcomes, never research accuracy."""
import json
import sqlite3
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.services import prospective
from app.services.cultivation_plans import PlanStore
from ml.prospective_evaluation import evaluate


def headers(token):
    return {'Authorization': 'Bearer ' + token}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    path = tmp_path / 'plans.sqlite3'
    clock = [datetime.now(timezone.utc) + timedelta(seconds=10)]
    monkeypatch.setattr(prospective, 'now', lambda: clock[0])
    artifact = dict(version='fictional-v1', sha256='a' * 64,
                    available_at='2020-01-01T00:00:00+00:00', evidence_reference='FICTIONAL SOFTWARE FIXTURE')
    def predictor(snapshot):
        # Mutating the callback input must not change the frozen snapshot.
        snapshot['known_concentration']['overlap_acres_including_own'] = 999
        return dict(status='experimental_forecast', category='Medium', model=artifact,
                    historical_reference=artifact, target_definition_version='fictional-target-v1')
    client = TestClient(create_app(path, {'owner': 'owner', 'peer': 'peer', 'south': 'south'},
                                  analysis_tokens=['analyst'], admin_tokens=['admin'], prospective_predictor=predictor))
    def plan(token='owner', **changes):
        value = dict(farmer_id=token, district='Matara', region='north', crop='Corn', land_size_acres=2,
                     planting_date='2099-01-01', expected_harvest_date='2099-04-01')
        value.update(changes)
        response = client.post('/api/cultivation-plans', headers=headers(token), json=value)
        assert response.status_code == 201, response.text
        return response.json()['plan']['plan_id']
    protocol = dict(protocol_id='fictional-protocol-v1', target_kind='independently_observed_realized_concentration',
                    horizon_days=1, definition_version='fictional-target-v1',
                    definition='FICTIONAL independently surveyed eventual concentration target',
                    independent_outcome_evidence='FICTIONAL external survey, blinded to prediction')
    response = client.post('/api/prospective/protocols', headers=headers('admin'), json=protocol)
    assert response.status_code == 201, response.text
    return client, path, clock, plan, protocol


def assessment(client, identifier, protocol=True):
    value = dict(plan_id=identifier)
    if protocol:
        value['protocol_id'] = 'fictional-protocol-v1'
    response = client.post('/api/prospective/assessments', headers=headers('owner'), json=value)
    assert response.status_code == 201, response.text
    return response.json()


def audit(client, identifier):
    response = client.get('/api/prospective/audit/assessments/' + identifier, headers=headers('analyst'))
    assert response.status_code == 200, response.text
    return response.json()


def outcome(identifier, stamp, category='Medium'):
    return dict(assessment_id=identifier, category=category, target_definition_version='fictional-target-v1',
                observed_at=stamp.isoformat(), evidence_reference='FICTIONAL independently observed survey',
                evidence_sha256='b' * 64, independently_observed=True, derived_from_current_snapshot=False)


def test_scope_privacy_ownership_and_future_exclusion(setup):
    client, path, clock, plan, _ = setup
    own = plan()
    peer = plan('peer', expected_harvest_date='2099-04-15')  # inclusive +14
    plan('south', district='Hambantota')
    plan('peer', expected_harvest_date='2099-04-16')  # available but not overlapping
    future = plan('south', crop='Corn', expected_harvest_date='2099-04-02')
    repository = PlanStore(path)
    with repository.connection() as db:
        row = db.execute('SELECT * FROM cultivation_plan_versions WHERE plan_id=?', (future,)).fetchone()
        payload = json.loads(row['payload'])
        future_stamp = (clock[0] + timedelta(days=1)).isoformat()
        payload['submitted_at'] = payload['updated_at'] = future_stamp
        db.execute('UPDATE cultivation_plan_versions SET recorded_at=?,payload=? WHERE plan_id=?',
                   (future_stamp, json.dumps(payload), future))
    public = assessment(client, own)
    frozen = audit(client, public['assessment_id'])
    assert frozen['known_concentration']['overlap_acres_including_own'] == 4
    assert frozen['known_concentration']['overlapping_peer_plan_ids'] == [peer]
    assert future not in frozen['available_peer_plan_ids']
    assert len(frozen['available_peer_plan_ids']) == 2
    assert all(v['plan']['district'] == 'Matara' for v in frozen['peer_versions'])
    assert 'farmer_id' not in json.dumps(frozen)
    assert 'peer_versions' not in public and peer not in json.dumps(public)
    assert public['experimental_forecast']['category'] is None
    assert client.get('/api/prospective/assessments/' + public['assessment_id'], headers=headers('peer')).status_code == 404
    assert client.get('/api/prospective/audit/assessments/' + public['assessment_id'], headers=headers('owner')).status_code == 403
    assert client.post('/api/prospective/assessments', json={'plan_id': own}).status_code == 401
    assert client.post('/api/prospective/assessments', headers=headers('peer'), json={'plan_id': own}).status_code == 404
    assert client.post('/api/prospective/assessments', headers=headers('owner'),
                       json={'plan_id': own, 'cutoff': clock[0].isoformat()}).status_code == 422


def test_future_updates_and_registrations_do_not_change_assessment(setup):
    client, _, clock, plan, _ = setup
    own = plan(); peer = plan('peer')
    public = assessment(client, own)
    frozen = audit(client, public['assessment_id'])
    clock[0] += timedelta(days=2)
    assert client.delete('/api/cultivation-plans/' + peer, headers=headers('peer')).status_code == 200
    plan('south')
    assert audit(client, public['assessment_id']) == frozen
    assert client.get('/api/prospective/assessments/' + public['assessment_id'], headers=headers('owner')).json() == public


def test_independent_outcomes_and_readonly_scoring(setup):
    client, path, clock, plan, protocol = setup
    own = plan()
    first = assessment(client, own)['assessment_id']
    second = assessment(client, own)['assessment_id']
    assessment(client, own, protocol=False)
    report = evaluate(path, clock[0] - timedelta(seconds=10))
    assert report['status'] == 'no_eligible_independent_outcomes'
    assert client.post('/api/prospective/outcomes', headers=headers('admin'), json=outcome(first, clock[0])).status_code == 422
    assert client.post('/api/prospective/outcomes', headers=headers('owner'), json=outcome(first, clock[0])).status_code == 403
    clock[0] += timedelta(days=2)
    for identifier, label in [(first, 'Medium'), (second, 'High')]:
        response = client.post('/api/prospective/outcomes', headers=headers('admin'), json=outcome(identifier, clock[0], label))
        assert response.status_code == 201, response.text
    assert client.post('/api/prospective/outcomes', headers=headers('admin'), json=outcome(first, clock[0])).status_code == 409
    invalid = dict(outcome(first, clock[0]), derived_from_current_snapshot=True)
    assert client.post('/api/prospective/outcomes', headers=headers('admin'), json=invalid).status_code == 422
    # Evaluate with a future observation clock requires the real current date to advance too.
    # Instead, use a safely past fictional clock for a second fixture below.
    assert client.post('/api/prospective/protocols', headers=headers('admin'),
                       json=dict(protocol, protocol_id='replay', target_kind='current_formula_replay')).status_code == 422


def test_complete_offline_metrics_and_sql_immutability(tmp_path, monkeypatch):
    client = TestClient(create_app(tmp_path / 'p.sqlite3', {'owner': 'owner'}, admin_tokens=['admin']))
    repository = PlanStore(tmp_path / 'p.sqlite3')
    # Fictional historical registration with an explicit timestamp, never ASC backdating.
    from app.schemas.cultivation_plan import PlanInput
    saved = repository.save(PlanInput(farmer_id='owner', district='Hambantota', region='north', crop='Corn',
        land_size_acres=2, planting_date='2099-01-01', expected_harvest_date='2099-04-01'), 'owner')['plan']
    real = datetime.now(timezone.utc)
    cutoff = real - timedelta(days=4)
    with repository.connection() as db:
        db.execute('DELETE FROM cultivation_plan_versions')
        saved = saved.model_copy(update={'submitted_at': cutoff-timedelta(days=1), 'updated_at': cutoff-timedelta(days=1)})
        repository.record_version(db, saved)
    monkeypatch.setattr(prospective, 'now', lambda: cutoff-timedelta(hours=1))
    from app.schemas.prospective import Protocol, AssessmentRequest, Outcome
    protocol = Protocol(protocol_id='fixture', target_kind='independently_observed_realized_concentration', horizon_days=1,
        definition_version='target', definition='FICTIONAL independent later outcome definition',
        independent_outcome_evidence='FICTIONAL external survey evidence')
    prospective.register_protocol(repository, protocol, 'fixture-admin')
    monkeypatch.setattr(prospective, 'now', lambda: cutoff)
    artifact = dict(version='fixture', sha256='a'*64, available_at=(cutoff-timedelta(days=1)).isoformat(), evidence_reference='fixture')
    predictor = lambda _: dict(status='experimental_forecast', category='Medium', model=artifact,
                               historical_reference=artifact, target_definition_version='target')
    result = prospective.assess(repository, 'owner', AssessmentRequest(plan_id=saved.plan_id, protocol_id='fixture'), predictor)
    monkeypatch.setattr(prospective, 'now', lambda: cutoff+timedelta(days=2))
    prospective.record_outcome(repository, Outcome(**dict(outcome(result['assessment_id'], cutoff+timedelta(days=2)),
                                                       target_definition_version='target')), 'fixture-admin')
    before = (tmp_path / 'p.sqlite3').read_bytes()
    report = evaluate(tmp_path / 'p.sqlite3')
    assert (tmp_path / 'p.sqlite3').read_bytes() == before
    assert report['counts']['scored'] == 1
    assert report['cohorts'][0]['accuracy'] == 1.0
    assert report['cohorts'][0]['per_class']['Medium']['recall'] == 1.0
    assert report['cohorts'][0]['district'] == 'Hambantota'
    assert saved.plan_id not in json.dumps(report)
    from ml.prospective_evaluation import main
    import sys
    output = tmp_path / 'evaluation.json'
    monkeypatch.setattr(sys, 'argv', ['prospective_evaluation', '--database', str(tmp_path / 'p.sqlite3'), '--output', str(output)])
    main()
    assert json.loads(output.read_text())['counts']['scored'] == 1
    with pytest.raises(FileExistsError):
        main()
    assert evaluate(tmp_path / 'p.sqlite3', cutoff+timedelta(hours=12))['status'] == 'no_eligible_independent_outcomes'
    for table in prospective.TABLES:
        with repository.connection() as db:
            for sql in (f"UPDATE {table} SET digest='changed'", f'DELETE FROM {table}',
                        f'INSERT OR REPLACE INTO {table} SELECT * FROM {table}'):
                with pytest.raises(sqlite3.IntegrityError, match='Immutable'):
                    db.execute(sql)
    with pytest.raises(ValueError, match='timezone-aware'):
        evaluate(tmp_path / 'p.sqlite3', datetime.now())


def test_future_artifact_and_no_forecast_by_default(setup):
    client, path, clock, plan, _ = setup
    own = plan()
    artifact = dict(version='future', sha256='a'*64, available_at=(clock[0]+timedelta(days=1)).isoformat(), evidence_reference='fixture')
    future_provider = lambda _: dict(status='experimental_forecast', category='High', model=artifact,
                                    historical_reference=artifact, target_definition_version='fictional-target-v1')
    bad = TestClient(create_app(path, {'owner': 'owner'}, prospective_predictor=future_provider))
    assert bad.post('/api/prospective/assessments', headers=headers('owner'),
                    json={'plan_id': own, 'protocol_id': 'fictional-protocol-v1'}).status_code == 422
    plain = TestClient(create_app(path, {'owner': 'owner'}))
    result = assessment(plain, own)
    assert result['experimental_forecast']['status'] == 'unavailable'


def test_invalid_timestamp_evidence_fails_closed(setup):
    client, path, clock, plan, _ = setup
    own = plan()
    artifact = dict(version='naive', sha256='a'*64, available_at='2020-01-01T00:00:00', evidence_reference='fixture')
    provider = lambda _: dict(status='experimental_forecast', category='Medium', model=artifact,
                              historical_reference=artifact, target_definition_version='fictional-target-v1')
    bad = TestClient(create_app(path, {'owner': 'owner'}, prospective_predictor=provider))
    request = {'plan_id': own, 'protocol_id': 'fictional-protocol-v1'}
    assert bad.post('/api/prospective/assessments', headers=headers('owner'), json=request).status_code == 503
    with PlanStore(path).connection() as db:
        assert db.execute('SELECT COUNT(*) FROM prospective_assessments').fetchone()[0] == 0
        db.execute('UPDATE cultivation_plan_versions SET recorded_at=?', ('2020-01-01T00:00:00',))
    assert client.post('/api/prospective/assessments', headers=headers('owner'), json=request).status_code == 503


def test_integrity_check_detects_privileged_tampering(setup):
    client, path, _, plan, _ = setup
    identifier = assessment(client, plan())['assessment_id']
    # Only a DB administrator can bypass the append-only guards. Hash verification
    # detects payload-only tampering; it is not protection against recomputed hashes.
    with PlanStore(path).connection() as db:
        db.execute('DROP TRIGGER immutable_prospective_assessments_UPDATE')
        db.execute("UPDATE prospective_assessments SET payload='{}'")
    assert client.get('/api/prospective/assessments/' + identifier, headers=headers('owner')).status_code == 503
    with pytest.raises(ValueError, match='Audit integrity'):
        evaluate(path)
