"""In-memory prior-year features. Never construct features for 2024-2025.

Rolling windows contain up to three available prior observations, not three
calendar years. Trends are least-squares slopes per calendar year; fewer than
two observations produce missing trends. Missing years are never filled.
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ADVANCED_COLUMNS = (
    "Previous_Year_Land_Acres", "Previous_Year_Production_kg",
    "Previous_Year_Yield_kg_per_Acre", "Rolling_3Y_Mean_Land_Acres",
    "Rolling_3Y_Mean_Production_kg", "Rolling_3Y_Mean_Yield",
    "Rolling_3Y_Land_Trend", "Rolling_3Y_Production_Trend",
    "Rolling_3Y_History_Count", "Rolling_3Y_Yield_History_Count",
)


def load_development_rows(path):
    """Read year for routing, then discard test rows without feature inspection."""
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        rows = [row for row in reader if 2002 <= int(row["Target_Year"]) <= 2023]
    data = pd.DataFrame(rows, columns=headers)
    for column in ("Target_Year", "Prior_History_Count", "Historical_Mean_Land_Acres",
                   "Historical_Mean_Production_kg", "Historical_Mean_Yield_kg_per_Acre"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    return data


def load_prior_official(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        # No 2023+ outcomes are needed for prediction features through 2023.
        return [row for row in csv.DictReader(stream) if 2001 <= int(row["year"]) <= 2022]


def _mean(values):
    return math.fsum(values) / len(values) if values else np.nan


def _trend(history, field):
    if len(history) < 2:
        return np.nan
    years = np.array([r["year"] for r in history], dtype=float)
    values = np.array([r[field] for r in history], dtype=float)
    centered = years - years.mean()
    return float(np.dot(centered, values - values.mean()) / np.dot(centered, centered))


def build_advanced_features(development, official):
    if not development.Target_Year.between(2002, 2023).all():
        raise ValueError("Advanced features restricted to 2002-2023; test rows forbidden")
    keys = ["District", "Crop", "Season", "Target_Year"]
    if development.duplicated(keys).any():
        raise ValueError("Duplicate development keys")
    groups = defaultdict(list)
    seen = set()
    for source in official:
        year = int(source["year"])
        if not 2001 <= year <= 2022 or source["season"] not in {"Maha", "Yala"}:
            continue
        group = (source["district_name"], source["crop_name"], source["season"])
        key = (*group, year)
        if key in seen:
            raise ValueError("Duplicate official key")
        seen.add(key)
        area = float(source["cultivated_extent_hectares"]) * 2.4710538147
        production = float(source["production_metric_tons"]) * 1000
        if not all(math.isfinite(v) and v >= 0 for v in (area, production)):
            raise ValueError("Invalid official observation")
        groups[group].append(dict(year=year, land=area, production=production,
                                  yield_=production / area if area > 0 else np.nan))
    extra = []
    for row in development.itertuples(index=False):
        prior = sorted((r for r in groups[(row.District, row.Crop, row.Season)]
                        if r["year"] < row.Target_Year), key=lambda r: r["year"])
        previous = next((r for r in prior if r["year"] == row.Target_Year - 1), None)
        rolling = prior[-3:]
        yields = [r["yield_"] for r in rolling if math.isfinite(r["yield_"])]
        extra.append(dict(zip(ADVANCED_COLUMNS, (
            previous["land"] if previous else np.nan,
            previous["production"] if previous else np.nan,
            previous["yield_"] if previous else np.nan,
            _mean([r["land"] for r in rolling]),
            _mean([r["production"] for r in rolling]), _mean(yields),
            _trend(rolling, "land"), _trend(rolling, "production"),
            len(rolling), len(yields),
        ))))
    result = development.copy()
    for column in ADVANCED_COLUMNS:
        result[column] = [row[column] for row in extra]
    return result


if __name__ == "__main__":
    data = load_development_rows(ROOT / "data/processed/official_training_dataset.csv")
    result = build_advanced_features(data, load_prior_official(ROOT / "data/official/official_historical_2001_2025.csv"))
    print(f"Development rows retained: {len(result)}; nothing saved; test rows excluded")
    print("Rolling history counts:", result.Rolling_3Y_History_Count.value_counts().sort_index().to_dict())
    print("Missing advanced features:", result[list(ADVANCED_COLUMNS)].isna().sum().to_dict())
