"""Fictional availability fixtures; no training or agricultural validation."""
from datetime import date, datetime, timezone
import sqlite3
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.seed_demo_data import seed
from app.services import historical_research_evaluator as demo
from app.services.farmer_workflow import defensible_high


def row(identifier, year=2025, planting="2025-06-01", harvest="2025-08-25", acres=2., **changes):
    return dict(Record_ID=identifier, Year=year, District="Hambantota", Crop="Mung Beans", Season="Yala",
                Planting_Date=pd.Timestamp(planting), Expected_Harvest_Date=pd.Timestamp(harvest),
                Land_Size_Acres=acres, Expected_Yield_kg_per_Acre=100., Expected_Production_kg=acres*100., **changes)


def evidence(stamp, verified=True):
    return dict(Observation_Available_At=stamp, Observation_Availability_Verified=verified,
                Observation_Evidence_Reference="FICTIONAL exact-version evidence")


@pytest.fixture
def research(monkeypatch):
    data = pd.DataFrame([row("prior", 2024, "2024-06-01", "2024-08-25"),
                         *[row(f"peer-{i}") for i in range(3)],
                         row("later-planting", planting="2025-06-12")])
    monkeypatch.setattr(demo, "load_historical_dataset", lambda: data.copy())
    class FrozenFixture:
        feature_names_in_ = np.array(demo.FEATURES)
        classes_ = np.array(["High", "Low", "Medium"])
        def predict(self, features):
            return ["High"]
        def predict_proba(self, features):
            return [[.7, .1, .2]]
    monkeypatch.setattr(demo, "get_model_pipeline", lambda *_: (FrozenFixture(), 2024))
    return data


def evaluate(planting=date(2025, 6, 16), cutoff=None):
    return demo.evaluate_historical_scenario("Hambantota", "Mung Beans", "Yala", 3.5, planting,
                                             date(planting.year, 8, 25), decision_cutoff=cutoff)


def test_same_harvest_different_decision_cutoffs(research):
    early = evaluate(cutoff=date(2025, 6, 10))
    late = evaluate(cutoff=date(2025, 6, 16))
    assert early["features"]["Overlap_Plan_Count"] == 4
    assert late["features"]["Overlap_Plan_Count"] == 5
    assert early["concentration_indicators"] == late["concentration_indicators"]
    assert early["concentration_indicators"]["provably_available_window"]["record_count"] == 0
    assert late["observation_availability"]["replay_unknown_peer_records"] == 4


def test_same_cutoff_different_planting_dates(research):
    first = evaluate(date(2025, 6, 10), date(2025, 6, 9))
    second = evaluate(date(2025, 6, 16), date(2025, 6, 9))
    assert first["features"] == second["features"]
    assert first["prediction"] == second["prediction"]
    july = evaluate(date(2025, 7, 1), date(2025, 6, 9))
    assert july["features"]["Planting_Month"] == 7
    assert july["features"]["Overlap_Plan_Count"] == first["features"]["Overlap_Plan_Count"]


def test_verified_after_cutoff_excluded_from_replay_and_known_features(research, monkeypatch):
    baseline = evaluate(cutoff=date(2025, 6, 10))
    late = row("observed-late", acres=1e9, **evidence("2025-06-11T00:00:00+05:30"))
    late_prior = row("prior-published-late", 2023, "2023-06-01", "2023-08-25", 1e9,
                     **evidence("2025-06-11T00:00:00+05:30"))
    monkeypatch.setattr(demo, "load_historical_dataset", lambda: pd.concat([research, pd.DataFrame([late, late_prior])], ignore_index=True))
    result = evaluate(cutoff=date(2025, 6, 10))
    assert result["features"] == baseline["features"]
    assert result["concentration_indicators"]["observed_after_cutoff_count"] == 1
    assert result["concentration_indicators"]["provably_available_window"]["record_count"] == 0


def test_observation_requires_attestation_timezone_and_exact_version(research):
    records = pd.DataFrame([row("unknown"), row("naive", **evidence("2025-06-09T12:00:00")),
        row("unattested", **evidence("2025-06-09T12:00:00Z", False)),
        row("equal", **evidence("2025-06-10T00:00:00+05:30")),
        row("after", **evidence("2025-06-09T19:00:00Z")),
        row("submitted-only", Submitted_At="2025-01-01T00:00:00Z")])
    assert demo.observation_availability(records, date(2025, 6, 10)).tolist() == ["unknown", "unknown", "unknown", "available", "after_cutoff", "unknown"]


