"""Synthetic fixtures stay in memory or pytest temp databases, never live plans."""
import copy
import json
import math
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.services.historical_trend import analyse, classify, fit, options, predict, quantile, read_rows, report


def rows(end=2025):
    deviations = [0, 8, -6, 12, -4, 3, -9]
    return [dict(district_name='Hambantota', crop_name='Bandakka', season='Maha', year=str(y),
        cultivated_extent_hectares=str(100 + 4 * (y - 2000) + deviations[(y - 2000) % 7])) for y in range(2001, end + 1)]


def run(data, year=2025):
    return analyse(data, 'Hambantota', 'Bandakka', 'Maha', year)


def test_linear_trend_uses_real_calendar_years():
    points = [{'year': year, 'hectares': 100 + 10 * (year - 2000)} for year in [2001, 2002, 2004, 2008, 2010]]
    model = fit(points)
    assert model['slope_hectares_per_year'] == pytest.approx(10)
    assert predict(model, 2011) == pytest.approx(210)


def test_rolling_origin_and_heldout_future_leakage():
    original = rows(2028)
    first = run(original)
    modified = copy.deepcopy(original)
    for row in modified:
        if int(row['year']) >= 2025:
            row['cultivated_extent_hectares'] = '100000'
    second = run(modified)
    assert first['status'] == 'available'
    for key in ['trend', 'baseline_hectares', 'thresholds', 'calibration', 'training_years']:
        assert first[key] == second[key]
    assert first['observed_hectares'] != second['observed_hectares']
    assert max(first['training_years']) == 2024
    assert len(first['calibration']) == 19
    for item in first['calibration']:
        assert item['trained_through'] == item['year'] - 1 < 2025
        previous = [{'year': int(r['year']), 'hectares': float(r['cultivated_extent_hectares'])}
                    for r in original if int(r['year']) < item['year']]
        assert item['baseline_hectares'] == pytest.approx(predict(fit(previous), item['year']))


def test_future_missing_values_and_units_do_not_influence_evaluation():
    original = rows(2026)
    changed = copy.deepcopy(original)
    changed[-1].update(cultivated_extent_hectares='nan', extent_unit='acres')
    assert run(original) == run(changed)


def test_empirical_terciles_and_interpolation_resist_single_extreme():
    assert quantile(list(range(9)), 1 / 3) == pytest.approx(8 / 3)
    assert quantile(list(range(9)), 2 / 3) == pytest.approx(16 / 3)
    assert quantile(list(range(8)) + [1e100], 2 / 3) == pytest.approx(16 / 3)
    result = run(rows())
    errors = [c['deviation_percent'] for c in result['calibration']]
    assert result['thresholds']['lower_percent'] == quantile(errors, 1 / 3)
    assert result['thresholds']['upper_percent'] == quantile(errors, 2 / 3)
    assert result['thresholds']['lower_hectares'] == pytest.approx(result['baseline_hectares'] * (1 + quantile(errors, 1 / 3) / 100))


@pytest.mark.parametrize('value,expected', [(-11, 'Low'), (-10, 'Medium'), (0, 'Medium'), (10, 'Medium'), (11, 'High')])
def test_classification_boundaries(value, expected):
    assert classify(value, -10, 10) == expected


@pytest.mark.parametrize('value', ['', None, 'nan', 'inf', '-1'])
def test_missing_invalid_measurements_never_create_category(value):
    data = rows(); data[10]['cultivated_extent_hectares'] = value
    result = run(data)
    assert result['status'] == 'Insufficient Data' and result['category'] is None
    assert result['quality']['invalid_years'] == [2011]


def test_zero_baseline_and_tied_error_distribution():
    data = rows()
    for row in data:
        row['cultivated_extent_hectares'] = '0'
    assert run(data)['category'] is None
    assert 'zero or negative' in run(data)['reason']
    for row in data:
        row['cultivated_extent_hectares'] = '100'
    assert run(data)['category'] is None
    assert 'tied terciles' in run(data)['reason']


