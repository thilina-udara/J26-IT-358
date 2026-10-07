"""Describe exploratory k=2 clusters of synthetic/prototype cultivation groups.

Cluster identifiers are arbitrary and carry no risk meaning. All input columns
are preserved; only the three specified features enter scaling and clustering.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
INPUT_PATH = DATA_DIRECTORY / "clustering_features.csv"
OUTPUT_PATH = DATA_DIRECTORY / "kmeans_clustered_data.csv"
IDENTIFIER_COLUMNS = ["District", "Year", "Season", "Crop"]
FEATURE_COLUMNS = [
    "Total_Land_Acres",
    "Total_Expected_Production_kg",
    "Average_Expected_Yield_kg_per_Acre",
]


def interpret_kmeans(frame):
    """Return annotated rows and centers in standardized and original scales."""
    missing = [column for column in IDENTIFIER_COLUMNS + FEATURE_COLUMNS
               if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if "Cluster" in frame.columns:
        raise ValueError("Input already contains Cluster; refusing to overwrite it")
    for column in IDENTIFIER_COLUMNS:
        if (frame[column].isna() | frame[column].astype(str).str.strip().eq("")).any():
            raise ValueError(f"Missing identifier values in {column}")
    if frame.duplicated(IDENTIFIER_COLUMNS).any():
        raise ValueError("Duplicate District-Year-Season-Crop groups")
    features = frame[FEATURE_COLUMNS].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError("Features must be finite and non-missing")
    if features.lt(0).any().any():
        raise ValueError("Features must be non-negative")
    if len(features.drop_duplicates()) < 2:
        raise ValueError("At least two distinct feature vectors are required")

    scaler = StandardScaler()
    standardized = scaler.fit_transform(features)
    model = KMeans(n_clusters=2, random_state=42, n_init=20)
    labels = model.fit_predict(standardized)
    if len(np.unique(labels)) != 2:
        raise ValueError("K-Means did not produce two distinct clusters")
    clustered = frame.copy()
    clustered["Cluster"] = labels
    centers = pd.DataFrame(model.cluster_centers_, columns=FEATURE_COLUMNS)
    centers.index.name = "Cluster"
    original_centers = pd.DataFrame(
        scaler.inverse_transform(model.cluster_centers_), columns=FEATURE_COLUMNS,
    )
    original_centers.index.name = "Cluster"
    return clustered, centers, original_centers


def print_interpretation(clustered, centers, original_centers):
    print("Cluster 0 and Cluster 1 are arbitrary identifiers, not risk levels.")
    print("Cluster sizes (aggregated cultivation groups):")
    print(clustered.groupby("Cluster").size().rename("Group_Count").to_string())
    # Summarize original-scale values rather than standardized model inputs.
    numeric = clustered[FEATURE_COLUMNS].apply(pd.to_numeric, errors="raise")
    numeric["Cluster"] = clustered["Cluster"]
    summary = numeric.groupby("Cluster")[FEATURE_COLUMNS].agg(["mean", "median"])
    summary.columns = [f"{feature}_{statistic}" for feature, statistic in summary.columns]
    print("Original-scale feature means and medians:")
    print(summary.to_string(float_format=lambda value: f"{value:.6f}"))
    for column in ("Crop", "District", "Season", "Year"):
        print(f"{column} x Cluster count table:")
        print(pd.crosstab(clustered[column], clustered["Cluster"]).to_string())
    print("Standardized cluster centers:")
    print(centers.to_string(float_format=lambda value: f"{value:.6f}"))
    print("Inverse-transformed original-scale cluster centers:")
    print(original_centers.to_string(float_format=lambda value: f"{value:.6f}"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    try:
        protected = [args.input, INPUT_PATH,
                     DATA_DIRECTORY / "cultivation_data_2020_2025.csv",
                     DATA_DIRECTORY / "processed_cultivation_data.csv",
                     DATA_DIRECTORY / "kmeans_evaluation.csv",
                     DATA_DIRECTORY / "dbscan_evaluation.csv"]
        for path in protected:
            if args.output.resolve() == path.resolve() or (
                args.output.exists() and path.exists() and args.output.samefile(path)
            ):
                raise ValueError("Output must not overwrite source datasets or evaluation results")
        frame = pd.read_csv(args.input, encoding="utf-8-sig")
        clustered, centers, original_centers = interpret_kmeans(frame)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        clustered.to_csv(args.output, index=False)
        print("K-Means interpretation: n_clusters=2, random_state=42, n_init=20")
        print_interpretation(clustered, centers, original_centers)
        print(f"Saved {len(clustered)} rows to: {args.output.resolve()}")
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
