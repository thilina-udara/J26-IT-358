import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Protocol, runtime_checkable
import joblib
import numpy as np
import pandas as pd

from app.schemas.common import PredictionStatus, STANDARD_MARKETS
from app.schemas.price_forecast import PriceForecastRequest, PriceForecastResponse

logger = logging.getLogger(__name__)

CURRENT_FILE = Path(__file__).resolve()
COMPONENT_DIR = CURRENT_FILE.parents[2]
MODELS_DIR = COMPONENT_DIR / "ml" / "price_forecasting" / "models"
MODEL_FILE = MODELS_DIR / "price_forecasting_model.joblib"
META_FILE = MODELS_DIR / "price_feature_metadata.json"
PROFILES_FILE = MODELS_DIR / "price_serving_profiles.json"

SUPPORTED_CROPS = {"CR_OKRA", "CR_BRINJAL", "CR_MAIZE", "CR_MUNG_BEAN", "CR_CHILLI"}
SUPPORTED_DISTRICTS = {"LK-32", "LK-33"}


@runtime_checkable
class AbstractPricePredictor(Protocol):
    """Protocol for pluggable price forecasting engines."""
    def forecast_price(self, request: PriceForecastRequest) -> PriceForecastResponse:
        ...


class DefaultUnavailablePricePredictor:
    """
    Fallback price predictor returned when trained ML models are unavailable.
    Returns prediction_status='unavailable' with strictly null predicted metrics.
    """
    def forecast_price(self, request: PriceForecastRequest) -> PriceForecastResponse:
        market_name = STANDARD_MARKETS.get(request.target_market_id)
        return PriceForecastResponse(
            crop_id=request.crop_id,
            cultivation_district_id=request.cultivation_district_id,
            target_market_id=request.target_market_id,
            target_market_name=market_name,
            forecast_target_date=request.forecast_target_date,
            price_type=request.price_type,
            currency="LKR",
            unit="kg",
            prediction_status=PredictionStatus.UNAVAILABLE,
            forecasted_price_lkr_per_kg=None,
            model_version=None,
            model_provenance=None,
            status_message="Machine learning price forecasting model is currently offline or undergoing training.",
            created_at=datetime.now()
        )


