"""Validate and preprocess cultivation data; never overwrite the input CSV."""

import argparse
from pathlib import Path

import pandas as pd

from .validate_data import (
    ALLOWED_VALUES, DATE_COLUMNS, NUMERIC_COLUMNS, add_validation_arguments,
    clean_text, load_csv, parse_date, print_report, validate_data,
)


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "processed_cultivation_data.csv"


def preprocess_data(frame):
    """Preserve all input columns and rows; add only basic date features."""
    processed = frame.copy()
    for column in ("Record_ID", *ALLOWED_VALUES):
        processed[column] = processed[column].map(clean_text)
    for column, allowed in ALLOWED_VALUES.items():
        canonical = {value.casefold(): value for value in allowed}
        processed[column] = processed[column].map(lambda value: canonical[value.casefold()])
    for column in NUMERIC_COLUMNS:
        processed[column] = pd.to_numeric(processed[column].map(clean_text), errors="raise")
        processed[column] = processed[column].astype("int64" if column == "Year" else "float64")
    for column in DATE_COLUMNS:
        processed[column] = pd.to_datetime(processed[column].map(parse_date))
    processed["Planting_Month"] = processed["Planting_Date"].dt.month
    processed["Harvest_Month"] = processed["Expected_Harvest_Date"].dt.month
    processed["Growth_Duration_Days"] = (processed["Expected_Harvest_Date"] - processed["Planting_Date"]).dt.days
    return processed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_validation_arguments(parser)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve() or (args.output.exists() and args.output.samefile(args.input)):
            raise ValueError("Output must differ from the original CSV")
        frame = load_csv(args.input)
        errors, warnings = validate_data(frame, args.production_rtol, args.production_atol)
        print_report(frame, errors, warnings)
        if errors:
            print("Preprocessing stopped; output was not written")
            return 1
        features = {"Planting_Month", "Harvest_Month", "Growth_Duration_Days"}
        if features.intersection(frame.columns):
            raise ValueError("Input already contains derived feature columns; refusing to overwrite them")
        processed = preprocess_data(frame)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        processed.to_csv(args.output, index=False, date_format="%Y-%m-%d")
        print(f"Saved {len(processed)} records to {args.output.resolve()}")
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
