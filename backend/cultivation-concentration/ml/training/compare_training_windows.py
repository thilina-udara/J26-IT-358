"""CV-selected RF training windows; no test inspection or saved models.

Rolling windows restrict training rows only. The existing cumulative historical
features are preserved and may summarize years before the training window.
"""
import hashlib
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from ml.preprocessing.build_advanced_features import ROOT, load_development_rows
from ml.training.compare_advanced_features import evaluate

STRATEGIES = {"Expanding": None, "Rolling 8-year": 8, "Rolling 12-year": 12}
VALIDATION_PERIODS = ((2014, 2015), (2016, 2017), (2018, 2019), (2020, 2021))
METRICS = ("accuracy", "balanced_accuracy", "macro_f1", "high_recall")


def window_split(data, start, end, window=None):
    if not data.Target_Year.between(2002, 2023).all():
        raise ValueError("Test rows forbidden")
    first = 2002 if window is None else max(2002, start - window)
    train = data.loc[data.Target_Year.between(first, start - 1)].copy()
    validation = data.loc[data.Target_Year.between(start, end)].copy()
    if train.empty or validation.empty:
        raise ValueError("Empty window split")
    return train, validation


def select_strategy(means):
    return max(means, key=lambda name: (means[name]["macro_f1"], means[name]["balanced_accuracy"]))


def compare_windows(data, evaluator=evaluate):
    if not data.Target_Year.between(2002, 2023).all():
        raise ValueError("Test rows forbidden")
    if data.duplicated(["District", "Crop", "Season", "Target_Year"]).any():
        raise ValueError("Duplicate target keys")
    development = data.loc[data.Target_Year <= 2021]
    folds, means = {}, {}
    for name, window in STRATEGIES.items():
        folds[name] = []
        for start, end in VALIDATION_PERIODS:
            train, validation = window_split(development, start, end, window)
            metrics = evaluator(train, validation)
            folds[name].append(dict(metrics, training_rows=len(train), validation_rows=len(validation),
                                    training_start=int(train.Target_Year.min()), training_end=int(train.Target_Year.max()),
                                    validation_start=start, validation_end=end))
        means[name] = {metric: float(np.mean([fold[metric] for fold in folds[name]])) for metric in METRICS}
    selected = select_strategy(means)
    # Only after CV selection, perform the separate validation comparison.
    final = {}
    for name in dict.fromkeys(("Expanding", selected)):
        train, validation = window_split(data, 2022, 2023, STRATEGIES[name])
        final[name] = dict(evaluator(train, validation), training_rows=len(train))
    return folds, means, selected, final


def main():
    path = ROOT / "data/processed/official_training_dataset.csv"
    before = hashlib.sha256(path.read_bytes()).digest()
    folds, means, selected, final = compare_windows(load_development_rows(path))
    print("Original RF configuration; same eight approved features; fold-specific training-fitted preprocessing.")
    print("Rolling windows restrict training rows; cumulative historical features remain unchanged.")
    for name, results in folds.items():
        print(name)
        for fold in results:
            print(f"  Train {fold['training_start']}-{fold['training_end']} ({fold['training_rows']} rows); validation {fold['validation_start']}-{fold['validation_end']} ({fold['validation_rows']} rows): " + ", ".join(f"{metric}={fold[metric]:.4f}" for metric in METRICS))
    print("Mean CV metrics (equal fold weights)")
    print("Strategy          Accuracy  Balanced Accuracy  Macro F1  High Recall")
    for name in sorted(means, key=lambda n: (-means[n]['macro_f1'], -means[n]['balanced_accuracy'])):
        print(f"{name:17} " + "  ".join(f"{means[name][m]:.4f}" for m in METRICS))
    print(f"CV-selected strategy: {selected}; Macro F1 first, balanced accuracy tie-breaker.")
    print("2022-2023 validation comparison")
    for name, result in final.items():
        print(f"{name} ({result['training_rows']} training rows): " + ", ".join(f"{m}={result[m]:.4f}" for m in METRICS))
        print("Confusion matrix: actual rows, predicted columns; Low, Medium, High")
        print(result["confusion_matrix"])
    delta = final[selected]["macro_f1"] - final["Expanding"]["macro_f1"]
    print(f"Selected versus baseline validation Macro F1 change: {delta:+.4f}")
    if selected == "Expanding":
        print("Recent-history windows did not improve mean CV Macro F1; selected strategy equals baseline.")
    elif delta < 0:
        print("CV-selected rolling strategy performs worse on validation.")
    print("Validation repeatedly used in prior experiments; this is diagnostic evidence, not final generalization assessment. Test not inspected, transformed, predicted or evaluated. No production models saved. Labels describe concentration, not observed oversupply.")
    assert hashlib.sha256(path.read_bytes()).digest() == before


if __name__ == "__main__":
    main()
