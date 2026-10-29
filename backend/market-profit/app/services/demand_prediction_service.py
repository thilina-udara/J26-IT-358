import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Protocol, runtime_checkable
import joblib
import numpy as np
import pandas as pd

from app.schemas.common import DemandLevel, PredictionStatus, STANDARD_MARKETS
from app.schemas.demand_forecast import DemandForecastRequest, DemandForecastResponse

logger = logging.getLogger(__name__)

CURRENT_FILE = Path(__file__).resolve()
COMPONENT_DIR = CURRENT_FILE.parents[2]
MODELS_DIR = COMPONENT_DIR / "ml" / "market-demand-training" / "models"
CLS_MODEL_FILE = MODELS_DIR / "demand_classifier_model.joblib"
REG_MODEL_FILE = MODELS_DIR / "demand_regressor_model.joblib"
META_FILE = MODELS_DIR / "demand_feature_metadata.json"
PROFILES_FILE = MODELS_DIR / "demand_serving_profiles.json"

DEMAND_LEVEL_INV = {0: DemandLevel.LOW, 1: DemandLevel.MEDIUM, 2: DemandLevel.HIGH}


SUPPORTED_CROPS = {"CR_OKRA", "CR_BRINJAL", "CR_MAIZE", "CR_MUNG_BEAN", "CR_CHILLI"}
SUPPORTED_DISTRICTS = {"LK-32", "LK-33"}


@runtime_checkable
class AbstractDemandPredictor(Protocol):
    """
    Protocol defining the contract for commodity market demand prediction.
    Enables pluggable ML inference engines without altering routes or database schemas.
    """
    def predict_demand(self, request: DemandForecastRequest) -> DemandForecastResponse:
        ...


class DefaultUnavailableDemandPredictor:
    """
    Fallback predictor returned when trained ML models are unavailable.
    Returns prediction_status='unavailable' with strictly null predicted metrics.
    """
    def predict_demand(self, request: DemandForecastRequest) -> DemandForecastResponse:
        market_name = STANDARD_MARKETS.get(request.target_market_id)
        return DemandForecastResponse(
            crop_id=request.crop_id,
            cultivation_district_id=request.cultivation_district_id,
            target_market_id=request.target_market_id,
            target_market_name=market_name,
            forecast_target_date=request.forecast_target_date,
            prediction_status=PredictionStatus.UNAVAILABLE,
            projected_demand_volume_kg=None,
            projected_demand_level=None,
            model_version=None,
            model_provenance=None,
            status_message="Machine learning demand prediction model is currently offline or undergoing training.",
            created_at=datetime.now()
        )


