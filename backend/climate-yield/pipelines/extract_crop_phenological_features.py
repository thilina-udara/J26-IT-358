"""
Phase 1: Leakage-Free Phenological Feature Extraction Module
Component: Component 04 — Climate Early Warning and Crop Yield Impact DSS
Target Crops: Maize, Chilli, Green Gram

Methodological Safeguards Enforced:
1. Strict pre-season and crop-specific mid-season operational decision cutoffs.
2. Complete exclusion of future observations and harvest-period weather.
3. Crop-calendar aligned phenological monitoring based on DOA/AFACI guidance:
   - Maize & Chilli: 76-day mid-season window (Dec 15 Maha / Jun 15 Yala).
   - Green Gram: 45/46-day mid-season window (Nov 15 Maha / May 15 Yala) capping at flowering.
4. Strictly lagged historical baseline (prior 3 years strictly preceding current sample).
   - Zero look-ahead leakage; samples with < 2 prior years explicitly flagged as insufficient.
5. Multi-layer soil moisture:
   - Layer 1 (0-7 cm) topsoil skin moisture.
   - Layers 2 & 3 thickness-weighted sub-surface root zone approximation (7-100 cm).
6. Macroeconomic shock flag (2021/22 chemical fertilizer import ban control).
"""

import os
import sys
import json
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd

# Path Resolution
RESEARCH_DIR = r"D:\01_research\climate_research_system"
BACKEND_DIR = r"D:\Project\GitHubClone\J26-IT-358\backend\climate-yield"

# Raw Data Sources (Authoritative gridded & official statistics panels)
CROP_PATH = os.path.join(RESEARCH_DIR, "06_district_boundaries", "processed", "district_crop_records.csv")
WEATHER_PATH = os.path.join(RESEARCH_DIR, "01_weather_data", "sri_lanka_weather_daily_cleaned.csv")
SPI_PATH = os.path.join(RESEARCH_DIR, "02_drought_spi", "district_monthly_spi.csv")
SM_LAYERS_PATH = os.path.join(RESEARCH_DIR, "03_era5_soil_moisture", "processed", "district_monthly_soil_moisture_layers_1981_2025.csv")

# Output Directories
OUTPUT_DATA_DIRS = [
    os.path.join(RESEARCH_DIR, "data"),
    os.path.join(BACKEND_DIR, "data")
]

for out_d in OUTPUT_DATA_DIRS:
    try:
        os.makedirs(out_d, exist_ok=True)
    except Exception:
        pass

# Crop Scope and Canonical Names
TARGET_CROP_MAPPING = {
    "Maize": "Maize",
    "Chillies Green": "Chilli",
    "Green Gram": "Green Gram"
}

# Major Irrigation Districts (Tier 1 Water Availability Classification)
MAJOR_IRRIGATION_DISTRICTS = {
    "Anuradhapura", "Polonnaruwa", "Ampara", "Hambantota",
    "Kurunegala", "Trincomalee", "Batticaloa", "Monaragala",
    "Mannar", "Vavuniya", "Kilinochchi"
}


