"""Compare clustering on historical concentration ratios without selecting a model.

Rows without historical baselines are excluded, never imputed. DBSCAN metrics
describe non-noise observations only; noise is not a risk category.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
INPUT_PATH = DATA_DIRECTORY / "relative_concentration_features.csv"
KMEANS_OUTPUT_PATH = DATA_DIRECTORY / "relative_kmeans_evaluation.csv"
DBSCAN_OUTPUT_PATH = DATA_DIRECTORY / "relative_dbscan_evaluation.csv"
FEATURE_COLUMNS = ["Land_Concentration_Ratio", "Production_Concentration_Ratio"]
EXPECTED_OBSERVATIONS = 120
EPS_VALUES = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
MIN_SAMPLES_VALUES = (3, 4, 5, 6)
METRICS = {
    "Silhouette_Score": silhouette_score,
    "Davies_Bouldin_Index": davies_bouldin_score,
    "Calinski_Harabasz_Score": calinski_harabasz_score,
}


def prepare_features(frame):
    """Filter before scaling; reject undefined ratios rather than filling them."""
    required = ["Has_Historical_Baseline", *FEATURE_COLUMNS]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    baseline = frame["Has_Historical_Baseline"].astype("string").str.strip().str.lower()
    if not baseline.isin(["true", "false"]).all():
        raise ValueError("Has_Historical_Baseline must contain only True or False")
    retained = frame.loc[baseline.eq("true")]
    print(f"Total observations: {len(frame)}")
    print(f"Observations with historical baseline: {len(retained)}")
    print(f"Excluded observations without historical baseline: {len(frame) - len(retained)}")
    if len(retained) != EXPECTED_OBSERVATIONS:
        raise ValueError(f"Expected exactly {EXPECTED_OBSERVATIONS} baseline observations, got {len(retained)}")
    features = retained[FEATURE_COLUMNS].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError("Baseline observations contain missing or non-finite ratios; no imputation is allowed")
    if features.lt(0).any().any():
        raise ValueError("Concentration ratios must be non-negative")
    if len(features.drop_duplicates()) < 8:
        raise ValueError("At least 8 distinct ratio vectors are required for K-Means")
    return StandardScaler().fit_transform(features)


def clustering_metrics(observations, labels):
    """Undefined metrics remain NaN, including zero/one-cluster cases."""
    scores = {name: np.nan for name in METRICS}
    if 2 <= len(np.unique(labels)) < len(observations):
        for name, metric in METRICS.items():
            scores[name] = float(metric(observations, labels))
    return scores


def evaluate_kmeans(scaled):
    results = []
    for k in range(2, 9):
        model = KMeans(n_clusters=k, random_state=42, n_init=20)
        labels = model.fit_predict(scaled)
        if len(np.unique(labels)) != k:
            raise ValueError(f"K-Means produced fewer than {k} clusters")
        results.append({"k": k, "Inertia": model.inertia_,
                        **clustering_metrics(scaled, labels)})
    return pd.DataFrame(results)


def evaluate_dbscan(scaled):
    results = []
    for eps in EPS_VALUES:
        for min_samples in MIN_SAMPLES_VALUES:
            labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(scaled)
            retained = labels != -1
            noise_count = int((~retained).sum())
            results.append({
                "eps": eps,
                "min_samples": min_samples,
                "Number_of_Clusters": len(np.unique(labels[retained])),
                "Number_of_Noise_Points": noise_count,
                "Noise_Percentage": noise_count / len(scaled) * 100,
                **clustering_metrics(scaled[retained], labels[retained]),
            })
    return pd.DataFrame(results)


def print_comparisons(kmeans, dbscan):
    display = {"index": False, "float_format": lambda value: f"{value:.6f}"}
    print("Complete K-Means comparison (random_state=42, n_init=20):")
    print(kmeans.to_string(**display))
    print("Best K-Means metric results:")
    for column, highest in [("Inertia", False), ("Silhouette_Score", True),
                            ("Davies_Bouldin_Index", False), ("Calinski_Harabasz_Score", True)]:
        best = kmeans[column].max() if highest else kmeans[column].min()
        candidates = kmeans.loc[kmeans[column].eq(best), "k"].tolist()
        direction = "Highest" if highest else "Lowest"
        print(f"{direction} {column}: k={candidates}, value={best:.6f}")
    print("Inertia normally decreases with k; its minimum alone does not determine k.")
    valid = dbscan.dropna(subset=list(METRICS)).sort_values(
        ["Silhouette_Score", "eps", "min_samples"], ascending=[False, True, True],
    )
    print(f"Valid DBSCAN configurations ranked by silhouette ({len(valid)}):")
    if valid.empty:
        print("No configuration has at least two valid non-noise clusters.")
    else:
        print(valid.to_string(**display))
        print("Highest-silhouette DBSCAN configuration (ties ordered by eps, min_samples):")
        print(valid.head(1).to_string(**display))
        print(f"Noise percentage for this configuration: {valid.iloc[0]['Noise_Percentage']:.6f}%")
    print("DBSCAN metrics exclude noise; interpret silhouette alongside noise percentage.")
    print("No final clustering algorithm or cluster count has been selected.")


def main():
    try:
        frame = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")
        scaled = prepare_features(frame)
        print(f"StandardScaler features: {', '.join(FEATURE_COLUMNS)}")
        kmeans = evaluate_kmeans(scaled)
        dbscan = evaluate_dbscan(scaled)
        kmeans.to_csv(KMEANS_OUTPUT_PATH, index=False)
        dbscan.to_csv(DBSCAN_OUTPUT_PATH, index=False, na_rep="NaN")
        print_comparisons(kmeans, dbscan)
        print(f"Saved to: {KMEANS_OUTPUT_PATH}")
        print(f"Saved to: {DBSCAN_OUTPUT_PATH}")
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
