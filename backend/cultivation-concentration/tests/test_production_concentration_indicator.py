import copy
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.services.production_concentration_indicator import (
    _calibration, _category, _reference, indicator, report
)


def rows(start=2001, end=2025):
    return [
        dict(district_name="Hambantota", crop_name="Bandakka", season="Maha",
             year=str(year), production_metric_tons=str(100 + (year - 2000) * 10))
        for year in range(start, end + 1)
    ]


def test_reference_uses_observed_2010_to_2024_median():
    points = [{"year": year, "production_kg": year * 1000} for year in range(2001, 2026)]
    reference, years = _reference(points, 2026)
    assert reference == pytest.approx(2017 * 1000)
    assert years == list(range(2010, 2025))


@pytest.mark.parametrize("value, expected", [(-11, "Low"), (-10, "Medium"), (0, "Medium"), (10, "Medium"), (11, "High")])
def test_category_boundaries(value, expected):
    assert _category(value, -10, 10) == expected


def test_calibration_has_reference_and_no_future_leakage():
    data = rows()
    result = indicator(data, "Hambantota", "Bandakka", "Maha")
    changed = copy.deepcopy(data)
    changed[-1]["production_metric_tons"] = "999999"
    assert result["status"] == "available"
    assert result["calibration_sample_count"] == 15
    assert result["forecast_2026_kg"] != indicator(changed, "Hambantota", "Bandakka", "Maha")["forecast_2026_kg"]


def test_insufficient_reference_and_invalid_values_do_not_force_category():
    assert indicator(rows(2020, 2025), "Hambantota", "Bandakka", "Maha")["status"] == "Insufficient Data"
    invalid = rows()
    invalid[10]["production_metric_tons"] = "nan"
    result = indicator(invalid, "Hambantota", "Bandakka", "Maha")
    assert result["status"] == "Insufficient Data"
    json.dumps(result, allow_nan=False)


def test_real_bandakka_hambantota_maha_report():
    result = report("Hambantota", "Bandakka", "Maha")
    assert result["status"] == "available"
    assert result["forecast_2026_kg"] == pytest.approx(3345400)
    assert result["historical_reference_kg"] == pytest.approx(3217000)
    assert result["deviation_percent"] == pytest.approx(3.9912962387)
    assert result["lower_threshold_percent"] == pytest.approx(-0.6157030803)
    assert result["upper_threshold_percent"] == pytest.approx(9.8571861676)
    assert result["category"] == "Medium"
    assert result["source"]["farmer_records_used"] is False


def test_admin_indicator_api_requires_auth_and_returns_real_result(tmp_path):
    from app.main import create_app
    from app.migrations import migrate
    from app.services.admin_auth import hash_password, now_seconds

    path = tmp_path / "admin.sqlite3"
    migrate(path)
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO admin_accounts VALUES(?,?,?,?,?,?,0)",
            ("indicator-officer", "indicator.test", hash_password("TestingOnly@2026!"), "Test officer", "officer", now_seconds()),
        )
    client = TestClient(create_app(str(path)))
    endpoint = "/api/admin/analytics/production-concentration-indicator"
    assert client.get(endpoint).status_code == 401
    login = client.post("/api/admin/auth/login", json={"login_identifier": "indicator.test", "password": "TestingOnly@2026!"})
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert len(client.get(endpoint + "/options", headers=headers).json()["series"]) == 24
    response = client.get(endpoint, headers=headers)
    assert response.status_code == 200
    assert response.json()["category"] == "Medium"
