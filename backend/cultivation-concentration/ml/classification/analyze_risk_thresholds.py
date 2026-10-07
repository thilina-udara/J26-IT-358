"""Compare candidate thresholds only; do not select a final risk scheme.

Thresholds are supplied candidates, not learned by ML. Scores are read as-is.
The comparison CSV contains overall and grouped summaries, with percentages
calculated within each group and zero-count risk levels explicitly included.
"""

from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
INPUT_PATH = DATA_DIRECTORY / "risk_score_analysis.csv"
OUTPUT_PATH = DATA_DIRECTORY / "risk_threshold_sensitivity.csv"
SCHEMES = {"A": (0.80, 1.20), "B": (0.75, 1.25), "C": (0.70, 1.30)}
LEVELS = ["Low", "Medium", "High"]
GROUPS = ["Crop", "District", "Year", "Season"]


def candidate_levels(scores, lower, upper):
    """Both endpoints belong to Medium; compare unrounded scores."""
    return pd.Series(
        np.select([scores.lt(lower), scores.gt(upper)], ["Low", "High"], default="Medium"),
        index=scores.index,
    )


def summarize(frame):
    summary = frame.groupby("Candidate_Risk_Level")["Risk_Score"].agg(
        Count="count", Mean_Risk_Score="mean", Minimum_Risk_Score="min",
        Maximum_Risk_Score="max",
    ).reindex(LEVELS)
    summary["Count"] = summary["Count"].fillna(0).astype(int)
    summary.insert(1, "Percentage", summary["Count"] / len(frame) * 100)
    summary.index.name = "Risk_Level"
    return summary


def analyze_thresholds(frame):
    required = ["Risk_Score"] + GROUPS
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if len(frame) != 120:
        raise ValueError(f"Expected all 120 usable observations, found {len(frame)}")
    scores = pd.to_numeric(frame["Risk_Score"], errors="raise")
    if not np.isfinite(scores.to_numpy(dtype=float)).all():
        raise ValueError("Risk_Score must be finite and non-missing; no rows were dropped")
    for group in GROUPS:
        if (frame[group].isna() | frame[group].astype(str).str.strip().eq("")).any():
            raise ValueError(f"Missing grouping value in {group}")

    comparisons = []
    print("Threshold sensitivity analysis only; candidates are not learned by ML.")
    print("No final threshold scheme is selected. Existing Risk_Score values are unchanged.")
    print(f"Observations analyzed per scheme: {len(frame)}")
    for scheme, (lower, upper) in SCHEMES.items():
        candidate = frame.copy()
        candidate["Risk_Score"] = scores
        candidate["Candidate_Risk_Level"] = candidate_levels(scores, lower, upper)
        print(f"\nScheme {scheme}: Low < {lower:.2f}; Medium {lower:.2f} <= score <= {upper:.2f}; High > {upper:.2f}")
        overall = summarize(candidate)
        print("Overall counts, percentages, and Risk_Score statistics:")
        print(overall.to_string())
        tables = [("Overall", "All", overall)]
        for group in GROUPS:
            counts = pd.crosstab(candidate[group], candidate["Candidate_Risk_Level"])
            counts = counts.reindex(columns=LEVELS, fill_value=0)
            print(f"Risk-level counts by {group}:")
            print(counts.to_string())
            for value, subset in candidate.groupby(group, sort=True):
                tables.append((group, value, summarize(subset)))
        for grouping, value, table in tables:
            table = table.reset_index()
            table.insert(0, "Group_Value", value)
            table.insert(0, "Grouping", grouping)
            table.insert(0, "Upper_Threshold", upper)
            table.insert(0, "Lower_Threshold", lower)
            table.insert(0, "Scheme", scheme)
            comparisons.append(table)
    return pd.concat(comparisons, ignore_index=True)


def main():
    try:
        frame = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")
        comparison = analyze_thresholds(frame)
        # Write only the designated sensitivity output, protecting source CSVs.
        for source in DATA_DIRECTORY.glob("*.csv"):
            if source.name != OUTPUT_PATH.name and OUTPUT_PATH.exists() and OUTPUT_PATH.samefile(source):
                raise ValueError("Output must not overwrite an existing source dataset")
        comparison.to_csv(OUTPUT_PATH, index=False)
        print(f"\nSaved comparison to: {OUTPUT_PATH}")
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
