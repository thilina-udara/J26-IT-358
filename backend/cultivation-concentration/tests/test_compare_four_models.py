import numpy as np
import pytest

from ml.training.compare_four_models import (
    ROOT, FEATURE_COLUMNS, load_dataset, chronological_split,
    make_four_models, run_comparison, rank_results,
)
from ml.training.compare_models import make_models, NUMERIC


@pytest.fixture
def dataset():
    return load_dataset(ROOT / "data/processed/official_training_dataset.csv")


def test_splits_and_approved_columns(dataset):
    train, validation, test = chronological_split(dataset)
    assert train.Target_Year.between(2002, 2021).all()
    assert validation.Target_Year.between(2022, 2023).all()
    assert test.Target_Year.between(2024, 2025).all()
    assert not set(train.index) & set(validation.index)
    assert not (set(train.index) | set(validation.index)) & set(test.index)
    assert len(train) + len(validation) + len(test) == len(dataset)
    assert list(FEATURE_COLUMNS) == [
        "Prior_History_Count", "Historical_Mean_Land_Acres",
        "Historical_Mean_Production_kg", "Historical_Mean_Yield_kg_per_Acre",
        "District", "Crop", "Season", "Target_Year",
    ]


def test_settings_consistency_and_independent_preprocessing():
    models = make_four_models()
    for name, original in make_models().items():
        assert models[name].named_steps["classifier"].get_params() == original.named_steps["classifier"].get_params()
    assert len({id(model.named_steps["preprocessing"]) for model in models.values()}) == 4
    assert models["CatBoost"].named_steps["classifier"].get_params()["allow_writing_files"] is False
    for model in models.values():
        assert model.named_steps["classifier"].get_params()["random_state"] == 42


def test_all_preprocessing_fitted_training_only(dataset):
    train, validation, _ = chronological_split(dataset)
    inputs = train[list(FEATURE_COLUMNS)]
    later = validation[list(FEATURE_COLUMNS)].copy()
    later["District"] = "ValidationOnly"
    later[NUMERIC[0]] = np.nan
    for model in make_four_models().values():
        processor = model.named_steps["preprocessing"].fit(inputs)
        medians = processor.named_transformers_["numeric"].statistics_.copy()
        assert np.allclose(medians, inputs[NUMERIC].median().to_numpy())
        assert "ValidationOnly" not in processor.named_transformers_["categorical"].categories_[0]
        assert np.isfinite(processor.transform(later)).all()
        assert np.array_equal(medians, processor.named_transformers_["numeric"].statistics_)


def test_full_orchestration_never_predicts_test(dataset, capsys):
    calls = []
    class Spy:
        def fit(self, x, y):
            assert list(x.columns) == list(FEATURE_COLUMNS)
            assert x.Target_Year.between(2002, 2021).all()
            assert set(y) == {0, 1, 2}
            calls.append("fit")
        def predict(self, x):
            assert x.Target_Year.between(2022, 2023).all()
            calls.append("predict")
            return np.ones(len(x), dtype=int)
    models = {name: Spy() for name in make_four_models()}
    results, ranking = run_comparison(dataset, models)
    assert calls == ["fit", "predict"] * 4
    assert len(results) == len(ranking) == 4
    output = capsys.readouterr().out
    assert "Test (2024–2025): 48 rows" in output
    assert "Test (2024–2025): 48 rows;" not in output


def test_ranking_uses_macro_f1_then_balanced_accuracy():
    results = {
        "A": {"macro_f1": .7, "balanced_accuracy": .6, "accuracy": .99},
        "B": {"macro_f1": .7, "balanced_accuracy": .8, "accuracy": .8},
        "C": {"macro_f1": .8, "balanced_accuracy": .5, "accuracy": .7},
    }
    assert rank_results(results) == ["C", "B", "A"]