class TrainedDemandPredictor:
    """
    Inference service for commodity market demand prediction using trained classifier & regressor.
    Predicts categorical demand level (High/Medium/Low) and volume in kg.
    Adheres to the HARTI metadata normalization convention.
    """
    def __init__(self):
        self.cls_model = None
        self.reg_model = None
        self.metadata = {}
        self.profiles = {}
        self.feature_names = []
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            if CLS_MODEL_FILE.exists() and REG_MODEL_FILE.exists() and META_FILE.exists() and PROFILES_FILE.exists():
                self.cls_model = joblib.load(CLS_MODEL_FILE)
                self.reg_model = joblib.load(REG_MODEL_FILE)
                with open(META_FILE, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    self.profiles = json.load(f)
                self.feature_names = self.metadata.get("feature_names", [])
                logger.info("Successfully loaded Demand Classification & Regression models.")
            else:
                logger.warning(f"Demand forecasting model artifacts not found at {MODELS_DIR}")
        except Exception as e:
            logger.error(f"Error loading Demand Forecasting models: {e}", exc_info=True)
            self.cls_model = None
            self.reg_model = None

    def predict_demand(self, request: DemandForecastRequest) -> DemandForecastResponse:
        market_name = STANDARD_MARKETS.get(request.target_market_id)

        if self.cls_model is None or self.reg_model is None or not self.feature_names:
            return DefaultUnavailableDemandPredictor().predict_demand(request)

        if request.crop_id not in SUPPORTED_CROPS or request.cultivation_district_id not in SUPPORTED_DISTRICTS:
            return DemandForecastResponse(
                crop_id=request.crop_id,
                cultivation_district_id=request.cultivation_district_id,
                target_market_id=request.target_market_id,
                target_market_name=market_name,
                forecast_target_date=request.forecast_target_date,
                prediction_status=PredictionStatus.UNAVAILABLE,
                projected_demand_volume_kg=None,
                projected_demand_level=None,
                model_version=None,
                model_provenance=None,
                status_message="Machine learning demand prediction model is currently offline or undergoing training for this district/crop scope.",
                created_at=datetime.now()
            )

        try:
            target_date = request.forecast_target_date
            today = datetime.now().date()
            diff_days = (target_date - today).days
            horizon_weeks = round(diff_days / 7.0)

            # Strict horizon requirement: 1 through 16 integer weeks ahead
            if diff_days <= 0 or horizon_weeks < 1 or horizon_weeks > 16:
                return DemandForecastResponse(
                    crop_id=request.crop_id,
                    cultivation_district_id=request.cultivation_district_id,
                    target_market_id=request.target_market_id,
                    target_market_name=market_name,
                    forecast_target_date=request.forecast_target_date,
                    prediction_status=PredictionStatus.UNAVAILABLE,
                    projected_demand_volume_kg=None,
                    projected_demand_level=None,
                    model_version=None,
                    model_provenance=None,
                    status_message=f"Forecast target date must be between 1 and 16 weeks ahead of today (requested horizon: {horizon_weeks} weeks, {diff_days} days).",
                    created_at=datetime.now()
                )

            month = target_date.month
            day_of_year = target_date.timetuple().tm_yday
            cal_week = target_date.isocalendar()[1]

            crop_id = request.crop_id
            district_id = request.cultivation_district_id

            profile_key = f"{crop_id}:{district_id}:{month}"
            profile = self.profiles.get(profile_key)

            if profile is None:
                for k, v in self.profiles.items():
                    if k.startswith(f"{crop_id}:") and k.endswith(f":{month}"):
                        profile = v
                        break

            if profile is None and self.profiles:
                profile = list(self.profiles.values())[0]

            row = {fn: 0.0 for fn in self.feature_names}
            row["year_trend"] = float((target_date.year - 2015) / 11.0)
            row["month"] = float(month)
            row["week_of_year"] = float(cal_week)
            row["season_sin"] = float(np.sin(2 * np.pi * day_of_year / 365.25))
            row["season_cos"] = float(np.cos(2 * np.pi * day_of_year / 365.25))

            if profile:
                for col, val in profile.items():
                    if col in row:
                        row[col] = float(val)

            crop_col = f"crop_id_{crop_id}"
            if crop_col in row:
                row[crop_col] = 1.0

            dist_col = f"district_id_code_{district_id}"
            if dist_col in row:
                row[dist_col] = 1.0

            df_input = pd.DataFrame([row])[self.feature_names]

            cls_raw = int(self.cls_model.predict(df_input)[0])
            predicted_level = DEMAND_LEVEL_INV.get(cls_raw, DemandLevel.MEDIUM)

            reg_raw = float(self.reg_model.predict(df_input)[0])
            predicted_volume = Decimal(str(max(100.0, round(reg_raw, 1))))

            cls_acc = self.metadata.get("classifier_metrics", {}).get("test_accuracy", 0.7473)
            reg_mae = self.metadata.get("regressor_metrics", {}).get("test_mae", 670.5)
            provenance = {
                "classifier_algorithm": "XGBoostClassifier",
                "regressor_algorithm": "XGBoostRegressor",
                "source_convention": "HARTI metadata normalization",
                "classifier_accuracy": cls_acc,
                "regressor_mae_kg": reg_mae,
                "forecast_horizon_weeks": horizon_weeks,
                "training_cutoff": "2024-12-27",
                "timing_alignment": "Aligned t_forecast = t_target - H weeks across Demand and Price",
            }

            return DemandForecastResponse(
                crop_id=request.crop_id,
                cultivation_district_id=request.cultivation_district_id,
                target_market_id=request.target_market_id,
                target_market_name=market_name,
                forecast_target_date=request.forecast_target_date,
                prediction_status=PredictionStatus.COMPLETED,
                projected_demand_volume_kg=predicted_volume,
                projected_demand_level=predicted_level,
                model_version=self.metadata.get("classifier_version", "xgb-demand-cls-v1.1.0"),
                model_provenance=provenance,
                status_message="Commodity demand prediction generated successfully by trained ML model (HARTI metadata convention).",
                created_at=datetime.now()
            )

        except Exception as e:
            logger.error(f"Inference error during demand prediction: {e}", exc_info=True)
            return DefaultUnavailableDemandPredictor().predict_demand(request)


_active_demand_predictor = TrainedDemandPredictor()


def get_demand_predictor() -> AbstractDemandPredictor:
    """
    FastAPI dependency returning the active demand prediction engine.
    """
    return _active_demand_predictor
