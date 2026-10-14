"""Tests for historical research demo workflow, data isolation, and temporal cutoffs.

Verifies:
- Operational farmer registration remains strictly future-date-only.
- Zero peers produces insufficient evidence (risk_level: None), not automatic Low Risk or arbitrary scores.
- Historical dates work only in the isolated research demo workflow.
- Research demo requires explicit server-side authorization (disabled by default).
- Public responses withhold private inference; internal retrospective availability remains unverified.
- Data isolation: Seeding into operational cultivation_plans.sqlite3 is strictly prohibited.
- High historical proxy predictions do not bypass recommendation approval gates.
"""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.seed_demo_data import seed
from app.services.historical_research_evaluator import (
    FEATURES,
    evaluate_historical_scenario,
    get_model_pipeline,
)


@pytest.fixture
def isolated_app(tmp_path):
    db_path = str(tmp_path / "test_plans.sqlite3")
    tokens = {"token-f1": "farmer-01"}
    app = create_app(
        database_path=db_path,
        farmer_tokens=tokens,
        analysis_tokens=["analyst-token"],
        admin_tokens=["admin-token"],
    )
    return app, tokens["token-f1"], db_path


def test_operational_workflow_rejects_past_or_current_dates(isolated_app):
    """Operational farmer registration must strictly enforce future-date-only."""
    app, token, _ = isolated_app
    client = TestClient(app)
    headers = {"Authorization": "Bearer token-f1"}

    # Attempt to submit a past date (e.g., 2025-05-15 or yesterday)
    past_date = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
    harvest_date = (datetime.now(timezone.utc) + timedelta(days=90)).date().isoformat()

    res = client.post(
        "/api/farmer-workflow/plans",
        headers=headers,
        json={
            "district": "Matara",
            "region": "hakmana",
            "crop": "Bandakka",
            "land_size_acres": 2.0,
            "planting_date": past_date,
            "expected_harvest_date": harvest_date,
            "season": "Maha",
        },
    )
    assert res.status_code == 422
    assert "Planting must be in the future" in res.text


def test_operational_zero_peers_produces_insufficient_evidence(isolated_app):
    """Zero registered peers must produce insufficient evidence, never automatic Low Risk."""
    app, token, _ = isolated_app
    client = TestClient(app)
    headers = {"Authorization": "Bearer token-f1"}

    future_planting = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
    future_harvest = (datetime.now(timezone.utc) + timedelta(days=120)).date().isoformat()

    create_res = client.post(
        "/api/farmer-workflow/plans",
        headers=headers,
        json={
            "district": "Matara",
            "region": "hakmana",
            "crop": "Bandakka",
            "land_size_acres": 2.0,
            "planting_date": future_planting,
            "expected_harvest_date": future_harvest,
            "season": "Maha",
        },
    )
    assert create_res.status_code == 201
    plan_id = create_res.json()["plan"]["plan_id"]

    analyze_res = client.post(
        "/api/farmer-workflow/analyze",
        headers=headers,
        json={"plan_id": plan_id, "season": "Maha"},
    )
    assert analyze_res.status_code == 200
    report = analyze_res.json()

    # Must be insufficient evidence with risk_level None
    assert report["status"] == "insufficient_evidence"
    assert report["assessment"]["risk_level"] is None
    # Recommendations must remain blocked (not recommending alternative crops)
    assert report["recommendations"]["status"] == "blocked_unvalidated_risk"
    assert report["recommendations"]["alternatives"] == []


def test_research_demo_authorization_disabled_by_default(isolated_app, monkeypatch):
    """Research demo endpoints must return 403 Forbidden when CULTIVATION_RESEARCH_DEMO_ENABLED is false."""
    monkeypatch.delenv("CULTIVATION_RESEARCH_DEMO_ENABLED", raising=False)
    app, _, _ = isolated_app
    client = TestClient(app)

    status_res = client.get("/api/research-demo/status")
    assert status_res.status_code == 200
    assert status_res.json()["enabled"] is False

    eval_res = client.post(
        "/api/research-demo/evaluate",
        json={
            "district": "Hambantota",
            "crop": "Bandakka",
            "season": "Yala",
            "land_size_acres": 2.0,
            "planting_date": "2025-05-15",
            "expected_harvest_date": "2025-08-15",
            "model_name": "XGBoost",
        },
    )
    assert eval_res.status_code == 403
    assert "disabled" in eval_res.json()["detail"].lower()


def test_research_demo_evaluation_with_strict_temporal_cutoff(isolated_app, monkeypatch):
    """2025 replay is explicitly assumption-based and cannot establish current risk."""
    monkeypatch.setenv("CULTIVATION_RESEARCH_DEMO_ENABLED", "true")
    app, _, _ = isolated_app
    client = TestClient(app)

    # 1. Evaluate May 2025 Yala cohort in Hambantota
    res = client.post(
        "/api/research-demo/evaluate",
        json={
            "district": "Hambantota",
            "crop": "Bandakka",
            "season": "Yala",
            "land_size_acres": 2.0,
            "planting_date": "2025-05-20",
            "expected_harvest_date": "2025-07-20",
            "model_name": "XGBoost",
        },
    )
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "historical_result_withheld"
    assert data["operational_status"] == "risk_level_not_yet_validated"
    assert data["model_metadata"]["simulated_target_year"] == 2025
    assert data["model_metadata"]["trained_through"] == 2024
    assert data["model_metadata"]["is_out_of_time_holdout"] is False

    # Check that all 15 features exist
    for feat in FEATURES:
        assert feat in data["features"]

    assert data["prediction"]["overlapping_peer_count"] is None
    assert data["prediction"]["predicted_risk_level"] is None
    assert "class_probabilities" in data["prediction"]

    assert data["observation_availability"]["status"] == "not_established"
    assert data["concentration_indicators"]["provably_available_window"]["record_count"] is None
    assert data["diagnostic_alternatives"] == []
    assert data["recommendation_status"] == "blocked_unvalidated_risk"


def test_research_demo_date_boundary_validation(isolated_app, monkeypatch):
    """Research demo must reject dates outside the verified 2025-01-01 to 2026-08-31 window."""
    monkeypatch.setenv("CULTIVATION_RESEARCH_DEMO_ENABLED", "true")
    app, _, _ = isolated_app
    client = TestClient(app)

    # Date before 2025
    res = client.post(
        "/api/research-demo/evaluate",
        json={
            "district": "Hambantota",
            "crop": "Bandakka",
            "season": "Yala",
            "land_size_acres": 2.0,
            "planting_date": "2024-12-01",
            "expected_harvest_date": "2025-03-01",
            "model_name": "XGBoost",
        },
    )
    assert res.status_code == 422
    assert "between 2025-01-01 and 2026-08-31" in res.text


def test_database_isolation_seeder_protects_operational_database(tmp_path, monkeypatch):
    """Demo seeder must refuse to seed synthetic records into cultivation_plans.sqlite3."""
    monkeypatch.setenv("CULTIVATION_RESEARCH_DEMO_ENABLED", "true")
    operational_db = tmp_path / "cultivation_plans.sqlite3"
    with pytest.raises(RuntimeError, match="Data isolation violation"):
        seed(operational_db, "owner", date(2026, 1, 1), date(2026, 3, 31), False)
