import hashlib
import numpy as np
import pytest

from ml.training.compare_six_models import (
    ROOT, FEATURE_COLUMNS, load_dataset, make_six_models, run_six_comparison,
)
from ml.training.compare_four_models import make_four_models
from ml.training.compare_models import chronological_split, NUMERIC


def test_exactly_six_and_existing_settings_preserved():
    models = make_six_models()
    assert set(models) == {"Random Forest", "XGBoost", "Extra Trees", "CatBoost", "LightGBM", "HistGradientBoosting"}
    for name, model in make_four_models().items():
        assert model.named_steps["classifier"].get_params() == models[name].named_steps["classifier"].get_params()
    for model in models.values():
        assert model.named_steps["classifier"].get_params()["random_state"] == 42
    assert models["HistGradientBoosting"].named_steps["classifier"].early_stopping is False


def test_splits_features_preprocessing_and_source_unchanged():
    path = ROOT / "data/processed/official_training_dataset.csv"
    before = hashlib.sha256(path.read_bytes()).digest()
    data = load_dataset(path)
    train, validation, test = chronological_split(data)
    for split, bounds in zip((train, validation, test), ((2002, 2021), (2022, 2023), (2024, 2025))):
        assert split.Target_Year.between(*bounds).all()
    assert not set(train.index) & set(validation.index)
    assert not (set(train.index) | set(validation.index)) & set(test.index)
    assert len(FEATURE_COLUMNS) == 8
    assert not any("ratio" in c.lower() or "score" in c.lower() or "label" in c.lower() for c in FEATURE_COLUMNS)
    inputs = train[list(FEATURE_COLUMNS)]
    later = validation[list(FEATURE_COLUMNS)].copy()
    later["District"] = "ValidationOnly"
    later[NUMERIC[0]] = np.nan
    for model in make_six_models().values():
        processor = model.named_steps["preprocessing"].fit(inputs)
        medians = processor.named_transformers_["numeric"].statistics_.copy()
        assert np.allclose(medians, inputs[NUMERIC].median().to_numpy())
        assert "ValidationOnly" not in processor.named_transformers_["categorical"].categories_[0]
        assert np.isfinite(processor.transform(later)).all()
        assert np.array_equal(medians, processor.named_transformers_["numeric"].statistics_)
    assert hashlib.sha256(path.read_bytes()).digest() == before


def test_six_fit_predict_paths_never_receive_test(capsys):
    data = load_dataset(ROOT / "data/processed/official_training_dataset.csv")
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
    # Test labels are intentionally invalid here: comparison never consumes them.
    data.loc[data.Target_Year >= 2024, "Risk_Label"] = "DO_NOT_READ"
    results, ranking = run_six_comparison(data, {name: Spy() for name in make_six_models()})
    assert len(results) == len(ranking) == 6
    assert calls == ["fit", "predict"] * 6
    assert "Test (2024–2025): 48 rows" in capsys.readouterr().out
    with pytest.raises(ValueError, match="Exactly six"):
        run_six_comparison(data, {"one": Spy()})
