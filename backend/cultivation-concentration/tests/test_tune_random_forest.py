import numpy as np
import pytest
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder

from ml.training import tune_random_forest as module
from ml.training.compare_models import NUMERIC


@pytest.fixture
def data():
    return module.load_dataset(module.ROOT / "data/processed/official_training_dataset.csv")


def test_expanding_boundaries_and_positions(data):
    train, _, _ = module.chronological_split(data)
    previous = set()
    for (a, b), (end, vstart, vend) in zip(module.expanding_window_splits(train), module.FOLD_YEARS):
        assert train.iloc[a].Target_Year.between(2002, end).all()
        assert train.iloc[b].Target_Year.between(vstart, vend).all()
        assert not set(a) & set(b)
        assert previous <= set(a)
        previous = set(a)
    with pytest.raises(ValueError, match="2002-2021"):
        module.expanding_window_splits(data)


def test_selection_f1_then_balanced():
    assert module.select_best_candidate({"mean_test_macro_f1": [.6, .7, .7], "mean_test_balanced_accuracy": [.99, .6, .8]}) == 2
    assert module.select_best_candidate({"mean_test_macro_f1": [.8, .7], "mean_test_balanced_accuracy": [.5, .9]}) == 0
    assert np.prod([len(values) for values in module.PARAM_GRID.values()]) == 108


def test_real_search_fits_preprocessing_per_fold(data, monkeypatch):
    train, _, _ = module.chronological_split(data)
    train = train.copy()
    # Validation-only category must not appear in fold 1's fitted encoder.
    train.loc[train.Target_Year == 2014, "District"] = "LaterCategory"
    imputer_seen, encoder_seen = [], []
    original_imputer_fit = SimpleImputer.fit
    original_encoder_fit = OneHotEncoder.fit
    def imputer_fit(self, x, *args, **kwargs):
        result = original_imputer_fit(self, x, *args, **kwargs)
        assert np.allclose(self.statistics_, x.median().to_numpy())
        imputer_seen.append((int(x.Target_Year.max()), self.statistics_.copy()))
        return result
    def encoder_fit(self, x, *args, **kwargs):
        result = original_encoder_fit(self, x, *args, **kwargs)
        encoder_seen.append(set(self.categories_[0]))
        return result
    monkeypatch.setattr(SimpleImputer, "fit", imputer_fit)
    monkeypatch.setattr(OneHotEncoder, "fit", encoder_fit)
    search = module.tune(train, {"classifier__n_estimators": [2], "classifier__max_depth": [3]})
    assert [end for end, _ in imputer_seen] == [2013, 2015, 2017, 2019, 2021]
    assert "LaterCategory" not in encoder_seen[0]
    assert "LaterCategory" in encoder_seen[1]
    assert list(search.best_estimator_.feature_names_in_) == list(module.FEATURE_COLUMNS)


def test_orchestration_keeps_validation_out_of_tuning_and_test_unused(data, monkeypatch):
    calls = []
    sentinel = object()
    class Search:
        best_estimator_ = sentinel
    def fake_tune(training, grid, progress):
        assert training.Target_Year.between(2002, 2021).all()
        calls.append("tune")
        return Search()
    def fake_compare(train, validation, models):
        assert train.Target_Year.between(2002, 2021).all()
        assert validation.Target_Year.between(2022, 2023).all()
        assert models["Tuned RF"] is sentinel
        calls.append("compare")
        return {}, None
    monkeypatch.setattr(module, "tune", fake_tune)
    monkeypatch.setattr(module, "compare_on_validation", fake_compare)
    data.loc[data.Target_Year >= 2024, "Risk_Label"] = "DO_NOT_USE"
    module.run_tuning(data)
    assert calls == ["tune", "compare"]
