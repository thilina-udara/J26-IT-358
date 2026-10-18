"""Tests for admin ML research monitoring endpoint and model validation metrics."""
import sqlite3
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.admin_auth import ADMIN_SESSION_PREFIX, hash_password, now_seconds
from app.services.model_validation_metrics import load_frozen_validation_metrics


@pytest.fixture
def test_app(tmp_path):
    from app.migrations import migrate
    db_file = tmp_path / "test_admin.sqlite3"
    migrate(db_file)
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            """INSERT INTO admin_accounts(admin_id, login_identifier, password_hash, full_name, role, created_at, disabled)
               VALUES (?, ?, ?, ?, ?, ?, 0)""",
            ("admin-test-1", "test.officer", hash_password("TestOfficer@2026!"), "Test Officer", "officer", now_seconds()),
        )
    return create_app(str(db_file))


def test_load_frozen_validation_metrics():
    """Verify metrics.json is loaded correctly and non-empty."""
    metrics = load_frozen_validation_metrics()
    assert "model_metadata" in metrics
    assert "temporal_degradation_analysis" in metrics
    assert "chronological_evaluations" in metrics

    meta = metrics["model_metadata"]
    assert meta["model_name"] == "XGBoost"
    assert meta["pipeline_bundle"] == "selected_xgboost_2024"
    assert meta["feature_count"] == 15
    assert meta["holdout_used_for_selection"] is False

    evals = metrics["chronological_evaluations"]
    assert len(evals) == 4
    period_ids = [e["period_id"] for e in evals]
    assert period_ids == ["2023_fold", "2024_fold", "2025_holdout", "pooled_evaluation"]

    # Verify 2023 fold values match frozen metrics.json
    f2023 = next(e for e in evals if e["period_id"] == "2023_fold")
    assert f2023["records_evaluated"] == 1781
    assert f2023["accuracy"] == 0.9124
    assert f2023["macro_f1"] == 0.8035
    assert f2023["class_metrics"]["Medium"]["recall"] == 0.9296
    assert f2023["class_metrics"]["High"]["precision"] == 1.0

    # Verify 2025 holdout degradation
    f2025 = next(e for e in evals if e["period_id"] == "2025_holdout")
    assert f2025["records_evaluated"] == 2526
    assert f2025["accuracy"] == 0.7557
    assert f2025["macro_f1"] == 0.6295
    assert f2025["class_metrics"]["Medium"]["recall"] == 0.2239

    # Verify confusion matrices have correct dimensions
    for ev in evals:
        matrix = ev["confusion_matrix"]["matrix"]
        assert len(matrix) == 3
        for row in matrix:
            assert len(row) == 3


def test_admin_monitoring_endpoint_requires_auth(test_app):
    """Admin monitoring endpoint requires valid officer/admin bearer token."""
    client = TestClient(test_app)
    res = client.get("/api/admin/analytics/ml-research-monitoring")
    assert res.status_code == 401


def test_admin_monitoring_endpoint_returns_validation_metrics(test_app):
    """Admin monitoring endpoint returns structured validation metrics."""
    client = TestClient(test_app)
    login_res = client.post(
        "/api/admin/auth/login",
        json={"login_identifier": "test.officer", "password": "TestOfficer@2026!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token.startswith(ADMIN_SESSION_PREFIX)

    res = client.get(
        "/api/admin/analytics/ml-research-monitoring",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert "disclaimer" in data
    assert "benchmarks" in data
    assert "clustering" in data
    assert "validation_metrics" in data

    val = data["validation_metrics"]
    assert val["model_metadata"]["model_name"] == "XGBoost"
    assert len(val["chronological_evaluations"]) >= 3
    assert "temporal_degradation_analysis" in val
    assert len(val["temporal_degradation_analysis"]["observations"]) >= 3


def test_admin_clustering_disaggregation_and_privacy(test_app):
    """Verify separate K-Means and DBSCAN structure, parameters, and small-cohort privacy suppression."""
    client = TestClient(test_app)
    login_res = client.post(
        "/api/admin/auth/login",
        json={"login_identifier": "test.officer", "password": "TestOfficer@2026!"},
    )
    token = login_res.json()["access_token"]

    res = client.get(
        "/api/admin/analytics/ml-research-monitoring",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    clustering = data["clustering"]

    # Target pilot districts
    for dist in ("Matara", "Hambantota"):
        assert dist in clustering
        info = clustering[dist]
        assert "kmeans" in info
        assert "dbscan" in info
        assert "noise" in info
        assert "interpretation" in info
        assert "Clusters describe plan similarity and density, not oversupply or Low/Medium/High risk" in info["interpretation"]

        # With empty or <3 farmers in newly created test DB, status must be insufficient_or_private
        assert info["status"] == "insufficient_or_private"
        assert len(info["kmeans"]) == 0
        assert len(info["dbscan"]) == 0


def test_admin_clustering_synthetic_demo_mode(test_app):
    """Verify synthetic research demo mode executes clustering on isolated synthetic cohort."""
    client = TestClient(test_app)
    login_res = client.post(
        "/api/admin/auth/login",
        json={"login_identifier": "test.officer", "password": "TestOfficer@2026!"},
    )
    token = login_res.json()["access_token"]

    # Request with mode=synthetic_demo
    res = client.get(
        "/api/admin/analytics/ml-research-monitoring?mode=synthetic_demo",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    clustering = data["clustering"]

    for dist in ("Matara", "Hambantota"):
        assert dist in clustering
        info = clustering[dist]
        assert info["mode"] == "synthetic_research_demo"
        assert info["status"] == "available"
        assert "Synthetic Research Demonstration — Not Real Farmer Data" in info["notice"]
        assert info["synthetic_plan_count"] >= 8
        assert info["distinct_synthetic_farmers"] >= 3

        # Verify K-Means executed and returned clusters with parameters
        assert "kmeans" in info
        assert len(info["kmeans"]) >= 2
        assert "configuration" in info
        assert info["configuration"]["requested_k"] == 3
        assert info["configuration"]["eps"] == 1.0
        assert info["configuration"]["min_samples"] == 2

        # Verify DBSCAN executed and returned dense clusters and noise
        assert "dbscan" in info
        assert len(info["dbscan"]) >= 2
        assert "noise" in info
        assert info["noise"]["status"] == "available"
        assert info["noise"]["plan_count"] >= 1


