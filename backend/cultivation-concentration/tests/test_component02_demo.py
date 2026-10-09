"""SIMULATED demo only: temporary SQLite, fictional references and mock evidence.

No approvals, labels or agricultural quantities in this test are real evidence.
Run with pytest -s to print the privacy-filtered demonstration transcript.
"""
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.cultivation_plans import PlanStore
from app.services.plan_clustering import snapshot
from app.services import production_reference, production_risk
from app.schemas.production_risk import ProductionRegistry
from ml.preprocessing.build_production_reference import build, save
from tests.test_alternatives import evidence
from tests.test_production_reference import row


def test_simulated_end_to_end_demo(tmp_path, monkeypatch):
    crops = ('Corn', 'Brinjal', 'Pumpkin', 'Bandakka')
    historical = []
    for crop in crops:
        for i, value in enumerate((100, 200, 400) if crop == 'Corn' else (1000, 2000, 4000)):
            historical.append(row(f'FICTIONAL-{crop}-{i}', Crop=crop,
                Expected_Harvest_Date=f'{4+i}/1/2020', Expected_Production_kg=str(value)))
    bundle = build(historical)
    bundle['provenance']['source'] = 'FICTIONAL SOFTWARE DEMO; NOT ASC DATA'
    reference_path, _ = save(bundle, tmp_path/'fictional-references')
    # Scope the path substitution and simulation annotations to this one test.
    reference_evaluate = production_reference.evaluate
    production_evaluate = production_risk.evaluate
    def reference_demo(*args, **kwargs):
        result = reference_evaluate(*args, **kwargs, path=reference_path)
        return dict(result, simulation=True, data_origin='fictional_test_fixture',
                    explanation='SIMULATED: ' + result['explanation'])
    def production_demo(*args, **kwargs):
        result = production_evaluate(*args, **kwargs)
        return dict(result, simulation=True, data_origin='fictional_test_fixture',
                    explanation='SIMULATED: ' + result['explanation'])
    monkeypatch.setattr(production_reference, 'evaluate', reference_demo)
    monkeypatch.setattr(production_risk, 'evaluate', production_demo)
    path = tmp_path/'fictional-plans.sqlite3'
    tokens = {f'demo-{i}':f'fictional-farmer-{i}' for i in range(12)}
    headers = {'Authorization':'Bearer demo-0'}
    body = dict(crop='Corn', district='Matara', region='north', land_size_acres=5,
                planting_date='2030-01-01', expected_harvest_date='2030-04-01', season='Maha')
    client = TestClient(create_app(path, tokens, ['demo-analyst']))
    assert client.post('/api/farmer-workflow/plans', json=body).status_code == 401
    identifier = None
    for i in range(12):
        response = client.post('/api/farmer-workflow/plans',
            headers={'Authorization':f'Bearer demo-{i}'},
            json=dict(body, crop=crops[i//3], land_size_acres=5 if i < 3 else 2))
        assert response.status_code == 201, response.text
        if i == 0:
            identifier = response.json()['plan']['plan_id']
            insufficient = response.json()['workflow']['experimental_reference_assessment']
            assert insufficient['status'] == 'insufficient_evidence'
    cutoff = datetime.now(timezone.utc)
    plans = snapshot(PlanStore(path), cutoff)
    owned = next(p for p in plans if p['plan_id'] == identifier)
    assignments = [dict(plan_id=p['plan_id'], updated_at=p['updated_at'], season='Maha', verified=True,
        reference='SIMULATED season evidence, not an agricultural approval', available_at='2021-01-01T00:00:00Z') for p in plans]
    entries = []
    for crop in crops:
        values = [w['expected_kg'] for w in bundle['windows'] if w['scope'] == production_reference.SCOPE
                  and w['half_window_days'] == 14 and w['crop'] == crop]
        entries.append(dict(crop=crop, district='Matara', season='Maha', verified=True,
            reference='SIMULATED attestation ' + reference_path.stem,
            reference_definition='SIMULATED ' + production_reference.SCOPE,
            available_at='2021-01-01T00:00:00Z', verified_at='2021-01-01T00:00:00Z',
            valid_from='2029-01-01', valid_to='2031-12-31', historical_observation_end='2020-06-01',
            yield_kg_per_acre=100, reference_window_production_kg=values,
            applicable_without_variety_or_product=True, comparable_coverage_verified=True,
            quantile_method_approved_for_experiment=True))
    registry = ProductionRegistry(evidence=entries, season_assignments=assignments)
    # Internal test assertion; collective values are not printed or disclosed via farmer API.
    internal = reference_demo(plans + [owned], owned, 'Maha', cutoff, registry)
    assert internal['experimental_risk_level'] == 'High'
    assert internal['overlapping_plan_count'] == 3 and internal['overlapping_acres'] == 15
    assert internal['current_expected_production_kg'] == 1500
    mock_suitability = evidence()
    base = mock_suitability['suitability'][0]
    mock_suitability['suitability'] = [dict(base, crop=crop, evidence_id='SIMULATED-'+crop,
        source_reference='SIMULATED software fixture, not verified crop suitability') for crop in crops[1:]]
    client = TestClient(create_app(path, tokens, ['demo-analyst'],
        production_evidence=registry.model_dump(), alternative_evidence=mock_suitability))
    response = client.post('/api/farmer-workflow/analyze', headers=headers,
        json=dict(plan_id=identifier, season='Maha', as_of=cutoff.isoformat()))
    assert response.status_code == 200, response.text
    workflow = response.json()
    experimental = workflow['experimental_reference_assessment']
    assert experimental['simulation'] and experimental['experimental_risk_level'] == 'High'
    assert experimental['validation_status'] == 'unvalidated'
    assert experimental['current_expected_production_kg'] is None
    assert len(workflow['experimental_alternatives']) == 3
    assert all(c['assessment']['simulation'] and c['assessment']['experimental_risk_level'] == 'Low'
               for c in workflow['experimental_alternatives'])
    assert workflow['recommendations']['alternatives'] == []
    assert workflow['historical_prediction']['status'] == 'insufficient_evidence'
    assert workflow['clustering']['algorithms'] == ['K-Means', 'DBSCAN']
    assert all(p['farmer_id'] not in json.dumps(workflow) for p in plans)
    assert client.post('/api/farmer-workflow/analyze', headers={'Authorization':'Bearer demo-1'},
        json=dict(plan_id=identifier, season='Maha')).status_code == 404
    clusters = client.get('/api/cultivation-analysis/clusters', headers={'Authorization':'Bearer demo-analyst'},
        params=dict(district='Matara', as_of=cutoff.isoformat()))
    assert clusters.status_code == 200
    assert 'kmeans' in clusters.json() and 'dbscan' in clusters.json()
    assert client.get('/api/cultivation-analysis/clusters', headers=headers,
        params=dict(district='Matara')).status_code == 403
    selection = dict(plan_id=identifier, final_crop='Corn', district='Matara', region='north',
        land_size_acres=5, planting_date='2030-01-01', season='Maha', save=True)
    # Simulated High is not permission to select an unapproved production alternative.
    assert client.post('/api/farmer-workflow/select', headers=headers,
        json=dict(selection, final_crop='Brinjal')).status_code == 409
    for _ in range(2):
        saved = client.post('/api/farmer-workflow/select', headers=headers, json=selection)
        assert saved.status_code == 200, saved.text
        assert saved.json()['personalized_plan']['status'] == 'partial_plan'
        assert saved.json()['personalized_plan']['activities'] == []
    retrieved = client.get('/api/farmer-workflow/plans/'+identifier, headers=headers).json()
    assert len(retrieved['personalized_plan']['revisions']) == 2
    assert not retrieved['personalized_plan']['stale']
    assert len(snapshot(PlanStore(path), datetime.now(timezone.utc))) == 12
    print(json.dumps(dict(demo_status='SIMULATED ONLY; NOT AGRICULTURAL EVIDENCE',
        insufficient_evidence_example=insufficient, experimental_reference_assessment=experimental,
        simulated_candidate_comparisons=workflow['experimental_alternatives'],
        production_recommendations=workflow['recommendations'], clustering=workflow['clustering'],
        analyst_only_simulated_cluster_description=dict(simulation=True, data=clusters.json()),
        personalized_plan_status=saved.json()['personalized_plan']['status'],
        alternative_selection_status='blocked_by_unchanged_production_gate',
        persistence_check='12 active plans; two own personalized revisions; no duplicate acreage'), indent=2))
