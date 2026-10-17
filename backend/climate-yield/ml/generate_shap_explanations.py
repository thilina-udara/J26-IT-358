"""
TreeSHAP Explainability Generator
Quantifies global and local climate feature attributions on crop yield.
Generates:
  1. Global Beeswarm Summary Plot (shap_global_summary.png)
  2. Local Drought Shock Waterfall Plot (shap_waterfall_drought.png)
  3. Local Flood/Deluge Shock Waterfall Plot (shap_waterfall_flood.png)
  4. Global Feature Importance Rankings (shap_feature_importance.json)
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import xgboost as xgb
import shap

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "..", "data", "component04_final_seasonal_dataset.csv"))
MODEL_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "yield_model_xgboost.json"))
OUTPUT_DIR = CURRENT_DIR

if not os.path.exists(DATA_PATH):
    local_data = os.path.join(CURRENT_DIR, "component04_final_seasonal_dataset.csv")
    if os.path.exists(local_data):
        DATA_PATH = local_data
    else:
        print(f"ERROR: Dataset component04_final_seasonal_dataset.csv not found at: {DATA_PATH}")
        sys.exit(1)

if not os.path.exists(MODEL_PATH):
    print(f"ERROR: Trained model artifact not found at: {MODEL_PATH}")
    sys.exit(1)

print("=" * 80)
print("GENERATING TREESHAP EXPLAINABLE AI (XAI) ATTRIBUTIONS")
print("=" * 80)
print(f"Dataset : {DATA_PATH}")
print(f"Model   : {MODEL_PATH}")

df = pd.read_csv(DATA_PATH)

NUM_COLS = [
    "rainfall_growing_season_total_mm",
    "temp_growing_season_mean_c",
    "soil_moisture_growing_season_min",
    "spi3_growing_season_worst"
]
CAT_COLS = ["district", "season", "crop_name", "irrigation_zone_type"]

X_raw = pd.get_dummies(df[CAT_COLS + NUM_COLS], columns=CAT_COLS, drop_first=False)

# Human-readable feature naming dictionary for visualization
FEATURE_NAME_MAP = {
    "rainfall_growing_season_total_mm": "Seasonal Rainfall (mm)",
    "soil_moisture_growing_season_min": "Min Soil Moisture (m3/m3)",
    "spi3_growing_season_worst": "Worst SPI-3 (Drought/Wet Index)",
    "temp_growing_season_mean_c": "Mean Temperature (C)",
    "irrigation_zone_type_Major Irrigation": "Zone: Major Irrigation",
    "irrigation_zone_type_Minor / Rainfed": "Zone: Rainfed / Minor",
    "season_Maha": "Season: Maha (NE Monsoon)",
    "season_Yala": "Season: Yala (SW Monsoon)",
    "crop_name_Brinjal": "Crop: Brinjal",
    "crop_name_Chilli": "Crop: Chilli",
    "crop_name_Green Gram": "Crop: Green Gram",
    "crop_name_Maize": "Crop: Maize",
    "crop_name_Okra": "Crop: Okra",
    "crop_name_Pumpkin": "Crop: Pumpkin",
    "crop_name_Tomato": "Crop: Tomato"
}

X_display = X_raw.rename(columns=lambda col: FEATURE_NAME_MAP.get(col, col.replace("district_", "District: ")))

# Test Split (2021-2025 unseen observations)
test_mask = df["crop_year"] >= 2021
X_test_raw = X_raw[test_mask].reset_index(drop=True)
X_test_display = X_display[test_mask].reset_index(drop=True)
test_df = df[test_mask].reset_index(drop=True)

print(f"Evaluating SHAP attributions across {len(X_test_raw):,} unseen test samples (2021-2025)...")

# Load model
xgb_model = xgb.XGBRegressor()
xgb_model.load_model(MODEL_PATH)

# Initialize TreeExplainer
explainer = shap.TreeExplainer(xgb_model)
shap_values = explainer(X_test_raw)

# Assign display feature names to the Explanation object
shap_values.feature_names = list(X_test_display.columns)

# Calculate mean absolute SHAP values
mean_abs_shap = np.mean(np.abs(shap_values.values), axis=0)
feature_ranking = sorted(
    zip(shap_values.feature_names, mean_abs_shap),
    key=lambda x: x[1],
    reverse=True
)

total_shap_mass = sum(mean_abs_shap)
feature_importance_list = [
    {
        "rank": idx + 1,
        "feature": name,
        "mean_abs_shap_mt_ha": round(float(val), 4),
        "relative_importance_pct": round(float((val / total_shap_mass) * 100), 2)
    }
    for idx, (name, val) in enumerate(feature_ranking)
]

print("\n--- Top 10 Features by Global SHAP Importance ---")
for f in feature_importance_list[:10]:
    print(f"  {f['rank']:<2}. {f['feature']:<30} : {f['mean_abs_shap_mt_ha']:.4f} MT/ha ({f['relative_importance_pct']}%)")

# Categorical Group Importance Summary
climate_features = [
    "Seasonal Rainfall (mm)",
    "Min Soil Moisture (m3/m3)",
    "Worst SPI-3 (Drought/Wet Index)",
    "Mean Temperature (C)"
]
climate_importance_sum = sum(f["relative_importance_pct"] for f in feature_importance_list if f["feature"] in climate_features)
crop_importance_sum = sum(f["relative_importance_pct"] for f in feature_importance_list if f["feature"].startswith("Crop:"))
zone_importance_sum = sum(f["relative_importance_pct"] for f in feature_importance_list if f["feature"].startswith("Zone:"))
district_importance_sum = sum(f["relative_importance_pct"] for f in feature_importance_list if f["feature"].startswith("District:"))

importance_summary = {
    "system_name": "Climate-Yield Decision Support Service",
    "evaluation_period": "2021 - 2025 (Unseen Test)",
    "total_samples": int(len(X_test_raw)),
    "group_importance_percentages": {
        "climate_hazards": round(climate_importance_sum, 2),
        "crop_agronomy": round(crop_importance_sum, 2),
        "irrigation_zones": round(zone_importance_sum, 2),
        "spatial_districts": round(district_importance_sum, 2)
    },
    "feature_rankings": feature_importance_list
}

# ------------------------------------------------------------------------------
# Helper for Grouped Local Waterfall Attributions
# ------------------------------------------------------------------------------
def build_grouped_waterfall(idx, test_df, X_test_raw, shap_vals):
    row_meta = test_df.iloc[idx]
    cols = list(X_test_raw.columns)
    
    crop_name = row_meta["crop_name"]
    district = row_meta["district"]
    season = row_meta["season"]
    zone = row_meta["irrigation_zone_type"]
    
    crop_cols = [i for i, c in enumerate(cols) if c.startswith("crop_name_")]
    dist_cols = [i for i, c in enumerate(cols) if c.startswith("district_")]
    season_cols = [i for i, c in enumerate(cols) if c.startswith("season_")]
    zone_cols = [i for i, c in enumerate(cols) if c.startswith("irrigation_zone_type_")]
    
    rain_idx = cols.index("rainfall_growing_season_total_mm")
    soil_idx = cols.index("soil_moisture_growing_season_min")
    spi_idx = cols.index("spi3_growing_season_worst")
    temp_idx = cols.index("temp_growing_season_mean_c")
    
    crop_shap = sum(shap_vals.values[idx][i] for i in crop_cols)
    dist_shap = sum(shap_vals.values[idx][i] for i in dist_cols)
    season_shap = sum(shap_vals.values[idx][i] for i in season_cols)
    zone_shap = sum(shap_vals.values[idx][i] for i in zone_cols)
    
    rain_shap = shap_vals.values[idx][rain_idx]
    soil_shap = shap_vals.values[idx][soil_idx]
    spi_shap = shap_vals.values[idx][spi_idx]
    temp_shap = shap_vals.values[idx][temp_idx]
    
    new_names = [
        f"Crop Baseline ({crop_name})",
        f"Seasonal Rainfall ({row_meta['rainfall_growing_season_total_mm']:.0f} mm)",
        f"Worst SPI-3 Index ({row_meta['spi3_growing_season_worst']:+.2f})",
        f"Min Soil Moisture ({row_meta['soil_moisture_growing_season_min']:.3f} m3/m3)",
        f"Mean Temperature ({row_meta['temp_growing_season_mean_c']:.1f} C)",
        f"District Context ({district})",
        f"Season Type ({season})",
        f"Irrigation ({zone})"
    ]
    new_values = np.array([crop_shap, rain_shap, spi_shap, soil_shap, temp_shap, dist_shap, season_shap, zone_shap])
    new_data = np.array([
        1,
        row_meta["rainfall_growing_season_total_mm"],
        row_meta["spi3_growing_season_worst"],
        row_meta["soil_moisture_growing_season_min"],
        row_meta["temp_growing_season_mean_c"],
        1, 1, 1
    ])
    
    exp = shap.Explanation(
        values=new_values,
        base_values=shap_vals[idx].base_values,
        data=new_data,
        feature_names=new_names
    )
    return exp

# ------------------------------------------------------------------------------
# Export Artifacts
# ------------------------------------------------------------------------------
target_dirs = [OUTPUT_DIR]

for d in target_dirs:
    os.makedirs(d, exist_ok=True)
    
    # 1. JSON Export
    json_path = os.path.join(d, "shap_feature_importance.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(importance_summary, f, indent=2)
    print(f"\n[Artifact Saved] -> {json_path}")

    # 2. Global Beeswarm Summary Plot (300 DPI)
    plot_path = os.path.join(d, "shap_global_summary.png")
    plt.figure(figsize=(11, 7), dpi=300)
    shap.summary_plot(
        shap_values.values,
        X_test_display,
        max_display=15,
        show=False,
        plot_size=(11, 7)
    )
    plt.title(
        "TreeSHAP Global Feature Attributions on Seasonal Crop Yield (2021-2025 Test Split)\n"
        "Impact on Model Output: Yield Shift (Metric Tons / Hectare)",
        fontsize=12,
        fontweight="bold",
        pad=16
    )
    plt.xlabel("SHAP Value (Impact on Yield in MT/ha: Positive = Yield Gain, Negative = Deficit)", fontsize=10, fontweight="bold")
    plt.tight_layout()
    plt.savefig(plot_path, bbox_inches="tight")
    plt.close()
    print(f"[Artifact Saved] -> {plot_path}")

    # 3. Local Drought Shock Waterfall Plot (300 DPI)
    # 2023 Yala Puttalam Maize (index 840 in test_df)
    drought_matches = test_df[(test_df["crop_year"] == 2023) & (test_df["season"] == "Yala") & (test_df["district"] == "Puttalam") & (test_df["crop_name"] == "Maize")]
    if not drought_matches.empty:
        drought_idx = drought_matches.index[0]
        exp_drought = build_grouped_waterfall(drought_idx, test_df, X_test_raw, shap_values)
        drought_plot_path = os.path.join(d, "shap_waterfall_drought.png")
        plt.figure(figsize=(10, 6), dpi=300)
        shap.plots.waterfall(exp_drought, max_display=8, show=False)
        plt.title(
            "TreeSHAP Disaster Attribution: 2023 Yala Puttalam Maize (Severe Drought Shock)\n"
            f"Actual Yield: {test_df.iloc[drought_idx]['yield_metric_tons_per_hectare']:.2f} MT/ha | Model Prediction f(x): {exp_drought.values.sum() + exp_drought.base_values:.2f} MT/ha",
            fontsize=11,
            fontweight="bold",
            pad=14
        )
        plt.xlabel("Yield Shift (Metric Tons / Hectare)", fontsize=10, fontweight="bold")
        plt.tight_layout()
        plt.savefig(drought_plot_path, bbox_inches="tight")
        plt.close()
        print(f"[Artifact Saved] -> {drought_plot_path}")

    # 4. Local Monsoon Deluge / Flood Shock Waterfall Plot (300 DPI)
    # 2024 Maha Polonnaruwa Maize (index 861 in test_df)
    flood_matches = test_df[(test_df["crop_year"] == 2024) & (test_df["season"] == "Maha") & (test_df["district"] == "Polonnaruwa") & (test_df["crop_name"] == "Maize")]
    if not flood_matches.empty:
        flood_idx = flood_matches.index[0]
        exp_flood = build_grouped_waterfall(flood_idx, test_df, X_test_raw, shap_values)
        flood_plot_path = os.path.join(d, "shap_waterfall_flood.png")
        plt.figure(figsize=(10, 6), dpi=300)
        shap.plots.waterfall(exp_flood, max_display=8, show=False)
        plt.title(
            "TreeSHAP Disaster Attribution: 2024 Maha Polonnaruwa Maize (Extreme Monsoon Deluge)\n"
            f"Actual Yield: {test_df.iloc[flood_idx]['yield_metric_tons_per_hectare']:.2f} MT/ha | Model Prediction f(x): {exp_flood.values.sum() + exp_flood.base_values:.2f} MT/ha",
            fontsize=11,
            fontweight="bold",
            pad=14
        )
        plt.xlabel("Yield Shift (Metric Tons / Hectare)", fontsize=10, fontweight="bold")
        plt.tight_layout()
        plt.savefig(flood_plot_path, bbox_inches="tight")
        plt.close()
        print(f"[Artifact Saved] -> {flood_plot_path}")

print("=" * 80)
print("TREESHAP EXPLANATION PIPELINE COMPLETE!")
print("=" * 80)
