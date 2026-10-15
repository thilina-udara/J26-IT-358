"""Fictional credential/evaluator fixtures; private loopback boundary regressions."""
import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.private_research_workbench import create_workbench, local_credential

TOKEN = "fictional-local-researcher-credential-00000000"
BODY = dict(district="Hambantota", crop="Mung Beans", season="Yala", land_size_acres=3.5,
            planting_date="2025-06-16", expected_harvest_date="2025-08-25", model_name="XGBoost")
HEADERS = {"Authorization": "Bearer " + TOKEN}


def fixture_result(**_):
    return dict(status="historical_proxy_prediction", model_metadata=dict(model_name="XGBoost", trained_through=2024,
        training_cutoff_basis="recorded dataset Year upper bound", feature_names=["District", "Crop"]),
        prediction=dict(historical_proxy_label="High", class_probabilities={"High": .7, "Medium": .2, "Low": .1},
                        overlapping_peer_count=123, overlapping_peer_acres=999),
        observation_availability=dict(status="unverified", replay_unknown_peer_records=123),
        features={"Past_Mean_Window_Acres": 999})


def client(evaluator=fixture_result, host="127.0.0.1", address="127.0.0.1"):
    return TestClient(create_workbench(TOKEN, evaluator), base_url=f"http://{host}:8011", client=(address, 12345))


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer fictional-farmer-token"}])
def test_private_predictions_require_separate_researcher_credential(headers):
    calls = []
    response = client(lambda **value: calls.append(value)).post("/api/private-research/evaluate", json=BODY, headers=headers)
    assert response.status_code == 401 and calls == []
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("host,address,extra", [
    ("example.invalid", "127.0.0.1", {}), ("127.0.0.1", "192.0.2.10", {}),
    ("127.0.0.1", "127.0.0.1", {"Origin": "http://localhost:3000"}),
    ("127.0.0.1", "127.0.0.1", {"Origin": "null"}),
    ("127.0.0.1", "192.0.2.10", {"X-Forwarded-For": "127.0.0.1"}),
])
def test_remote_rebinding_and_cross_origin_requests_are_blocked(host, address, extra):
    calls = []
    response = client(lambda **value: calls.append(value), host, address).post(
        "/api/private-research/evaluate", json=BODY, headers={**HEADERS, **extra})
    assert response.status_code == 403 and calls == []
    assert "access-control-allow-origin" not in response.headers


def test_private_model_output_allowlist_does_not_release_collective_statistics():
    response = client().post("/api/private-research/evaluate", json=BODY, headers={**HEADERS, "Origin": "http://127.0.0.1:8011"})
    assert response.status_code == 200
    result = response.json()
    assert result["classification"] == "High" and result["mode"] == "private_local_model_test"
    assert result["operational_status"] == "risk_level_not_yet_validated"
    assert result["recommendation_status"] == "blocked_unvalidated_risk"
    for private in ("overlapping_peer_count", "overlapping_peer_acres", "Past_Mean_Window_Acres", "replay_unknown_peer_records"):
        assert private not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"


@pytest.mark.parametrize("patch", [
    {"planting_date": "2026-10-13", "expected_harvest_date": "2027-01-01"},
    {"planting_date": "2024-12-31"}, {"decision_cutoff": "2025-06-17"},
    {"decision_cutoff": "2024-12-31"}, {"expected_harvest_date": "2025-06-15"},
    {"include_private": True}, {"observation_availability_verified": True},
])
def test_bad_dates_and_client_approval_injections_are_rejected_before_inference(patch):
    calls = []
    response = client(lambda **value: calls.append(value)).post("/api/private-research/evaluate", json={**BODY, **patch}, headers=HEADERS)
    assert response.status_code == 422 and calls == []


def test_empty_research_coverage_cannot_be_promoted_to_low():
    def insufficient(**value):
        result = fixture_result(**value)
        result.update(status="insufficient_research_coverage")
        result["prediction"].update(historical_proxy_label=None, class_probabilities=None)
        return result
    response = client(insufficient).post("/api/private-research/evaluate", json=BODY, headers=HEADERS)
    assert response.json()["classification"] is None
    assert response.json()["status"] == "insufficient_research_coverage"


def test_failure_never_echoes_private_artifact_paths_or_records():
    def broken(**_): raise ValueError("fictional-private-record-secret")
    response = client(broken).post("/api/private-research/evaluate", json=BODY, headers=HEADERS)
    assert response.status_code == 503 and "fictional-private-record-secret" not in response.text


def test_public_farmer_app_has_no_private_workbench_routes(tmp_path):
    public = TestClient(create_app(tmp_path / "operational.sqlite3", {TOKEN: "fictional-farmer"}))
    assert public.post("/api/private-research/evaluate", json=BODY, headers=HEADERS).status_code == 404


def test_credential_is_local_persistent_and_never_overwrites_invalid_existing_file(tmp_path):
    file = tmp_path / "research-token.txt"
    value = local_credential(file)
    assert len(value) >= 32 and local_credential(file) == value
    file.write_text("invalid", encoding="utf-8")
    with pytest.raises(ValueError): local_credential(file)
    assert file.read_text() == "invalid"


def test_launcher_binds_loopback_without_proxy_header_trust_or_credential_logging(tmp_path, monkeypatch, capsys):
    import sys
    import uvicorn
    from app import private_research_workbench as workbench
    launched = []
    monkeypatch.setattr(workbench, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["private-research-workbench"])
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: launched.append(kwargs))
    workbench.main()
    assert launched == [dict(host="127.0.0.1", port=8011, proxy_headers=False, access_log=False)]
    token = (tmp_path / "storage/private_research_workbench_token.txt").read_text().strip()
    assert token not in capsys.readouterr().out


def test_real_frozen_inference_does_not_create_operational_database_or_modify_artifacts():
    import json
    from app.private_research_workbench import ROOT
    catalog = json.loads((ROOT / "models/artifact_catalog.json").read_text())
    operational = ROOT / "storage/cultivation_plans.sqlite3"
    before = hashlib.sha256(operational.read_bytes()).hexdigest() if operational.exists() else None
    local = TestClient(create_workbench(TOKEN), base_url="http://127.0.0.1:8011", client=("127.0.0.1", 12345))
    for year, model in ((2025, "XGBoost"), (2026, "XGBoost"), (2025, "CatBoost"),
                        (2025, "Random Forest"), (2025, "LinearSVC"), (2025, "RBF SVC")):
        response = local.post("/api/private-research/evaluate", json={**BODY,
            "planting_date": f"{year}-06-16", "expected_harvest_date": f"{year}-08-25", "model_name": model}, headers=HEADERS)
        assert response.status_code == 200, response.text
        assert response.json()["classification"] in ("Low", "Medium", "High")
        assert response.json()["trained_through"] == 2024
    after = hashlib.sha256(operational.read_bytes()).hexdigest() if operational.exists() else None
    assert before == after
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in catalog["files"].items())
