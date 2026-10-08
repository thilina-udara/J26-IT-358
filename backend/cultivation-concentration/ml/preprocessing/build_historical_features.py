"""Official-only descriptive concentration measures, not observed oversupply.

Baselines are arithmetic means of available observations in strictly prior years
within district/crop/season. Missing years are not filled. Historical yield is
the mean of yearly yields, not a pooled production/area ratio.
"""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HECTARE_TO_ACRES = 2.4710538147
METRIC_TON_TO_KG = 1000
DISTRICTS = {"Matara", "Hambantota"}
CROPS = {"Mung Beans", "Corn", "Bandakka", "Brinjal", "Pumpkin", "Chillies"}
SOURCE_COLUMNS = (
    "district_name", "crop_name", "year", "season",
    "cultivated_extent_hectares", "production_metric_tons",
)
OUTPUT_COLUMNS = SOURCE_COLUMNS + (
    "land_acres", "production_kg", "yield_kg_per_acre", "prior_history_count",
    "historical_mean_land_acres", "historical_mean_production_kg",
    "historical_mean_yield_kg_per_acre", "land_concentration_ratio",
    "production_concentration_ratio", "has_prior_historical_baseline",
    "both_concentration_ratios_valid",
)


def _nonnegative(value, column):
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid {column}: {value!r}") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Invalid {column}: {value!r}")
    return number


def safe_ratio(numerator, denominator):
    """Represent undefined or nonfinite ratios as None (blank in CSV)."""
    if numerator is None or denominator is None or denominator <= 0:
        return None
    value = numerator / denominator
    return value if math.isfinite(value) else None


def build_features(records):
    """Return new rows; never mutate input rows. Reject ambiguous duplicate keys."""
    groups = defaultdict(list)
    keys = set()
    for original in records:
        if (original.get("district_name") not in DISTRICTS
                or original.get("crop_name") not in CROPS
                or original.get("season") not in {"Maha", "Yala"}):
            continue
        try:
            year = int(original["year"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Invalid official year") from exc
        if not 2001 <= year <= 2025:
            continue
        group = (original["district_name"], original["crop_name"], original["season"])
        key = (*group, year)
        if key in keys:
            raise ValueError(f"Duplicate district/crop/season/year key: {key}")
        keys.add(key)
        area = _nonnegative(original.get("cultivated_extent_hectares"), "cultivated_extent_hectares")
        production = _nonnegative(original.get("production_metric_tons"), "production_metric_tons")
        row = {column: original[column] for column in SOURCE_COLUMNS}
        row.update(year=year, land_acres=area * HECTARE_TO_ACRES,
                   production_kg=production * METRIC_TON_TO_KG)
        if not math.isfinite(row["land_acres"]) or not math.isfinite(row["production_kg"]):
            raise ValueError(f"Unit conversion overflow: {key}")
        row["yield_kg_per_acre"] = safe_ratio(row["production_kg"], row["land_acres"])
        groups[group].append(row)

    output = []
    for group in sorted(groups):
        history = []
        for row in sorted(groups[group], key=lambda r: r["year"]):
            row["prior_history_count"] = len(history)
            for field in ("land_acres", "production_kg", "yield_kg_per_acre"):
                values = [prior[field] for prior in history if prior[field] is not None]
                row[f"historical_mean_{field}"] = math.fsum(values) / len(values) if values else None
            # A baseline exists when all three historical means are available.
            # Zero means exist, but cannot be denominators for valid ratios.
            row["has_prior_historical_baseline"] = all(
                row[f"historical_mean_{field}"] is not None
                for field in ("land_acres", "production_kg", "yield_kg_per_acre")
            )
            row["land_concentration_ratio"] = safe_ratio(row["land_acres"], row["historical_mean_land_acres"])
            row["production_concentration_ratio"] = safe_ratio(row["production_kg"], row["historical_mean_production_kg"])
            row["both_concentration_ratios_valid"] = all(
                row[field] is not None for field in ("land_concentration_ratio", "production_concentration_ratio")
            )
            output.append(row)
            history.append(row)  # Update only after calculating this year's features.
    return output


def load_official(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        missing = set(SOURCE_COLUMNS) - set(columns)
        if missing or len(columns) != len(set(columns)):
            raise ValueError(f"Invalid headers; missing columns: {sorted(missing)}")
        records = list(reader)
        if any(None in row or any(row.get(c) is None for c in SOURCE_COLUMNS) for row in records):
            raise ValueError("Malformed CSV row")
        return records


def write_features(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects both existing artifacts and the source CSV.
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows):
    valid = sum(row["both_concentration_ratios_valid"] for row in rows)
    exists = sum(row["has_prior_historical_baseline"] for row in rows)
    print(f"Total processed rows: {len(rows)}")
    print(f"Rows with prior historical baselines: {exists}; without: {len(rows) - exists}")
    print(f"Rows with valid historical baselines for both ratios: {valid}")
    print(f"Rows without valid baselines for both ratios: {len(rows) - valid}")
    print("Year coverage: " + ", ".join(map(str, sorted({row['year'] for row in rows}))))
    for field in ("land_concentration_ratio", "production_concentration_ratio"):
        print(f"Missing/invalid {field}: {sum(row[field] is None for row in rows)}")
    print("Descriptive historical measures only; not observed oversupply or risk labels.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/official/official_historical_2001_2025.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/official_historical_features.csv")
    parser.add_argument("--expected-rows", type=int, default=580)
    args = parser.parse_args(argv)
    try:
        rows = build_features(load_official(args.input))
        if len(rows) != args.expected_rows:
            raise ValueError(f"Expected {args.expected_rows} seasonal rows, found {len(rows)}")
        write_features(rows, args.output)
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(1, f"Feature build failed: {exc}\n")
    print_summary(rows)
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
