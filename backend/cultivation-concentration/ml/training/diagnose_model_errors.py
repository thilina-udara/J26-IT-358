"""Original RF error diagnosis; no test inspection, tuning, or saved artifacts."""
import hashlib
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from ml.preprocessing.build_advanced_features import ROOT, load_development_rows
from ml.training.compare_models import LABELS, LABEL_ENCODING, approved_inputs, make_models, NUMERIC, CATEGORICAL


def distributions(data):
    counts = data.Risk_Label.value_counts().reindex(LABELS, fill_value=0)
    return pd.DataFrame({"count": counts, "percent": counts / len(data) * 100})


def training_prevalence(training):
    if not training.Target_Year.between(2002, 2021).all():
        raise ValueError("Prevalence analysis requires training years only")
    counts = pd.crosstab(training.Target_Year, training.Risk_Label).reindex(columns=LABELS, fill_value=0)
    return counts, counts.div(counts.sum(axis=1), axis=0) * 100


def grouped_errors(predictions, column):
    groups = predictions.groupby(column, sort=True).agg(records=("Error", "size"), errors=("Error", "sum"))
    groups["error_percent"] = groups.errors / groups.records * 100
    return groups.sort_values(["errors", "error_percent"], ascending=False)


def diagnose(data):
    if not data.Target_Year.between(2002, 2023).all():
        raise ValueError("Test rows forbidden")
    if not set(data.Risk_Label) <= set(LABELS):
        raise ValueError("Invalid risk label")
    if data.duplicated(["District", "Crop", "Season", "Target_Year"]).any():
        raise ValueError("Duplicate target keys")
    train = data.loc[data.Target_Year.between(2002, 2021)].copy()
    validation = data.loc[data.Target_Year.between(2022, 2023)].copy()
    if train.empty or validation.empty or set(train.Risk_Label) != set(LABELS):
        raise ValueError("Invalid development splits")
    model = make_models()["Random Forest"]
    model.fit(approved_inputs(train), train.Risk_Label.map(LABEL_ENCODING))
    predicted = np.asarray(model.predict(approved_inputs(validation)), dtype=int)
    validation["Predicted_Label"] = [LABELS[index] for index in predicted]
    validation["Error"] = validation.Risk_Label != validation.Predicted_Label
    # Aggregate one-hot impurity importances back to the eight original features.
    processor = model.named_steps["preprocessing"]
    values = model.named_steps["classifier"].feature_importances_
    importance = dict(zip(NUMERIC, values[:len(NUMERIC)]))
    offset = len(NUMERIC)
    for column, categories in zip(CATEGORICAL, processor.named_transformers_["categorical"].categories_):
        importance[column] = float(values[offset:offset + len(categories)].sum())
        offset += len(categories)
    return train, validation, importance


def main():
    path = ROOT / "data/processed/official_training_dataset.csv"
    # Reader routes using Target_Year and discards 2024-2025 without feature inspection.
    before = hashlib.sha256(path.read_bytes()).digest()
    train, validation, importance = diagnose(load_development_rows(path))
    print(f"Training rows: {len(train)}; validation rows: {len(validation)}; validation errors: {int(validation.Error.sum())}")
    print("Training class distribution\n" + distributions(train).round(2).to_string())
    print("Validation class distribution\n" + distributions(validation).round(2).to_string())
    for column in ("District", "Crop", "Season", "Target_Year", "Risk_Label"):
        print(f"Validation errors by {column}\n" + grouped_errors(validation, column).round(2).to_string())
    mistakes = validation.loc[validation.Error]
    print("Confusions (actual -> predicted):")
    print(mistakes.groupby(["Risk_Label", "Predicted_Label"]).size().sort_values(ascending=False).to_string())
    print("Confusion matrix: actual rows / predicted columns; Low, Medium, High")
    print(confusion_matrix(validation.Risk_Label, validation.Predicted_Label, labels=list(LABELS)))
    print("Misclassified validation records:")
    print(mistakes[["District", "Crop", "Season", "Target_Year", "Risk_Label", "Predicted_Label"]].to_string(index=False))
    counts, percentages = training_prevalence(train)
    print("Training-year class counts:\n" + counts.to_string())
    print("Training-year class percentages:\n" + percentages.round(1).to_string())
    for start, end in ((2002, 2005), (2006, 2009), (2010, 2013), (2014, 2017), (2018, 2021)):
        print(f"Training era {start}-{end}:\n" + distributions(train.loc[train.Target_Year.between(start, end)]).round(2).to_string())
    print("Exploratory impurity feature importance (not causal; correlated features and high-cardinality inputs can bias importance):")
    for column, value in sorted(importance.items(), key=lambda pair: -pair[1]):
        print(f"  {column}: {value:.4f}")
    print("Possible reasons for low chronological CV: changing class prevalence; limited observations per group and fold; cumulative baselines drifting with structural changes; year/history features cannot extrapolate future regimes reliably; omitted demand, weather and planting-intention information. These are hypotheses, not established causes.")
    print("Recommendations (not implemented):")
    print("1. Evaluate predeclared feature changes with nested rolling-origin evaluation within training years and report per-fold uncertainty; preserve final test isolation.")
    print("2. Collect independently sourced, timestamped pre-planting weather and planting-intention predictors, checking publication/availability dates.")
    print("3. Audit official source definitions, revisions and denominator stability; test a predeclared minimum-history or uncertainty flag using training-only evaluation while retaining existing labels.")
    print("Validation reused in previous experiments; results are diagnostic, not an independent final assessment. Labels describe operational concentration, not observed oversupply. No models saved; test not inspected or evaluated.")
    assert hashlib.sha256(path.read_bytes()).digest() == before


if __name__ == "__main__":
    main()
