"""Production fixtures stay in memory and pytest temp databases only."""
import copy
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.services.production_forecast import (forecast, linear_model, linear_prediction, choose,
    options, reference_range, report, to_kg)


def rows(start=2001, end=2025):
    return [dict(district_name='Hambantota', crop_name='Bandakka', season='Maha', year=str(year),
                 production_metric_tons=str(100 + (year - 2000) * 10)) for year in range(start, end + 1)]


def run(data):
    return forecast(data, 'Hambantota', 'Bandakka', 'Maha')


def test_explicit_unit_conversion_and_no_area_conversion():
    assert to_kg('2.5') == 2500
    assert to_kg('2.5', 'kg') == 2.5
    assert to_kg(0) == 0
    for unit in ['hectares', 'acres', 'tons', 'kg/ha']:
        with pytest.raises(ValueError):
            to_kg(10, unit)
    area_only = [dict(r, cultivated_extent_hectares=10) for r in rows()]
    for r in area_only:
        del r['production_metric_tons']
    assert run(area_only)['expected_production_kg'] is None


def test_ols_forecast_and_naive_compared_on_same_origins():
    result = run(rows())
    assert result['status'] == 'available' and result['model'] == 'linear_trend'
    assert result['expected_production_kg'] == pytest.approx(360000)
    assert result['candidate_forecasts_kg']['linear_trend'] == pytest.approx(360000)
    assert result['candidate_forecasts_kg']['naive'] == pytest.approx(350000)
    assert result['evaluation']['candidate_mae_kg']['linear_trend'] == pytest.approx(0)
    assert result['evaluation']['candidate_mae_kg']['naive'] == pytest.approx(10000)
    assert result['evaluation']['selection_policy_mae_kg'] == pytest.approx(0)
    assert result['reference_range_kg']['lower'] == pytest.approx(360000)
    assert result['reference_range_kg']['upper'] == pytest.approx(360000)
    assert result['training_years'] == list(range(2001, 2026))
    assert result['evaluation']['policy_years'] == list(range(2011, 2026))


def test_naive_tie_and_zero_production_are_valid():
    data = rows()
    for row in data:
        row['production_metric_tons'] = '0'
    result = run(data)
    assert result['model'] == 'naive' and result['expected_production_kg'] == 0
    assert result['reference_range_kg']['lower'] == result['reference_range_kg']['upper'] == 0
    assert result['reference_range_kg']['nominal_coverage'] is None


def test_production_is_aggregated_once_per_season_not_total_plus_seasons():
    data = rows(); expected = run(data)
    mixed = data + [dict(r, season='Total', production_metric_tons='999999') for r in data]
    mixed += [dict(r, season='Yala', production_metric_tons='555555') for r in data]
    mixed += [dict(r, district_name='Matara') for r in data] + [data[0].copy()]
    result = run(mixed)
    for key in ['expected_production_kg', 'reference_range_kg', 'evaluation', 'history']:
        assert result[key] == expected[key]
    assert result['quality']['duplicate_rows_ignored'] == 1
    assert run(data + [dict(data[0], production_metric_tons='1')])['status'] == 'Insufficient Data'
    assert forecast(data, 'Hambantota', 'Bandakka', 'Total')['expected_production_kg'] is None


def test_2026_and_future_values_do_not_enter_training_or_model_selection():
    data = rows(); original = copy.deepcopy(data)
    future = [dict(data[-1], year='2026', production_metric_tons='nan', production_unit='hectares'),
              dict(data[-1], year='2027', production_metric_tons='1000000000')]
    assert run(data) == run(data + future)
    assert options(data) == options(data + future)
    assert data == original


def test_each_historical_fit_and_method_selection_use_only_earlier_data():
    data = rows()
    for i, row in enumerate(data):
        row['production_metric_tons'] = str(100 + i * 4 + [5, -10, 15, 0][i % 4])
    result = run(data)
    records = result['candidate_backtests']
    for record in records:
        year = record['year']
        prior = [{'year': int(r['year']), 'production_kg': to_kg(r['production_metric_tons'])}
                 for r in data if int(r['year']) < year]
        assert record['trained_through'] == year - 1
        assert record['forecasts_kg']['linear_trend'] == pytest.approx(linear_prediction(linear_model(prior), year))
        assert record['forecasts_kg']['naive'] == prior[-1]['production_kg']
    for record in result['policy_backtests']:
        earlier_errors = [r for r in records if r['year'] < record['year']]
        assert max(record['selection_years']) < record['year']
        assert record['model'] == choose(earlier_errors)
    modified = copy.deepcopy(data)
    modified[-1]['production_metric_tons'] = '1000000'
    second = run(modified)
    assert result['candidate_backtests'][-1]['forecasts_kg'] == second['candidate_backtests'][-1]['forecasts_kg']
    assert result['policy_backtests'][-1]['forecast_kg'] == second['policy_backtests'][-1]['forecast_kg']
    assert result['policy_backtests'][-1]['model'] == second['policy_backtests'][-1]['model']
    assert result['policy_backtests'][:-1] == second['policy_backtests'][:-1]