def test_known_future_planting_is_available_independently_of_replay(research, monkeypatch):
    known = [row(f"registered-before-planting-{i}", planting="2025-06-20",
                 **evidence("2025-06-08T00:00:00Z")) for i in range(3)]
    monkeypatch.setattr(demo, "load_historical_dataset", lambda: pd.DataFrame(known))
    result = evaluate(cutoff=date(2025, 6, 10))
    assert result["concentration_indicators"]["provably_available_window"]["record_count"] == 3
    assert result["prediction"]["overlapping_peer_count"] == 0
    assert result["prediction"]["historical_proxy_label"] is None


def test_future_records_yields_and_current_labels_do_not_leak(research, monkeypatch):
    baseline = evaluate(cutoff=date(2025, 6, 10))
    changed = research.copy()
    changed["Risk_Label"] = "Low"
    changed["Overlap_Acres"] = 1e12
    changed["Historical_P67_Acres"] = 1e12
    changed["Expected_Yield_kg_per_Acre"] = 1e12
    changed.loc[changed.Year == 2025, "Expected_Production_kg"] = 1e12
    future = row("future", 2026, "2026-06-01", "2026-08-25", 1e12)
    monkeypatch.setattr(demo, "load_historical_dataset", lambda: pd.concat([changed, pd.DataFrame([future])], ignore_index=True))
    result = evaluate(cutoff=date(2025, 6, 10))
    assert result["features"] == baseline["features"]
    assert result["features"]["Own_Expected_Production_kg"] is None


def test_training_semantics_historical_production_and_cross_year_peers():
    from ml.preprocessing.concentration_common import engineer_fast
    from ml.training.xgboost_concentration import add_features
    raw = pd.DataFrame([row("prior-a", 2023, "2023-06-01", "2023-08-25", 2),
                        row("prior-b", 2023, "2023-06-02", "2023-08-30", 4),
                        row("cross-year", 2023, "2023-12-20", "2024-01-15", 3),
                        row("scenario", 2024, "2024-01-05", "2024-01-20", 3.5)])
    raw.loc[1, "Expected_Production_kg"] = 1200
    expected = add_features(raw, engineer_fast(raw)).set_index("Record_ID").loc["scenario"]
    actual, peers, _ = demo.historical_features(raw[raw.Record_ID != "scenario"], "Hambantota", "Mung Beans", "Yala", 3.5,
                                               date(2024, 1, 5), date(2024, 1, 20), date(2024, 1, 5))
    assert len(peers) == 1
    for name in demo.FEATURES:
        if name == "Own_Expected_Production_kg":
            assert np.isnan(actual[name])
        elif isinstance(actual[name], str):
            assert actual[name] == expected[name]
        else:
            assert actual[name] == pytest.approx(expected[name])
    assert actual["Past_Mean_Window_Production_kg"] == 1400


@pytest.mark.parametrize("count", [0, 1, 2])
def test_sparse_and_zero_peers_abstain_and_suppress(research, monkeypatch, count):
    monkeypatch.setattr(demo, "load_historical_dataset", lambda: research.iloc[:count+1].copy())
    result = evaluate()
    assert result["status"] == "insufficient_research_coverage"
    assert result["prediction"]["historical_proxy_label"] is None
    assert result["prediction"]["class_probabilities"] is None
    assert result["prediction"]["overlapping_peer_acres"] is None
    assert result["diagnostic_alternatives"] == []
    if count:
        assert result["features"]["Overlap_Plan_Count"] is None


def test_probability_order_and_no_market_or_recommendation_promotion(research):
    result = evaluate()
    assert result["prediction"]["class_probabilities"] == {"High": .7, "Low": .1, "Medium": .2}
    assert result["prediction"]["historical_proxy_label"] == "High"
    assert result["operational_status"] == "risk_level_not_yet_validated"
    assert result["recommendation_status"] == "blocked_unvalidated_risk"
    assert result["diagnostic_alternatives"] == []
    assert not defensible_high(dict(status=result["status"], risk_level="High"), datetime.now(timezone.utc))


