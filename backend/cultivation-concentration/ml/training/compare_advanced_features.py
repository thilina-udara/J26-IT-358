"""Fixed RF feature experiment; development rows only, no saved artifacts."""
import hashlib
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, classification_report, confusion_matrix

from ml.preprocessing.build_advanced_features import (
    ROOT, ADVANCED_COLUMNS, load_development_rows, load_prior_official, build_advanced_features,
)
from ml.training.compare_models import FEATURE_COLUMNS, NUMERIC, CATEGORICAL, LABELS, LABEL_ENCODING, make_models
from ml.training.tune_random_forest import expanding_window_splits


def evaluate(train, validation, advanced=False):
    if not train.Target_Year.between(2002, 2021).all() or not validation.Target_Year.between(2002, 2023).all():
        raise ValueError("Test rows forbidden")
    if train.Target_Year.max() >= validation.Target_Year.min():
        raise ValueError("Training must precede evaluation years")
    features = list(FEATURE_COLUMNS) + (list(ADVANCED_COLUMNS) if advanced else [])
    model = clone(make_models()["Random Forest"])
    if advanced:
        model.set_params(preprocessing=ColumnTransformer([
            ("numeric", SimpleImputer(strategy="median", keep_empty_features=True), NUMERIC + list(ADVANCED_COLUMNS)),
            ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
        ]))
    model.fit(train[features], train.Risk_Label.map(LABEL_ENCODING))
    predicted = model.predict(validation[features])
    actual = validation.Risk_Label.map(LABEL_ENCODING)
    report = classification_report(actual, predicted, labels=[0, 1, 2], target_names=list(LABELS), output_dict=True, zero_division=0)
    return dict(accuracy=accuracy_score(actual, predicted), balanced_accuracy=balanced_accuracy_score(actual, predicted),
                macro_f1=f1_score(actual, predicted, labels=[0, 1, 2], average="macro", zero_division=0),
                high_precision=report["High"]["precision"], high_recall=report["High"]["recall"],
                confusion_matrix=confusion_matrix(actual, predicted, labels=[0, 1, 2]))


def print_results(title, results):
    print(title)
    print("Features  Accuracy  Balanced Accuracy  Macro F1  High Precision  High Recall")
    for name, metrics in results.items():
        print(f"{name:9} " + "  ".join(f"{metrics[key]:.4f}" for key in ("accuracy", "balanced_accuracy", "macro_f1", "high_precision", "high_recall")))
        print("Confusion matrix: actual rows/predicted columns; Low, Medium, High")
        print(metrics["confusion_matrix"])


def main():
    training_path = ROOT / "data/processed/official_training_dataset.csv"
    official_path = ROOT / "data/official/official_historical_2001_2025.csv"
    before = {p: hashlib.sha256(p.read_bytes()).digest() for p in (training_path, official_path)}
    data = build_advanced_features(load_development_rows(training_path), load_prior_official(official_path))
    train = data.loc[data.Target_Year.between(2002, 2021)]
    validation = data.loc[data.Target_Year.between(2022, 2023)]
    print(f"Development rows: {len(data)}; train={len(train)}, validation={len(validation)}; test features never inspected or built")
    print("Rolling history counts:", data.Rolling_3Y_History_Count.value_counts().sort_index().to_dict())
    print("Missing advanced features:", data[list(ADVANCED_COLUMNS)].isna().sum().to_dict())
    fold_metrics = {"Original": [], "Advanced": []}
    for i, (a, b) in enumerate(expanding_window_splits(train), 1):
        results = {name: evaluate(train.iloc[a], train.iloc[b], name == "Advanced") for name in fold_metrics}
        print_results(f"Expanding-window fold {i}", results)
        for name in fold_metrics:
            fold_metrics[name].append(results[name])
    print("Mean expanding-window CV (equal fold weights):")
    for name, folds in fold_metrics.items():
        print(name, {key: round(float(np.mean([r[key] for r in folds])), 4) for key in ("accuracy", "balanced_accuracy", "macro_f1", "high_precision", "high_recall")})
    results = {name: evaluate(train, validation, name == "Advanced") for name in fold_metrics}
    print_results("2022-2023 validation", results)
    delta = results["Advanced"]["macro_f1"] - results["Original"]["macro_f1"]
    print(f"Advanced validation Macro F1 change: {delta:+.4f}; " + ("worse" if delta < 0 else "better" if delta > 0 else "unchanged"))
    print("Validation has been used in earlier experiments; repeated comparisons do not establish independent generalization. CV windows are year-by-year forecasts using all observations from strictly earlier years.")
    print("Operational concentration labels, not observed oversupply. No artifacts saved; test unevaluated.")
    assert all(hashlib.sha256(p.read_bytes()).digest() == digest for p, digest in before.items())


if __name__ == "__main__":
    main()
