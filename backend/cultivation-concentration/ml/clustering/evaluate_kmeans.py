"""Compare exploratory K-Means metrics without selecting k or assigning risk.

Only three standardized numeric features enter the model. Source identifiers
remain in the input CSV for later interpretation; cluster labels are not saved.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
INPUT_PATH = DATA_DIRECTORY / "clustering_features.csv"
OUTPUT_PATH = DATA_DIRECTORY / "kmeans_evaluation.csv"
FEATURE_COLUMNS = [
    "Total_Land_Acres",
    "Total_Expected_Production_kg",
    "Average_Expected_Yield_kg_per_Acre",
]
RANDOM_STATE = 42
N_INIT = 20


def evaluate_kmeans(frame):
    missing = [column for column in FEATURE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required features: {', '.join(missing)}")
    # No identifiers or other numeric columns are passed to the scaler/model.
    features = frame[FEATURE_COLUMNS].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError("Clustering features must contain only finite, non-missing values")
    if features.lt(0).any().any():
        raise ValueError("Clustering features must be non-negative")
    if len(features) <= 8:
        raise ValueError("At least 9 records are required to evaluate k=2 through 8")
    if len(features.drop_duplicates()) < 8:
        raise ValueError("At least 8 distinct feature vectors are required")

    scaled = StandardScaler().fit_transform(features)
    results = []
    for k in range(2, 9):
        model = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=N_INIT)
        labels = model.fit_predict(scaled)
        if len(np.unique(labels)) != k:
            raise ValueError(f"K-Means produced fewer than {k} distinct clusters")
        results.append({
            "k": k,
            "Inertia": model.inertia_,
            "Silhouette_Score": silhouette_score(scaled, labels),
            "Davies_Bouldin_Index": davies_bouldin_score(scaled, labels),
            "Calinski_Harabasz_Score": calinski_harabasz_score(scaled, labels),
        })
    return pd.DataFrame(results)


def print_preferred_k(results, column, highest):
    best = results[column].max() if highest else results[column].min()
    candidates = results.loc[results[column].eq(best), "k"].tolist()
    direction = "Highest" if highest else "Lowest"
    print(f"{direction} {column}: k={', '.join(map(str, candidates))} (value={best:.6f})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    try:
        protected = [args.input, INPUT_PATH, DATA_DIRECTORY / "processed_cultivation_data.csv",
                     DATA_DIRECTORY / "cultivation_data_2020_2025.csv"]
        for path in protected:
            if args.output.resolve() == path.resolve() or (
                args.output.exists() and path.exists() and args.output.samefile(path)
            ):
                raise ValueError("Output must not overwrite a source dataset")
        frame = pd.read_csv(args.input, encoding="utf-8-sig")
        results = evaluate_kmeans(frame)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        results.to_csv(args.output, index=False)
        print(f"Input records: {len(frame)}")
        print(f"Standardized features: {', '.join(FEATURE_COLUMNS)}")
        print(f"K-Means settings: random_state={RANDOM_STATE}, n_init={N_INIT}")
        print(results.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
        print_preferred_k(results, "Silhouette_Score", highest=True)
        print_preferred_k(results, "Davies_Bouldin_Index", highest=False)
        print_preferred_k(results, "Calinski_Harabasz_Score", highest=True)
        print("Metric preferences are exploratory evidence, not proof of the scientifically correct k.")
        print("Interpret the results before selecting a cluster count; no final k has been selected.")
        print(f"Saved to: {args.output.resolve()}")
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
