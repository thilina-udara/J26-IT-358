"""Reproducible validation-only comparison; no saved models or test predictions."""
import argparse
import hashlib
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

from ml.preprocessing.build_training_dataset import FEATURE_COLUMNS, ROOT

LABELS = ("Low", "Medium", "High")
LABEL_ENCODING = {label: index for index, label in enumerate(LABELS)}
NUMERIC = list(FEATURE_COLUMNS[:4]) + ["Target_Year"]
CATEGORICAL = ["District", "Crop", "Season"]


def load_dataset(path):
    data = pd.read_csv(path)
    if list(data.columns) != list(FEATURE_COLUMNS) + ["Risk_Label"]:
        raise ValueError("Unexpected CSV columns; approved features plus Risk_Label required")
    if not set(data.Risk_Label) <= set(LABELS) or data.Risk_Label.isna().any():
        raise ValueError("Invalid label encoding")
    for column in NUMERIC:
        data[column] = pd.to_numeric(data[column], errors="raise")
        if np.isinf(data[column]).any():
            raise ValueError(f"Infinite numeric feature: {column}")
    if data.Target_Year.isna().any() or not data.Target_Year.between(2002, 2025).all() or (data.Target_Year % 1 != 0).any():
        raise ValueError("Invalid Target_Year")
    allowed = {"District": {"Matara", "Hambantota"}, "Crop": {"Mung Beans", "Corn", "Bandakka", "Brinjal", "Pumpkin", "Chillies"}, "Season": {"Maha", "Yala"}}
    for column, values in allowed.items():
        if data[column].isna().any() or not set(data[column]) <= values:
            raise ValueError(f"Invalid category: {column}")
    if data.duplicated(["District", "Crop", "Season", "Target_Year"]).any():
        raise ValueError("Duplicate target keys")
    return data


def chronological_split(data):
    splits = tuple(data.loc[data.Target_Year.between(start, end)].copy() for start, end in ((2002, 2021), (2022, 2023), (2024, 2025)))
    if any(split.empty for split in splits) or sum(map(len, splits)) != len(data):
        raise ValueError("Invalid or empty chronological splits")
    if set(splits[0].Risk_Label) != set(LABELS):
        raise ValueError("Training must support all three labels")
    return splits


def approved_inputs(data):
    return data.loc[:, list(FEATURE_COLUMNS)]


def make_preprocessor():
    return ColumnTransformer([
        ("numeric", SimpleImputer(strategy="median", keep_empty_features=True), NUMERIC),
        ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
    ])


def make_models():
    # Fixed initial configurations, no search or validation-driven tuning.
    return {
        "Random Forest": Pipeline([("preprocessing", make_preprocessor()), ("classifier", RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=1))]),
        "XGBoost": Pipeline([("preprocessing", make_preprocessor()), ("classifier", XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, objective="multi:softprob", num_class=3, eval_metric="mlogloss", tree_method="hist", random_state=42, n_jobs=1))]),
    }


def compare_on_validation(train, validation, models=None):
    """Accept no test data: fit train only and predict validation only."""
    models = make_models() if models is None else models
    results = {}
    y_train = train.Risk_Label.map(LABEL_ENCODING).to_numpy()
    y_validation = validation.Risk_Label.map(LABEL_ENCODING).to_numpy()
    for name, model in models.items():
        model.fit(approved_inputs(train), y_train)
        predicted = model.predict(approved_inputs(validation))
        results[name] = {
            "accuracy": accuracy_score(y_validation, predicted),
            "balanced_accuracy": balanced_accuracy_score(y_validation, predicted),
            "macro_f1": f1_score(y_validation, predicted, labels=[0, 1, 2], average="macro", zero_division=0),
            "report": classification_report(y_validation, predicted, labels=[0, 1, 2], target_names=list(LABELS), output_dict=True, zero_division=0),
            "confusion_matrix": confusion_matrix(y_validation, predicted, labels=[0, 1, 2]),
        }
    selected = max(results, key=lambda name: (results[name]["macro_f1"], results[name]["balanced_accuracy"]))
    return results, selected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/official_training_dataset.csv")
    args = parser.parse_args(argv)
    before = hashlib.sha256(args.input.read_bytes()).digest()
    data = load_dataset(args.input)
    print("CSV columns: " + ", ".join(data.columns))
    print(f"Label encoding: {LABEL_ENCODING}")
    train, validation, test = chronological_split(data)
    for name, split in (("Train", train), ("Validation", validation), ("Test (counts only)", test)):
        counts = split.Risk_Label.value_counts()
        print(f"{name}: {len(split)} rows, years {int(split.Target_Year.min())}-{int(split.Target_Year.max())}; " + ", ".join(f"{label}={counts.get(label, 0)}" for label in LABELS))
    results, selected = compare_on_validation(train, validation)
    print("Model             Accuracy  Balanced accuracy  Macro F1")
    for name, metrics in results.items():
        print(f"{name:17} {metrics['accuracy']:.4f}    {metrics['balanced_accuracy']:.4f}             {metrics['macro_f1']:.4f}")
        for label in LABELS:
            print(f"  {label}: precision={metrics['report'][label]['precision']:.4f}, recall={metrics['report'][label]['recall']:.4f}")
        print("  Confusion matrix: rows=actual, columns=predicted; Low, Medium, High")
        print(metrics["confusion_matrix"])
    print(f"Selected: {selected}; validation Macro F1 first, balanced accuracy tie-breaker.")
    print("Test set not transformed or predicted; no test metrics or model artifacts saved.")
    print("Labels are operational concentration categories, not observed market oversupply.")
    if hashlib.sha256(args.input.read_bytes()).digest() != before:
        raise RuntimeError("Input CSV changed during run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
