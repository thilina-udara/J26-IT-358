"""Describe historical concentration indicators without scoring or labeling risk.

No-history observations are excluded, never imputed. Percentiles use linear
interpolation; standard deviations use the sample convention (ddof=1).
"""

from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
INPUT_PATH = DATA_DIRECTORY / "relative_concentration_features.csv"
OUTPUT_PATH = DATA_DIRECTORY / "risk_indicator_percentiles.csv"
INDICATORS = ["Land_Concentration_Ratio", "Production_Concentration_Ratio"]
PERCENTILES = [10, 20, 25, 33, 50, 67, 75, 80, 90]


def usable_observations(frame):
    required = ["Has_Historical_Baseline", "Crop", "District", *INDICATORS]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    baseline = frame["Has_Historical_Baseline"].astype("string").str.strip().str.lower()
    if not baseline.isin(["true", "false"]).all():
        raise ValueError("Has_Historical_Baseline must contain only True or False")
    usable = frame.loc[baseline.eq("true"), ["Crop", "District", *INDICATORS]].copy()
    if usable.empty:
        raise ValueError("No observations have historical baselines")
    usable[INDICATORS] = usable[INDICATORS].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(usable[INDICATORS].to_numpy(dtype=float)).all():
        raise ValueError("Baseline ratios must be finite and non-missing; no imputation is allowed")
    if usable[INDICATORS].lt(0).any().any():
        raise ValueError("Concentration ratios must be non-negative")
    for column in ["Crop", "District"]:
        if (usable[column].isna() | usable[column].astype(str).str.strip().eq("")).any():
            raise ValueError(f"Missing {column} in baseline observations")
    return usable


def percentile_summary(frame):
    summary = frame[INDICATORS].quantile(
        [percentile / 100 for percentile in PERCENTILES], interpolation="linear",
    ).T
    summary.index.name = "Indicator"
    summary.columns = [f"P{percentile}" for percentile in PERCENTILES]
    return summary


def descriptive_summary(frame):
    summary = frame[INDICATORS].agg(["min", "max", "mean", "median", "std"]).T
    summary.index.name = "Indicator"
    return summary


def ratio_counts(frame):
    land_above = frame[INDICATORS[0]].ge(1.0)
    production_above = frame[INDICATORS[1]].ge(1.0)
    return pd.Series({
        "Both ratios < 1.0": int((~land_above & ~production_above).sum()),
        "Land >= 1.0 and production < 1.0": int((land_above & ~production_above).sum()),
        "Land < 1.0 and production >= 1.0": int((~land_above & production_above).sum()),
        "Both ratios >= 1.0": int((land_above & production_above).sum()),
    }, name="Observations")


def print_analysis(frame, overall):
    display = {"float_format": lambda value: f"{value:.6f}"}
    print("Descriptive statistics (sample standard deviation, ddof=1):")
    print(descriptive_summary(frame).to_string(**display))
    print("Overall percentiles (linear interpolation):")
    print(overall.to_string(**display))
    land, production = (frame[column] for column in INDICATORS)
    print("Correlation between land and production concentration ratios:")
    if len(frame) < 2 or land.nunique() < 2 or production.nunique() < 2:
        print("Pearson: NaN; Spearman: NaN (insufficient variation or observations)")
    else:
        print(f"Pearson: {land.corr(production, method='pearson'):.6f}")
        # Pearson correlation of average ranks is Spearman correlation, with ties handled.
        print(f"Spearman: {land.rank(method='average').corr(production.rank(method='average')):.6f}")
    for group_column in ["Crop", "District"]:
        print(f"Percentile summaries by {group_column}:")
        for group, observations in frame.groupby(group_column, sort=True):
            print(f"{group_column}: {group} (n={len(observations)})")
            print(percentile_summary(observations).to_string(**display))
    print("Counts relative to the historical mean (ratio 1.0):")
    print(ratio_counts(frame).to_string())


def main():
    try:
        source = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")
        usable = usable_observations(source)
        print(f"Total observations: {len(source)}")
        print(f"Usable observations with historical baseline: {len(usable)}")
        print(f"Excluded observations without historical baseline: {len(source) - len(usable)}")
        overall = percentile_summary(usable)
        print_analysis(usable, overall)
        overall.reset_index().to_csv(OUTPUT_PATH, index=False)
        print(f"Saved overall percentile results to: {OUTPUT_PATH}")
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
