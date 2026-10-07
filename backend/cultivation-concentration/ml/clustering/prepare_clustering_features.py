"""Aggregate synthetic/prototype records into cultivation concentration features.

Farmer_Record_Count counts source rows, not verified unique real farmers.
Average_Expected_Yield_kg_per_Acre is the unweighted mean of record yields.
No clustering, labels, or risk scores are produced.
"""

import argparse
import math
from pathlib import Path

import pandas as pd


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
INPUT_PATH = DATA_DIRECTORY / "processed_cultivation_data.csv"
OUTPUT_PATH = DATA_DIRECTORY / "clustering_features.csv"
GROUP_COLUMNS = ["District", "Year", "Season", "Crop"]
SOURCE_NUMERIC_COLUMNS = [
    "Land_Size_Acres", "Expected_Production_kg", "Expected_Yield_kg_per_Acre",
]
FEATURE_COLUMNS = [
    "Farmer_Record_Count", "Total_Land_Acres", "Average_Land_Acres",
    "Total_Expected_Production_kg", "Average_Expected_Yield_kg_per_Acre",
]


def validate_numeric(frame, columns):
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        if not values.map(lambda value: pd.notna(value) and math.isfinite(value)).all():
            raise ValueError(f"{column} contains missing, non-numeric, or non-finite values")
        if values.lt(0).any():
            raise ValueError(f"{column} contains negative values")
        frame[column] = values


def validate_groups(frame):
    for column in GROUP_COLUMNS:
        values = frame[column]
        if (values.isna() | values.astype(str).str.strip().eq("")).any():
            raise ValueError(f"Missing grouping values in {column}")


def prepare_features(frame):
    required = GROUP_COLUMNS + SOURCE_NUMERIC_COLUMNS
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Input contains no records")
    source = frame[required].copy()
    validate_groups(source)
    validate_numeric(source, SOURCE_NUMERIC_COLUMNS)
    features = source.groupby(GROUP_COLUMNS, as_index=False, sort=True).agg(
        Farmer_Record_Count=("Land_Size_Acres", "size"),
        Total_Land_Acres=("Land_Size_Acres", "sum"),
        Average_Land_Acres=("Land_Size_Acres", "mean"),
        Total_Expected_Production_kg=("Expected_Production_kg", "sum"),
        Average_Expected_Yield_kg_per_Acre=("Expected_Yield_kg_per_Acre", "mean"),
    )
    validate_groups(features)
    validate_numeric(features, FEATURE_COLUMNS)
    if features.duplicated(subset=GROUP_COLUMNS).any():
        raise ValueError("Duplicate District-Year-Season-Crop groups in output")
    if features["Farmer_Record_Count"].sum() != len(source):
        raise ValueError("Aggregated record counts do not match input row count")
    return features


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    try:
        # Protect both datasets even when custom paths are supplied.
        protected = [args.input, INPUT_PATH, DATA_DIRECTORY / "cultivation_data_2020_2025.csv"]
        for path in protected:
            if args.output.resolve() == path.resolve() or (
                args.output.exists() and path.exists() and args.output.samefile(path)
            ):
                raise ValueError("Output must not overwrite an input or source dataset")
        frame = pd.read_csv(args.input, encoding="utf-8-sig")
        features = prepare_features(frame)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        features.to_csv(args.output, index=False)
        print(f"Input row count: {len(frame)}")
        print(f"Output row count: {len(features)}")
        print(f"Output column names: {', '.join(features.columns)}")
        print(f"Missing value count: {int(features.isna().sum().sum())}")
        print(f"Duplicate group count: {int(features.duplicated(subset=GROUP_COLUMNS).sum())}")
        print("First 10 rows:")
        print(features.head(10).to_string(index=False))
        print("Descriptive statistics for numeric clustering features:")
        print(features[FEATURE_COLUMNS].describe().to_string())
        print(f"Saved to: {args.output.resolve()}")
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
