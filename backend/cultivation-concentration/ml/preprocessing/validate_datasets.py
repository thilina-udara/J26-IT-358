"""Read-only CSV validation. Run directly or with python -m ml.preprocessing.validate_datasets."""

import argparse
import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DISTRICTS = {"Matara", "Hambantota"}
CROPS = {"Mung Beans", "Corn", "Bandakka", "Brinjal", "Pumpkin", "Chillies"}
FARMER_COLUMNS = (
    "Record_ID", "District", "Year", "Season", "Crop", "Planting_Date",
    "Land_Size_Acres", "Expected_Harvest_Date", "Expected_Yield_kg_per_Acre",
    "Expected_Production_kg",
)
OFFICIAL_COLUMNS = (
    "district_name", "crop_name", "year", "season",
    "cultivated_extent_hectares", "production_metric_tons",
)


@dataclass
class ValidationResult:
    path: Path
    row_count: int = 0
    columns: tuple = ()
    issues: Counter = field(default_factory=Counter)
    notes: list = field(default_factory=list)
    seasonal_row_count: int = 0
    annual_total_count: int = 0

    @property
    def valid(self):
        return not self.issues


def load_csv(path):
    """Open only for reading; retain rows and original headers."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = tuple(reader.fieldnames or ())
        return columns, list(reader)


def _load(path, required):
    result = ValidationResult(Path(path))
    try:
        result.columns, rows = load_csv(path)
    except (OSError, UnicodeError, csv.Error) as exc:
        result.issues["CSV read failure"] += 1
        result.notes.append(str(exc))
        return result, []
    result.row_count = len(rows)
    for column in required:
        if column not in result.columns:
            result.issues[f"Missing required column: {column}"] += 1
    result.issues["Duplicate headers"] += len(result.columns) - len(set(result.columns))
    for row in rows:
        if None in row:
            result.issues["Rows with extra CSV fields"] += 1
        for column in result.columns:
            value = row.get(column)
            if value is None or value.strip().lower() in {"", "na", "n/a", "nan", "null", "none"}:
                result.issues[f"Missing values: {column}"] += 1
    counts = Counter(tuple(row.get(c) for c in result.columns) for row in rows)
    result.issues["Duplicate rows"] += sum(n - 1 for n in counts.values())
    result.issues = +result.issues
    if not rows:
        result.issues["Empty dataset"] += 1
    return result, rows


def _number(value):
    try:
        number = Decimal(value)
        return number if number.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _categories(result, row, year_column, first, last, district, crop, seasons):
    year = _number(row.get(year_column))
    if year is None or year != year.to_integral_value() or not first <= year <= last:
        result.issues["Invalid year"] += 1
    for column, allowed in ((district, DISTRICTS), (crop, CROPS), ("season" if year_column == "year" else "Season", seasons)):
        if row.get(column) not in allowed:
            result.issues[f"Invalid category: {column}"] += 1


def validate_farmer(path, expected_rows=1450):
    result, rows = _load(path, FARMER_COLUMNS)
    if result.row_count != expected_rows:
        result.issues[f"Row count differs from expected {expected_rows}"] += 1
    provenance = [c for c in result.columns if c.strip().lower() in {
        "data_source", "source", "provenance", "record_source", "record_origin", "is_synthetic",
    }]
    if not provenance:
        result.notes.append("Farmer records have unverified provenance.")
    else:
        result.notes.append("Provenance columns: " + ", ".join(provenance) + "; declarations require independent verification.")
    result.notes.append("Adjusted farmer dataset: synthetic prototype data unless independent evidence establishes individual record origins; no individual origin is verified by this validator.")
    ids = Counter(row.get("Record_ID") for row in rows if row.get("Record_ID"))
    result.issues["Duplicate Record_ID values"] += sum(n - 1 for n in ids.values())
    for row in rows:
        _categories(result, row, "Year", 2020, 2025, "District", "Crop", {"Maha", "Yala"})
        land, yield_, production = [_number(row.get(c)) for c in (
            "Land_Size_Acres", "Expected_Yield_kg_per_Acre", "Expected_Production_kg",
        )]
        for name, value in (("land size", land), ("expected yield", yield_)):
            if value is None or value <= 0:
                result.issues[f"Invalid/nonpositive {name}"] += 1
        if yield_ is not None and yield_ % 10 != 0:
            result.issues["Expected yield is not a multiple of 10"] += 1
        if production is None:
            result.issues["Invalid expected production"] += 1
        elif land is not None and yield_ is not None and land * yield_ != production:
            result.issues["Production calculation mismatch"] += 1
        dates = []
        for column in ("Planting_Date", "Expected_Harvest_Date"):
            try:
                dates.append(datetime.strptime(row.get(column) or "", "%m/%d/%Y"))
            except ValueError:
                dates.append(None)
                result.issues[f"Invalid date: {column}"] += 1
        if all(dates) and dates[1] < dates[0]:
            result.issues["Harvest before planting"] += 1
    result.issues = +result.issues
    return result


def seasonal_records(rows):
    """Return a seasonal view without deleting or mutating annual Total rows."""
    return [row for row in rows if row.get("season") in {"Maha", "Yala"}]


def validate_official(path):
    result, rows = _load(path, OFFICIAL_COLUMNS)
    for row in rows:
        _categories(result, row, "year", 2001, 2025, "district_name", "crop_name", {"Maha", "Yala", "Total"})
        for column in ("cultivated_extent_hectares", "production_metric_tons"):
            value = _number(row.get(column))
            if value is None or value < 0:
                result.issues[f"Invalid/negative {column}"] += 1
    result.seasonal_row_count = len(seasonal_records(rows))
    result.annual_total_count = sum(row.get("season") == "Total" for row in rows)
    result.notes.append(f"Seasonal analysis: {result.seasonal_row_count} rows; excluded {result.annual_total_count} annual Total rows in memory only.")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--farmer", type=Path, default=ROOT / "data/farmer/cultivation_data_2020_2025.csv")
    parser.add_argument("--official", type=Path, default=ROOT / "data/official/official_historical_2001_2025.csv")
    parser.add_argument("--expected-farmer-rows", type=int, default=1450)
    args = parser.parse_args(argv)
    results = [validate_farmer(args.farmer, args.expected_farmer_rows), validate_official(args.official)]
    for result in results:
        print(f"{'PASS' if result.valid else 'FAIL'}: {result.path}")
        print(f"  {result.row_count} data rows; {len(result.columns)} columns")
        for issue, count in sorted(result.issues.items()):
            print(f"  {issue}: {count}")
        for note in result.notes:
            print(f"  {note}")
    print("CSV files opened read-only. PASS indicates structural/value checks, not verified authenticity.")
    return 0 if all(result.valid for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
