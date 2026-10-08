"""Build prior-year inputs and fixed operational concentration targets only.

Targets describe historical concentration, not observed market oversupply.
Original official records are used to verify the provenance of every baseline.
No training, threshold tuning, or farmer data access is performed.
"""

import argparse
import csv
import math
from collections import Counter
from pathlib import Path

try:  # Support both direct script execution and package imports.
    from .build_historical_features import ROOT, OUTPUT_COLUMNS, build_features, load_official
except ImportError:
    from build_historical_features import ROOT, OUTPUT_COLUMNS, build_features, load_official


FEATURE_COLUMNS = (
    "Prior_History_Count", "Historical_Mean_Land_Acres",
    "Historical_Mean_Production_kg", "Historical_Mean_Yield_kg_per_Acre",
    "District", "Crop", "Season", "Target_Year",
)
TARGET_COLUMN = "Risk_Label"
TRAINING_COLUMNS = FEATURE_COLUMNS + (TARGET_COLUMN,)
BASELINE_MAPPING = {
    "Prior_History_Count": "prior_history_count",
    "Historical_Mean_Land_Acres": "historical_mean_land_acres",
    "Historical_Mean_Production_kg": "historical_mean_production_kg",
    "Historical_Mean_Yield_kg_per_Acre": "historical_mean_yield_kg_per_acre",
}


def risk_label(score):
    if not math.isfinite(score) or score < 0:
        raise ValueError("Invalid risk score")
    return "Low" if score < 0.75 else "High" if score > 1.25 else "Medium"


def _key(row):
    year = int(row["year"])
    return row["district_name"], row["crop_name"], row["season"], year


def _matches(value, expected):
    if expected is None:
        return value == ""
    if isinstance(expected, bool):
        return value == str(expected)
    if isinstance(expected, (float, int)):
        try:
            number = float(value)
            return math.isfinite(number) and math.isclose(number, expected, rel_tol=1e-12, abs_tol=1e-9)
        except (ValueError, TypeError):
            return False
    return value == str(expected)


