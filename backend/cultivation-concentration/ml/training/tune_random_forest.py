"""Expanding-window RF tuning, then independent 2022-2023 comparison only."""
import argparse
import hashlib
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, make_scorer
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline

from ml.training.compare_models import (
    ROOT, LABELS, LABEL_ENCODING, FEATURE_COLUMNS, load_dataset,
    chronological_split, approved_inputs, make_preprocessor, make_models,
    compare_on_validation,
)

FOLD_YEARS = ((2013, 2014, 2015), (2015, 2016, 2017),
              (2017, 2018, 2019), (2019, 2020, 2021))
PARAM_GRID = {
    "classifier__n_estimators": [100, 200, 300],
    "classifier__max_depth": [5, 10, None],
    "classifier__min_samples_leaf": [1, 2, 4],
    "classifier__max_features": ["sqrt", 0.7],
    "classifier__class_weight": [None, "balanced"],
}


def expanding_window_splits(training):
    if not training.Target_Year.between(2002, 2021).all():
        raise ValueError("Tuning input must contain only 2002-2021")
    folds = []
    for end, start_validation, end_validation in FOLD_YEARS:
        train = np.flatnonzero(training.Target_Year.between(2002, end).to_numpy())
        validation = np.flatnonzero(training.Target_Year.between(start_validation, end_validation).to_numpy())
        if not len(train) or not len(validation):
            raise ValueError("Empty expanding-window fold")
        if set(training.iloc[train].Risk_Label) != set(LABELS):
            raise ValueError("Each fold training set must support all labels")
        folds.append((train, validation))
    return folds


def select_best_candidate(results):
    """Macro F1 first, balanced accuracy second; grid order resolves exact ties."""
    f1 = np.asarray(results["mean_test_macro_f1"])
    balanced = np.asarray(results["mean_test_balanced_accuracy"])
    if not np.isfinite(f1).all() or not np.isfinite(balanced).all():
        raise ValueError("Nonfinite CV metrics")
    return max(range(len(f1)), key=lambda i: (f1[i], balanced[i]))


def tune(training, param_grid=None, progress=False):
    folds = expanding_window_splits(training)
    pipeline = Pipeline([
        ("preprocessing", make_preprocessor()),
        ("classifier", RandomForestClassifier(random_state=42, n_jobs=1)),
    ])
    # GridSearchCV clones the full pipeline per candidate/fold, including imputer
    # and encoder. The selected pipeline is refitted on 2002-2021 only.
    search = GridSearchCV(
        pipeline, PARAM_GRID if param_grid is None else param_grid,
        scoring={"macro_f1": make_scorer(f1_score, labels=[0, 1, 2], average="macro", zero_division=0),
                 "balanced_accuracy": "balanced_accuracy"},
        cv=folds, refit=select_best_candidate, n_jobs=1,
        error_score="raise", return_train_score=False, verbose=1 if progress else 0,
    )
    search.fit(approved_inputs(training), training.Risk_Label.map(LABEL_ENCODING).to_numpy())
    return search


def run_tuning(data, param_grid=None, progress=False):
    train, validation, test = chronological_split(data)
    for name, split in (("Training/tuning", train), ("Independent validation", validation)):
        print(f"{name}: {len(split)} rows; " + ", ".join(f"{label}={sum(split.Risk_Label == label)}" for label in LABELS), flush=True)
    print(f"Final test: {len(test)} rows; not transformed, predicted, or evaluated.", flush=True)
    for index, (a, b) in enumerate(expanding_window_splits(train), 1):
        print(f"Fold {index}: train 2002-{FOLD_YEARS[index-1][0]} ({len(a)} rows), validation {FOLD_YEARS[index-1][1]}-{FOLD_YEARS[index-1][2]} ({len(b)} rows)", flush=True)
    search = tune(train, param_grid, progress)
    # Independent validation never influences parameter selection.
    models = {"Original RF": make_models()["Random Forest"], "Tuned RF": search.best_estimator_}
    results, _ = compare_on_validation(train, validation, models)
    return search, results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/official_training_dataset.csv")
    args = parser.parse_args(argv)
    before = hashlib.sha256(args.input.read_bytes()).digest()
    print("Features: " + ", ".join(FEATURE_COLUMNS), flush=True)
    search, results = run_tuning(load_dataset(args.input), progress=True)
    i = search.best_index_
    print("Selected parameters:", {k.removeprefix("classifier__"): v for k, v in search.best_params_.items()})
    print(f"Mean CV Macro F1: {search.cv_results_['mean_test_macro_f1'][i]:.4f}; mean CV balanced accuracy: {search.cv_results_['mean_test_balanced_accuracy'][i]:.4f}")
    for fold in range(4):
        print(f"Selected candidate fold {fold+1}: Macro F1={search.cv_results_[f'split{fold}_test_macro_f1'][i]:.4f}, balanced accuracy={search.cv_results_[f'split{fold}_test_balanced_accuracy'][i]:.4f}")
    print("Model        Accuracy  Macro F1  Balanced Accuracy  High Precision  High Recall")
    for name, metrics in results.items():
        high = metrics["report"]["High"]
        print(f"{name:12} {metrics['accuracy']:.4f}    {metrics['macro_f1']:.4f}    {metrics['balanced_accuracy']:.4f}             {high['precision']:.4f}          {high['recall']:.4f}")
        print("Confusion matrix: actual rows, predicted columns; Low, Medium, High")
        print(metrics["confusion_matrix"])
    print("Parameters selected using CV only. No final model saved; final test remains unevaluated.")
    print("Labels describe operational concentration, not observed market oversupply.")
    if hashlib.sha256(args.input.read_bytes()).digest() != before:
        raise RuntimeError("Input dataset changed during tuning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
