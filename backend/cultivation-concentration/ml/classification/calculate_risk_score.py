"""Analyze a candidate equal-weight cultivation score without assigning labels.

The 0.5 / 0.5 weights are a candidate methodology, not learned by ML.
Percentiles describe the score distribution; they are not risk thresholds.
"""

from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
INPUT_PATH = DATA_DIRECTORY / "relative_concentration_features.csv"
OUTPUT_PATH = DATA_DIRECTORY / "risk_score_analysis.csv"
RATIO_COLUMNS = ["Land_Concentration_Ratio", "Production_Concentration_Ratio"]
PERCENTILES = [10, 20, 25, 33, 50, 67, 75, 80, 90]
STATISTICS = ["count", "min", "max", "mean", "median", "std"]


def calculate_risk_score(frame):
    """Retain every baseline-eligible row and append the exact candidate score."""
    required = ["Has_Historical_Baseline", "Crop", "District"] + RATIO_COLUMNS
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    output = frame.loc[frame["Has_Historical_Baseline"].eq(True)].copy()
    if len(output) != 120:
        raise ValueError(f"Expected 120 baseline-eligible observations, found {len(output)}")
    ratios = output[RATIO_COLUMNS].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(ratios.to_numpy(dtype=float)).all():
        raise ValueError("Eligible ratios must be finite and non-missing; no rows were dropped")
    for column in ["Crop", "District"]:
        if (output[column].isna() | output[column].astype(str).str.strip().eq("")).any():
            raise ValueError(f"Eligible observations have missing {column} values")
    output["Risk_Score"] = (
        0.5 * ratios["Land_Concentration_Ratio"]
        + 0.5 * ratios["Production_Concentration_Ratio"]
    )
    return output


def print_analysis(output):
    scores = output["Risk_Score"]
    print("Candidate equal-weight methodology (weights not learned by ML)")
    print("Risk_Score = 0.5 * Land_Concentration_Ratio + 0.5 * Production_Concentration_Ratio")
    print(f"Usable observations retained: {len(output)}")
    print("Descriptive statistics (sample standard deviation, ddof=1):")
    print(scores.agg(STATISTICS).to_string())
    percentiles = scores.quantile([value / 100 for value in PERCENTILES], interpolation="linear")
    percentiles.index = [f"P{value}" for value in PERCENTILES]
    print("Percentiles (linear interpolation; descriptive only, not thresholds):")
    print(percentiles.to_string())
    for group in ["Crop", "District"]:
        print(f"Risk_Score statistics by {group} (sample standard deviation):")
        print(output.groupby(group)["Risk_Score"].agg(STATISTICS).to_string())
    print("Counts relative to 1.0 (exact equality, no rounding or tolerance):")
    print(f"Risk_Score < 1.0: {int(scores.lt(1.0).sum())}")
    print(f"Risk_Score == 1.0: {int(scores.eq(1.0).sum())}")
    print(f"Risk_Score > 1.0: {int(scores.gt(1.0).sum())}")
    for ascending, label in [(False, "highest"), (True, "lowest")]:
        print(f"10 observations with the {label} Risk_Score:")
        print(output.sort_values("Risk_Score", ascending=ascending, kind="stable")
              .head(10).to_string(index=False))


def main():
    try:
        frame = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")
        output = calculate_risk_score(frame)
        # Only the designated new analysis output may be written.
        if OUTPUT_PATH.exists() and OUTPUT_PATH.samefile(INPUT_PATH):
            raise ValueError("Output must not overwrite the input dataset")
        output.to_csv(OUTPUT_PATH, index=False)
        print_analysis(output)
        print(f"Saved to: {OUTPUT_PATH}")
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