def load_and_clean_crop_targets() -> pd.DataFrame:
    """
    Loads DCS seasonal crop records and isolates valid observations
    for Maize, Chilli, and Green Gram across 2001-2025.
    Constructs strictly lagged historical baselines with zero look-ahead leakage.
    """
    if not os.path.exists(CROP_PATH):
        raise FileNotFoundError(f"DCS crop records not found at: {CROP_PATH}")

    raw_crops = pd.read_csv(CROP_PATH)
    
    # Filter strictly to seasonal records (exclude annual 'Total')
    seasonal_crops = raw_crops[raw_crops["season"].isin(["Maha", "Yala"])].copy()
    
    # Filter strictly to approved target crops
    target_crops = seasonal_crops[seasonal_crops["crop_name"].isin(TARGET_CROP_MAPPING.keys())].copy()
    target_crops["crop_name"] = target_crops["crop_name"].map(TARGET_CROP_MAPPING)

    # Standardize and aggregate district names
    agg_crops = target_crops.groupby(
        ["boundary_district_name", "year", "season", "crop_name"],
        as_index=False
    ).agg({
        "cultivated_extent_hectares": "sum",
        "production_metric_tons": "sum"
    })

    agg_crops.rename(columns={
        "boundary_district_name": "district",
        "year": "crop_year"
    }, inplace=True)

    # Filter strictly for valid activity (extent > 0 and production > 0)
    valid_crops = agg_crops[
        (agg_crops["cultivated_extent_hectares"] > 0) &
        (agg_crops["production_metric_tons"] > 0)
    ].copy()

    valid_crops["yield_metric_tons_per_hectare"] = (
        valid_crops["production_metric_tons"] / valid_crops["cultivated_extent_hectares"]
    )

    # Irrigation zone classification
    valid_crops["irrigation_zone_type"] = valid_crops["district"].apply(
        lambda d: "Major Irrigation" if d in MAJOR_IRRIGATION_DISTRICTS else "Minor / Rainfed"
    )

    # Sort strictly chronologically for rolling baseline computation
    valid_crops = valid_crops.sort_values(by=["district", "crop_name", "season", "crop_year"]).reset_index(drop=True)

    # Compute strictly backward-looking historical baseline (prior years strictly earlier than current sample)
    baseline_records = []
    for (d, c, s), grp in valid_crops.groupby(["district", "crop_name", "season"]):
        grp = grp.sort_values("crop_year")
        years = grp["crop_year"].values
        yields = grp["yield_metric_tons_per_hectare"].values

        for yr, yld in zip(years, yields):
            # Prior 3 years strictly: yr - 3 <= y < yr (Sample yr and future yields strictly excluded)
            prior_records = yields[(years >= yr - 3) & (years < yr)]
            n_prior = len(prior_records)

            if n_prior >= 2:
                base_val = round(float(prior_records.mean()), 4)
                status = "VALID_3YR_ROLLING" if n_prior == 3 else "VALID_2YR_ROLLING"
                eligible = 1
            elif n_prior == 1:
                base_val = round(float(prior_records.mean()), 4)
                status = "WARMUP_1YR_LAG"
                eligible = 0
            else:
                base_val = np.nan
                status = "INSUFFICIENT_HISTORY"
                eligible = 0

            baseline_records.append({
                "district": d,
                "crop_name": c,
                "season": s,
                "crop_year": yr,
                "historical_baseline_yield_mt_ha": base_val,
                "baseline_status": status,
                "n_prior_history_years": n_prior,
                "is_eligible_for_anomaly_training": eligible
            })

    df_base = pd.DataFrame(baseline_records)
    merged_crops = pd.merge(valid_crops, df_base, on=["district", "crop_name", "season", "crop_year"], how="left")

    # Yield Anomaly Target (% Relative Deficit or Surplus)
    # Calculated strictly when a defensible baseline exists (>= 2 preceding years); NaN otherwise
    merged_crops["yield_anomaly_pct"] = np.where(
        pd.notna(merged_crops["historical_baseline_yield_mt_ha"]) &
        (merged_crops["historical_baseline_yield_mt_ha"] > 0) &
        (merged_crops["is_eligible_for_anomaly_training"] == 1),
        ((merged_crops["yield_metric_tons_per_hectare"] - merged_crops["historical_baseline_yield_mt_ha"]) /
         merged_crops["historical_baseline_yield_mt_ha"]) * 100.0,
        np.nan
    )

    # Macroeconomic Confounder Control: April 2021 nationwide chemical fertilizer import ban
    merged_crops["is_fertilizer_crisis_year"] = merged_crops["crop_year"].isin([2021, 2022]).astype(int)

    return merged_crops


