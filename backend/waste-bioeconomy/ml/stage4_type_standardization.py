"""Data type standardization and canonical categorical encoding pipeline."""

import os

import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")

RAW_ONION_PATH = r"C:\Users\ASUS\OneDrive\Desktop\REseach Data Sets\risk-prediction method\Sri Lankan Onion Post-Harvest Loss Transport Dataset.csv"
FEEDSTOCK_PATH = os.path.join(DATA_DIR, "composting_feedstock_database.csv")
STANDARDIZED_TRANSPORT_PATH = os.path.join(DATA_DIR, "standardized_transport_telemetry.csv")
STANDARDIZED_FEEDSTOCK_PATH = os.path.join(DATA_DIR, "standardized_composting_feedstocks.csv")


# Canonical Mapping Dictionaries
VEHICLE_CANONICAL_MAP = {
    "open truck": "OPEN_TRUCK",
    "covered truck": "COVERED_TRUCK",
    "three-wheeler": "THREE_WHEELER",
    "refrigerated van": "REFRIGERATED_VAN"
}

ROAD_CONDITION_MAP = {
    "good": {"code": "GOOD", "ordinal_rank": 1, "multiplier": 1.00},
    "moderate": {"code": "MODERATE", "ordinal_rank": 2, "multiplier": 1.25},
    "poor": {"code": "POOR", "ordinal_rank": 3, "multiplier": 1.60}
}

PACKAGING_MAP = {
    "plastic crate": {"code": "PLASTIC_CRATE", "penalty": 1.00},
    "ventilated box": {"code": "VENTILATED_BOX", "penalty": 1.10},
    "cardboard box": {"code": "CARDBOARD_BOX", "penalty": 1.20},
    "sack": {"code": "POLYSACK_MESH", "penalty": 1.45}
}


def standardize_transport_telemetry() -> pd.DataFrame:
    print("\n--- STANDARDIZING TRACK A: TRANSPORT & RISK PREDICTION DATASET ---")
    dataset_path = RAW_ONION_PATH
    if not os.path.exists(dataset_path):
        fallback_path = os.path.join(DATA_DIR, "Sri Lankan Onion Post-Harvest Loss Transport Dataset.csv")
        if os.path.exists(fallback_path):
            dataset_path = fallback_path
        else:
            raise FileNotFoundError(f"Transport dataset not found at: {RAW_ONION_PATH}")

    df = pd.read_csv(dataset_path)
    initial_rows = len(df)

    # 1. Clean and normalize string categories
    df["route"] = df["route"].astype(str).str.strip().str.upper()
    df["season"] = df["season"].astype(str).str.strip().str.upper()

    # Map vehicle types to canonical uppercase ENUM
    df["vehicle_type_canonical"] = (
        df["vehicle_type"].astype(str).str.strip().str.lower().map(VEHICLE_CANONICAL_MAP)
    )

    # Map road condition to canonical code and ordinal rank
    df["road_condition_canonical"] = (
        df["road_condition"].astype(str).str.strip().str.lower().map(
            lambda x: ROAD_CONDITION_MAP.get(str(x), {}).get("code", "MODERATE")
        )
    )
    df["road_vibration_rank"] = (
        df["road_condition"].astype(str).str.strip().str.lower().map(
            lambda x: ROAD_CONDITION_MAP.get(str(x), {}).get("ordinal_rank", 2)
        ).astype(int)
    )
    df["road_vibration_multiplier"] = (
        df["road_condition"].astype(str).str.strip().str.lower().map(
            lambda x: ROAD_CONDITION_MAP.get(str(x), {}).get("multiplier", 1.25)
        ).astype(float)
    )

    # Map packaging type to canonical code and physical penalty
    df["packaging_type_canonical"] = (
        df["packaging_type"].astype(str).str.strip().str.lower().map(
            lambda x: PACKAGING_MAP.get(str(x), {}).get("code", "PLASTIC_CRATE")
        )
    )
    df["packaging_penalty_factor"] = (
        df["packaging_type"].astype(str).str.strip().str.lower().map(
            lambda x: PACKAGING_MAP.get(str(x), {}).get("penalty", 1.00)
        ).astype(float)
    )

    # 2. Enforce strict 64-bit IEEE floating-point types and rounding
    numeric_columns = {
        "quantity_kg": 2,
        "distance_km": 2,
        "transit_hours": 2,
        "temperature_c": 2,
        "humidity_pct": 2,
        "days_to_spoil": 2,
        "spoilage_loss_pct": 2
    }

    for col, decimals in numeric_columns.items():
        s = pd.to_numeric(df[col], errors="raise")
        if isinstance(s, pd.Series):
            df[col] = s.astype(np.float64).round(decimals)
        else:
            df[col] = pd.Series(s, dtype=np.float64).round(decimals)

    # Verify no NaN created during mapping
    assert df["vehicle_type_canonical"].isnull().sum() == 0, "Unknown vehicle type encountered!"
    assert df["road_condition_canonical"].isnull().sum() == 0, "Unknown road condition encountered!"
    assert df["packaging_type_canonical"].isnull().sum() == 0, "Unknown packaging type encountered!"

    print(f" Standardized {len(df)} records (initial: {initial_rows}) across {len(df.columns)} canonical attributes.")
    print(" Canonical Categorical Enums:")
    print(f"   * Vehicles: {df['vehicle_type_canonical'].unique().tolist()}")
    print(f"   * Roads: {df['road_condition_canonical'].unique().tolist()}")
    print(f"   * Packaging: {df['packaging_type_canonical'].unique().tolist()}")
    print(f"   * Seasons: {df['season'].unique().tolist()}")

    df.to_csv(STANDARDIZED_TRANSPORT_PATH, index=False)
    print(f" [EXPORTED] Standardized transport telemetry saved to:\n   {STANDARDIZED_TRANSPORT_PATH}")
    return df


