from datetime import datetime
from typing import Protocol, runtime_checkable
from app.schemas.common import PredictionStatus, STANDARD_MARKETS
from app.schemas.price_forecast import PriceForecastRequest, PriceForecastResponse


@runtime_checkable
class AbstractPricePredictor(Protocol):
    """
    Protocol defining the contract for commodity market price forecasting.
    Enables pluggable ML inference engines without altering routes or database schemas.
    """
    def forecast_price(self, request: PriceForecastRequest) -> PriceForecastResponse:
        ...


class DefaultUnavailablePricePredictor:
    """
    Default price predictor returned when trained ML models have not yet been connected.
    Returns prediction_status='unavailable' with strictly null predicted price values,
    refusing to generate mock prices, fake confidence intervals, or placeholder forecasts.
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


_default_price_predictor = DefaultUnavailablePricePredictor()


def get_price_predictor() -> AbstractPricePredictor:
    """
    FastAPI dependency returning the active price forecasting engine.
    Can be easily swapped or overridden when trained ML models are ready.
    """
    return _default_price_predictor