def test_high_historical_prediction_does_not_activate_farmer_workflow(tmp_path, monkeypatch):
    from app.services import historical_prediction
    from tests.test_farmer_workflow import body
    from tests.test_security_privacy import contains_collective_numbers
    monkeypatch.setattr(historical_prediction, "predict_context", lambda *_: dict(
        status="historical_proxy_prediction", risk_level="High", model="FICTIONAL SOFTWARE FIXTURE",
        scope="historical_district_crop_season_proxy"))
    client = TestClient(create_app(tmp_path / "operational.sqlite3", {"owner-token": "owner"}))
    result = client.post("/api/farmer-workflow/plans", headers={"Authorization": "Bearer owner-token"},
                         json=dict(body(), season="Yala"))
    assert result.status_code == 201, result.text
    workflow = result.json()["workflow"]
    assert workflow["historical_prediction"]["risk_level"] == "High"
    assert workflow["assessment"]["risk_level"] is None
    assert workflow["recommendations"]["status"] == "blocked_unvalidated_risk"
    assert workflow["recommendations"]["alternatives"] == []
    assert not contains_collective_numbers(workflow)


def test_2026_never_borrows_2025_metrics(research):
    result = evaluate(date(2026, 6, 16), date(2026, 6, 10))
    assert result["model_metadata"]["benchmark_metrics"] is None


def test_api_replay_does_not_touch_operational_database_or_expose_ids(research, tmp_path, monkeypatch):
    monkeypatch.setenv("CULTIVATION_RESEARCH_DEMO_ENABLED", "true")
    database = tmp_path / "operational.sqlite3"
    client = TestClient(create_app(database, {"token": "owner"}))
    # Initialize only the test operational DB, then compare its bytes.
    from app.services.cultivation_plans import PlanStore
    PlanStore(database)
    before = database.read_bytes()
    payload = dict(district="Hambantota", crop="Mung Beans", season="Yala", land_size_acres=3.5,
                   planting_date="2025-06-16", expected_harvest_date="2025-08-25", decision_cutoff="2025-06-10")
    result = client.post("/api/research-demo/evaluate", json=payload)
    assert result.status_code == 200, result.text
    assert before == database.read_bytes()
    assert "peer-" not in result.text and "Record_ID" not in result.text and "farmer_id" not in result.text
    assert client.post("/api/research-demo/evaluate", json=dict(payload, decision_cutoff="2025-06-17")).status_code == 422
    assert client.post("/api/research-demo/evaluate", json=dict(payload, Observation_Availability_Verified=True)).status_code == 422


def test_seeder_refuses_configured_operational_and_app_refuses_synthetic(tmp_path, monkeypatch):
    monkeypatch.setenv("CULTIVATION_RESEARCH_DEMO_ENABLED", "true")
    configured = tmp_path / "arbitrary.sqlite3"
    monkeypatch.setenv("CULTIVATION_PLAN_DB", str(configured))
    with pytest.raises(RuntimeError, match="isolation"):
        seed(configured, "fictional", date(2026, 1, 1), date(2026, 1, 31), False)
    assert not configured.exists()
    database = tmp_path / "research_demo.sqlite3"
    seed(database, "fictional", date(2026, 1, 1), date(2026, 1, 31), False)
    with pytest.raises(ValueError, match="Synthetic"):
        create_app(database)
    renamed = tmp_path / "renamed.sqlite3"
    renamed.write_bytes(database.read_bytes())
    with pytest.raises(ValueError, match="Synthetic"):
        create_app(renamed)


def test_seeder_preserves_existing_non_demo_records(tmp_path, monkeypatch):
    monkeypatch.setenv("CULTIVATION_RESEARCH_DEMO_ENABLED", "true")
    database = tmp_path / "research_demo.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE cultivation_plans (plan_id TEXT)")
        db.execute("INSERT INTO cultivation_plans VALUES ('private-existing')")
    before = database.read_bytes()
    with pytest.raises(RuntimeError, match="non-demo"):
        seed(database, "fictional", date(2026, 1, 1), date(2026, 1, 31), True)
    assert database.read_bytes() == before


@pytest.mark.parametrize("model,count", [("XGBoost", 15), ("CatBoost", 15), ("Random Forest", 11), ("LinearSVC", 11), ("RBF SVC", 11)])
def test_saved_feature_contracts_and_labels(model, count):
    pipeline, trained_through = demo.get_model_pipeline(model, 2025)
    assert trained_through == 2024
    assert list(pipeline.feature_names_in_) == demo.FEATURES[:count]
    assert len(pipeline.classes_) == 3
