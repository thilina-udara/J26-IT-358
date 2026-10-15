from datetime import datetime
from typing import Protocol, runtime_checkable
from app.schemas.common import PredictionStatus, STANDARD_MARKETS
from app.schemas.demand_forecast import DemandForecastRequest, DemandForecastResponse


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
    Default demand predictor returned when trained ML models have not yet been connected.
    Returns prediction_status='unavailable' with strictly null predicted metrics,
    refusing to generate mock values, fake confidence scores, or fabricated forecasts.
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


_default_demand_predictor = DefaultUnavailableDemandPredictor()


def get_demand_predictor() -> AbstractDemandPredictor:
    """
    FastAPI dependency returning the active demand prediction engine.
    Can be easily swapped or overridden when trained ML models are ready.
    """
    return _default_demand_predictor
