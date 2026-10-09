import pytest
from ml.training.compare_training_windows import (
    ROOT, load_development_rows, window_split, compare_windows, STRATEGIES,
    VALIDATION_PERIODS, select_strategy,
)


def test_window_boundaries_and_same_validation_keys():
    data = load_development_rows(ROOT / "data/processed/official_training_dataset.csv")
    for start, end in VALIDATION_PERIODS:
        reference = None
        for window in STRATEGIES.values():
            train, validation = window_split(data, start, end, window)
            assert train.Target_Year.max() < start
            assert train.Target_Year.min() == (2002 if window is None else max(2002, start - window))
            assert validation.Target_Year.between(start, end).all()
            assert not set(train.index) & set(validation.index)
            keys = set(validation.index)
            if reference is None:
                reference = keys
            assert reference == keys


def test_cv_selection_precedes_independent_validation_and_test_rejected():
    data = load_development_rows(ROOT / "data/processed/official_training_dataset.csv")
    calls = []
    def evaluator(train, validation):
        assert train.Target_Year.max() < validation.Target_Year.min()
        assert train.Target_Year.max() <= 2021
        assert validation.Target_Year.max() <= 2023
        calls.append((len(train), int(validation.Target_Year.min())))
        value = 1 / len(train)
        return dict(accuracy=value, balanced_accuracy=value, macro_f1=value, high_recall=value)
    folds, means, selected, final = compare_windows(data, evaluator)
    assert len(calls[:12]) == 12
    assert all(year <= 2020 for _, year in calls[:12])
    assert all(year == 2022 for _, year in calls[12:])
    assert selected == "Rolling 8-year"
    assert len(final) == 2
    assert all(len(results) == 4 for results in folds.values())
    test = data.iloc[:1].copy()
    test["Target_Year"] = 2024
    with pytest.raises(ValueError, match="Test rows forbidden"):
        compare_windows(test, evaluator)


def test_selection_macro_f1_then_balanced():
    assert select_strategy({"A": {"macro_f1": .7, "balanced_accuracy": .8}, "B": {"macro_f1": .8, "balanced_accuracy": .5}}) == "B"
    assert select_strategy({"A": {"macro_f1": .7, "balanced_accuracy": .8}, "B": {"macro_f1": .7, "balanced_accuracy": .5}}) == "A"
