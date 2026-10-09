import numpy as np
import pandas as pd
import pytest
from ml.training.compare_models import (
    ROOT, FEATURE_COLUMNS, LABELS, LABEL_ENCODING, NUMERIC, approved_inputs,
    chronological_split, load_dataset, make_preprocessor, compare_on_validation,
)


def test_real_split_boundaries_and_disjoint_keys():
    data = load_dataset(ROOT / "data/processed/official_training_dataset.csv")
    splits = chronological_split(data)
    for split, bounds in zip(splits, ((2002, 2021), (2022, 2023), (2024, 2025))):
        assert split.Target_Year.between(*bounds).all()
        assert set(split.Risk_Label) == set(LABELS)
    assert sum(map(len, splits)) == len(data)
    indices = [set(split.index) for split in splits]
    assert not (indices[0] & indices[1] or indices[0] & indices[2] or indices[1] & indices[2])
    assert LABEL_ENCODING == {"Low": 0, "Medium": 1, "High": 2}
    assert list(approved_inputs(data.assign(risk_score=999)).columns) == list(FEATURE_COLUMNS)


def test_training_only_imputation_and_encoding():
    data = load_dataset(ROOT / "data/processed/official_training_dataset.csv")
    train, validation, _ = chronological_split(data)
    train = approved_inputs(train)
    validation = approved_inputs(validation).copy()
    validation["District"] = "UnseenDistrict"
    validation[NUMERIC[0]] = np.nan
    processor = make_preprocessor().fit(train)
    medians = processor.named_transformers_["numeric"].statistics_.copy()
    assert np.allclose(medians, train[NUMERIC].median().to_numpy())
    categories = processor.named_transformers_["categorical"].categories_
    assert "UnseenDistrict" not in categories[0]
    transformed = processor.transform(validation)
    assert np.isfinite(transformed).all()
    assert np.array_equal(processor.named_transformers_["numeric"].statistics_, medians)


def test_comparison_calls_fit_train_predict_validation_only():
    data = load_dataset(ROOT / "data/processed/official_training_dataset.csv")
    train, validation, _ = chronological_split(data)
    class Spy:
        def fit(self, inputs, labels):
            assert inputs.Target_Year.between(2002, 2021).all()
            assert list(inputs.columns) == list(FEATURE_COLUMNS)
            assert set(labels) == {0, 1, 2}
        def predict(self, inputs):
            assert inputs.Target_Year.between(2022, 2023).all()
            return np.ones(len(inputs), dtype=int)
    results, selected = compare_on_validation(train, validation, {"Spy": Spy()})
    assert selected == "Spy"
    assert results["Spy"]["confusion_matrix"].shape == (3, 3)
    assert all(label in results["Spy"]["report"] for label in LABELS)
