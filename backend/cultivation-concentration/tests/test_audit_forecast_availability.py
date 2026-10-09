import pytest
from ml.preprocessing.audit_forecast_availability import (
    ROOT, check_availability, audit_targets, inspect_inputs, load_cutoffs,
)


def test_availability_requires_evidence_and_unambiguous_dates():
    assert "missing" in check_availability()
    assert "ambiguous" in check_availability("2020-01-01")
    assert "evidence" in check_availability("2020-01-01T00:00:00Z")
    assert "not configured" in check_availability("2020-01-01T00:00:00Z", evidence_verified=True)
    assert check_availability("2020-01-01T00:00:00Z", "2020-01-01T05:30:00+05:30", True) == "available"
    assert check_availability("2020-01-02T00:00:00Z", "2020-01-01T00:00:00Z", True) == "unavailable at cutoff"


def test_actual_inputs_missing_evidence_and_strict_history():
    oh, th, observations, targets = inspect_inputs(ROOT / "data/official/official_historical_2001_2025.csv", ROOT / "data/processed/official_training_dataset.csv")
    assert "publication_date" not in oh and "data_available_at" not in th
    report = audit_targets(observations, targets)
    assert len(report) == 508
    assert all(row["Count_Matches_Training"] for row in report)
    assert all(not row["Availability_Verified"] for row in report)
    assert all(all(year < row["Target_Year"] for year in row["Historical_Years"]) for row in report)
    assert max(int(row["year"]) for row in observations) == 2022
    assert max(row["Target_Year"] for row in report) == 2023
    target = dict(targets[0], Target_Year="2024")
    with pytest.raises(ValueError, match="Test rows forbidden"):
        audit_targets(observations, [target])


def test_configurable_cutoffs_no_defaults(tmp_path):
    assert load_cutoffs() == {}
    path = tmp_path / "cutoffs.csv"
    path.write_text("Target_Year,Season,Forecast_Cutoff\n2020,Maha,2020-01-01T00:00:00Z\n2020,Yala,2020-02-01T00:00:00Z\n", encoding="utf-8")
    assert set(load_cutoffs(path)) == {(2020, "Maha"), (2020, "Yala")}
    path.write_text("Target_Year,Season,Forecast_Cutoff\n2020,Maha,2020-01-01\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_cutoffs(path)
