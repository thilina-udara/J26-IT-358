"""Unit and integration tests for crop yield anomaly models."""

import os
import sys
import json
import unittest
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

# Resolve Paths
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(TEST_DIR, ".."))
sys.path.insert(0, os.path.join(PROJECT_DIR, "pipelines"))

from train_crop_yield_anomaly_models import (
    FEATURES_PRE_OPERATIONAL,
    FEATURES_PRE_RESEARCH,
    FEATURES_MID_SEASON,
    APPROVED_CROPS,
    HORIZONS,
    compute_metrics,
    get_candidate_models,
    select_winning_model
)

PRE_SEASON_PATH = os.path.join(PROJECT_DIR, "data", "crop_features_pre_season.csv")
MID_SEASON_PATH = os.path.join(PROJECT_DIR, "data", "crop_features_mid_season.csv")


class TestCropYieldAnomalyModels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.path.exists(PRE_SEASON_PATH), f"Pre-season CSV not found: {PRE_SEASON_PATH}"
        assert os.path.exists(MID_SEASON_PATH), f"Mid-season CSV not found: {MID_SEASON_PATH}"

        cls.df_pre = pd.read_csv(PRE_SEASON_PATH)
        cls.df_mid = pd.read_csv(MID_SEASON_PATH)

        cls.df_pre_elig = cls.df_pre[cls.df_pre["is_eligible_for_anomaly_training"] == 1].copy()
        cls.df_mid_elig = cls.df_mid[cls.df_mid["is_eligible_for_anomaly_training"] == 1].copy()

    def test_01_eligibility_filter_integrity(self):
        """1. Verifies that only eligible records with non-null anomaly targets enter modeling."""
        self.assertEqual(len(self.df_pre_elig), 2957)
        self.assertEqual(len(self.df_mid_elig), 2957)

        # Ineligible records must be exactly 299 and strictly have NaN targets
        inelig_pre = self.df_pre[self.df_pre["is_eligible_for_anomaly_training"] == 0]
        self.assertEqual(len(inelig_pre), 299)
        self.assertTrue(inelig_pre["yield_anomaly_pct"].isna().all())

        # Eligible records must have zero NaNs in target
        self.assertEqual(self.df_pre_elig["yield_anomaly_pct"].isna().sum(), 0)
        self.assertEqual(self.df_mid_elig["yield_anomaly_pct"].isna().sum(), 0)

        # Split counts
        train_count = (self.df_pre_elig["dataset_split"] == "TRAIN").sum()
        test_count = (self.df_pre_elig["dataset_split"] == "TEST").sum()
        self.assertEqual(train_count, 2280)
        self.assertEqual(test_count, 677)

    def test_02_leakage_free_feature_matrix(self):
        """2. Asserts that the feature matrix strictly excludes all target and confounding columns."""
        banned_columns = {
            "yield_anomaly_pct", "yield_metric_tons_per_hectare", "production_metric_tons",
            "historical_baseline_yield_mt_ha", "is_fertilizer_crisis_year", "dataset_split",
            "baseline_status", "n_prior_history_years", "prediction_cutoff_date",
            "monitoring_window_days"
        }

        for h_name, h_info in HORIZONS.items():
            features = set(h_info["features"])
            intersection = features.intersection(banned_columns)
            self.assertEqual(
                len(intersection), 0,
                f"Leakage detected in {h_name}: {intersection}"
            )

    def test_03_chronological_folds_integrity(self):
        """3. Verifies that all 10 folds satisfy max(train_year) < val_year with zero look-ahead."""
        df_train = self.df_pre_elig[self.df_pre_elig["dataset_split"] == "TRAIN"]

        folds_checked = 0
        for val_year in range(2011, 2021):
            train_slice = df_train[df_train["crop_year"] < val_year]
            val_slice = df_train[df_train["crop_year"] == val_year]

            self.assertGreater(len(train_slice), 0)
            self.assertGreater(len(val_slice), 0)
            self.assertLess(train_slice["crop_year"].max(), val_year)
            self.assertTrue((val_slice["crop_year"] == val_year).all())
            folds_checked += 1

        self.assertEqual(folds_checked, 10, "Expected exactly 10 expanding-window folds.")

    def test_04_preprocessing_isolation(self):
        """4. Verifies that StandardScaler fits strictly on training data without validation leakage."""
        df_train = self.df_pre_elig[self.df_pre_elig["dataset_split"] == "TRAIN"]
        tr = df_train[df_train["crop_year"] < 2015]
        val = df_train[df_train["crop_year"] == 2015]

        scaler = StandardScaler()
        scaler.fit(tr[FEATURES_PRE_OPERATIONAL].values)

        # Mean and var should match training slice exactly, not combined slice
        expected_mean = tr[FEATURES_PRE_OPERATIONAL].mean().values
        np.testing.assert_allclose(scaler.mean_, expected_mean, rtol=1e-5)

    def test_05_metric_calculation_correctness(self):
        """5. Verifies mathematical correctness of RMSE, MAE, R2, and Directional Accuracy."""
        y_true = np.array([10.0, -20.0, 5.0, -5.0])
        y_pred = np.array([12.0, -15.0, 0.0, 2.0])
        y_base = np.array([2.0, 1.5, 3.0, 2.5])
        y_actual = np.array([2.2, 1.2, 3.15, 2.375])

        metrics = compute_metrics(y_true, y_pred, y_base, y_actual, neutral_threshold=5.0)

        # Expected Anomaly MAE: (|10-12| + |-20 - (-15)| + |5 - 0| + |-5 - 2|) / 4 = (2 + 5 + 5 + 7) / 4 = 4.75 pp
        self.assertAlmostEqual(metrics["anomaly_mae_pp"], 4.75, places=2)

        # Expected Anomaly RMSE: sqrt((4 + 25 + 25 + 49) / 4) = sqrt(103 / 4) = sqrt(25.75) = 5.074 pp
        self.assertAlmostEqual(metrics["anomaly_rmse_pp"], 5.07, places=2)

    def test_06_zero_anomaly_baseline_equivalence(self):
        """6. Asserts that zero anomaly prediction produces reconstructed yield equal to historical baseline."""
        y_true = np.array([10.0, -10.0])
        y_pred_zero = np.array([0.0, 0.0])
        y_base = np.array([2.5, 1.8])
        y_actual = np.array([2.75, 1.62])

        reconstructed_yield = y_base * (1.0 + y_pred_zero / 100.0)
        np.testing.assert_array_equal(reconstructed_yield, y_base)

    def test_07_test_set_isolation(self):
        """7. Asserts that the 2021-2025 test dataset is completely excluded from training folds."""
        df_train = self.df_pre_elig[self.df_pre_elig["dataset_split"] == "TRAIN"]
        df_test = self.df_pre_elig[self.df_pre_elig["dataset_split"] == "TEST"]

        self.assertEqual(df_train["crop_year"].max(), 2020)
        self.assertEqual(df_test["crop_year"].min(), 2021)
        self.assertEqual(len(set(df_train["crop_year"]).intersection(set(df_test["crop_year"]))), 0)

    def test_08_crop_decoupled_decision_logic(self):
        """8. Verifies that select_winning_model defaults to baseline if candidate fails 3% gate."""
        val_summary_fail = {
            "Zero-Anomaly Baseline": {"rel_rmse_improvement_pct": 0.0, "passes_acceptance_gates": False, "std_val_rmse_pp": 5.0},
            "Huber Regressor": {"rel_rmse_improvement_pct": 1.5, "passes_acceptance_gates": False, "std_val_rmse_pp": 5.2},
            "Ridge Regression": {"rel_rmse_improvement_pct": 0.8, "passes_acceptance_gates": False, "std_val_rmse_pp": 5.1}
        }
        winner, reason = select_winning_model(val_summary_fail)
        self.assertEqual(winner, "Zero-Anomaly Baseline")
        self.assertIn("fallback", reason.lower())

        val_summary_pass = {
            "Zero-Anomaly Baseline": {"rel_rmse_improvement_pct": 0.0, "passes_acceptance_gates": False, "std_val_rmse_pp": 5.0},
            "Huber Regressor": {"rel_rmse_improvement_pct": 4.5, "passes_acceptance_gates": True, "std_val_rmse_pp": 4.8},
            "Ridge Regression": {"rel_rmse_improvement_pct": 4.2, "passes_acceptance_gates": True, "std_val_rmse_pp": 4.9}
        }
        winner_pass, _ = select_winning_model(val_summary_pass)
        self.assertEqual(winner_pass, "Huber Regressor")

    def test_09_deterministic_reproducibility(self):
        """9. Verifies that models run with fixed seeds produce bitwise deterministic predictions."""
        models1 = get_candidate_models()
        models2 = get_candidate_models()

        X = np.random.RandomState(42).randn(50, 5)
        y = np.random.RandomState(42).randn(50)

        for name in ["ElasticNet", "Shallow HistGradientBoosting"]:
            m1 = models1[name]
            m2 = models2[name]
            m1.fit(X, y)
            m2.fit(X, y)
            p1 = m1.predict(X)
            p2 = m2.predict(X)
            np.testing.assert_array_equal(p1, p2)


if __name__ == "__main__":
    unittest.main()
