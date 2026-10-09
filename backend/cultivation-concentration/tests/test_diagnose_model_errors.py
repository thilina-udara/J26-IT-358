import numpy as np
import pandas as pd
import pytest
from ml.training import diagnose_model_errors as module
from ml.training.compare_models import FEATURE_COLUMNS


def data():
    return module.load_development_rows(module.ROOT / "data/processed/official_training_dataset.csv")


def test_actual_diagnostics_preserve_input_and_counts():
    original = data()
    before = original.copy(deep=True)
    train, validation, importance = module.diagnose(original)
    pd.testing.assert_frame_equal(before, original)
    assert len(train) == 460 and len(validation) == 48
    assert validation.Error.sum() == 13
    assert set(importance) == set(FEATURE_COLUMNS)
    assert sum(importance.values()) == pytest.approx(1)
    for column in ("District", "Crop", "Season", "Target_Year", "Risk_Label"):
        grouped = module.grouped_errors(validation, column)
        assert grouped.errors.sum() == 13
        assert grouped.records.sum() == 48
    counts, percentages = module.training_prevalence(train)
    assert counts.to_numpy().sum() == 460
    assert np.allclose(percentages.sum(axis=1), 100)
    with pytest.raises(ValueError, match="training years"):
        module.training_prevalence(validation)


def test_train_predict_boundaries_and_features(monkeypatch):
    original_factory = module.make_models
    model = original_factory()["Random Forest"]
    fit, predict = model.fit, model.predict
    calls = []
    def checked_fit(x, y):
        assert list(x.columns) == list(FEATURE_COLUMNS)
        assert x.Target_Year.between(2002, 2021).all()
        calls.append("fit")
        return fit(x, y)
    def checked_predict(x):
        assert x.Target_Year.between(2022, 2023).all()
        calls.append("predict")
        return predict(x)
    monkeypatch.setattr(model, "fit", checked_fit)
    monkeypatch.setattr(model, "predict", checked_predict)
    monkeypatch.setattr(module, "make_models", lambda: {"Random Forest": model})
    module.diagnose(data())
    assert calls == ["fit", "predict"]
    test_row = data().iloc[:1].copy()
    test_row["Target_Year"] = 2024
    with pytest.raises(ValueError, match="Test rows forbidden"):
        module.diagnose(test_row)