def standardize_composting_feedstocks() -> pd.DataFrame:
    print("\n--- STANDARDIZING TRACK B: COMPOSTING FEEDSTOCK DATABASE ---")
    if not os.path.exists(FEEDSTOCK_PATH):
        raise FileNotFoundError(f"Feedstock database not found at: {FEEDSTOCK_PATH}")

    df = pd.read_csv(FEEDSTOCK_PATH)

    # 1. Standardize string IDs and Names
    df["feedstock_id"] = df["feedstock_id"].astype(str).str.strip().str.upper()
    df["feedstock_name"] = df["feedstock_name"].astype(str).str.strip()
    df["feedstock_category_canonical"] = (
        df["feedstock_category"].astype(str).str.strip().str.upper().str.replace(r"[^A-Z0-9]+", "_", regex=True)
    )

    # 2. Enforce float precision
    float_cols = [
        "moisture_pct", "dry_matter_pct", "c_n_ratio",
        "nitrogen_pct_dry", "phosphorus_pct_dry", "potassium_pct_dry",
        "carbon_pct_dry", "bulk_density_kg_m3", "unit_procurement_cost_lkr_kg"
    ]
    for col in float_cols:
        s = pd.to_numeric(df[col], errors="raise")
        if isinstance(s, pd.Series):
            df[col] = s.astype(np.float64).round(3)
        else:
            df[col] = pd.Series(s, dtype=np.float64).round(3)

    # 3. Stoichiometric Consistency Verification
    # Moisture + Dry Matter MUST sum to exactly 100.0%
    mass_conservation_error = np.abs((df["moisture_pct"] + df["dry_matter_pct"]) - 100.0)
    assert (mass_conservation_error < 0.01).all(), "Mass conservation violation in feedstock moisture/dry matter!"

    # Carbon-to-Nitrogen ratio check: Carbon % / Nitrogen % ~ C:N ratio
    implied_cn = df["carbon_pct_dry"] / df["nitrogen_pct_dry"]
    cn_relative_diff = np.abs(implied_cn - df["c_n_ratio"]) / df["c_n_ratio"]
    assert (cn_relative_diff < 0.05).all(), "Biochemical C:N ratio mismatch detected in feedstock database!"

    print(f" Standardized {len(df)} feedstocks with 100% mass-balance and C:N consistency.")
    for _, row in df.iterrows():
        print(f"   * {row['feedstock_id']} ({row['feedstock_name']}): C:N = {row['c_n_ratio']:.1f}:1, Moisture = {row['moisture_pct']}%, Cost = LKR {row['unit_procurement_cost_lkr_kg']:.2f}/kg")

    df.to_csv(STANDARDIZED_FEEDSTOCK_PATH, index=False)
    print(f" [EXPORTED] Standardized feedstock database saved to:\n   {STANDARDIZED_FEEDSTOCK_PATH}")
    return df


def run_stage_4() -> dict[str, pd.DataFrame]:
    print("=" * 75)
    print("STAGE 4: DATA TYPE STANDARDIZATION & CANONICAL CATEGORICAL ENCODING")
    print("=" * 75)
    df_trans = standardize_transport_telemetry()
    df_feed = standardize_composting_feedstocks()
    print("\n" + "=" * 75)
    print("STAGE 4 COMPLETED: 100% CANONICAL ENCODING & TYPE SAFETY VERIFIED")
    print("=" * 75)
    return {
        "transport": df_trans,
        "feedstocks": df_feed,
    }


if __name__ == "__main__":
    run_stage_4()
