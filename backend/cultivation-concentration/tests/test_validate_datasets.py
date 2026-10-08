import csv
import hashlib

import pytest

from ml.preprocessing.validate_datasets import (
    FARMER_COLUMNS, OFFICIAL_COLUMNS, ROOT, load_csv, seasonal_records,
    validate_farmer, validate_official,
)


def write_csv(tmp_path, columns, rows):
    path = tmp_path / "fixture.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest.fixture
def farmer():
    return dict(zip(FARMER_COLUMNS, (
        "MAT_1", "Matara", "2020", "Maha", "Corn", "11/1/2020",
        "1.5", "2/1/2021", "400", "600",
    )))


def test_valid_farmer_and_provenance(tmp_path, farmer):
    result = validate_farmer(write_csv(tmp_path, FARMER_COLUMNS, [farmer]), 1)
    assert result.valid
    assert "Farmer records have unverified provenance." in result.notes
    assert any("synthetic prototype data" in note for note in result.notes)
    farmer["Data_Source"] = "declared real"
    result = validate_farmer(write_csv(tmp_path, (*FARMER_COLUMNS, "Data_Source"), [farmer]), 1)
    assert result.valid
    assert any("independent verification" in note for note in result.notes)


@pytest.mark.parametrize("column,value,issue", [
    ("Year", "2019", "Invalid year"),
    ("Year", "2020.5", "Invalid year"),
    ("District", "Other", "Invalid category: District"),
    ("Crop", "Other", "Invalid category: Crop"),
    ("Season", "Total", "Invalid category: Season"),
    ("Land_Size_Acres", "0", "Invalid/nonpositive land size"),
    ("Land_Size_Acres", "-1", "Invalid/nonpositive land size"),
    ("Expected_Yield_kg_per_Acre", "NaN", "Invalid/nonpositive expected yield"),
    ("Expected_Yield_kg_per_Acre", "0", "Invalid/nonpositive expected yield"),
    ("Expected_Yield_kg_per_Acre", "405", "Expected yield is not a multiple of 10"),
    ("Expected_Production_kg", "601", "Production calculation mismatch"),
    ("Expected_Production_kg", "Infinity", "Invalid expected production"),
    ("Planting_Date", "2/30/2020", "Invalid date: Planting_Date"),
    ("Expected_Harvest_Date", "10/1/2020", "Harvest before planting"),
])
def test_farmer_rejects_invalid_values(tmp_path, farmer, column, value, issue):
    farmer[column] = value
    assert validate_farmer(write_csv(tmp_path, FARMER_COLUMNS, [farmer]), 1).issues[issue] == 1


def test_missing_duplicates_and_count(tmp_path, farmer):
    farmer["Crop"] = ""
    result = validate_farmer(write_csv(tmp_path, FARMER_COLUMNS, [farmer, farmer]), 1)
    assert result.issues["Missing values: Crop"] == 2
    assert result.issues["Duplicate rows"] == 1
    assert result.issues["Duplicate Record_ID values"] == 1
    assert result.issues["Row count differs from expected 1"] == 1
    columns = FARMER_COLUMNS[:-1]
    farmer.pop("Expected_Production_kg")
    result = validate_farmer(write_csv(tmp_path, columns, [farmer]), 1)
    assert result.issues["Missing required column: Expected_Production_kg"] == 1


def test_official_total_view_preserves_file(tmp_path):
    rows = [dict(zip(OFFICIAL_COLUMNS, ("Matara", "Corn", "2001", season, "2", "0"))) for season in ("Maha", "Yala", "Total")]
    path = write_csv(tmp_path, OFFICIAL_COLUMNS, rows)
    before = path.read_bytes()
    result = validate_official(path)
    assert result.valid
    assert result.seasonal_row_count == 2
    assert result.annual_total_count == 1
    assert len(seasonal_records(rows)) == 2
    assert len(rows) == 3
    assert path.read_bytes() == before


@pytest.mark.parametrize("column,value,issue", [
    ("year", "2026", "Invalid year"),
    ("district_name", "Other", "Invalid category: district_name"),
    ("crop_name", "Other", "Invalid category: crop_name"),
    ("season", "Other", "Invalid category: season"),
    ("cultivated_extent_hectares", "-1", "Invalid/negative cultivated_extent_hectares"),
    ("production_metric_tons", "Infinity", "Invalid/negative production_metric_tons"),
])
def test_official_invalid(tmp_path, column, value, issue):
    row = dict(zip(OFFICIAL_COLUMNS, ("Matara", "Corn", "2001", "Maha", "2", "0")))
    row[column] = value
    assert validate_official(write_csv(tmp_path, OFFICIAL_COLUMNS, [row])).issues[issue] == 1


def test_actual_datasets_are_unchanged():
    paths = [ROOT / "data/farmer/cultivation_data_2020_2025.csv", ROOT / "data/official/official_historical_2001_2025.csv"]
    before = [hashlib.sha256(path.read_bytes()).digest() for path in paths]
    farmer, official = validate_farmer(paths[0]), validate_official(paths[1])
    assert farmer.valid, farmer.issues
    assert farmer.row_count == 1450
    assert official.valid, official.issues
    assert official.seasonal_row_count + official.annual_total_count == official.row_count
    assert [hashlib.sha256(path.read_bytes()).digest() for path in paths] == before


def test_unreadable_file(tmp_path):
    assert not validate_farmer(tmp_path / "absent.csv").valid
    assert not validate_official(tmp_path / "absent.csv").valid
