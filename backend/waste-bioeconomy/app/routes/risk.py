"""
FastAPI Route Handlers for Spoilage Risk Scoring & Telemetry Stress
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks & Waste Management
Student: Lakruwan W.M.K. (IT23330382)
Project: J26-IT-358
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.core.risk_service import RiskScoringService
from app.schemas.risk import (
    ModelBenchmarkResponse,
    RiskPredictionRequest,
    RiskPredictionResponse,
)

router = APIRouter(
    prefix="/api/v1/risk",
    tags=["Spoilage Risk Scoring & Telemetry Stress Analysis"]
)


@router.post(
    "/predict",
    response_model=RiskPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict In-Transit Spoilage Loss % & Partition Payload Mass",
    description=(
        "Ingests real-time transit telemetry (temperature, humidity, vehicle insulation, "
        "road vibration rank, packaging penalty) to predict quantitative post-harvest spoilage loss "
        "using XGBoost Regressor and Classifier. Partitions incoming payload into Stream 1 "
        "(commercial fresh food) and Stream 2 (circular bioeconomy cull waste)."
    ),
)
def predict_spoilage_risk(request: RiskPredictionRequest) -> RiskPredictionResponse:
    try:
        service = RiskScoringService.get_instance()
        return service.predict_risk(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing XGBoost risk inference: {exc!s}"
        ) from exc


@router.get(
    "/benchmark",
    response_model=ModelBenchmarkResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Comparative Model Evaluation Benchmarks (Table 1)",
    description=(
        "Returns empirical benchmark metrics comparing the proposed XGBoost ensemble against "
        "Static Rule-Based heuristic, Linear/Logistic regression, and Random Forest baselines "
        "evaluated on the stratified 1,199-trip holdout test set."
    ),
)
def get_model_benchmarks() -> ModelBenchmarkResponse:
    try:
        service = RiskScoringService.get_instance()
        return service.get_benchmark_data()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading model benchmark table: {exc!s}"
        ) from exc


@router.get(
    "/feature-importance",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Retrieve XGBoost Feature Importance Rankings",
    description="Returns normalized gain-based feature importance rankings across all 45 encoded features.",
)
def get_feature_importance() -> dict[str, Any]:
    try:
        service = RiskScoringService.get_instance()
        return service.get_feature_importance()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving feature importance: {exc!s}"
        ) from exc


@router.get(
    "/crops",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Retrieve Supported Focal Crop Agronomic Profiles",
    description="Returns physiological baselines (moisture %, C:N ratio, baseline respiration, Q10 factor) for 8 focal Sri Lankan crops.",
)
def get_crop_profiles() -> dict[str, Any]:
    try:
        service = RiskScoringService.get_instance()
        return service.get_crop_profiles()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving crop profiles: {exc!s}"
        ) from exc
