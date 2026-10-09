import numpy as np
import pandas as pd
import pytest
from ml.preprocessing.build_advanced_features import build_advanced_features, ROOT, load_development_rows, load_prior_official
from ml.training.compare_advanced_features import evaluate


def observation(year, area):
    return dict(district_name="Matara", crop_name="Corn", season="Maha", year=str(year), cultivated_extent_hectares=str(area), production_metric_tons=str(area * 2))


def targets(years):
    return pd.DataFrame([dict(District="Matara", Crop="Corn", Season="Maha", Target_Year=y) for y in years])


def test_calendar_lag_and_rolling_with_missing_year():
    result = build_advanced_features(targets([2002, 2003, 2005]), [observation(2001, 1), observation(2003, 3), observation(2004, 4)])
    assert result.iloc[0].Previous_Year_Land_Acres == pytest.approx(2.4710538147)
    assert np.isnan(result.iloc[1].Previous_Year_Land_Acres)
    assert result.iloc[1].Rolling_3Y_History_Count == 1
    assert np.isnan(result.iloc[1].Rolling_3Y_Land_Trend)
    assert result.iloc[2].Rolling_3Y_History_Count == 3
    assert result.iloc[2].Rolling_3Y_Mean_Land_Acres == pytest.approx(8 / 3 * 2.4710538147)
    assert result.iloc[2].Rolling_3Y_Land_Trend == pytest.approx(2.4710538147)


def test_no_current_future_leakage_and_only_three_observations():
    past = [observation(y, y - 2000) for y in range(2001, 2006)]
    a = build_advanced_features(targets([2006]), past)
    b = build_advanced_features(targets([2006]), past + [observation(2006, 999), observation(2025, 999)])
    pd.testing.assert_frame_equal(a, b)
    assert a.iloc[0].Rolling_3Y_Mean_Land_Acres == pytest.approx(4 * 2.4710538147)
    with pytest.raises(ValueError, match="test rows forbidden"):
        build_advanced_features(targets([2024]), past)


def test_empty_and_zero_area_history():
    result = build_advanced_features(targets([2002]), [observation(2001, 0)])
    assert result.iloc[0].Rolling_3Y_History_Count == 1
    assert result.iloc[0].Rolling_3Y_Yield_History_Count == 0
    assert np.isnan(result.iloc[0].Rolling_3Y_Mean_Yield)
    empty = build_advanced_features(targets([2002]), [])
    assert empty.iloc[0].Rolling_3Y_History_Count == 0
    assert np.isnan(empty.iloc[0].Rolling_3Y_Mean_Land_Acres)


def test_development_only_preserves_labels_count_and_base_features():
    original = load_development_rows(ROOT / "data/processed/official_training_dataset.csv")
    result = build_advanced_features(original, load_prior_official(ROOT / "data/official/official_historical_2001_2025.csv"))
    assert len(result) == len(original) == 508
    assert result.Target_Year.max() == 2023
    pd.testing.assert_frame_equal(result[original.columns], original)
    with pytest.raises(ValueError, match="Test rows forbidden"):
        evaluate(result, targets([2024]))