def load_historical(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not set(OUTPUT_COLUMNS) <= set(headers):
            raise ValueError("Invalid historical feature headers")
        rows = list(reader)
        if any(None in row or any(row.get(c) is None for c in OUTPUT_COLUMNS) for row in rows):
            raise ValueError("Malformed historical CSV row")
        return rows


def build_training_rows(historical_rows, official_records):
    """Verify against strictly prior-year official baselines before projecting inputs.

Use verified rebuilt numeric values to avoid propagation of CSV rounding.
All source keys, observations, ratios, flags and baselines must agree. This
rejects stale inputs and tampered baselines rather than silently repairing them.
"""
    verified = {_key(r): r for r in build_features(official_records)}
    seen = set()
    for row in historical_rows:
        key = _key(row)
        if key in seen:
            raise ValueError(f"Duplicate historical key: {key}")
        seen.add(key)
        if key not in verified:
            raise ValueError(f"Unknown historical key: {key}")
        for column in OUTPUT_COLUMNS:
            if not _matches(row.get(column), verified[key][column]):
                raise ValueError(f"Historical verification failed: {key}, {column}")
    if seen != set(verified):
        raise ValueError("Historical CSV does not cover all official seasonal keys")
    output = []
    for key in sorted(verified):
        row = verified[key]
        if not row["both_concentration_ratios_valid"]:
            continue
        target = risk_label(0.5 * row["land_concentration_ratio"] + 0.5 * row["production_concentration_ratio"])
        projected = {feature: row[source] for feature, source in BASELINE_MAPPING.items()}
        projected.update(District=key[0], Crop=key[1], Season=key[2], Target_Year=key[3], Risk_Label=target)
        output.append(projected)
    validate_training_rows(output)
    return output


def validate_training_rows(rows):
    """Enforce the feature whitelist, types, ranges and unique target keys."""
    seen = set()
    for row in rows:
        if set(row) != set(TRAINING_COLUMNS):
            raise ValueError("Training column whitelist violation")
        for column in ("Prior_History_Count", "Target_Year"):
            if type(row[column]) is not int:
                raise ValueError(f"Expected integer: {column}")
        if row["Prior_History_Count"] <= 0 or not 2001 <= row["Target_Year"] <= 2025:
            raise ValueError("Invalid history count or target year")
        if row["Prior_History_Count"] > row["Target_Year"] - 2001:
            raise ValueError("History count exceeds available strictly prior years")
        for column in FEATURE_COLUMNS[1:4]:
            value = row[column]
            if type(value) is not float or not math.isfinite(value) or value < 0:
                raise ValueError(f"Expected finite nonnegative float: {column}")
        if row["Historical_Mean_Land_Acres"] <= 0 or row["Historical_Mean_Production_kg"] <= 0:
            raise ValueError("Invalid ratio baseline")
        allowed = {
            "District": {"Matara", "Hambantota"},
            "Crop": {"Mung Beans", "Corn", "Bandakka", "Brinjal", "Pumpkin", "Chillies"},
            "Season": {"Maha", "Yala"}, "Risk_Label": {"Low", "Medium", "High"},
        }
        for column, values in allowed.items():
            if type(row[column]) is not str or row[column] not in values:
                raise ValueError(f"Invalid category: {column}")
        key = tuple(row[c] for c in ("District", "Crop", "Season", "Target_Year"))
        if key in seen:
            raise ValueError(f"Duplicate training key: {key}")
        seen.add(key)


def write_or_compare(rows, path):
    """Exclusive creation; an existing CSV is compared and never overwritten."""
    path = Path(path)
    validate_training_rows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        stream = path.open("x", encoding="utf-8", newline="")
    except FileExistsError:
        with path.open("r", encoding="utf-8-sig", newline="") as existing:
            reader = csv.DictReader(existing)
            headers = reader.fieldnames
            saved = list(reader)
        differences = []
        if headers != list(TRAINING_COLUMNS):
            differences.append("column names/order differ")
        if len(saved) != len(rows):
            differences.append(f"row count: existing {len(saved)}, expected {len(rows)}")
        for index, (actual, expected) in enumerate(zip(saved, rows), start=2):
            for column in TRAINING_COLUMNS:
                if not _matches(actual.get(column), expected[column]):
                    differences.append(f"CSV line {index}, {column}: {actual.get(column)!r} != {expected[column]!r}")
        return False, differences
    with stream:
        writer = csv.DictWriter(stream, fieldnames=TRAINING_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return True, []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/official_historical_features.csv")
    parser.add_argument("--official", type=Path, default=ROOT / "data/official/official_historical_2001_2025.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/official_training_dataset.csv")
    args = parser.parse_args(argv)
    try:
        rows = build_training_rows(load_historical(args.input), load_official(args.official))
        created, differences = write_or_compare(rows, args.output)
    except (OSError, ValueError, KeyError, csv.Error) as exc:
        parser.exit(1, f"Training dataset build failed: {exc}\n")
    print(f"Labeled rows: {len(rows)}")
    counts = Counter(row[TARGET_COLUMN] for row in rows)
    print("Labels: " + ", ".join(f"{label}={counts[label]}" for label in ("Low", "Medium", "High")))
    print("Features: " + ", ".join(FEATURE_COLUMNS))
    print("Year coverage: " + ", ".join(map(str, sorted({row['Target_Year'] for row in rows}))))
    print("Verified strictly prior-year baselines; current-year observations used only for targets.")
    print("Labels represent operational historical concentration, not observed oversupply.")
    if created:
        print(f"Created: {args.output}")
    else:
        print(f"Existing output preserved: {len(differences)} differences" if differences else "Existing output preserved: matches fresh in-memory result.")
        for difference in differences[:20]:
            print("  " + difference)
    return 1 if differences else 0


if __name__ == "__main__":
    raise SystemExit(main())
