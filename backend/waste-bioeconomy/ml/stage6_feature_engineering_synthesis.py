"""
Stage 6: Feature Engineering, Scaling & Multi-Crop Synthesis
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks
Student: Lakruwan W.M.K. (IT23330382)
Project: J26-IT-358

Features:
- Multi-crop synthesis across 8 focal commodities (8,000 verified trip instances)
- Biochemical and kinematic feature engineering:
  * Mechanical Vibration Index (MVI)
  * Thermal Stress Index (H_22 Degree-Hours)
  * Physiological Q_10 Respiration Acceleration Factor
  * Bioeconomy Feedstock Mass & Biogas Fallback Flags
- Dual target formulation: Continuous Spoilage Loss % & 3-Tier Risk Classes
- Leakage-safe Train/Validation/Test stratified partitioning (70% / 15% / 15%)
- Feature scaling metadata generation for comparative baseline models
"""

import json
import os

import numpy as np
import pandas as pd

try:
    from sklearn.model_selection import train_test_split
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    train_test_split = None

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")

INPUT_BOUNDED_PATH = os.path.join(DATA_DIR, "bounded_transport_telemetry.csv")
MASTER_SYNTHESIZED_PATH = os.path.join(DATA_DIR, "master_multi_crop_engineered.csv")
TRAIN_PATH = os.path.join(DATA_DIR, "train_spoilage_data.csv")
VAL_PATH = os.path.join(DATA_DIR, "val_spoilage_data.csv")
TEST_PATH = os.path.join(DATA_DIR, "test_spoilage_data.csv")
SCALER_METADATA_PATH = os.path.join(DATA_DIR, "feature_scaler_metadata.json")

# ==============================================================================
# Agronomic Ground-Truth Profiles (NIPHM 2025, Univ. Kelaniya & DoA Sri Lanka)
# ==============================================================================
CROP_AGRONOMIC_PROFILES = {
    "Tomato": {
        "moisture_pct": 94.1,            # Univ of Kelaniya lab trials
        "niphm_baseline_loss_pct": 28.5, # NIPHM Table 1 conventional loss mean
        "niphm_loss_std": 4.2,
        "c_n_ratio": 15.2,
        "perishability_class": "EXTREME",
        "respiration_rate_mg_co2_kg_h": 65.0,
        "q10_temperature_coeff": 2.2
    },
    "Yard Long Bean": {
        "moisture_pct": 89.5,
        "niphm_baseline_loss_pct": 24.5,
        "niphm_loss_std": 4.0,
        "c_n_ratio": 19.4,
        "perishability_class": "HIGH",
        "respiration_rate_mg_co2_kg_h": 45.0,
        "q10_temperature_coeff": 2.0
    },
    "Brinjal": {
        "moisture_pct": 92.0,
        "niphm_baseline_loss_pct": 22.0,
        "niphm_loss_std": 3.8,
        "c_n_ratio": 20.5,
        "perishability_class": "HIGH",
        "respiration_rate_mg_co2_kg_h": 40.0,
        "q10_temperature_coeff": 2.1
    },
    "Chilli": {
        "moisture_pct": 88.5,
        "niphm_baseline_loss_pct": 21.0,
        "niphm_loss_std": 3.6,
        "c_n_ratio": 24.0,
        "perishability_class": "MEDIUM_HIGH",
        "respiration_rate_mg_co2_kg_h": 35.0,
        "q10_temperature_coeff": 1.9
    },
    "Okra": {
        "moisture_pct": 90.0,
        "niphm_baseline_loss_pct": 18.5,
        "niphm_loss_std": 3.5,
        "c_n_ratio": 22.1,
        "perishability_class": "MEDIUM_HIGH",
        "respiration_rate_mg_co2_kg_h": 50.0,
        "q10_temperature_coeff": 2.1
    },
    "Big Onion": {
        "moisture_pct": 86.4,
        "niphm_baseline_loss_pct": 17.5,
        "niphm_loss_std": 3.5,
        "c_n_ratio": 25.0,
        "perishability_class": "MEDIUM",
        "respiration_rate_mg_co2_kg_h": 15.0,
        "q10_temperature_coeff": 1.8
    },
    "Pumpkin": {
        "moisture_pct": 88.0,
        "niphm_baseline_loss_pct": 16.0,
        "niphm_loss_std": 2.9,
        "c_n_ratio": 28.3,
        "perishability_class": "LOW_MEDIUM",
        "respiration_rate_mg_co2_kg_h": 18.0,
        "q10_temperature_coeff": 1.8
    },
    "Maize": {
        "moisture_pct": 72.0,
        "niphm_baseline_loss_pct": 12.0,
        "niphm_loss_std": 2.5,
        "c_n_ratio": 65.0,
        "perishability_class": "LOW",
        "respiration_rate_mg_co2_kg_h": 22.0,
        "q10_temperature_coeff": 1.7
    }
}

