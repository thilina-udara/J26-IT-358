"""ML inference service for in-transit spoilage risk scoring and mass-partitioning."""

import json
import os
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from app.schemas.risk import (
    ModelBenchmarkItem,
    ModelBenchmarkResponse,
    RiskPredictionRequest,
    RiskPredictionResponse,
    TelemetryStressIndices,
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")

REGRESSOR_PATH = os.path.join(MODELS_DIR, "spoilage_xgboost_regressor.json")
CLASSIFIER_PATH = os.path.join(MODELS_DIR, "spoilage_xgboost_classifier.json")
PREPROCESSOR_PATH = os.path.join(MODELS_DIR, "encoder_and_scaler.joblib")
FEATURE_IMPORTANCE_PATH = os.path.join(MODELS_DIR, "feature_importance_ranking.json")
BENCHMARK_CSV_PATH = os.path.join(DATA_DIR, "model_benchmark_comparison_table.csv")

# Agronomic reference profiles from NIPHM 2025, University of Kelaniya, and Sri Lanka DoA
CROP_AGRONOMIC_PROFILES: dict[str, dict[str, Any]] = {
    "Tomato": {
        "moisture_pct": 94.1,
        "c_n_ratio": 15.2,
        "perishability_class": "EXTREME",
        "respiration_rate_mg_co2_kg_h": 65.0,
        "q10_temperature_coeff": 2.2,
        "scientific_name": "Solanum lycopersicum",
    },
    "Yard Long Bean": {
        "moisture_pct": 89.5,
        "c_n_ratio": 19.4,
        "perishability_class": "HIGH",
        "respiration_rate_mg_co2_kg_h": 45.0,
        "q10_temperature_coeff": 2.0,
        "scientific_name": "Vigna unguiculata sesquipedalis",
    },
    "Brinjal": {
        "moisture_pct": 92.0,
        "c_n_ratio": 20.5,
        "perishability_class": "HIGH",
        "respiration_rate_mg_co2_kg_h": 40.0,
        "q10_temperature_coeff": 2.1,
        "scientific_name": "Solanum melongena",
    },
    "Chilli": {
        "moisture_pct": 88.5,
        "c_n_ratio": 24.0,
        "perishability_class": "MEDIUM_HIGH",
        "respiration_rate_mg_co2_kg_h": 35.0,
        "q10_temperature_coeff": 1.9,
        "scientific_name": "Capsicum annuum",
    },
    "Okra": {
        "moisture_pct": 90.0,
        "c_n_ratio": 22.1,
        "perishability_class": "MEDIUM_HIGH",
        "respiration_rate_mg_co2_kg_h": 50.0,
        "q10_temperature_coeff": 2.1,
        "scientific_name": "Abelmoschus esculentus",
    },
    "Big Onion": {
        "moisture_pct": 86.4,
        "c_n_ratio": 25.0,
        "perishability_class": "MEDIUM",
        "respiration_rate_mg_co2_kg_h": 15.0,
        "q10_temperature_coeff": 1.8,
        "scientific_name": "Allium cepa",
    },
    "Pumpkin": {
        "moisture_pct": 88.0,
        "c_n_ratio": 28.3,
        "perishability_class": "LOW_MEDIUM",
        "respiration_rate_mg_co2_kg_h": 18.0,
        "q10_temperature_coeff": 1.8,
        "scientific_name": "Cucurbita moschata",
    },
    "Maize": {
        "moisture_pct": 72.0,
        "c_n_ratio": 65.0,
        "perishability_class": "LOW",
        "respiration_rate_mg_co2_kg_h": 22.0,
        "q10_temperature_coeff": 1.7,
        "scientific_name": "Zea mays",
    },
}

VEHICLE_THERMAL_FACTORS: dict[str, dict[str, Any]] = {
    "OPEN_TRUCK": {"heat_accumulation": 1.35, "ventilation": 1.20, "is_refrigerated": 0},
    "COVERED_TRUCK": {"heat_accumulation": 1.50, "ventilation": 0.70, "is_refrigerated": 0},
    "THREE_WHEELER": {"heat_accumulation": 1.20, "ventilation": 1.10, "is_refrigerated": 0},
    "REFRIGERATED_VAN": {"heat_accumulation": 0.40, "ventilation": 1.00, "is_refrigerated": 1},
}

ROAD_CONDITION_FACTORS: dict[str, dict[str, Any]] = {
    "GOOD": {"rank": 1, "multiplier": 1.00},
    "MODERATE": {"rank": 2, "multiplier": 1.25},
    "POOR": {"rank": 3, "multiplier": 1.60},
}

PACKAGING_FACTORS: dict[str, float] = {
    "PLASTIC_CRATE": 1.00,
    "VENTILATED_BOX": 1.10,
    "CARDBOARD_BOX": 1.20,
    "POLYSACK_MESH": 1.45,
    "SACK": 1.45,
}


class RiskScoringService:
    """
    Supervised Machine Learning Service for predicting in-transit spoilage risk
    and driving dual-stream mass partitioning.
    """

    _instance: Optional["RiskScoringService"] = None

    def __init__(self) -> None:
        self.regressor: xgb.XGBRegressor | None = None
        self.classifier: xgb.XGBClassifier | None = None
        self.encoder: Any = None
        self.scaler: Any = None
        self.numerical_features: list[str] = []
        self.categorical_features: list[str] = []
        self.all_feature_names: list[str] = []
        self._load_models()

    @classmethod
    def get_instance(cls) -> "RiskScoringService":
        if cls._instance is None:
            cls._instance = RiskScoringService()
        return cls._instance

    def _load_models(self) -> None:
        """Loads serialized XGBoost models and preprocessor bundle."""
        if not os.path.exists(REGRESSOR_PATH) or not os.path.exists(CLASSIFIER_PATH):
            raise FileNotFoundError("XGBoost model artifacts missing. Run train_spoilage_model.py first.")

        # Load XGBoost Regressor
        self.regressor = xgb.XGBRegressor()
        self.regressor.load_model(REGRESSOR_PATH)

        # Load XGBoost Classifier
        self.classifier = xgb.XGBClassifier()
        self.classifier.load_model(CLASSIFIER_PATH)

        # Load Preprocessor Bundle
        bundle: dict[str, Any] = joblib.load(PREPROCESSOR_PATH)
        self.encoder = bundle["encoder"]
        self.scaler = bundle.get("scaler")
        self.numerical_features = bundle["numerical_features"]
        self.categorical_features = bundle["categorical_features"]
        self.all_feature_names = bundle["all_feature_names"]

    def _canonicalize_inputs(self, req: RiskPredictionRequest) -> tuple[str, str, str, str]:
        """Normalizes user string inputs to canonical enums."""
        # Vehicle
        v_raw = req.vehicle_type.strip().upper().replace(" ", "_").replace("-", "_")
        if v_raw not in VEHICLE_THERMAL_FACTORS:
            v_canonical = "OPEN_TRUCK"
        else:
            v_canonical = v_raw

        # Road
        r_raw = req.road_condition.strip().upper()
        if r_raw not in ROAD_CONDITION_FACTORS:
            r_canonical = "MODERATE"
        else:
            r_canonical = r_raw

        # Packaging
        p_raw = req.packaging_type.strip().upper().replace(" ", "_")
        if p_raw not in PACKAGING_FACTORS:
            p_canonical = "POLYSACK_MESH" if "SACK" in p_raw else "PLASTIC_CRATE"
        else:
            p_canonical = p_raw

        # Crop name matching
        crop_match = "Tomato"
        for c in CROP_AGRONOMIC_PROFILES:
            if c.lower() in req.crop_name.strip().lower() or req.crop_name.strip().lower() in c.lower():
                crop_match = c
                break

        return crop_match, v_canonical, r_canonical, p_canonical

    def predict_risk(self, req: RiskPredictionRequest) -> RiskPredictionResponse:
        """
        Executes end-to-end telemetry stress synthesis, ML inference, and dual-stream
        mass partitioning.
        """
        if self.regressor is None or self.classifier is None or self.encoder is None:
            raise RuntimeError("ML models have not been loaded.")

        crop_name, v_canonical, r_canonical, p_canonical = self._canonicalize_inputs(req)
        crop_profile = CROP_AGRONOMIC_PROFILES.get(crop_name, CROP_AGRONOMIC_PROFILES["Tomato"])
        veh_spec = VEHICLE_THERMAL_FACTORS[v_canonical]
        road_spec = ROAD_CONDITION_FACTORS[r_canonical]
        p_penalty = PACKAGING_FACTORS.get(p_canonical, 1.0)

        # ----------------------------------------------------------------------
        # Derived Biochemical & Kinematic Telemetry Stress Indices
        # ----------------------------------------------------------------------
        # 1. Transit Velocity
        transit_speed_kmh = req.distance_km / req.transit_hours if req.transit_hours > 0 else 30.0

        # 2. Thermal Environment & Effective Temperature
        if veh_spec["is_refrigerated"] == 1:
            effective_temp = 12.0  # Cold chain target setpoint
        else:
            effective_temp = req.ambient_temperature_c * veh_spec["heat_accumulation"]

        # 3. Mechanical Vibration Index (MVI)
        mvi = req.distance_km * road_spec["multiplier"] * p_penalty

        # 4. Thermal Stress Index (Degree-Hours above 22°C amplified by humidity)
        deg_above_22 = max(0.0, effective_temp - 22.0)
        thermal_stress_index = deg_above_22 * req.transit_hours * (1.0 + (req.ambient_humidity_pct / 100.0))

        # 5. Q10 Respiration Acceleration Factor
        q10_val = crop_profile["q10_temperature_coeff"]
        q10_factor = (crop_profile["respiration_rate_mg_co2_kg_h"] / 15.0) * (q10_val ** ((effective_temp - 20.0) / 10.0))

        # ----------------------------------------------------------------------
        # Build Vector for Machine Learning Inference
        # ----------------------------------------------------------------------
        numerical_dict = {
            "quantity_kg": float(req.payload_kg),
            "distance_km": float(req.distance_km),
            "transit_hours": float(req.transit_hours),
            "transit_speed_kmh": float(transit_speed_kmh),
            "ambient_temperature_c": float(req.ambient_temperature_c),
            "effective_temperature_c": float(effective_temp),
            "ambient_humidity_pct": float(req.ambient_humidity_pct),
            "mechanical_vibration_index": float(mvi),
            "thermal_stress_index": float(thermal_stress_index),
            "q10_respiration_factor": float(q10_factor),
            "crop_moisture_pct": float(crop_profile["moisture_pct"]),
            "crop_c_n_ratio": float(crop_profile["c_n_ratio"]),
            "respiration_rate_baseline": float(crop_profile["respiration_rate_mg_co2_kg_h"]),
            "road_vibration_rank": int(road_spec["rank"]),
            "road_vibration_multiplier": float(road_spec["multiplier"]),
            "packaging_penalty_factor": float(p_penalty),
            "is_refrigerated": int(veh_spec["is_refrigerated"]),
        }
        num_vec = np.array([[numerical_dict[col] for col in self.numerical_features]], dtype=np.float64)

        categorical_df = pd.DataFrame([{
            "crop_name": crop_name,
            "perishability_class": crop_profile["perishability_class"],
            "route": req.route if req.route else "DAMBULLA - COLOMBO",
            "season": req.season if req.season else "YALA",
            "vehicle_type": v_canonical,
            "road_condition": r_canonical,
            "packaging_type": p_canonical,
        }])
        cat_encoded = self.encoder.transform(categorical_df[self.categorical_features])
        x_input = np.hstack((num_vec, np.asarray(cat_encoded, dtype=np.float64)))

        # ----------------------------------------------------------------------
        # Model Inferences
        # ----------------------------------------------------------------------
        pred_loss_pct = float(np.clip(self.regressor.predict(x_input)[0], 1.0, 75.0))
        pred_class = int(self.classifier.predict(x_input)[0])

        # Risk tier label directly output by trained XGBoost Classifier (0=LOW, 1=MEDIUM, 2=HIGH)
        CLASS_TIER_MAP = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}
        risk_tier = CLASS_TIER_MAP.get(pred_class, "MEDIUM")

        if risk_tier == "LOW":
            retail_channel = "Standard Supermarket & Premium Wholesale Distribution"
        elif risk_tier == "MEDIUM":
            retail_channel = "Fast-Track Discount Local Market (Immediate Same-Day Sale)"
        else:
            retail_channel = "Salvage Wholesaling & Intensive Pre-Grading Allocation"

        # ----------------------------------------------------------------------
        # Mass Partitioning (Stream 1 vs Stream 2)
        # ----------------------------------------------------------------------
        loss_fraction = pred_loss_pct / 100.0
        stream_1_fresh_kg = round(req.payload_kg * (1.0 - loss_fraction), 2)
        stream_2_waste_kg = round(req.payload_kg * loss_fraction, 2)
        stream_1_pct = round((1.0 - loss_fraction) * 100.0, 2)
        stream_2_pct = round(pred_loss_pct, 2)

        # Biogas Fallback Logic
        biogas_trigger = 1 if (
            (crop_profile["moisture_pct"] > 90.0 and pred_loss_pct > 25.0) or
            (crop_profile["c_n_ratio"] < 18.0)
        ) else 0

        stream_2_dest = "ANAEROBIC_BIOGAS_DIVERSION" if biogas_trigger == 1 else "AEROBIC_COMPOSTING"

        return RiskPredictionResponse(
            crop_name=crop_name,
            total_payload_kg=round(req.payload_kg, 2),
            predicted_spoilage_loss_pct=round(pred_loss_pct, 2),
            risk_class=pred_class,
            risk_tier=risk_tier,
            stream_1_fresh_produce_kg=stream_1_fresh_kg,
            stream_1_fresh_pct=stream_1_pct,
            stream_1_recommended_channel=retail_channel,
            stream_2_bioeconomy_feedstock_kg=stream_2_waste_kg,
            stream_2_waste_pct=stream_2_pct,
            stream_2_destination=stream_2_dest,
            biogas_fallback_trigger=biogas_trigger,
            stress_indices=TelemetryStressIndices(
                transit_speed_kmh=round(transit_speed_kmh, 2),
                effective_temperature_c=round(effective_temp, 2),
                mechanical_vibration_index=round(mvi, 2),
                thermal_stress_index=round(thermal_stress_index, 2),
                q10_respiration_factor=round(q10_factor, 3),
            ),
            model_version="XGBoost v3.4.1 (RMSE=1.44%, R2=0.9691)",
        )

    def get_benchmark_data(self) -> ModelBenchmarkResponse:
        """Loads and formats the comparative benchmark table."""
        if not os.path.exists(BENCHMARK_CSV_PATH):
            raise FileNotFoundError(f"Benchmark file not found at: {BENCHMARK_CSV_PATH}")

        df = pd.read_csv(BENCHMARK_CSV_PATH)
        items: list[ModelBenchmarkItem] = []
        for _, row in df.iterrows():
            items.append(ModelBenchmarkItem(
                model_name=str(row["Model"]),
                model_type=str(row["Type"]),
                accuracy_pct=float(row["Accuracy (%)"]),
                precision=float(row["Precision"]),
                recall=float(row["Recall"]),
                macro_f1=float(row["Macro F1"]),
                rmse_pct=float(row["RMSE (%)"]),
                mae_pct=float(row["MAE (%)"]),
            ))

        return ModelBenchmarkResponse(
            benchmark_comparison=items,
            evaluation_dataset="Stratified Test Holdout (N=1,199 trips)",
            target_objectives={
                "target_rmse_threshold_pct": 10.0,
                "achieved_xgb_rmse_pct": 1.44,
                "target_macro_f1_threshold": 0.85,
                "achieved_xgb_macro_f1": 0.7977,
                "achieved_xgb_weighted_f1": 0.8218,
                "achieved_xgb_accuracy_pct": 81.98,
                "target_status": "SUPERVISED_REGRESSION_TARGET_EXCEEDED"
            }
        )

    def get_feature_importance(self) -> dict[str, Any]:
        """Loads the feature importance ranking from JSON."""
        if not os.path.exists(FEATURE_IMPORTANCE_PATH):
            raise FileNotFoundError(f"Feature ranking file not found at: {FEATURE_IMPORTANCE_PATH}")

        with open(FEATURE_IMPORTANCE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def get_crop_profiles(self) -> dict[str, Any]:
        """Returns the agronomic profile reference dataset."""
        return CROP_AGRONOMIC_PROFILES
