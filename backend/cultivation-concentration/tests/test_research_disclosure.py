"""HTTP outputs must be independent of private historical populations."""
from copy import deepcopy
import json
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import create_app
from app.schemas.research_demo import HistoricalScenarioRequest, HistoricalScenarioResponse
from app.services import historical_research_evaluator as internal
from app.services.research_disclosure import public_scenario

REQUEST = dict(district="Hambantota", crop="Mung Beans", season="Yala", land_size_acres=3.5,
               planting_date="2025-06-16", expected_harvest_date="2025-08-25", decision_cutoff="2025-06-10")


def test_public_metadata_router_does_not_require_private_ml_dependencies():
    import subprocess
    import sys
    from pathlib import Path
    script = """
import sys
for name in ('pandas','joblib','numpy','xgboost'):
    sys.modules[name] = None
from app.research_demo_routes import router
from app.services.research_disclosure import public_scenario
from app.schemas.research_demo import HistoricalScenarioRequest
result = public_scenario(HistoricalScenarioRequest(district='Hambantota', crop='Mung Beans',
    season='Yala', land_size_acres=3.5, planting_date='2025-06-16', expected_harvest_date='2025-08-25'))
assert result.disclosure_status == 'collective_values_withheld'
assert router().routes
"""
    subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1], check=True)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CULTIVATION_RESEARCH_DEMO_ENABLED", "true")
    return TestClient(create_app(tmp_path / "operational.sqlite3", {"owner": "fictional-owner"}))


def assert_private(result):
    assert result["disclosure_status"] == "collective_values_withheld"
    assert result["status"] == "historical_result_withheld"
    for key, value in result["prediction"].items():
        if key not in ("coverage_status", "peer_explanation"):
            assert value is None, key
    for name, value in result["features"].items():
        if name not in ("District", "Crop", "Season", "Land_Size_Acres", "Planting_Month", "Harvest_Month"):
            assert value is None, name
    for name in ("replay_unknown_peer_records", "replay_unknown_prior_records"):
        assert result["observation_availability"][name] is None
    values = result["concentration_indicators"]
    for name in ("unknown_availability_count", "observed_after_cutoff_count"):
        assert values[name] is None
    for name in ("historical_dataset_window", "provably_available_window"):
        assert values[name] == dict(record_count=None, acres=None, disclosure_status="collective_values_withheld")
    assert result["diagnostic_alternatives"] == []
    assert result["operational_status"] == "risk_level_not_yet_validated"
    HistoricalScenarioResponse.model_validate_json(json.dumps(result))


@pytest.mark.parametrize("count", [0, 1, 2, 3, 100])
def test_singleton_small_and_large_populations_produce_identical_serialized_response(client, monkeypatch, count):
    # Values are purely fictional; even singleton means and existence must not escape.
    rows = pd.DataFrame([dict(Record_ID=f"fictional-{i}", Land_Size_Acres=7.25+i) for i in range(count)])
    calls = []
    monkeypatch.setattr(internal, "load_historical_dataset", lambda: (calls.append("dataset"), rows)[1])
    monkeypatch.setattr(internal, "get_model_pipeline", lambda *_: pytest.fail("Public response opened private model"))
    monkeypatch.setattr(internal, "evaluate_historical_scenario", lambda **_: pytest.fail("Public response performed private inference"))
    result = client.post("/api/research-demo/evaluate", json=REQUEST)
    assert result.status_code == 200, result.text
    assert calls == []
    expected = public_scenario(HistoricalScenarioRequest(**REQUEST)).model_dump(mode="json")
    assert result.json() == expected
    assert_private(result.json())
    assert "fictional-" not in result.text and "7.25" not in result.text


def test_repeated_cutoffs_and_own_acreage_changes_do_not_reveal_private_differences(client):
    for cutoff in ("2025-06-09", "2025-06-10", "2025-06-16"):
        for acres in (1, 3.5, 7.25, 100):
            payload = dict(REQUEST, decision_cutoff=cutoff, land_size_acres=acres)
            first = client.post("/api/research-demo/evaluate", json=payload)
            second = client.post("/api/research-demo/evaluate", json=payload)
            assert first.content == second.content
            assert_private(first.json())
            assert first.json()["features"]["Land_Size_Acres"] == acres  # Own input only.
            assert first.json()["prediction"]["total_window_acres"] is None


@pytest.mark.parametrize("model", ["XGBoost", "CatBoost", "Random Forest", "LinearSVC", "RBF SVC"])
def test_all_model_contracts_withhold_history_and_class_outputs(client, model):
    result = client.post("/api/research-demo/evaluate", json=dict(REQUEST, model_name=model)).json()
    assert_private(result)
    assert result["model_metadata"]["feature_count"] == (15 if model in ("XGBoost", "CatBoost") else 11)


@pytest.mark.parametrize("field", ["Observation_Availability_Verified", "publication_verified", "disclosure_status", "include_private", "features"])
def test_client_cannot_grant_publication_or_disclosure_permission(client, field):
    assert client.post("/api/research-demo/evaluate", json=dict(REQUEST, **{field: True})).status_code == 422


def test_no_comparison_or_export_side_endpoint_exposes_internal_results(client):
    for path in ("compare", "export", "features"):
        assert client.post(f"/api/research-demo/{path}", json=REQUEST).status_code == 404
    status = client.get("/api/research-demo/status").json()
    assert "peer" not in json.dumps(status) and "acreage" not in json.dumps(status)


@pytest.mark.parametrize("section,key,value", [
    ("prediction", "overlapping_peer_count", 1), ("prediction", "total_window_acres", 10.75),
    ("prediction", "historical_proxy_label", "High"), ("prediction", "class_probabilities", {"High": .99}),
    ("prediction", "is_isolated_plan", True), ("features", "Previous_Year_Mean_Plan_Acres", 7.25),
    ("features", "Overlap_Plan_Count", 2), ("observation_availability", "replay_unknown_peer_records", 1),
    ("concentration_indicators", "unknown_availability_count", 1),
    ("model_metadata", "private_total", 7.25),
])
def test_response_schema_rejects_private_fields_even_in_an_export_serializer(section, key, value):
    result = public_scenario(HistoricalScenarioRequest(**REQUEST)).model_dump(mode="json")
    result[section][key] = value
    with pytest.raises(ValidationError):
        HistoricalScenarioResponse.model_validate(result)


def test_benchmark_metadata_cannot_carry_an_unlisted_private_statistic():
    result = public_scenario(HistoricalScenarioRequest(**REQUEST)).model_dump(mode="json")
    result["model_metadata"]["benchmark_metrics"]["singleton_acres"] = 7.25
    with pytest.raises(ValidationError):
        HistoricalScenarioResponse.model_validate(result)


def test_response_schema_rejects_arithmetic_totals_and_raw_extra_fields():
    result = public_scenario(HistoricalScenarioRequest(**REQUEST)).model_dump(mode="json")
    for key in ("raw_records", "peer_ids", "window_difference"):
        injected = deepcopy(result)
        injected[key] = ["private"]
        with pytest.raises(ValidationError):
            HistoricalScenarioResponse.model_validate(injected)