def test_empirical_signed_error_reference_range_and_zero_floor():
    reference = reference_range(100, [-10, 0, 10])
    assert reference['lower'] == pytest.approx(92)
    assert reference['upper'] == pytest.approx(108)
    assert reference_range(2, [-10, 0, 10])['lower'] == 0
    assert reference_range(0, [-100, -50, -10])['upper'] == 0


@pytest.mark.parametrize('value', ['', None, '-1', 'nan', 'inf', '1e308'])
def test_missing_negative_or_nonfinite_production_never_creates_forecast(value):
    data = rows(); data[10]['production_metric_tons'] = value
    result = run(data)
    assert result['status'] == 'Insufficient Data'
    assert result['expected_production_kg'] is None and result['reference_range_kg'] is None
    assert result['quality']['invalid_years'] == [2011]
    json.dumps(result, allow_nan=False)


def test_inconsistent_source_units_rejected():
    data = rows(); data[10]['production_unit'] = 'kg'
    assert run(data)['expected_production_kg'] is None


def test_missing_year_is_not_zero_and_only_one_year_errors_are_used():
    data = [r for r in rows() if r['year'] != '2009']
    result = run(data)
    assert result['status'] == 'available'
    assert result['quality']['missing_years'] == [2009]
    assert 2009 not in result['training_years']
    assert 2010 not in [r['year'] for r in result['candidate_backtests']]
    assert run([r for r in data if r['year'] != '2025'])['status'] == 'Insufficient Data'


def test_insufficient_history_does_not_display_point_or_range():
    result = run(rows(2016, 2025))
    assert result['expected_production_kg'] is None and result['reference_range_kg'] is None
    assert 'eight' in result['reason']


def test_fitted_negative_prediction_is_constrained_without_modifying_observations():
    data = rows()
    for r in data:
        r['production_metric_tons'] = str(49 - 2 * (int(r['year']) - 2001))
    result = run(data)
    assert result['status'] == 'available' and result['model'] == 'linear_trend'
    assert result['expected_production_kg'] == 0
    assert result['quality']['forecast_floored_at_zero']
    assert result['history'][-1]['production_kg'] == 1000


def test_real_series_are_available_with_no_live_population_comparison():
    for s in options():
        result = report(s['district'], s['crop'], s['season'])
        assert result['status'] == 'available', (s, result['reason'])
        assert result['forecast_year'] == 2026 and max(result['training_years']) == 2025
        assert result['expected_production_kg'] >= 0
        assert 0 <= result['reference_range_kg']['lower'] <= result['reference_range_kg']['upper']
        assert result['planned_comparison']['cumulative_planned_kg'] is None
        assert result['source']['quantity_column'] == 'production_metric_tons'
        assert not result['source']['provenance_verified']
        json.dumps(result, allow_nan=False)


def test_admin_production_api_authorization_and_validation(tmp_path):
    from app.main import create_app
    from app.migrations import migrate
    from app.services.admin_auth import hash_password, now_seconds
    path = tmp_path / 'admin.sqlite3'; migrate(path)
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO admin_accounts VALUES(?,?,?,?,?,?,0)',
            ('production-officer', 'production.test', hash_password('TestingOnly@2026!'), 'Test officer', 'officer', now_seconds()))
    client = TestClient(create_app(str(path)))
    endpoint = '/api/admin/analytics/production-forecast'
    assert client.get(endpoint).status_code == 401
    assert client.get(endpoint + '/options').status_code == 401
    login = client.post('/api/admin/auth/login', json={'login_identifier': 'production.test', 'password': 'TestingOnly@2026!'})
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    assert len(client.get(endpoint + '/options', headers=headers).json()['series']) == 24
    response = client.get(endpoint + '?forecast_year=2026', headers=headers)
    assert response.status_code == 200 and response.json()['expected_production_kg'] >= 0
    assert client.get(endpoint + '?forecast_year=2027', headers=headers).status_code == 422
    assert client.get(endpoint + '?season=Total', headers=headers).status_code == 422
    assert client.get(endpoint + '?crop=Rice', headers=headers).status_code == 422
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM cultivation_plans').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM farmer_accounts').fetchone()[0] == 0
