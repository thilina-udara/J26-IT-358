"""Apply Scheme B prototype operational thresholds to existing Risk_Score values.

The historical baseline is 1.0, and Medium is the symmetric +/-25% band.
These thresholds are not universally validated agricultural thresholds and
were not learned by machine learning. No model is trained by this script.
"""

from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
INPUT_PATH = DATA_DIRECTORY / "risk_score_analysis.csv"
OUTPUT_PATH = DATA_DIRECTORY / "labeled_risk_data.csv"
LEVELS = ["Low", "Medium", "High"]
EXPECTED_COUNTS = {"Low": 39, "Medium": 57, "High": 24}
GROUPS = ["Crop", "District", "Year", "Season"]


def assign_risk_levels(scores):
    """Apply exact Scheme B boundaries without rounding scores."""
    numeric = pd.to_numeric(scores, errors="raise")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Risk_Score must be finite and non-missing")
    labels = pd.Series(index=scores.index, dtype="object", name="Risk_Level")
    labels.loc[numeric.lt(0.75)] = "Low"
    labels.loc[numeric.ge(0.75) & numeric.le(1.25)] = "Medium"
    labels.loc[numeric.gt(1.25)] = "High"
    if labels.isna().any():
        raise ValueError("Missing Risk_Level values after applying Scheme B")
    return labels


def create_risk_labels(frame):
    required = ["Risk_Score"] + GROUPS
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if len(frame) != 120:
        raise ValueError(f"Expected 120 observations, found {len(frame)}")
    if "Risk_Level" in frame.columns:
        raise ValueError("Input already contains Risk_Level")
    for group in GROUPS:
        if (frame[group].isna() | frame[group].astype(str).str.strip().eq("")).any():
            raise ValueError(f"Missing grouping value in {group}")
    output = frame.copy()
    output["Risk_Level"] = assign_risk_levels(frame["Risk_Score"])
    counts = output["Risk_Level"].value_counts().reindex(LEVELS, fill_value=0)
    if counts.to_dict() != EXPECTED_COUNTS:
        raise ValueError(
            f"Risk_Level counts do not match: expected {EXPECTED_COUNTS}, "
            f"found {counts.to_dict()}"
        )
    return output


def print_summary(output):
    print("Scheme B: prototype operational thresholds, not learned by ML")
    print("Not universally validated agricultural thresholds")
    print("Low: score < 0.75; Medium: 0.75 <= score <= 1.25; High: score > 1.25")
    print("Medium is the symmetric +/-25% operational band around baseline 1.0")
    print(f"Total observations: {len(output)}")
    counts = output["Risk_Level"].value_counts().reindex(LEVELS, fill_value=0)
    print("Risk_Level counts:")
    print(counts.to_string())
    print("Risk_Level percentages:")
    print((counts / len(output) * 100).rename("Percentage").to_string())
    for group in GROUPS:
        print(f"Risk_Level counts by {group}:")
        print(pd.crosstab(output[group], output["Risk_Level"])
              .reindex(columns=LEVELS, fill_value=0).to_string())
    print(f"Missing Risk_Level values: {int(output['Risk_Level'].isna().sum())}")
    print("Verified expected counts: Low = 39, Medium = 57, High = 24")


def main():
    # Validation errors propagate and prevent writing an invalid labeled dataset.
    frame = pd.read_csv(INPUT_PATH, encoding="utf-8-sig", float_precision="round_trip")
    output = create_risk_labels(frame)
    for source in DATA_DIRECTORY.glob("*.csv"):
        if source.name != OUTPUT_PATH.name and OUTPUT_PATH.exists() and OUTPUT_PATH.samefile(source):
            raise ValueError("Output must not overwrite an existing source dataset")
    output.to_csv(OUTPUT_PATH, index=False)
    print_summary(output)
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
