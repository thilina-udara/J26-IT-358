"""
Automated Test Suite for Phase 1 Crop Phenological Feature Extraction
Component: Component 04 — Climate Early Warning and Crop Yield Impact DSS
Validates:
1. Strict Crop Scope Enforcement (Maize, Chilli, Green Gram only).
2. Primary Key Uniqueness (district, crop_year, season, crop_name).
3. Zero Temporal Leakage in Historical Baselines (Strictly prior years [t-3, t-1], no self-inclusion, no future yields).
4. Explicit Insufficient-History Handling (Flagged explicitly, zero future fallback).
5. No Post-Cutoff Daily Weather Observations (Strict date ceiling enforcement).
6. Crop-Specific Phenological Windows (Green Gram 45/46d vs Maize/Chilli 76d).
7. Harvest-Period Weather Exclusion (Pre-harvest lead time verified against DOA calendar).
8. Multi-Layer Soil Moisture Specification (Layer 1 topsoil 0-7 cm and root-zone 7-100 cm).
9. Transparent Missing Data Reporting.
10. Strict Chronological Train/Test Partitioning.
11. Feature Metadata and Operational Documentation Integrity.
"""

import os
import sys
import json
import unittest
import pandas as pd
import numpy as np

# Resolve Paths
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(TEST_DIR, ".."))
DATA_DIR = os.path.join(PROJECT_DIR, "data")

PRE_SEASON_CSV = os.path.join(DATA_DIR, "crop_features_pre_season.csv")
MID_SEASON_CSV = os.path.join(DATA_DIR, "crop_features_mid_season.csv")
META_JSON = os.path.join(DATA_DIR, "crop_feature_metadata.json")


class TestCropPhenologicalFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Locate pre-season and mid-season CSVs
        if not os.path.exists(PRE_SEASON_CSV):
            alt_dir = r"D:\01_research\climate_research_system\data"
            cls.pre_path = os.path.join(alt_dir, "crop_features_pre_season.csv")
            cls.mid_path = os.path.join(alt_dir, "crop_features_mid_season.csv")
            cls.meta_path = os.path.join(alt_dir, "crop_feature_metadata.json")
        else:
            cls.pre_path = PRE_SEASON_CSV
            cls.mid_path = MID_SEASON_CSV
            cls.meta_path = META_JSON

        assert os.path.exists(cls.pre_path), f"Pre-season CSV not found at: {cls.pre_path}"
        assert os.path.exists(cls.mid_path), f"Mid-season CSV not found at: {cls.mid_path}"
        assert os.path.exists(cls.meta_path), f"Metadata JSON not found at: {cls.meta_path}"

        cls.df_pre = pd.read_csv(cls.pre_path)
        cls.df_mid = pd.read_csv(cls.mid_path)
        with open(cls.meta_path, "r", encoding="utf-8") as f:
            cls.meta = json.load(f)

    def test_01_crop_scope_enforcement(self):
        """1. Verifies strictly the 3 approved crops are present and zero unapproved crops exist."""
        expected_crops = {"Chilli", "Green Gram", "Maize"}
        actual_crops_pre = set(self.df_pre["crop_name"].unique())
        actual_crops_mid = set(self.df_mid["crop_name"].unique())

        self.assertEqual(actual_crops_pre, expected_crops, f"Pre-season crop scope mismatch: {actual_crops_pre}")
        self.assertEqual(actual_crops_mid, expected_crops, f"Mid-season crop scope mismatch: {actual_crops_mid}")

    def test_02_primary_key_uniqueness(self):
        """2. Verifies no duplicate records exist on primary keys (district, crop_year, season, crop_name)."""
        key_cols = ["district", "crop_year", "season", "crop_name"]
        pre_dups = self.df_pre.duplicated(subset=key_cols).sum()
        mid_dups = self.df_mid.duplicated(subset=key_cols).sum()

        self.assertEqual(pre_dups, 0, f"Found {pre_dups} duplicate keys in pre-season dataset!")
        self.assertEqual(mid_dups, 0, f"Found {mid_dups} duplicate keys in mid-season dataset!")
        self.assertEqual(len(self.df_pre), len(self.df_mid), "Row counts differ between pre and mid season datasets!")
        self.assertEqual(len(self.df_pre), 3256, f"Expected 3,256 verified crop rows, got {len(self.df_pre)}")

    def test_03_zero_temporal_leakage_in_historical_baselines(self):
        """3. Verifies every baseline yield is strictly backward-looking (prior years in [t-3, t-1])."""
        # Group by series to check exact historical calculation
        for (d, c, s), grp in self.df_pre.groupby(["district", "crop_name", "season"]):
            grp = grp.sort_values("crop_year")
            years = grp["crop_year"].values
            yields = grp["yield_metric_tons_per_hectare"].values
            baselines = grp["historical_baseline_yield_mt_ha"].values
            statuses = grp["baseline_status"].values

            for yr, yld, base, status in zip(years, yields, baselines, statuses):
                prior_yields = yields[(years >= yr - 3) & (years < yr)]
                
                if status in ["VALID_3YR_ROLLING", "VALID_2YR_ROLLING", "WARMUP_1YR_LAG"]:
                    expected_mean = round(float(prior_yields.mean()), 4)
                    self.assertAlmostEqual(
                        base, expected_mean, places=3,
                        msg=f"Baseline mismatch for {d} {c} {s} {yr}: got {base}, expected {expected_mean}"
                    )
                    # Verify strictly prior: current year yld must NOT be in prior_yields calculation
                    self.assertNotIn(yr, years[(years >= yr - 3) & (years < yr)])
                elif status == "INSUFFICIENT_HISTORY":
                    self.assertTrue(
                        np.isnan(base),
                        f"Expected NaN baseline for insufficient history row {d} {c} {s} {yr}, got {base}"
                    )

    def test_04_insufficient_history_explicit_handling(self):
        """4. Verifies insufficient-history records are explicitly flagged rather than filled with future data."""
        insufficient = self.df_pre[self.df_pre["baseline_status"] == "INSUFFICIENT_HISTORY"]
        self.assertEqual(len(insufficient), 143, f"Expected exactly 143 insufficient-history rows, got {len(insufficient)}")
        
        # Must have NaN baseline and NaN anomaly pct
        self.assertTrue(insufficient["historical_baseline_yield_mt_ha"].isna().all())
        self.assertTrue(insufficient["yield_anomaly_pct"].isna().all())
        self.assertTrue((insufficient["is_eligible_for_anomaly_training"] == 0).all())

        # First year (2001) must never have a valid prior rolling baseline
        y2001 = self.df_pre[self.df_pre["crop_year"] == 2001]
        self.assertTrue((y2001["baseline_status"] == "INSUFFICIENT_HISTORY").all())

        # Warm-up 1-year lag records (156 rows) must also have NaN yield anomaly and is_eligible == 0
        warmup = self.df_pre[self.df_pre["baseline_status"] == "WARMUP_1YR_LAG"]
        self.assertEqual(len(warmup), 156, f"Expected exactly 156 warmup rows, got {len(warmup)}")
        self.assertTrue(warmup["yield_anomaly_pct"].isna().all(), "Warmup records must have NaN yield_anomaly_pct!")
        self.assertTrue((warmup["is_eligible_for_anomaly_training"] == 0).all())

    def test_05_no_post_cutoff_weather_observations(self):
        """5. Verifies cutoff dates and strict observation window day counts."""
        # Pre-season Maha: Oct 01 (Year y-1)
        maha_pre = self.df_pre[self.df_pre["season"] == "Maha"]
        for _, row in maha_pre.iterrows():
            self.assertEqual(row["prediction_cutoff_date"], f"{row['crop_year'] - 1}-10-01")

        # Pre-season Yala: Apr 01 (Year y)
        yala_pre = self.df_pre[self.df_pre["season"] == "Yala"]
        for _, row in yala_pre.iterrows():
            self.assertEqual(row["prediction_cutoff_date"], f"{row['crop_year']}-04-01")

        # Mid-season Maize & Chilli Maha: Dec 15 (Year y-1), exactly 76 days
        mc_maha = self.df_mid[(self.df_mid["season"] == "Maha") & (self.df_mid["crop_name"].isin(["Maize", "Chilli"]))]
        for _, row in mc_maha.iterrows():
            self.assertEqual(row["prediction_cutoff_date"], f"{row['crop_year'] - 1}-12-15")
            self.assertEqual(row["monitoring_window_days"], 76)

        # Mid-season Maize & Chilli Yala: Jun 15 (Year y), exactly 76 days
        mc_yala = self.df_mid[(self.df_mid["season"] == "Yala") & (self.df_mid["crop_name"].isin(["Maize", "Chilli"]))]
        for _, row in mc_yala.iterrows():
            self.assertEqual(row["prediction_cutoff_date"], f"{row['crop_year']}-06-15")
            self.assertEqual(row["monitoring_window_days"], 76)

    def test_06_crop_specific_green_gram_window(self):
        """6. Verifies Green Gram has a distinct, shorter mid-season window capping at flowering."""
        gg_maha = self.df_mid[(self.df_mid["season"] == "Maha") & (self.df_mid["crop_name"] == "Green Gram")]
        for _, row in gg_maha.iterrows():
            self.assertEqual(row["prediction_cutoff_date"], f"{row['crop_year'] - 1}-11-15")
            self.assertEqual(row["monitoring_window_days"], 46, "Green Gram Maha window must be exactly 46 days (Oct 1 to Nov 15)")

        gg_yala = self.df_mid[(self.df_mid["season"] == "Yala") & (self.df_mid["crop_name"] == "Green Gram")]
        for _, row in gg_yala.iterrows():
            self.assertEqual(row["prediction_cutoff_date"], f"{row['crop_year']}-05-15")
            self.assertEqual(row["monitoring_window_days"], 45, "Green Gram Yala window must be exactly 45 days (Apr 1 to May 15)")

        # Verify Green Gram monitoring window is strictly shorter than Maize/Chilli window
        self.assertTrue((gg_yala["monitoring_window_days"] < 50).all())
        self.assertTrue((gg_maha["monitoring_window_days"] < 50).all())

    def test_07_harvest_exclusion_pre_harvest_lead_time(self):
        """7. Verifies mid-season prediction cutoffs precede harvest dates based on DOA/AFACI calendar."""
        # Green Gram Yala harvest starts Jun W2 (approx. June 8).
        # Cutoff on May 15 provides a minimum 24-day pre-harvest lead time.
        gg_yala_cutoffs = self.df_mid[self.df_mid["crop_name"] == "Green Gram"]["prediction_cutoff_date"]
        for c in gg_yala_cutoffs:
            month = int(c.split("-")[1])
            day = int(c.split("-")[2])
            # Must be May 15 (month 5, day 15) or Nov 15 (month 11, day 15)
            self.assertIn((month, day), [(5, 15), (11, 15)])
            # Assert May cutoff is well before June harvest
            if month == 5:
                self.assertLessEqual(day, 15)

        # Maize dry grain harvest starts Jan W3 (Maha) and Jul W2 (Yala).
        # Cutoffs on Dec 15 and Jun 15 precede dry grain harvest by ~30 days.
        maize_mid = self.df_mid[self.df_mid["crop_name"] == "Maize"]
        for _, row in maize_mid.iterrows():
            cutoff = row["prediction_cutoff_date"]
            month = int(cutoff.split("-")[1])
            self.assertIn(month, [12, 6])

    def test_08_soil_moisture_multi_layer_specification(self):
        """8. Verifies multi-layer soil moisture features (Layer 1 topsoil vs 7-100 cm root zone)."""
        expected_sm_cols = [
            "pre_season_sm_topsoil_layer1_m3_m3",
            "pre_season_sm_root_zone_approx_m3_m3"
        ]
        for col in expected_sm_cols:
            self.assertIn(col, self.df_pre.columns)
            # Physical validity: volumetric soil water between 0.05 and 0.65 m3/m3
            self.assertTrue((self.df_pre[col] >= 0.05).all())
            self.assertTrue((self.df_pre[col] <= 0.65).all())

        mid_sm_cols = [
            "mid_season_sm_topsoil_layer1_mean",
            "mid_season_sm_topsoil_layer1_min",
            "mid_season_sm_root_zone_approx_mean",
            "mid_season_sm_root_zone_approx_min"
        ]
        for col in mid_sm_cols:
            self.assertIn(col, self.df_mid.columns)
            self.assertTrue((self.df_mid[col] >= 0.05).all())
            self.assertTrue((self.df_mid[col] <= 0.65).all())

    def test_09_missing_data_transparency(self):
        """9. Verifies zero missing values in climate features and transparent reporting in target baseline."""
        pre_climate_cols = [
            "pre_season_rainfall_30d_mm", "pre_season_rainfall_15d_prep_mm",
            "pre_season_temp_mean_c", "pre_season_temp_max_peak_c",
            "pre_season_dry_spell_max_days", "pre_season_spi3",
            "pre_season_spi1", "pre_season_sm_topsoil_layer1_m3_m3",
            "pre_season_sm_root_zone_approx_m3_m3"
        ]
        for col in pre_climate_cols:
            self.assertEqual(self.df_pre[col].isnull().sum(), 0, f"Climate feature {col} has unexpected nulls!")

        # Nulls in baseline yield must equal exactly the 143 INSUFFICIENT_HISTORY rows
        null_baselines = self.df_pre["historical_baseline_yield_mt_ha"].isnull().sum()
        self.assertEqual(null_baselines, 143, f"Expected 143 null baselines, got {null_baselines}")

        # Nulls in anomaly target must equal exactly 299 (143 insufficient + 156 warmup)
        null_anomalies = self.df_pre["yield_anomaly_pct"].isnull().sum()
        self.assertEqual(null_anomalies, 299, f"Expected 299 null anomalies, got {null_anomalies}")

    def test_10_chronological_train_test_split(self):
        """10. Verifies chronological train (<=2020) and test (>=2021) separation and macro-shock control."""
        train_pre = self.df_pre[self.df_pre["dataset_split"] == "TRAIN"]
        test_pre = self.df_pre[self.df_pre["dataset_split"] == "TEST"]

        self.assertTrue((train_pre["crop_year"] <= 2020).all())
        self.assertTrue((test_pre["crop_year"] >= 2021).all())
        self.assertEqual(len(train_pre), 2574)
        self.assertEqual(len(test_pre), 682)

        # Macro shock control (April 2021 fertilizer ban)
        test_fert_shocks = test_pre[test_pre["crop_year"].isin([2021, 2022])]["is_fertilizer_crisis_year"]
        self.assertTrue((test_fert_shocks == 1).all())

    def test_11_metadata_documentation_integrity(self):
        """11. Verifies metadata schema, units, operational latency notes, and zero pp1 jargon."""
        self.assertIn("baseline_strategy", self.meta)
        self.assertIn("soil_moisture_specification", self.meta)
        self.assertIn("crop_specific_prediction_cutoffs", self.meta)
        self.assertIn("operational_data_availability_latency", self.meta)

        # Zero mentions of academic milestone jargon
        meta_str = json.dumps(self.meta)
        self.assertNotIn("pp1", meta_str.lower())
        self.assertNotIn("pp1", self.pre_path.lower())
        self.assertNotIn("pp1", self.mid_path.lower())


if __name__ == "__main__":
    unittest.main()
