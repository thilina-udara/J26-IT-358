"""Validate cultivation observations without changing the source CSV.

Dates accept explicit MM/DD/YYYY (the source format) or YYYY-MM-DD.
Production tolerance is a data-consistency check, not a risk methodology.
CSV row numbers in diagnostics include the header as row 1.
"""

import argparse
import csv
import math
from datetime import datetime
from pathlib import Path

import pandas as pd


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "cultivation_data_2020_2025.csv"
REQUIRED_COLUMNS = [
    "Record_ID", "District", "Year", "Season", "Crop", "Planting_Date",
    "Land_Size_Acres", "Expected_Harvest_Date", "Expected_Yield_kg_per_Acre",
    "Expected_Production_kg",
]
ALLOWED_VALUES = {
    "District": ("Matara", "Hambantota"),
    "Season": ("Maha", "Yala"),
    "Crop": ("Mung Beans", "Corn", "Bandakka", "Brinjal", "Pumpkin", "Chillies"),
}
NUMERIC_COLUMNS = ["Year", "Land_Size_Acres", "Expected_Yield_kg_per_Acre", "Expected_Production_kg"]
DATE_COLUMNS = ["Planting_Date", "Expected_Harvest_Date"]


def clean_text(value):
    """Trim and collapse whitespace without guessing or correcting spelling."""
    return " ".join(str(value).split())


def parse_date(value):
    for date_format in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(clean_text(value), date_format)
        except ValueError:
            pass
    return pd.NaT


def load_csv(path):
    """Read literal strings, preserving identifiers and explicit missing checks."""
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source)
        header = next(reader, [])
        if len(header) != len(set(header)):
            raise ValueError("CSV contains duplicate column names")
        for row_number, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValueError(f"CSV row {row_number} has {len(row)} fields; expected {len(header)}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig", skip_blank_lines=False)


def validate_data(frame, production_rtol=0.05, production_atol=1.0):
    """Return (errors, warnings); all checks operate on temporary values."""
    if not math.isfinite(production_rtol) or not math.isfinite(production_atol) or min(production_rtol, production_atol) < 0:
        raise ValueError("Production tolerances must be finite and non-negative")
    errors, warnings = [], []
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")
    if frame.empty:
        errors.append("Dataset contains no records")
    elif len(frame) != 1450:
        warnings.append(f"Row count is {len(frame)}; approximately 1450 expected (no rows removed)")
    if missing:
        return errors, warnings

    def report(mask, message):
        rows = [str(index + 2) for index in frame.index[mask]]
        if rows:
            errors.append(f"{message}: {len(rows)} record(s); CSV rows {', '.join(rows)}")

    cleaned = frame[REQUIRED_COLUMNS].apply(lambda column: column.map(clean_text))
    for column in REQUIRED_COLUMNS:
        report(cleaned[column].eq(""), f"Missing values in {column}")
    report(cleaned.Record_ID.ne("") & cleaned.Record_ID.duplicated(keep=False), "Duplicate Record_ID")
    for column, allowed in ALLOWED_VALUES.items():
        report(~cleaned[column].str.casefold().isin([value.casefold() for value in allowed]), f"Invalid {column}; allowed {', '.join(allowed)}")

    numbers = {}
    for column in NUMERIC_COLUMNS:
        values = pd.to_numeric(cleaned[column], errors="coerce")
        finite = values.map(lambda value: pd.notna(value) and math.isfinite(value))
        report(~finite, f"Non-numeric or non-finite {column}")
        numbers[column] = values.where(finite)
        if column == "Year":
            report(finite & ((values % 1 != 0) | ~values.between(2020, 2025)), "Year must be an integer from 2020 to 2025")
        else:
            report(finite & values.le(0), f"{column} must be positive")

    dates = {column: cleaned[column].map(parse_date) for column in DATE_COLUMNS}
    for column, values in dates.items():
        report(values.isna(), f"Invalid {column}; expected MM/DD/YYYY or YYYY-MM-DD")
    both_dates = dates["Planting_Date"].notna() & dates["Expected_Harvest_Date"].notna()
    report(both_dates & dates["Expected_Harvest_Date"].le(dates["Planting_Date"]), "Harvest date must be after planting date")
    expected = numbers["Land_Size_Acres"] * numbers["Expected_Yield_kg_per_Acre"]
    actual = numbers["Expected_Production_kg"]
    eligible = expected.notna() & actual.notna() & expected.gt(0) & actual.gt(0)
    tolerance = (expected.abs() * production_rtol).clip(lower=production_atol)
    report(eligible & (actual - expected).abs().gt(tolerance), f"Production mismatch (relative tolerance {production_rtol:.1%}, absolute tolerance {production_atol:g} kg)")
    return errors, warnings


def print_report(frame, errors, warnings):
    print(f"Records: {len(frame)}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    print("Validation FAILED" if errors else "Validation PASSED")


def add_validation_arguments(parser):
    parser.add_argument("--input", type=Path, default=DATA_PATH)
    parser.add_argument("--production-rtol", type=float, default=0.05, help="Relative production tolerance (default: 0.05)")
    parser.add_argument("--production-atol", type=float, default=1.0, help="Absolute production tolerance in kg (default: 1)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_validation_arguments(parser)
    args = parser.parse_args()
    try:
        frame = load_csv(args.input)
        errors, warnings = validate_data(frame, args.production_rtol, args.production_atol)
        print_report(frame, errors, warnings)
        return 1 if errors else 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
