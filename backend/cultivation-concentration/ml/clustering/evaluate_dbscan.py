"""Evaluate exploratory DBSCAN configurations; metrics exclude noise points.

Silhouette rankings describe retained observations only and must be interpreted
alongside noise percentage. No final model, cluster labels, or risk labels are
saved. DBSCAN noise is not a risk category.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
INPUT_PATH = DATA_DIRECTORY / "clustering_features.csv"
OUTPUT_PATH = DATA_DIRECTORY / "dbscan_evaluation.csv"
FEATURE_COLUMNS = [
    "Total_Land_Acres",
    "Total_Expected_Production_kg",
    "Average_Expected_Yield_kg_per_Acre",
]
EPS_VALUES = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
MIN_SAMPLES_VALUES = (3, 4, 5, 6)
METRICS = {
    "Silhouette_Score": silhouette_score,
    "Davies_Bouldin_Index": davies_bouldin_score,
    "Calinski_Harabasz_Score": calinski_harabasz_score,
}


def non_noise_metrics(scaled, labels):
    """Return NaN for undefined metrics, including all-noise/one-cluster cases."""
    retained = labels != -1
    observations = scaled[retained]
    cluster_labels = labels[retained]
    cluster_count = len(np.unique(cluster_labels))
    scores = {name: np.nan for name in METRICS}
    if 2 <= cluster_count < len(observations):
        for name, metric in METRICS.items():
            try:
                score = float(metric(observations, cluster_labels))
                scores[name] = score if np.isfinite(score) else np.nan
            except ValueError:
                # A mathematically undefined metric must not stop the grid.
                pass
    return scores


def evaluate_dbscan(frame):
    missing = [column for column in FEATURE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required features: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Input contains no records")
    features = frame[FEATURE_COLUMNS].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError("Clustering features must contain only finite, non-missing values")
    if features.lt(0).any().any():
        raise ValueError("Clustering features must be non-negative")
    # Fit once on the complete input, as in the K-Means experiment.
    scaled = StandardScaler().fit_transform(features)
    results = []
    for eps in EPS_VALUES:
        for min_samples in MIN_SAMPLES_VALUES:
            labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(scaled)
            noise_count = int(np.count_nonzero(labels == -1))
            results.append({
                "eps": eps,
                "min_samples": min_samples,
                "Number_of_Clusters": len(np.unique(labels[labels != -1])),
                "Number_of_Noise_Points": noise_count,
                "Noise_Percentage": noise_count / len(frame) * 100,
                **non_noise_metrics(scaled, labels),
            })
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    try:
        protected = [args.input, INPUT_PATH,
                     DATA_DIRECTORY / "processed_cultivation_data.csv",
                     DATA_DIRECTORY / "cultivation_data_2020_2025.csv",
                     DATA_DIRECTORY / "kmeans_evaluation.csv"]
        for path in protected:
            if args.output.resolve() == path.resolve() or (
                args.output.exists() and path.exists() and args.output.samefile(path)
            ):
                raise ValueError("Output must not overwrite source datasets or K-Means results")
        frame = pd.read_csv(args.input, encoding="utf-8-sig")
        results = evaluate_dbscan(frame)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        results.to_csv(args.output, index=False, na_rep="NaN")
        print(f"Input records: {len(frame)}")
        print(f"Standardized features: {', '.join(FEATURE_COLUMNS)}")
        print("Comparison table (metrics use non-noise observations only):")
        display = {"index": False, "float_format": lambda value: f"{value:.6f}"}
        print(results.to_string(**display))
        valid = results.dropna(subset=list(METRICS)).sort_values(
            ["Silhouette_Score", "eps", "min_samples"],
            ascending=[False, True, True],
        )
        print(f"Valid configurations ranked by Silhouette Score ({len(valid)}):")
        if valid.empty:
            print("No configuration has valid values for all three evaluation metrics.")
        else:
            print(valid.to_string(**display))
            print("Highest-silhouette valid configuration (ties ordered by eps, min_samples):")
            print(valid.head(1).to_string(**display))
        print("Rankings are exploratory; no final model has been selected.")
        print("Interpret scores alongside noise percentage; noise is not a risk label.")
        print(f"Saved to: {args.output.resolve()}")
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