def extract_climate_features() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extracts strictly leakage-free Pre-Season and Crop-Specific Mid-Season climate features
    across all 25 districts and 2001-2025.
    
    Incorporates:
    - ECMWF ERA5-Land multi-layer soil moisture (Layer 1: 0-7 cm, Layer 2: 7-28 cm, Layer 3: 28-100 cm).
    - Crop-specific phenological cutoffs:
      * Maize & Chilli: Dec 15 (Maha) / Jun 15 (Yala) (76-day window).
      * Green Gram: Nov 15 (Maha) / May 15 (Yala) (45/46-day window, pre-harvest flowering).
    """
    print("Loading daily weather, monthly SPI, and multi-layer soil moisture datasets...")
    df_weather = pd.read_csv(WEATHER_PATH)
    df_weather["date"] = pd.to_datetime(df_weather["date"])
    df_weather["year"] = df_weather["date"].dt.year
    df_weather["month"] = df_weather["date"].dt.month
    df_weather["day"] = df_weather["date"].dt.day

    df_spi = pd.read_csv(SPI_PATH)
    df_sm = pd.read_csv(SM_LAYERS_PATH)

    # Calculate thickness-weighted root-zone approximation across Layers 2 and 3:
    # Layer 2 thickness = 21 cm (7 to 28 cm)
    # Layer 3 thickness = 72 cm (28 to 100 cm)
    # Total thickness = 93 cm
    df_sm["sm_root_zone_approx_m3_m3"] = (
        (21.0 * df_sm["soil_moisture_layer2_m3_m3"] + 72.0 * df_sm["soil_moisture_layer3_m3_m3"]) / 93.0
    )

    # Fast Lookups: (district, year, month)
    spi_lookup = df_spi.set_index(["district", "year", "month"])[["spi_1", "spi_3", "rainfall_monthly_mm"]].to_dict("index")
    sm_l1_lookup = df_sm.set_index(["district_name", "year", "month"])["soil_moisture_layer1_m3_m3"].to_dict()
    sm_rz_lookup = df_sm.set_index(["district_name", "year", "month"])["sm_root_zone_approx_m3_m3"].to_dict()

    districts = sorted(df_weather["district"].unique())
    years = range(2001, 2026)
    target_crops = ["Maize", "Chilli", "Green Gram"]

    pre_records = []
    mid_records = []

    print("Extracting operational decision features across districts, seasons, and crops...")
    for d in districts:
        w_dist = df_weather[df_weather["district"] == d]

        for y in years:
            # ==================================================================
            # 1. MAHA SEASON OF CROP YEAR y
            # Sowing window: Oct W2 - Nov W3 (Year y-1)
            # ==================================================================

            # --- A. Pre-Season Milestone (Prediction Cutoff: October 01, Year y-1) ---
            # Observable period: September 1 to September 30, Year y-1 (Common across crops)
            w_sep = w_dist[(w_dist["year"] == y - 1) & (w_dist["month"] == 9)]
            w_sep_late = w_dist[(w_dist["year"] == y - 1) & (w_dist["month"] == 9) & (w_dist["day"] >= 16)]

            spi_info_sep = spi_lookup.get((d, y - 1, 9), {})
            sm_sep_l1 = sm_l1_lookup.get((d, y - 1, 9), np.nan)
            sm_sep_rz = sm_rz_lookup.get((d, y - 1, 9), np.nan)

            dry_spell_pre = 0
            curr_dry = 0
            for r in w_sep["rainfall_mm"].values:
                if r < 1.0:
                    curr_dry += 1
                    dry_spell_pre = max(dry_spell_pre, curr_dry)
                else:
                    curr_dry = 0

            pre_payload_maha = {
                "district": d,
                "crop_year": y,
                "season": "Maha",
                "prediction_cutoff_date": f"{y-1}-10-01",
                "pre_season_rainfall_30d_mm": round(float(w_sep["rainfall_mm"].sum()), 2),
                "pre_season_rainfall_15d_prep_mm": round(float(w_sep_late["rainfall_mm"].sum()), 2),
                "pre_season_temp_mean_c": round(float(w_sep["temp_mean"].mean()), 2),
                "pre_season_temp_max_peak_c": round(float(w_sep["temp_max"].max()), 2),
                "pre_season_dry_spell_max_days": dry_spell_pre,
                "pre_season_spi3": round(float(spi_info_sep.get("spi_3", np.nan)), 3),
                "pre_season_spi1": round(float(spi_info_sep.get("spi_1", np.nan)), 3),
                "pre_season_sm_topsoil_layer1_m3_m3": round(float(sm_sep_l1), 4) if pd.notna(sm_sep_l1) else np.nan,
                "pre_season_sm_root_zone_approx_m3_m3": round(float(sm_sep_rz), 4) if pd.notna(sm_sep_rz) else np.nan
            }
            pre_records.append(pre_payload_maha)

            # --- B. Mid-Season Milestones (Crop-Specific Cutoffs) ---
            for c in target_crops:
                if c in ["Maize", "Chilli"]:
                    # Maize & Chilli: Dec 15 cutoff, Oct 1 to Dec 15 monitoring (76 days)
                    w_mid = w_dist[
                        ((w_dist["year"] == y - 1) & (w_dist["month"].isin([10, 11]))) |
                        ((w_dist["year"] == y - 1) & (w_dist["month"] == 12) & (w_dist["day"] <= 15))
                    ]
                    cutoff_date = f"{y-1}-12-15"
                    spi_info = spi_lookup.get((d, y - 1, 11), {})  # November SPI (available by Dec 5)
                    sm_m1_l1 = sm_l1_lookup.get((d, y - 1, 10), np.nan)
                    sm_m2_l1 = sm_l1_lookup.get((d, y - 1, 11), np.nan)
                    sm_m1_rz = sm_rz_lookup.get((d, y - 1, 10), np.nan)
                    sm_m2_rz = sm_rz_lookup.get((d, y - 1, 11), np.nan)
                    
                    l1_vals = [v for v in [sm_m1_l1, sm_m2_l1] if pd.notna(v)]
                    rz_vals = [v for v in [sm_m1_rz, sm_m2_rz] if pd.notna(v)]
                    sm_l1_mean = float(np.mean(l1_vals)) if l1_vals else np.nan
                    sm_l1_min = float(np.min(l1_vals)) if l1_vals else np.nan
                    sm_rz_mean = float(np.mean(rz_vals)) if rz_vals else np.nan
                    sm_rz_min = float(np.min(rz_vals)) if rz_vals else np.nan
                else:
                    # Green Gram: Nov 15 cutoff, Oct 1 to Nov 15 monitoring (46 days)
                    # Excludes late pod maturation and harvest period (Dec W4)
                    w_mid = w_dist[
                        ((w_dist["year"] == y - 1) & (w_dist["month"] == 10)) |
                        ((w_dist["year"] == y - 1) & (w_dist["month"] == 11) & (w_dist["day"] <= 15))
                    ]
                    cutoff_date = f"{y-1}-11-15"
                    spi_info = spi_lookup.get((d, y - 1, 10), {})  # October SPI (available by Nov 5)
                    sm_oct_l1 = sm_l1_lookup.get((d, y - 1, 10), np.nan)
                    sm_oct_rz = sm_rz_lookup.get((d, y - 1, 10), np.nan)
                    sm_l1_mean = float(sm_oct_l1) if pd.notna(sm_oct_l1) else np.nan
                    sm_l1_min = sm_l1_mean
                    sm_rz_mean = float(sm_oct_rz) if pd.notna(sm_oct_rz) else np.nan
                    sm_rz_min = sm_rz_mean

                dry_spell_mid = 0
                curr_dry = 0
                for r in w_mid["rainfall_mm"].values:
                    if r < 1.0:
                        curr_dry += 1
                        dry_spell_mid = max(dry_spell_mid, curr_dry)
                    else:
                        curr_dry = 0

                mid_records.append({
                    "district": d,
                    "crop_year": y,
                    "season": "Maha",
                    "crop_name": c,
                    "prediction_cutoff_date": cutoff_date,
                    "monitoring_window_days": len(w_mid),
                    "mid_season_rainfall_cum_mm": round(float(w_mid["rainfall_mm"].sum()), 2),
                    "mid_season_temp_mean_c": round(float(w_mid["temp_mean"].mean()), 2),
                    "mid_season_temp_max_peak_c": round(float(w_mid["temp_max"].max()), 2),
                    "mid_season_heat_days_ge_34c": int((w_mid["temp_max"] >= 34.0).sum()),
                    "mid_season_heat_days_ge_35c": int((w_mid["temp_max"] >= 35.0).sum()),
                    "mid_season_dry_spell_max_days": dry_spell_mid,
                    "mid_season_heavy_rain_days_ge_50mm": int((w_mid["rainfall_mm"] >= 50.0).sum()),
                    "mid_season_spi3": round(float(spi_info.get("spi_3", np.nan)), 3),
                    "mid_season_spi1": round(float(spi_info.get("spi_1", np.nan)), 3),
                    "mid_season_sm_topsoil_layer1_mean": round(sm_l1_mean, 4) if pd.notna(sm_l1_mean) else np.nan,
                    "mid_season_sm_topsoil_layer1_min": round(sm_l1_min, 4) if pd.notna(sm_l1_min) else np.nan,
                    "mid_season_sm_root_zone_approx_mean": round(sm_rz_mean, 4) if pd.notna(sm_rz_mean) else np.nan,
                    "mid_season_sm_root_zone_approx_min": round(sm_rz_min, 4) if pd.notna(sm_rz_min) else np.nan
                })

            # ==================================================================
            # 2. YALA SEASON OF CROP YEAR y
            # Sowing window: Apr W1 - May W2 (Year y)
            # ==================================================================

            # --- A. Pre-Season Milestone (Prediction Cutoff: April 01, Year y) ---
            # Observable period: March 1 to March 31, Year y (31 days)
            w_mar = w_dist[(w_dist["year"] == y) & (w_dist["month"] == 3)]
            w_mar_late = w_dist[(w_dist["year"] == y) & (w_dist["month"] == 3) & (w_dist["day"] >= 17)]

            spi_info_mar = spi_lookup.get((d, y, 3), {})
            sm_mar_l1 = sm_l1_lookup.get((d, y, 3), np.nan)
            sm_mar_rz = sm_rz_lookup.get((d, y, 3), np.nan)

            dry_spell_yala_pre = 0
            curr_dry = 0
            for r in w_mar["rainfall_mm"].values:
                if r < 1.0:
                    curr_dry += 1
                    dry_spell_yala_pre = max(dry_spell_yala_pre, curr_dry)
                else:
                    curr_dry = 0

            pre_payload_yala = {
                "district": d,
                "crop_year": y,
                "season": "Yala",
                "prediction_cutoff_date": f"{y}-04-01",
                "pre_season_rainfall_30d_mm": round(float(w_mar["rainfall_mm"].sum()), 2),
                "pre_season_rainfall_15d_prep_mm": round(float(w_mar_late["rainfall_mm"].sum()), 2),
                "pre_season_temp_mean_c": round(float(w_mar["temp_mean"].mean()), 2),
                "pre_season_temp_max_peak_c": round(float(w_mar["temp_max"].max()), 2),
                "pre_season_dry_spell_max_days": dry_spell_yala_pre,
                "pre_season_spi3": round(float(spi_info_mar.get("spi_3", np.nan)), 3),
                "pre_season_spi1": round(float(spi_info_mar.get("spi_1", np.nan)), 3),
                "pre_season_sm_topsoil_layer1_m3_m3": round(float(sm_mar_l1), 4) if pd.notna(sm_mar_l1) else np.nan,
                "pre_season_sm_root_zone_approx_m3_m3": round(float(sm_mar_rz), 4) if pd.notna(sm_mar_rz) else np.nan
            }
            pre_records.append(pre_payload_yala)

            # --- B. Mid-Season Milestones (Crop-Specific Cutoffs) ---
            for c in target_crops:
                if c in ["Maize", "Chilli"]:
                    # Maize & Chilli: Jun 15 cutoff, Apr 1 to Jun 15 monitoring (76 days)
                    w_mid = w_dist[
                        ((w_dist["year"] == y) & (w_dist["month"].isin([4, 5]))) |
                        ((w_dist["year"] == y) & (w_dist["month"] == 6) & (w_dist["day"] <= 15))
                    ]
                    cutoff_date = f"{y}-06-15"
                    spi_info = spi_lookup.get((d, y, 5), {})  # May SPI (available by Jun 5)
                    sm_m1_l1 = sm_l1_lookup.get((d, y, 4), np.nan)
                    sm_m2_l1 = sm_l1_lookup.get((d, y, 5), np.nan)
                    sm_m1_rz = sm_rz_lookup.get((d, y, 4), np.nan)
                    sm_m2_rz = sm_rz_lookup.get((d, y, 5), np.nan)
                    
                    l1_vals = [v for v in [sm_m1_l1, sm_m2_l1] if pd.notna(v)]
                    rz_vals = [v for v in [sm_m1_rz, sm_m2_rz] if pd.notna(v)]
                    sm_l1_mean = float(np.mean(l1_vals)) if l1_vals else np.nan
                    sm_l1_min = float(np.min(l1_vals)) if l1_vals else np.nan
                    sm_rz_mean = float(np.mean(rz_vals)) if rz_vals else np.nan
                    sm_rz_min = float(np.min(rz_vals)) if rz_vals else np.nan
                else:
                    # Green Gram: May 15 cutoff, Apr 1 to May 15 monitoring (45 days)
                    # Harvest begins Jun W2 (June 8-15); May 15 cleanly isolates flowering/pod-setting
                    w_mid = w_dist[
                        ((w_dist["year"] == y) & (w_dist["month"] == 4)) |
                        ((w_dist["year"] == y) & (w_dist["month"] == 5) & (w_dist["day"] <= 15))
                    ]
                    cutoff_date = f"{y}-05-15"
                    spi_info = spi_lookup.get((d, y, 4), {})  # April SPI (available by May 5)
                    sm_apr_l1 = sm_l1_lookup.get((d, y, 4), np.nan)
                    sm_apr_rz = sm_rz_lookup.get((d, y, 4), np.nan)
                    sm_l1_mean = float(sm_apr_l1) if pd.notna(sm_apr_l1) else np.nan
                    sm_l1_min = sm_l1_mean
                    sm_rz_mean = float(sm_apr_rz) if pd.notna(sm_apr_rz) else np.nan
                    sm_rz_min = sm_rz_mean

                dry_spell_yala_mid = 0
                curr_dry = 0
                for r in w_mid["rainfall_mm"].values:
                    if r < 1.0:
                        curr_dry += 1
                        dry_spell_yala_mid = max(dry_spell_yala_mid, curr_dry)
                    else:
                        curr_dry = 0

                mid_records.append({
                    "district": d,
                    "crop_year": y,
                    "season": "Yala",
                    "crop_name": c,
                    "prediction_cutoff_date": cutoff_date,
                    "monitoring_window_days": len(w_mid),
                    "mid_season_rainfall_cum_mm": round(float(w_mid["rainfall_mm"].sum()), 2),
                    "mid_season_temp_mean_c": round(float(w_mid["temp_mean"].mean()), 2),
                    "mid_season_temp_max_peak_c": round(float(w_mid["temp_max"].max()), 2),
                    "mid_season_heat_days_ge_34c": int((w_mid["temp_max"] >= 34.0).sum()),
                    "mid_season_heat_days_ge_35c": int((w_mid["temp_max"] >= 35.0).sum()),
                    "mid_season_dry_spell_max_days": dry_spell_yala_mid,
                    "mid_season_heavy_rain_days_ge_50mm": int((w_mid["rainfall_mm"] >= 50.0).sum()),
                    "mid_season_spi3": round(float(spi_info.get("spi_3", np.nan)), 3),
                    "mid_season_spi1": round(float(spi_info.get("spi_1", np.nan)), 3),
                    "mid_season_sm_topsoil_layer1_mean": round(sm_l1_mean, 4) if pd.notna(sm_l1_mean) else np.nan,
                    "mid_season_sm_topsoil_layer1_min": round(sm_l1_min, 4) if pd.notna(sm_l1_min) else np.nan,
                    "mid_season_sm_root_zone_approx_mean": round(sm_rz_mean, 4) if pd.notna(sm_rz_mean) else np.nan,
                    "mid_season_sm_root_zone_approx_min": round(sm_rz_min, 4) if pd.notna(sm_rz_min) else np.nan
                })

    return pd.DataFrame(pre_records), pd.DataFrame(mid_records)


def run_pipeline():
    """Main execution entrypoint for Phase 1 feature extraction."""
    print("=" * 80)
    print("EXECUTING PHASE 1: LEAKAGE-FREE PHENOLOGICAL FEATURE EXTRACTION")
    print("=" * 80)

    # 1. Clean Crop Targets and Historical Baselines
    crops_df = load_and_clean_crop_targets()
    print(f"Loaded {len(crops_df):,} verified crop observations (2001-2025 across 25 districts).")
    print("\nBaseline status breakdown:")
    print(crops_df["baseline_status"].value_counts().to_string())

    # 2. Extract Leakage-Free Climate Features
    df_pre_clim, df_mid_clim = extract_climate_features()
    print(f"\nClimate features extracted: {len(df_pre_clim)} Pre-season and {len(df_mid_clim)} Mid-season records.")

    # 3. Join with Crops to form Dedicated Pre-Season and Mid-Season Datasets
    # Pre-season features are joined on (district, crop_year, season)
    pre_season_dataset = pd.merge(crops_df, df_pre_clim, on=["district", "crop_year", "season"], how="inner")
    
    # Mid-season features are crop-specific and joined on (district, crop_year, season, crop_name)
    mid_season_dataset = pd.merge(crops_df, df_mid_clim, on=["district", "crop_year", "season", "crop_name"], how="inner")

    # Add Chronological Train/Test Split Column
    pre_season_dataset["dataset_split"] = np.where(pre_season_dataset["crop_year"] <= 2020, "TRAIN", "TEST")
    mid_season_dataset["dataset_split"] = np.where(mid_season_dataset["crop_year"] <= 2020, "TRAIN", "TEST")

    print(f"\nFinal Pre-Season Feature Matrix: {len(pre_season_dataset):,} rows across {len(pre_season_dataset.columns)} columns.")
    print(f"Final Mid-Season Feature Matrix: {len(mid_season_dataset):,} rows across {len(mid_season_dataset.columns)} columns.")

    # 4. Save to Output Locations
    for out_d in OUTPUT_DATA_DIRS:
        pre_path = os.path.join(out_d, "crop_features_pre_season.csv")
        mid_path = os.path.join(out_d, "crop_features_mid_season.csv")
        meta_path = os.path.join(out_d, "crop_feature_metadata.json")

        pre_season_dataset.to_csv(pre_path, index=False)
        mid_season_dataset.to_csv(mid_path, index=False)

        metadata = {
            "pipeline_name": "Phase 1 Leakage-Free Crop Phenological Feature Extraction",
            "study_crops": ["Maize", "Chilli", "Green Gram"],
            "total_observations": len(pre_season_dataset),
            "train_observations_2001_2020": int((pre_season_dataset["dataset_split"] == "TRAIN").sum()),
            "test_observations_2021_2025": int((pre_season_dataset["dataset_split"] == "TEST").sum()),
            "eligible_anomaly_training_records": int(((pre_season_dataset["dataset_split"] == "TRAIN") & (pre_season_dataset["is_eligible_for_anomaly_training"] == 1)).sum()),
            "eligible_anomaly_test_records": int(((pre_season_dataset["dataset_split"] == "TEST") & (pre_season_dataset["is_eligible_for_anomaly_training"] == 1)).sum()),
            "excluded_warmup_records_total": int((pre_season_dataset["is_eligible_for_anomaly_training"] == 0).sum()),
            "baseline_strategy": {
                "formula": "Mean of preceding eligible yields in [crop_year - 3, crop_year - 1]",
                "zero_leakage_guarantee": "Current crop_year and all future crop_years are strictly excluded.",
                "eligibility_threshold": "Requires at least 2 preceding years in [t-3, t-1] (is_eligible_for_anomaly_training == 1).",
                "status_types": {
                    "VALID_3YR_ROLLING": "Full 3 preceding years available in [t-3, t-1]. Eligible for training.",
                    "VALID_2YR_ROLLING": "2 preceding years available in [t-3, t-1]. Eligible for training.",
                    "WARMUP_1YR_LAG": "1 preceding year available. Target yield_anomaly_pct set to NaN. Excluded from anomaly training.",
                    "INSUFFICIENT_HISTORY": "0 preceding years available (e.g. 2001). Target yield_anomaly_pct set to NaN. Excluded from anomaly training."
                }
            },
            "pre_season_features": [
                "pre_season_rainfall_30d_mm", "pre_season_rainfall_15d_prep_mm",
                "pre_season_temp_mean_c", "pre_season_temp_max_peak_c",
                "pre_season_dry_spell_max_days", "pre_season_spi3",
                "pre_season_spi1", "pre_season_sm_topsoil_layer1_m3_m3",
                "pre_season_sm_root_zone_approx_m3_m3"
            ],
            "mid_season_features": [
                "mid_season_rainfall_cum_mm", "mid_season_temp_mean_c",
                "mid_season_temp_max_peak_c", "mid_season_heat_days_ge_34c",
                "mid_season_heat_days_ge_35c", "mid_season_dry_spell_max_days",
                "mid_season_heavy_rain_days_ge_50mm", "mid_season_spi3",
                "mid_season_spi1", "mid_season_sm_topsoil_layer1_mean",
                "mid_season_sm_topsoil_layer1_min", "mid_season_sm_root_zone_approx_mean",
                "mid_season_sm_root_zone_approx_min"
            ],
            "soil_moisture_specification": {
                "source": "ECMWF ERA5-Land monthly reanalysis via Copernicus Climate Data Store",
                "topsoil_layer1": "Depth: 0 to 7 cm skin topsoil moisture (m3/m3). Reflects rapid surface drying.",
                "root_zone_approx": "Thickness-weighted average of Layer 2 (7-28 cm, 21 cm) and Layer 3 (28-100 cm, 72 cm): (21*L2 + 72*L3) / 93.",
                "scientific_limitation": "The root zone feature is an approximation from reanalysis modeling across 7-100 cm, not an in-situ probe measurement."
            },
            "crop_specific_prediction_cutoffs": {
                "Maize": {
                    "Maha": {"pre_season": "October 01 (Y-1)", "mid_season": "December 15 (Y-1)", "monitoring_days": 76},
                    "Yala": {"pre_season": "April 01 (Y)", "mid_season": "June 15 (Y)", "monitoring_days": 76},
                    "growth_stage_at_mid_season": "Flowering / Tasseling & Silking (~Day 50-60). Pre-harvest (grain harvest Jan W3 / Jul W2).",
                    "sowing_calendar_evidence": "DOA/AFACI (2013) Maize: Sowing Oct W2-Nov W2 / Apr W1-Apr W4; total life cycle 110-120 days."
                },
                "Chilli": {
                    "Maha": {"pre_season": "October 01 (Y-1)", "mid_season": "December 15 (Y-1)", "monitoring_days": 76},
                    "Yala": {"pre_season": "April 01 (Y)", "mid_season": "June 15 (Y)", "monitoring_days": 76},
                    "growth_stage_at_mid_season": "Flowering / Early fruit development. Pre-harvest for major picking.",
                    "sowing_calendar_evidence": "DOA/AFACI (2013) Chilli: Transplanting Oct W3-Nov W3 / Apr W2-May W2; total life cycle 150-180 days."
                },
                "Green Gram": {
                    "Maha": {"pre_season": "October 01 (Y-1)", "mid_season": "November 15 (Y-1)", "monitoring_days": 46},
                    "Yala": {"pre_season": "April 01 (Y)", "mid_season": "May 15 (Y)", "monitoring_days": 45},
                    "growth_stage_at_mid_season": "Flowering / Pod setting (~Day 30-35). Pre-harvest lead time: capped 3-4 weeks prior to first harvest.",
                    "sowing_calendar_evidence": "DOA/AFACI (2013) Green Gram: Sowing Oct W3-Nov W3 / Apr W2-May W2; harvesting Dec W4-Jan W4 / Jun W2-Jul W3; total life cycle 65-75 days.",
                    "sowing_variability_caveat": "Exact flowering timing varies by 1-2 weeks depending on rainfall onset and farmer planting decisions."
                }
            },
            "operational_data_availability_latency": {
                "real_time_usable_at_cutoff": [
                    "All pre-season and mid-season daily weather aggregations (rainfall, temp, heat days, dry spells)",
                    "Mid-season SPI and Soil Moisture (uses prior closed month: Nov for Dec 15; Oct for Nov 15; May for Jun 15; Apr for May 15, published 8-12 days before cutoff)"
                ],
                "operational_latency_caution_at_cutoff": [
                    "Pre-season SPI-1/SPI-3 (uses Sep for Oct 01 / Mar for Apr 01; requires 1-3 days post month-end for Met Dept calculation)",
                    "Pre-season ERA5-Land monthly soil moisture (official CDS release has 5-7 days latency; real-time operational deployment on Oct 01 / Apr 01 requires preliminary ERA5T data or station probe proxies)"
                ]
            },
            "macro_shock_control": {
                "flag": "is_fertilizer_crisis_year",
                "affected_years": [2021, 2022],
                "rationale": "Statistical control for nationwide chemical fertilizer import ban (April 2021). Not a causal proof or fertilizer advisory tool."
            }
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print(f"Saved artifacts successfully to: {out_d}")

    print("\nPhase 1 Feature Extraction Complete!")


if __name__ == "__main__":
    run_pipeline()
