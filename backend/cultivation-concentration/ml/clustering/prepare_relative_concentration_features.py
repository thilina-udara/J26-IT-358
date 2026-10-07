"""Build prior-year concentration baselines for synthetic/prototype groups.

One prior annual observation is the minimum history required. Baselines are
unweighted means within District/Season/Crop, using strictly earlier years.
No-history rows remain present with NaN baselines and derived values. A zero
baseline remains zero, while its ratio and deviation remain NaN.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
INPUT_PATH = DATA_DIRECTORY / "clustering_features.csv"
OUTPUT_PATH = DATA_DIRECTORY / "relative_concentration_features.csv"
HISTORY_GROUPS = ["District", "Season", "Crop"]
SOURCES = {
    "Land": ("Total_Land_Acres", "Historical_Mean_Land_Acres"),
    "Production": ("Total_Expected_Production_kg", "Historical_Mean_Production_kg"),
}
RELATIVE_COLUMNS = [
    "Land_Concentration_Ratio", "Production_Concentration_Ratio",
    "Land_Deviation_Percent", "Production_Deviation_Percent",
]
DERIVED_COLUMNS = ["Historical_Mean_Land_Acres", "Historical_Mean_Production_kg"] + RELATIVE_COLUMNS
STATUS_COLUMNS = ["Prior_History_Count", "Has_Historical_Baseline", "Historical_Baseline_Status"]


def prepare_relative_features(frame):
    required = HISTORY_GROUPS + ["Year"] + [source for source, _ in SOURCES.values()]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Input contains no observations")
    if set(DERIVED_COLUMNS + STATUS_COLUMNS).intersection(frame.columns):
        raise ValueError("Input already contains historical derived columns")
    for column in HISTORY_GROUPS + ["Year"]:
        if (frame[column].isna() | frame[column].astype(str).str.strip().eq("")).any():
            raise ValueError(f"Missing grouping value in {column}")
    if frame.duplicated(HISTORY_GROUPS + ["Year"]).any():
        raise ValueError("Duplicate District-Year-Season-Crop combinations")

    # Work with positional indices while retaining original columns and row order.
    output = frame.reset_index(drop=True).copy()
    numeric = output[required].copy()
    for column in ["Year"] + [source for source, _ in SOURCES.values()]:
        values = pd.to_numeric(numeric[column], errors="raise")
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"{column} must be finite and non-missing")
        if column == "Year":
            if values.mod(1).ne(0).any():
                raise ValueError("Year must be an integer")
        elif values.lt(0).any():
            raise ValueError(f"{column} must be non-negative")
        numeric[column] = values
    # Catch equivalent numeric years represented differently in custom inputs.
    if numeric.duplicated(HISTORY_GROUPS + ["Year"]).any():
        raise ValueError("Duplicate District-Year-Season-Crop combinations")
    ordered = numeric.sort_values(HISTORY_GROUPS + ["Year"])
    output["Prior_History_Count"] = ordered.groupby(HISTORY_GROUPS).cumcount().reindex(output.index)
    output["Has_Historical_Baseline"] = output["Prior_History_Count"].gt(0)
    for prefix, (source, baseline) in SOURCES.items():
        # Shift BEFORE expanding: the current year cannot enter its own mean.
        historical = ordered.groupby(HISTORY_GROUPS)[source].transform(
            lambda values: values.shift(1).expanding(min_periods=1).mean()
        )
        output[baseline] = historical.reindex(output.index)
        denominator = output[baseline].where(output[baseline].gt(0))
        output[f"{prefix}_Concentration_Ratio"] = numeric[source] / denominator
        output[f"{prefix}_Deviation_Percent"] = (
            (numeric[source] - output[baseline]) / denominator * 100
        )
    output["Historical_Baseline_Status"] = np.where(
        output["Has_Historical_Baseline"], "Available", "No_Prior_History",
    )
    zero_baseline = output["Has_Historical_Baseline"] & (
        output["Historical_Mean_Land_Acres"].eq(0)
        | output["Historical_Mean_Production_kg"].eq(0)
    )
    output.loc[zero_baseline, "Historical_Baseline_Status"] = "Zero_Baseline_Relative_Feature_Undefined"
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    try:
        # Protect existing datasets, including previous experiment outputs.
        protected = [args.input] + [path for path in DATA_DIRECTORY.glob("*.csv")
                                   if path.name != OUTPUT_PATH.name]
        for path in protected:
            if args.output.resolve() == path.resolve() or (
                args.output.exists() and path.exists() and args.output.samefile(path)
            ):
                raise ValueError("Output must not overwrite an existing source dataset")
        frame = pd.read_csv(args.input, encoding="utf-8-sig")
        output = prepare_relative_features(frame)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        output.to_csv(args.output, index=False, na_rep="NaN")
        available = int(output["Has_Historical_Baseline"].sum())
        print(f"Total observations: {len(output)}")
        print(f"Observations with historical baseline: {available}")
        print(f"Observations without historical baseline: {len(output) - available}")
        print("Minimum history: 1 prior-year observation within District/Season/Crop")
        print("Historical baseline statuses:")
        print(output["Historical_Baseline_Status"].value_counts().to_string())
        print("Missing values by derived feature:")
        print(output[DERIVED_COLUMNS].isna().sum().to_string())
        print("Descriptive statistics for relative/deviation features:")
        print(output[RELATIVE_COLUMNS].describe().to_string())
        print("First 15 rows (original input order):")
        print(output.head(15).to_string(index=False))
        print("Relative feature summary by Crop (NaN values excluded from statistics):")
        print(output.groupby("Crop")[RELATIVE_COLUMNS].agg(
            ["count", "mean", "median", "std", "min", "max"],
        ).to_string())
        print(f"Saved to: {args.output.resolve()}")
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
