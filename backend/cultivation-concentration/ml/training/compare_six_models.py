"""Six fixed baseline classifiers evaluated on 2022-2023 validation only."""
import argparse
import hashlib
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lightgbm import LGBMClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from ml.training.compare_four_models import (
    ROOT, FEATURE_COLUMNS, load_dataset, make_four_models, run_comparison,
)
from ml.training.compare_models import make_preprocessor


def make_six_models():
    models = make_four_models()
    models["LightGBM"] = Pipeline([
        ("preprocessing", make_preprocessor()),
        ("classifier", LGBMClassifier(
            n_estimators=100, learning_rate=0.05, num_leaves=7, max_depth=3,
            min_child_samples=20, objective="multiclass", random_state=42,
            n_jobs=1, verbosity=-1, deterministic=True, force_col_wise=True,
        )),
    ])
    models["HistGradientBoosting"] = Pipeline([
        ("preprocessing", make_preprocessor()),
        ("classifier", HistGradientBoostingClassifier(
            max_iter=100, learning_rate=0.05, max_leaf_nodes=7, max_depth=3,
            min_samples_leaf=20, early_stopping=False, random_state=42,
        )),
    ])
    return models


def run_six_comparison(data, models=None):
    models = make_six_models() if models is None else models
    if len(models) != 6:
        raise ValueError("Exactly six models are required")
    # HistGradientBoosting uses OpenMP; bound threads for repeatable resource use.
    with threadpool_limits(limits=1):
        return run_comparison(data, models)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/official_training_dataset.csv")
    args = parser.parse_args(argv)
    before = hashlib.sha256(args.input.read_bytes()).digest()
    data = load_dataset(args.input)
    print("Features: " + ", ".join(FEATURE_COLUMNS))
    results, ranking = run_six_comparison(data)
    print("Model                 Accuracy  Balanced Accuracy  Macro F1  High Precision  High Recall")
    for name in ranking:
        metrics = results[name]
        high = metrics["report"]["High"]
        print(f"{name:21} {metrics['accuracy']:.4f}    {metrics['balanced_accuracy']:.4f}             {metrics['macro_f1']:.4f}    {high['precision']:.4f}          {high['recall']:.4f}")
    for name in ranking:
        print(f"{name} confusion matrix: actual rows, predicted columns; Low, Medium, High")
        print(results[name]["confusion_matrix"])
    print(f"Best validation model: {ranking[0]}; ranked by Macro F1 then balanced accuracy.")
    print("Test counted only; no test transformation, prediction, or evaluation. No model artifacts saved.")
    print("Labels represent operational concentration risk, not actual observed market oversupply.")
    if hashlib.sha256(args.input.read_bytes()).digest() != before:
        raise RuntimeError("Input dataset changed during comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
