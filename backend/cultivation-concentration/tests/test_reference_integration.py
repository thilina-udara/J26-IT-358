"""Fictional evidence exercises software; it is not agricultural validation."""
import pytest
from app.schemas.production_risk import ProductionRegistry
from app.services.production_reference import evaluate, farmer_response, load_reference, SCOPE
from ml.preprocessing.build_production_reference import build, save
from tests.test_production_reference import row
from tests.test_production_risk import fixture


def setup(tmp_path):
    path, _ = save(build([row('a', Expected_Production_kg='100'),
        row('b', Expected_Harvest_Date='5/1/2020', Expected_Production_kg='200'),
        row('c', Expected_Harvest_Date='6/1/2020', Expected_Production_kg='400')]), tmp_path)
    plans, entry, assignments, cutoff = fixture()
    entry.update(reference='FICTIONAL attestation ' + path.stem, reference_definition=SCOPE,
                 available_at='2021-01-01T00:00:00Z', verified_at='2021-01-01T00:00:00Z',
                 historical_observation_end='2020-06-01', reference_window_production_kg=[100, 200, 400])
    return path, plans, entry, assignments, cutoff


def test_classification_once_and_privacy(tmp_path):
    path, plans, entry, assignments, cutoff = setup(tmp_path)
    registry = ProductionRegistry(evidence=[entry], season_assignments=assignments)
    result = evaluate(plans + [plans[0]], plans[0], 'Maha', cutoff, registry, path)
    assert result['experimental_risk_level'] == 'High'
    assert result['validation_status'] == 'unvalidated'
    assert result['current_expected_production_kg'] == 600
    assert result['overlapping_plan_count'] == 3 and result['overlapping_acres'] == 6
    assert result['historical_reference_median_kg'] == 200 and result['reference_sample_size'] == 3
    protected = farmer_response(result)
    assert protected['current_expected_production_kg'] is None
    assert protected['historical_p33_kg'] is None
    assert 'farmer_id' not in str(protected) and 'plan_id' not in str(protected)


@pytest.mark.parametrize('change', [{'district':'Hambantota'}, {'crop':'Brinjal'}])
def test_district_crop_isolation(tmp_path, change):
    path, plans, entry, assignments, cutoff = setup(tmp_path)
    plans.append(dict(plans[0], plan_id='outsider', farmer_id='outsider', land_size_acres=999, **change))
    result = evaluate(plans, plans[0], 'Maha', cutoff, ProductionRegistry(evidence=[entry], season_assignments=assignments), path)
    assert result['current_expected_production_kg'] == 600
    assert evaluate(plans, dict(plans[0], **change), 'Maha', cutoff, ProductionRegistry(), path)['experimental_risk_level'] is None


def test_season_sparse_cutoff_and_verification(tmp_path):
    path, plans, entry, assignments, cutoff = setup(tmp_path)
    for season, evidence in [('Yala', entry), ('Maha', dict(entry, verified=False)),
                             ('Maha', dict(entry, available_at='2027-01-01T00:00:00Z'))]:
        assert evaluate(plans, plans[0], season, cutoff, ProductionRegistry(evidence=[evidence], season_assignments=assignments), path)['experimental_risk_level'] is None
    plans[1]['updated_at'] = '2027-01-01T00:00:00Z'
    assert evaluate(plans, plans[0], 'Maha', cutoff, ProductionRegistry(evidence=[entry], season_assignments=assignments), path)['experimental_risk_level'] is None
    sparse, _ = save(build([row('only')]), tmp_path)
    assert evaluate(plans, plans[0], 'Maha', cutoff, ProductionRegistry(), sparse)['experimental_risk_level'] is None


def test_window_and_companion_integrity(tmp_path):
    path, plans, entry, assignments, cutoff = setup(tmp_path)
    bundle = load_reference(path)
    for window in bundle['windows']:
        if window['half_window_days'] == 14:
            window['window_start'] = window['harvest_anchor']
    invalid, _ = save(bundle, tmp_path)
    assert evaluate(plans, plans[0], 'Maha', cutoff, ProductionRegistry(), invalid)['experimental_risk_level'] is None
    companion = path.with_name(path.stem + '_distributions.csv')
    companion.write_text('invalid', encoding='utf-8')
    with pytest.raises(ValueError): load_reference(path)


def test_real_artifact_does_not_grant_verification():
    plans, _, _, cutoff = fixture()
    result = evaluate(plans, plans[0], 'Maha', cutoff, ProductionRegistry())
    assert result['reference_version'] == 'district_expected_production_reference_v1'
    assert result['experimental_risk_level'] is None and result['status'] == 'insufficient_evidence'


def test_workflow_keeps_production_gates(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    client = TestClient(create_app(tmp_path/'workflow.sqlite3', {'owner':'owner'}))
    response = client.post('/api/farmer-workflow/plans', headers={'Authorization':'Bearer owner'},
        json=dict(crop='Corn', district='Matara', land_size_acres=2, planting_date='2030-01-01',
                  expected_harvest_date='2030-04-01', season='Maha'))
    assert response.status_code == 201
    workflow = response.json()['workflow']
    assert workflow['experimental_reference_assessment']['status'] == 'insufficient_evidence'
    assert workflow['experimental_reference_assessment']['validation_status'] == 'unvalidated'
    assert workflow['recommendations']['alternatives'] == []
    assert workflow['historical_prediction']['risk_level'] is None


@pytest.mark.parametrize('harvest,expected', [('2030-03-18', True), ('2030-04-15', True), ('2030-04-16', False)])
def test_inclusive_harvest_boundaries(tmp_path, harvest, expected):
    path, plans, entry, assignments, cutoff = setup(tmp_path)
    plans[2]['expected_harvest_date'] = harvest
    result = evaluate(plans, plans[0], 'Maha', cutoff, ProductionRegistry(evidence=[entry], season_assignments=assignments), path)
    assert (result['experimental_risk_level'] is not None) == expected
