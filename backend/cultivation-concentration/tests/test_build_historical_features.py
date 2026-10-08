import copy
import csv
import hashlib

import pytest

from ml.preprocessing.build_historical_features import (
    ROOT, build_features, load_official, write_features,
)


def record(year, area=1, production=1, **overrides):
    row = dict(district_name="Matara", crop_name="Corn", season="Maha",
               year=str(year), cultivated_extent_hectares=str(area),
               production_metric_tons=str(production))
    row.update(overrides)
    return row


def test_conversions():
    row = build_features([record(2001, 2, 3)])[0]
    assert row["land_acres"] == pytest.approx(4.9421076294)
    assert row["production_kg"] == 3000
    assert row["yield_kg_per_acre"] == pytest.approx(3000 / 4.9421076294)


def test_order_prior_means_and_input_immutability():
    source = [record(2005, 9, 10), record(2001, 1, 2), record(2003, 3, 6)]
    before = copy.deepcopy(source)
    rows = build_features(source)
    assert source == before
    assert [r["year"] for r in rows] == [2001, 2003, 2005]
    assert [r["prior_history_count"] for r in rows] == [0, 1, 2]
    assert rows[1]["historical_mean_land_acres"] == pytest.approx(2.4710538147)
    assert rows[2]["historical_mean_land_acres"] == pytest.approx(4.9421076294)
    assert rows[2]["historical_mean_production_kg"] == 4000
    assert rows[2]["historical_mean_yield_kg_per_acre"] == pytest.approx(2000 / 2.4710538147)
    assert rows[2]["land_concentration_ratio"] == pytest.approx(4.5)
    assert rows[2]["production_concentration_ratio"] == pytest.approx(2.5)


def test_no_current_or_future_leakage():
    original = build_features([record(2001), record(2002, 2, 4), record(2025)])
    changed = build_features([record(2025, 900, 999), record(2002, 200, 400), record(2001)])
    assert original[0] == changed[0]
    for key in ("prior_history_count", "historical_mean_land_acres",
                "historical_mean_production_kg", "historical_mean_yield_kg_per_acre"):
        assert original[1][key] == changed[1][key]
    assert build_features([record(2001), record(2002, 2, 4)]) == original[:2]


def test_missing_and_zero_baselines():
    rows = build_features([record(2001, 1, 0), record(2002, 2, 3), record(2003, 1, 0)])
    first = rows[0]
    assert not first["has_prior_historical_baseline"]
    assert not first["both_concentration_ratios_valid"]
    assert first["historical_mean_land_acres"] is None
    assert first["land_concentration_ratio"] is None
    assert first["production_concentration_ratio"] is None
    assert first["yield_kg_per_acre"] == 0
    assert rows[1]["has_prior_historical_baseline"]
    assert rows[1]["historical_mean_production_kg"] == 0
    assert rows[1]["production_concentration_ratio"] is None
    assert not rows[1]["both_concentration_ratios_valid"]
    assert rows[2]["production_concentration_ratio"] == 0
    assert rows[2]["both_concentration_ratios_valid"]


def test_zero_area_yield_and_baseline():
    rows = build_features([record(2001, 0, 0), record(2002)])
    assert rows[0]["yield_kg_per_acre"] is None
    assert rows[1]["historical_mean_yield_kg_per_acre"] is None
    assert rows[1]["land_concentration_ratio"] is None
    assert not rows[1]["has_prior_historical_baseline"]


def test_groups_and_filters():
    rows = build_features([
        record(2001), record(2002, season="Yala"), record(2003, crop_name="Pumpkin"),
        record(2004, district_name="Hambantota"), record(2001, season="Total"),
        record(2000), record(2026), record(2001, district_name="Other"),
        record(2001, crop_name="Other"),
    ])
    assert len(rows) == 4
    assert all(r["prior_history_count"] == 0 for r in rows)


def test_duplicate_key_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        build_features([record(2001), record(2001, 2, 3)])


@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity", "bad"])
def test_invalid_measure_rejected(value):
    with pytest.raises(ValueError):
        build_features([record(2001, area=value)])


def test_actual_row_count_keys_order_and_read_only():
    path = ROOT / "data/official/official_historical_2001_2025.csv"
    before = hashlib.sha256(path.read_bytes()).digest()
    rows = build_features(load_official(path))
    assert len(rows) == 580
    keys = [(r["district_name"], r["crop_name"], r["season"], r["year"]) for r in rows]
    assert len(set(keys)) == 580
    assert keys == sorted(keys)
    assert {r["year"] for r in rows} == set(range(2001, 2026))
    assert sum(not r["has_prior_historical_baseline"] for r in rows) == 24
    zero = next(r for r in rows if (r["district_name"], r["crop_name"], r["season"], r["year"]) == ("Matara", "Corn", "Yala", 2014))
    assert zero["yield_kg_per_acre"] == zero["production_concentration_ratio"] == 0
    assert hashlib.sha256(path.read_bytes()).digest() == before


def test_output_blanks_and_no_overwrite(tmp_path):
    path = tmp_path / "processed/features.csv"
    write_features(build_features([record(2001)]), path)
    before = path.read_bytes()
    with path.open(newline="") as stream:
        row = next(csv.DictReader(stream))
    assert row["land_concentration_ratio"] == ""
    assert row["historical_mean_yield_kg_per_acre"] == ""
    assert row["has_prior_historical_baseline"] == "False"
    with pytest.raises(FileExistsError):
        write_features([], path)
    assert path.read_bytes() == before
