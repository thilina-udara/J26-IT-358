"""
TreeSHAP Explainability Generator
Quantifies global and local climate feature attributions on crop yield.
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
    "soil_moisture_growing_season_min": "Min Soil Moisture (m³/m³)",
    "spi3_growing_season_worst": "Worst SPI-3 (Drought/Wet Index)",
    "temp_growing_season_mean_c": "Mean Temperature (°C)",
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

# Apply feature naming
X_display = X_raw.rename(columns=lambda col: FEATURE_NAME_MAP.get(col, col.replace("district_", "District: ")))

# Test Split (2021-2025 unseen observations)
test_mask = df["crop_year"] >= 2021
X_test_raw = X_raw[test_mask]
X_test_display = X_display[test_mask]

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
    "Min Soil Moisture (m³/m³)",
    "Worst SPI-3 (Drought/Wet Index)",
    "Mean Temperature (°C)"
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
# Export Artifacts
# ------------------------------------------------------------------------------
target_dirs = [OUTPUT_DIR]

for d in target_dirs:
    os.makedirs(d, exist_ok=True)
    
    # 1. JSON Export
    json_path = os.path.join(d, "shap_feature_importance.json")
    with open(json_path, "w") as f:
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
        "TreeSHAP Global Feature Attributions on Seasonal Crop Yield (2021–2025 Test Split)\n"
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

print("=" * 80)
print("TREESHAP EXPLANATION PIPELINE COMPLETE!")
print("=" * 80)