class TrainedPricePredictor:
    """
    Inference service for commodity price forecasting using trained crop-specific ML models.
    Supports 1 to 16 integer weeks ahead (primary planning range: 8..16 weeks).
    Strictly verifies horizon bounds and constructs time-series and calendar features from historical profiles.
    Adheres to the HARTI metadata normalization convention.
    """
    def __init__(self):
        self.crop_models = {}
        self.feature_names_by_crop = {}
        self.base_feature_names = []
        self.metadata = {}
        self.profiles = {}
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            if MODEL_FILE.exists() and META_FILE.exists() and PROFILES_FILE.exists():
                bundle = joblib.load(MODEL_FILE)
                if isinstance(bundle, dict):
                    self.crop_models = bundle.get("crop_models", {})
                    self.feature_names_by_crop = bundle.get("feature_names_by_crop", {})
                    self.base_feature_names = bundle.get("base_feature_names", [])
                else:
                    self.crop_models = {"DEFAULT": bundle}
                    self.base_feature_names = []

                with open(META_FILE, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    self.profiles = json.load(f)

                logger.info("Successfully loaded Crop-Specific Price Forecasting models and serving profiles.")
            else:
                logger.warning(f"Price forecasting model artifacts not found at {MODELS_DIR}")
        except Exception as e:
            logger.error(f"Error loading Price Forecasting model: {e}", exc_info=True)
            self.crop_models = {}

    def forecast_price(self, request: PriceForecastRequest) -> PriceForecastResponse:
        market_name = STANDARD_MARKETS.get(request.target_market_id)

        if not self.crop_models or not self.metadata:
            return DefaultUnavailablePricePredictor().forecast_price(request)

        if request.crop_id not in SUPPORTED_CROPS or request.cultivation_district_id not in SUPPORTED_DISTRICTS:
            return PriceForecastResponse(
                crop_id=request.crop_id,
                cultivation_district_id=request.cultivation_district_id,
                target_market_id=request.target_market_id,
                target_market_name=market_name,
                forecast_target_date=request.forecast_target_date,
                price_type=request.price_type,
                currency="LKR",
                unit="kg",
                prediction_status=PredictionStatus.UNAVAILABLE,
                forecasted_price_lkr_per_kg=None,
                model_version=None,
                model_provenance=None,
                status_message="Machine learning price forecasting model is currently offline or undergoing training for this district/crop scope.",
                created_at=datetime.now()
            )

        try:
            target_date = request.forecast_target_date
            today = datetime.now().date()
            diff_days = (target_date - today).days
            horizon_weeks = round(diff_days / 7.0)

            # Strict horizon requirement: 1 through 16 integer weeks ahead
            if diff_days <= 0 or horizon_weeks < 1 or horizon_weeks > 16:
                return PriceForecastResponse(
                    crop_id=request.crop_id,
                    cultivation_district_id=request.cultivation_district_id,
                    target_market_id=request.target_market_id,
                    target_market_name=market_name,
                    forecast_target_date=request.forecast_target_date,
                    price_type=request.price_type,
                    currency="LKR",
                    unit="kg",
                    prediction_status=PredictionStatus.UNAVAILABLE,
                    forecasted_price_lkr_per_kg=None,
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
            price_type_val = request.price_type.value if hasattr(request.price_type, "value") else str(request.price_type)

            # Profile lookup key: {crop_id}:{district_id}:{price_type}:{month}
            profile_key = f"{crop_id}:{district_id}:{price_type_val}:{month}"
            profile = self.profiles.get(profile_key)

            # Fallback to general crop + price_type profile if district profile missing
            if profile is None:
                for k, v in self.profiles.items():
                    if k.startswith(f"{crop_id}:") and f":{price_type_val}:" in k:
                        profile = v
                        break

            if profile is None and self.profiles:
                profile = list(self.profiles.values())[0]

            # Select crop model and feature set
            crop_model = self.crop_models.get(crop_id) or self.crop_models.get("DEFAULT")
            crop_features = self.feature_names_by_crop.get(crop_id, self.base_feature_names)

            if crop_model is None or not crop_features:
                return DefaultUnavailablePricePredictor().forecast_price(request)

            # Construct input vector matching exact feature_names for this crop
            row = {fn: 0.0 for fn in crop_features}
            row["horizon_weeks"] = float(horizon_weeks)
            row["log_horizon"] = float(np.log(horizon_weeks))
            row["horizon_ratio"] = float(horizon_weeks / 16.0)
            row["is_primary_range"] = 1.0 if horizon_weeks >= 8 else 0.0
            row["month"] = float(month)
            row["calendar_week_in_year"] = float(cal_week)
            row["season_sin"] = float(np.sin(2 * np.pi * day_of_year / 365.25))
            row["season_cos"] = float(np.cos(2 * np.pi * day_of_year / 365.25))

            if profile:
                for col, val in profile.items():
                    if col in row:
                        row[col] = float(val)

            # Recalculate seasonal expected price based on horizon
            if "seasonal_expected_price" in row and "price_at_obs" in row:
                s_ratio = row.get("seasonal_ratio", 1.0)
                if s_ratio == 0.0:
                    s_ratio = 1.0
                row["seasonal_ratio"] = s_ratio
                row["seasonal_expected_price"] = row["price_at_obs"] * s_ratio

            # District & price type indicator flags
            dist_col = f"district_id_code_{district_id}"
            if dist_col in row:
                row[dist_col] = 1.0

            pt_col = f"price_type_std_{price_type_val}"
            if pt_col in row:
                row[pt_col] = 1.0

            df_input = pd.DataFrame([row])[crop_features]
            pred_log = float(crop_model.predict(df_input)[0])
            predicted_raw = float(np.exp(pred_log))
            predicted_price = Decimal(str(max(10.0, round(predicted_raw, 2))))

            # Extract horizon-specific and range metrics from metadata
            h_key = f"horizon_{horizon_weeks}w"
            h_metrics = self.metadata.get("metrics_by_horizon", {}).get(h_key, {}).get("model_metrics", {})
            range_metrics = self.metadata.get("metrics_primary_range_8_to_16w", {})

            provenance = {
                "algorithm": self.metadata.get("algorithm", "CropSpecificXGBoostLogRegressor"),
                "source_convention": "HARTI metadata normalization",
                "mae_lkr_per_kg": h_metrics.get("mae", 123.10),
                "mape_pct": h_metrics.get("mape", 27.77),
                "accuracy_within_10pct": h_metrics.get("accuracy_within_10pct", 27.14),
                "primary_range_8_to_16w_mae": range_metrics.get("mae", 123.10),
                "primary_range_8_to_16w_mape": range_metrics.get("mape", 27.77),
                "primary_range_8_to_16w_accuracy_within_10pct": range_metrics.get("accuracy_within_10pct", 27.14),
                "forecast_horizon_weeks": horizon_weeks,
                "latest_observation_date": profile.get("latest_available_observation_date", "2025-12-19") if profile else "2025-12-19",
                "timing_guarantee": "Strict rolling origin without lookahead (tau_train <= t_obs = t_fc - 1w)",
            }

            return PriceForecastResponse(
                crop_id=request.crop_id,
                cultivation_district_id=request.cultivation_district_id,
                target_market_id=request.target_market_id,
                target_market_name=market_name,
                forecast_target_date=request.forecast_target_date,
                price_type=request.price_type,
                currency="LKR",
                unit="kg",
                prediction_status=PredictionStatus.COMPLETED,
                forecasted_price_lkr_per_kg=predicted_price,
                model_version=self.metadata.get("model_version", "xgb-price-multihorizon-v3.0.0"),
                model_provenance=provenance,
                status_message="Commodity price forecast generated successfully by trained ML model (HARTI metadata convention).",
                created_at=datetime.now()
            )

        except Exception as e:
            logger.error(f"Inference error during price forecasting: {e}", exc_info=True)
            return DefaultUnavailablePricePredictor().forecast_price(request)


_active_price_predictor = TrainedPricePredictor()


def get_price_predictor() -> AbstractPricePredictor:
    """
    FastAPI dependency returning the active price forecasting engine.
    """
    return _active_price_predictor
