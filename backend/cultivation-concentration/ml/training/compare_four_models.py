"""Four fixed baseline models, validation evaluation only, no model artifacts."""
import argparse
import hashlib
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from catboost import CatBoostClassifier
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.pipeline import Pipeline

from ml.training.compare_models import (
    ROOT, FEATURE_COLUMNS, LABELS, LABEL_ENCODING, load_dataset,
    chronological_split, make_preprocessor, make_models, compare_on_validation,
)


def make_four_models():
    # Reuse the original configurations verbatim for comparable results.
    models = make_models()
    models["Extra Trees"] = Pipeline([
        ("preprocessing", make_preprocessor()),
        ("classifier", ExtraTreesClassifier(n_estimators=300, random_state=42, n_jobs=1)),
    ])
    models["CatBoost"] = Pipeline([
        ("preprocessing", make_preprocessor()),
        ("classifier", CatBoostClassifier(
            iterations=300, depth=4, learning_rate=0.05, loss_function="MultiClass",
            random_state=42, thread_count=1, verbose=False,
            allow_writing_files=False,
        )),
    ])
    return models


def rank_results(results):
    return sorted(results, key=lambda name: (
        -results[name]["macro_f1"], -results[name]["balanced_accuracy"], name,
    ))


def run_comparison(data, models=None):
    """Test is counted only; evaluator receives train and validation only."""
    train, validation, test = chronological_split(data)
    for name, split in (("Train (2002–2021)", train), ("Validation (2022–2023)", validation)):
        counts = split.Risk_Label.value_counts()
        print(f"{name}: {len(split)} rows; " + ", ".join(f"{label}={counts.get(label, 0)}" for label in LABELS))
    print(f"Test (2024–2025): {len(test)} rows")
    results, _ = compare_on_validation(train, validation, make_four_models() if models is None else models)
    return results, rank_results(results)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/official_training_dataset.csv")
    args = parser.parse_args(argv)
    before = hashlib.sha256(args.input.read_bytes()).digest()
    data = load_dataset(args.input)
    print("Features: " + ", ".join(FEATURE_COLUMNS))
    print(f"Label encoding: {LABEL_ENCODING}")
    results, ranking = run_comparison(data)
    print("Model             Accuracy  Balanced accuracy  Macro F1")
    for name in ranking:
        metrics = results[name]
        print(f"{name:17} {metrics['accuracy']:.4f}    {metrics['balanced_accuracy']:.4f}             {metrics['macro_f1']:.4f}")
    for name in ranking:
        metrics = results[name]
        print(name)
        for label in LABELS:
            print(f"  {label}: precision={metrics['report'][label]['precision']:.4f}, recall={metrics['report'][label]['recall']:.4f}")
        print("  Confusion matrix: actual rows, predicted columns; Low, Medium, High")
        print(metrics["confusion_matrix"])
    print(f"Best validation model: {ranking[0]}; Macro F1 first, balanced accuracy second.")
    print("Test counted only; no test transformation, prediction, or evaluation. No model artifacts saved.")
    print("Labels represent operational concentration risk, not observed market oversupply.")
    if hashlib.sha256(args.input.read_bytes()).digest() != before:
        raise RuntimeError("Input dataset changed during comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