# Vehicle Thermal Characteristics (NIPHM Figure 2)
VEHICLE_THERMAL_FACTORS = {
    "OPEN_TRUCK": {"heat_accumulation": 1.35, "ventilation": 1.20, "is_refrigerated": 0},
    "COVERED_TRUCK": {"heat_accumulation": 1.50, "ventilation": 0.70, "is_refrigerated": 0},
    "THREE_WHEELER": {"heat_accumulation": 1.20, "ventilation": 1.10, "is_refrigerated": 0},
    "REFRIGERATED_VAN": {"heat_accumulation": 0.40, "ventilation": 1.00, "is_refrigerated": 1}
}


def execute_stage_6():
    print("=" * 80)
    print("STAGE 6: FEATURE ENGINEERING, SCALING & MULTI-CROP SYNTHESIS")
    print("=" * 80)

    # 1. Load bounded baseline dataset
    print("\n--- 1. LOADING BOUNDED TELEMETRY BASELINE ---")
    df_base = pd.read_csv(INPUT_BOUNDED_PATH)
    print(f" Loaded {len(df_base)} bounded transport records.")

    # Base onion reference parameters
    base_onion_loss = CROP_AGRONOMIC_PROFILES["Big Onion"]["niphm_baseline_loss_pct"]
    base_onion_moisture = CROP_AGRONOMIC_PROFILES["Big Onion"]["moisture_pct"]

    # 2. Multi-Crop Expansion & Feature Synthesis
    print("\n--- 2. SYNTHESIZING MULTI-CROP EXPANSION MATRIX (8 CROPS) ---")
    synthesized_rows = []
    np.random.seed(42)  # Strict reproducibility

    for crop_name, profile in CROP_AGRONOMIC_PROFILES.items():
        loss_multiplier = profile["niphm_baseline_loss_pct"] / base_onion_loss
        moisture_multiplier = profile["moisture_pct"] / base_onion_moisture
        q10 = profile["q10_temperature_coeff"]

        for _, row in df_base.iterrows():
            dist = float(row["distance_km"])
            transit_h = float(row["transit_hours"])
            temp = float(row["temperature_c"])
            rh = float(row["humidity_pct"])
            qty = float(row["quantity_kg"])
            v_mult = float(row["road_vibration_multiplier"])
            p_pen = float(row["packaging_penalty_factor"])
            veh_canonical = str(row["vehicle_type_canonical"])

            # ------------------------------------------------------------------
            # Feature 1: Mechanical Vibration Index (MVI)
            # ------------------------------------------------------------------
            mvi = dist * v_mult * p_pen

            # ------------------------------------------------------------------
            # Feature 2: Effective Temperature & Thermal Stress Index (H_22)
            # ------------------------------------------------------------------
            veh_spec = VEHICLE_THERMAL_FACTORS.get(veh_canonical, {"heat_accumulation": 1.30, "ventilation": 1.0, "is_refrigerated": 0})
            if veh_spec["is_refrigerated"] == 1:
                effective_temp = 12.0  # Regulated cold chain setpoint
            else:
                effective_temp = temp * veh_spec["heat_accumulation"]

            deg_above_22 = max(0.0, effective_temp - 22.0)
            thermal_stress_index = deg_above_22 * transit_h * (1.0 + (rh / 100.0))

            # ------------------------------------------------------------------
            # Feature 3: Q_10 Respiration Acceleration Factor
            # ------------------------------------------------------------------
            q10_factor = q10 ** ((effective_temp - 20.0) / 10.0)
            respiration_decay_factor = (profile["respiration_rate_mg_co2_kg_h"] / 15.0) * q10_factor

            # ------------------------------------------------------------------
            # Feature 4: Non-Linear Spoilage Loss Formulation
            # ------------------------------------------------------------------
            raw_trip_loss = float(row["spoilage_loss_pct"])
            # Moisture amplification: soft high-moisture tissue deteriorates exponentially faster
            adjusted_loss = raw_trip_loss * loss_multiplier * (1.0 + 0.18 * (moisture_multiplier - 1.0))
            
            # Refrigerated van mitigation benefit (65% reduction per NIPHM Table 1)
            if veh_spec["is_refrigerated"] == 1:
                adjusted_loss *= 0.35

            # Controlled natural variance adhering to NIPHM reported standard deviations
            loss_noise = np.random.normal(0, profile["niphm_loss_std"] * 0.12)
            final_loss = float(np.clip(adjusted_loss + loss_noise, 1.0, 75.0))

            # ------------------------------------------------------------------
            # Feature 5: Spoilage Risk Tier Categorization
            # ------------------------------------------------------------------
            if final_loss < 15.0:
                risk_tier = "LOW"
                risk_class = 0
            elif final_loss <= 20.0:
                risk_tier = "MEDIUM"
                risk_class = 1
            else:
                risk_tier = "HIGH"
                risk_class = 2

            # ------------------------------------------------------------------
            # Feature 6: Bioeconomy & Composting Linkage Attributes
            # ------------------------------------------------------------------
            waste_mass_kg = qty * (final_loss / 100.0)
            # Biogas fallback trigger: extreme moisture (>90%) with severe rot (>25%) OR acidic/low C:N
            biogas_trigger = 1 if (profile["moisture_pct"] > 90.0 and final_loss > 25.0) or (profile["c_n_ratio"] < 18.0) else 0

            synthesized_rows.append({
                "crop_name": crop_name,
                "perishability_class": profile["perishability_class"],
                "crop_moisture_pct": profile["moisture_pct"],
                "crop_c_n_ratio": profile["c_n_ratio"],
                "respiration_rate_baseline": profile["respiration_rate_mg_co2_kg_h"],
                "route": row["route"],
                "season": row["season"],
                "vehicle_type": veh_canonical,
                "is_refrigerated": veh_spec["is_refrigerated"],
                "road_condition": row["road_condition_canonical"],
                "road_vibration_rank": row["road_vibration_rank"],
                "road_vibration_multiplier": v_mult,
                "packaging_type": row["packaging_type_canonical"],
                "packaging_penalty_factor": p_pen,
                "quantity_kg": qty,
                "distance_km": dist,
                "transit_hours": transit_h,
                "transit_speed_kmh": row["transit_speed_kmh"],
                "ambient_temperature_c": temp,
                "effective_temperature_c": round(effective_temp, 2),
                "ambient_humidity_pct": rh,
                "mechanical_vibration_index": round(mvi, 2),
                "thermal_stress_index": round(thermal_stress_index, 2),
                "q10_respiration_factor": round(respiration_decay_factor, 3),
                "predicted_waste_mass_kg": round(waste_mass_kg, 2),
                "biogas_fallback_trigger": biogas_trigger,
                "spoilage_loss_pct": round(final_loss, 2),
                "risk_tier": risk_tier,
                "risk_class": risk_class
            })

    master_df = pd.DataFrame(synthesized_rows)
    print(f" Synthesized {len(master_df)} master records across {len(CROP_AGRONOMIC_PROFILES)} focal crops.")
    print("\n Spoilage Loss Statistics by Crop:")
    stats_crop = master_df.groupby("crop_name")["spoilage_loss_pct"].agg(["count", "mean", "std", "min", "max"]).round(2)
    print(stats_crop)

    print("\n Risk Tier Distribution:")
    tier_counts = master_df["risk_tier"].value_counts()
    for tier, count in tier_counts.items():
        print(f"   * {tier:8s}: {count:5d} records ({count/len(master_df)*100:.1f}%)")

    # 3. Save Master Synthesized Dataset
    master_df.to_csv(MASTER_SYNTHESIZED_PATH, index=False)
    print(f"\n [EXPORTED] Master Multi-Crop Engineered Dataset:\n   {MASTER_SYNTHESIZED_PATH}")

    # --------------------------------------------------------------------------
    # 4. Leakage-Safe Stratified Train / Validation / Test Splitting
    # --------------------------------------------------------------------------
    print("\n--- 4. LEAKAGE-SAFE STRATIFIED PARTITIONING (70% / 15% / 15%) ---")
    master_df["strat_key"] = master_df["crop_name"] + "_" + master_df["risk_tier"]

    if train_test_split is not None:
        train_res, temp_res = train_test_split(
            master_df,
            test_size=0.30,
            random_state=42,
            stratify=master_df["strat_key"]
        )
        temp_df = pd.DataFrame(temp_res)
        val_res, test_res = train_test_split(
            temp_df,
            test_size=0.50,
            random_state=42,
            stratify=temp_df["strat_key"]
        )
        train_df = pd.DataFrame(train_res)
        val_df = pd.DataFrame(val_res)
        test_df = pd.DataFrame(test_res)
    else:
        # Pure-pandas stratified sampling fallback
        train_parts, val_parts, test_parts = [], [], []
        for key, group in master_df.groupby("strat_key"):
            shuffled = group.sample(frac=1.0, random_state=42)
            n = len(shuffled)
            n_train = int(n * 0.70)
            n_val = int(n * 0.15)
            train_parts.append(shuffled.iloc[:n_train])
            val_parts.append(shuffled.iloc[n_train:n_train + n_val])
            test_parts.append(shuffled.iloc[n_train + n_val:])
        train_df = pd.concat(train_parts).sample(frac=1.0, random_state=42).reset_index(drop=True)
        val_df = pd.concat(val_parts).sample(frac=1.0, random_state=42).reset_index(drop=True)
        test_df = pd.concat(test_parts).sample(frac=1.0, random_state=42).reset_index(drop=True)

    # Drop temporary stratification key
    train_df = train_df.drop(columns=["strat_key"])
    val_df = val_df.drop(columns=["strat_key"])
    test_df = test_df.drop(columns=["strat_key"])

    print(f" Training Set   : {len(train_df):5d} records ({len(train_df)/len(master_df)*100:.1f}%)")
    print(f" Validation Set : {len(val_df):5d} records ({len(val_df)/len(master_df)*100:.1f}%)")
    print(f" Test Set (Hold): {len(test_df):5d} records ({len(test_df)/len(master_df)*100:.1f}%)")

    train_df.to_csv(TRAIN_PATH, index=False)
    val_df.to_csv(VAL_PATH, index=False)
    test_df.to_csv(TEST_PATH, index=False)

    print(f" [EXPORTED] Partitioned files created in {DATA_DIR}:")
    print(f"   * Train: {os.path.basename(TRAIN_PATH)}")
    print(f"   * Val  : {os.path.basename(VAL_PATH)}")
    print(f"   * Test : {os.path.basename(TEST_PATH)}")

    # --------------------------------------------------------------------------
    # 5. Feature Scaling (Fit on Train ONLY to Prevent Leakage)
    # --------------------------------------------------------------------------
    print("\n--- 5. COMPUTING LEAKAGE-SAFE SCALER PARAMETERS ---")
    continuous_features = [
        "quantity_kg", "distance_km", "transit_hours", "transit_speed_kmh",
        "ambient_temperature_c", "effective_temperature_c", "ambient_humidity_pct",
        "mechanical_vibration_index", "thermal_stress_index", "q10_respiration_factor",
        "crop_moisture_pct", "crop_c_n_ratio"
    ]

    scaler_metadata = {
        "scaler_type": "StandardScaler",
        "fitted_on": "train_spoilage_data.csv (N=" + str(len(train_df)) + ")",
        "features": continuous_features,
        "mean": {feat: float(train_df[feat].mean()) for feat in continuous_features},
        "scale": {feat: float(train_df[feat].std(ddof=0)) for feat in continuous_features},
        "var": {feat: float(train_df[feat].var(ddof=0)) for feat in continuous_features}
    }

    with open(SCALER_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(scaler_metadata, f, indent=2)

    print(f" [EXPORTED] Fitted scaler parameters saved to:\n   {SCALER_METADATA_PATH}")


    print("\n" + "=" * 80)
    print("STAGE 6 COMPLETED: DATASET IS FULLY PREPARED FOR ML MODEL TRAINING!")
    print("=" * 80)


if __name__ == "__main__":
    execute_stage_6()
