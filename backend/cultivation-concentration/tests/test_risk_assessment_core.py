"""Standalone descriptive risk checks; no API or supervised training dependency."""
from datetime import date, datetime, timezone
from app.services.risk_indicators import prepare_indicators
from app.services.risk_assessment import explain
from app.services.current_plan_risk import evaluate


def test_district_window_and_unvalidated_risk_boundaries():
    plans = [dict(plan_id=str(i), farmer_id=f"fictional-{i}", district="Matara",
        region="north", crop="Corn", land_size_acres=2, expected_harvest_date=harvest)
        for i, harvest in enumerate(("2030-03-18", "2030-04-01", "2030-04-15", "2030-04-16"))]
    plans += [dict(plans[0], plan_id="other", farmer_id="other", district="Hambantota",
                   land_size_acres=100)]
    values = prepare_indicators(None, datetime(2020, 1, 1, tzinfo=timezone.utc),
        "Matara", "north", "Corn", "Maha", date(2030, 4, 1), prepared_snapshot=plans)
    assert values["total_planned_acreage"] == 6
    assert values["overlapping_farmer_count"] == 3
    assert values["harvest_overlap_intensity"] == 0.75
    assert explain(values)["risk_level"] is None
    assert evaluate(values)["status"] == "insufficient_evidence"


def test_minimum_distinct_farmer_privacy():
    plans = [dict(plan_id=str(i), farmer_id="one-fictional-farmer", district="Matara",
        region="north", crop="Corn", land_size_acres=2, expected_harvest_date="2030-04-01")
        for i in range(4)]
    values = prepare_indicators(None, datetime(2020, 1, 1, tzinfo=timezone.utc),
        "Matara", "north", "Corn", "Maha", date(2030, 4, 1), prepared_snapshot=plans)
    assert values["status"] == "suppressed_or_insufficient"
    assert "total_planned_acreage" not in values