def test_zero_observation_is_valid_and_not_a_missing_baseline():
    data = rows(); data[-1]['cultivated_extent_hectares'] = '0'
    result = run(data)
    assert result['status'] == 'available' and result['deviation_percent'] == -100


def test_units_must_be_hectares():
    data = rows(); data[5]['extent_unit'] = 'acres'
    assert run(data)['category'] is None
    assert 'inconsistent units' in run(data)['reason']


def test_insufficient_calibration_and_heldout_missing():
    result = run(rows(2010), 2010)
    assert result['baseline_hectares'] is not None
    assert result['category'] is None and 'eight' in result['reason']
    assert run(rows(2024), 2025)['category'] is None


def test_no_double_counting_annual_totals_duplicates_or_other_population():
    data = rows(); expected = run(data)
    additions = [dict(r, season='Total') for r in data] + [dict(r, district_name='Matara') for r in data]
    result = run(data + additions + [data[0].copy()])
    for key in ['baseline_hectares', 'observed_hectares', 'thresholds', 'category']:
        assert expected[key] == result[key]
    assert result['quality']['duplicate_rows_ignored'] == 1
    conflict = dict(data[0], cultivated_extent_hectares='999')
    assert run(data + [conflict])['category'] is None


def test_missing_years_are_not_interpolated_and_horizon_is_consistent():
    result = run([r for r in rows() if r['year'] != '2009'])
    assert result['quality']['missing_years'] == [2009]
    assert 2009 not in result['training_years']
    assert 2010 not in [c['year'] for c in result['calibration']]
    result = run([r for r in rows() if r['year'] != '2024'])
    assert result['category'] is None and 'preceding year' in result['reason']


def test_extreme_arithmetic_is_safe_json_and_never_infinite():
    data = rows()
    for r in data:
        r['cultivated_extent_hectares'] = '1e308'
    result = run(data)
    assert result['category'] is None
    json.dumps(result, allow_nan=False)


def test_real_dataset_backtests_all_24_groups_without_mutating_source():
    data = read_rows()
    assert len(data) == 878 and len(options(data)) == 24
    for group in options(data):
        result = report(group['district'], group['crop'], group['season'])
        assert result['status'] == 'available', (group, result['reason'])
        assert result['evaluation_year'] == 2025
        assert result['source']['seasonal_rows'] == 580
        assert result['source']['annual_total_rows_excluded'] == 298
        assert max(result['training_years']) == 2024
        json.dumps(result, allow_nan=False)


def test_admin_api_requires_auth_and_validates_selection(tmp_path):
    from app.main import create_app
    from app.migrations import migrate
    from app.services.admin_auth import hash_password, now_seconds
    path = tmp_path / 'admin.sqlite3'; migrate(path)
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO admin_accounts VALUES(?,?,?,?,?,?,0)',
                   ('officer-test', 'officer.test', hash_password('TestingOnly@2026!'), 'Test officer', 'officer', now_seconds()))
    client = TestClient(create_app(str(path)))
    endpoint = '/api/admin/analytics/historical-trend'
    assert client.get(endpoint).status_code == 401
    assert client.get(endpoint + '/options').status_code == 401
    response = client.post('/api/admin/auth/login', json={'login_identifier': 'officer.test', 'password': 'TestingOnly@2026!'})
    assert response.status_code == 200
    headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
    assert client.get(endpoint + '/options', headers=headers).json()['series']
    result = client.get(endpoint, headers=headers)
    assert result.status_code == 200 and result.json()['status'] == 'available'
    assert client.get(endpoint + '?crop=Potato', headers=headers).status_code == 422
    assert client.get(endpoint + '?season=Total', headers=headers).status_code == 422
    early = client.get(endpoint + '?evaluation_year=2005', headers=headers)
    assert early.status_code == 200 and early.json()['category'] is None
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM cultivation_plans').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM farmer_accounts').fetchone()[0] == 0
