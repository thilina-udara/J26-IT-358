"""Standalone clustering checks using fictional plans, without API dependencies.

Run: python -m pytest tests/test_plan_clustering_core.py
The version-table fixture tests the snapshot reader contract, not registration writes.
"""
import json
import sqlite3
from datetime import datetime, timezone

from app.services.plan_clustering import analyze, snapshot_versions, summarize


def plan(index, **changes):
    value = dict(
        plan_id=f"fictional-plan-{index}", farmer_id=f"fictional-farmer-{index}",
        district="Matara", region="north", crop="Corn", land_size_acres=2,
        planting_date="2030-01-01", expected_harvest_date="2030-04-01",
        status="active", submitted_at="2020-01-01T00:00:00+00:00",
    )
    value.update(changes)
    return value


def test_identical_plans_district_isolation_and_aggregate_privacy():
    matara = [plan(i) for i in range(6)]
    hambantota = [plan(i + 10, district="Hambantota", land_size_acres=100)
                  for i in range(3)]
    result = analyze(matara + hambantota, "Matara")
    assert result == analyze(list(reversed(matara)), "Matara")
    assert result["effective_k"] == 1
    for method in ("kmeans", "dbscan", "baseline"):
        group = result[method][0]
        assert group["plan_count"] == group["farmer_count"] == 6
        assert group["planned_acreage"] == 12
        assert group["peak_plan_centered_29_day_planned_acreage"] == 12
    other = analyze(matara + hambantota, "Hambantota")
    assert other["kmeans"][0]["planned_acreage"] == 300
    encoded = json.dumps(result)
    assert "fictional-plan-" not in encoded
    assert "fictional-farmer-" not in encoded
    assert "risk_label" not in encoded


def test_density_groups_and_suppressed_outlier():
    records = [plan(i) for i in range(3)]
    records += [plan(i, crop="Brinjal", region="south",
                     expected_harvest_date="2030-10-01") for i in range(3, 6)]
    records += [plan(6, land_size_acres=200, expected_harvest_date="2031-10-01")]
    result = analyze(records, "Matara", clusters=2, eps=0.1, min_samples=3)
    assert len(result["kmeans"]) == len(result["dbscan"]) == 2
    assert all(group["farmer_count"] == 3 for group in result["dbscan"])
    assert result["noise"]["status"] == "suppressed"
    assert "planned_acreage" not in result["noise"]
    assert "not automatically" in result["noise"]["meaning"]
    assert analyze([], "Matara")["status"] == "insufficient_or_private"
    assert analyze([plan(i, farmer_id="same") for i in range(6)], "Matara")[
        "status"] == "insufficient_or_private"


def test_inclusive_harvest_window_and_small_peak_suppression():
    records = [plan(0, expected_harvest_date="2030-03-18"), plan(1),
               plan(2, expected_harvest_date="2030-04-15"),
               plan(3, expected_harvest_date="2030-04-16")]
    group = summarize(records)
    assert group["peak_window_plan_count"] == 3
    assert group["peak_plan_centered_29_day_planned_acreage"] == 6
    assert group["peak_window_acreage_share"] == 0.75
    spread = [plan(i, expected_harvest_date=f"2030-0{i + 1}-01")
              for i in range(3)]
    assert "peak_window_status" in summarize(spread)
    assert "peak_plan_centered_29_day_planned_acreage" not in summarize(spread)


def test_snapshot_excludes_future_versions_submissions_and_cancelled_plans():
    with sqlite3.connect(":memory:") as db:
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE cultivation_plan_versions "
                   "(version_id INTEGER PRIMARY KEY, recorded_at TEXT, payload TEXT)")
        versions = [
            ("2020-01-01T00:00:00+00:00", plan(0)),
            ("2021-01-01T00:00:00+00:00", plan(0, land_size_acres=90)),
            ("2020-01-01T00:00:00+00:00", plan(
                1, submitted_at="2021-01-01T00:00:00+00:00")),
            ("2020-01-01T00:00:00+00:00", plan(2, status="cancelled")),
            ("2020-01-01T00:00:00+00:00", plan(3, planting_date="2019-01-01")),
        ]
        for recorded, value in versions:
            db.execute("INSERT INTO cultivation_plan_versions(recorded_at,payload) "
                       "VALUES (?,?)", (recorded, json.dumps(value)))
        cutoff = datetime(2020, 6, 1, tzinfo=timezone.utc)
        old = snapshot_versions(None, cutoff, connection=db)
        assert len(old) == 1 and old[0]["plan"]["land_size_acres"] == 2
        assert old[0]["version_id"] == 1
        newer = snapshot_versions(None, datetime(2021, 6, 1, tzinfo=timezone.utc), db)
        assert len(newer) == 2 and newer[0]["plan"]["land_size_acres"] == 90
        assert snapshot_versions(None, cutoff, db) == old
