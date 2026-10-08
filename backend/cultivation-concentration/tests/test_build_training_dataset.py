import copy
import hashlib
from collections import Counter

import pytest

from ml.preprocessing.build_historical_features import ROOT, build_features, load_official
from ml.preprocessing.build_training_dataset import (
    FEATURE_COLUMNS, TRAINING_COLUMNS, build_training_rows, load_historical,
    risk_label, validate_training_rows, write_or_compare,
)


def official(year, area, production):
    return dict(district_name="Matara", crop_name="Corn", season="Maha",
                year=str(year), cultivated_extent_hectares=str(area), production_metric_tons=str(production))


def historical(records):
    return [{k: "" if v is None else str(v) for k, v in row.items()} for row in build_features(records)]


@pytest.mark.parametrize("score,label", [(0, "Low"), (.74999, "Low"), (.75, "Medium"), (1.25, "Medium"), (1.25001, "High")])
def test_threshold_boundaries(score, label):
    assert risk_label(score) == label


@pytest.mark.parametrize("score", [-1, float("nan"), float("inf")])
def test_invalid_score(score):
    with pytest.raises(ValueError):
        risk_label(score)


def test_targets_types_prior_only_and_no_mutation():
    records = [official(2003, 4, 4), official(2001, 1, 1), official(2002, .5, .5)]
    source = historical(records)
    before = copy.deepcopy(source)
    rows = build_training_rows(source, records)
    assert source == before
    assert [r["Target_Year"] for r in rows] == [2002, 2003]
    assert [r["Risk_Label"] for r in rows] == ["Low", "High"]
    assert rows[0]["Prior_History_Count"] == 1
    assert rows[1]["Historical_Mean_Production_kg"] == 750
    assert all(set(r) == set(TRAINING_COLUMNS) for r in rows)
    assert all(type(r["Historical_Mean_Land_Acres"]) is float for r in rows)
    changed = [official(2001, 1, 1), official(2002, 99, 99), official(2025, 900, 900)]
    alternative = build_training_rows(historical(changed), changed)
    assert {c: rows[0][c] for c in FEATURE_COLUMNS} == {c: alternative[0][c] for c in FEATURE_COLUMNS}
    assert alternative[0]["Risk_Label"] == "High"


def test_tampered_future_baseline_rejected():
    records = [official(2001, 1, 1), official(2002, 3, 3)]
    source = historical(records)
    source[1]["historical_mean_production_kg"] = "2000"
    with pytest.raises(ValueError, match="historical_mean_production_kg"):
        build_training_rows(source, records)


def test_duplicates_and_missing_coverage_rejected():
    records = [official(2001, 1, 1), official(2002, 1, 1)]
    source = historical(records)
    with pytest.raises(ValueError, match="Duplicate"):
        build_training_rows(source + source[:1], records)
    with pytest.raises(ValueError, match="cover"):
        build_training_rows(source[1:], records)


def test_zero_baselines_excluded_zero_current_production_labeled():
    records = [official(2001, 1, 0), official(2002, 1, 1), official(2003, 1, 0)]
    rows = build_training_rows(historical(records), records)
    assert len(rows) == 1
    assert rows[0]["Target_Year"] == 2003
    assert rows[0]["Risk_Label"] == "Low"


def test_leaky_column_and_bad_types_rejected():
    records = [official(2001, 1, 1), official(2002, 1, 1)]
    row = build_training_rows(historical(records), records)[0]
    with pytest.raises(ValueError, match="whitelist"):
        validate_training_rows([{**row, "risk_score": 1}])
    with pytest.raises(ValueError, match="integer"):
        validate_training_rows([{**row, "Target_Year": "2002"}])
    with pytest.raises(ValueError, match="Duplicate"):
        validate_training_rows([row, row])


def test_write_compare_never_overwrites(tmp_path):
    records = [official(2001, 1, 1), official(2002, 1, 1)]
    rows = build_training_rows(historical(records), records)
    path = tmp_path / "training.csv"
    assert write_or_compare(rows, path) == (True, [])
    before = path.read_bytes()
    assert write_or_compare(rows, path) == (False, [])
    changed = [{**rows[0], "Risk_Label": "High"}]
    created, differences = write_or_compare(changed, path)
    assert not created and any("Risk_Label" in d for d in differences)
    assert path.read_bytes() == before


def test_actual_official_dataset_read_only():
    paths = [ROOT / "data/processed/official_historical_features.csv", ROOT / "data/official/official_historical_2001_2025.csv"]
    before = [hashlib.sha256(p.read_bytes()).digest() for p in paths]
    rows = build_training_rows(load_historical(paths[0]), load_official(paths[1]))
    assert len(rows) == 556
    assert Counter(r["Risk_Label"] for r in rows) == {"Low": 93, "Medium": 231, "High": 232}
    assert {r["Target_Year"] for r in rows} == set(range(2002, 2026))
    assert [hashlib.sha256(p.read_bytes()).digest() for p in paths] == before
