"""Pydantic schemas for in-transit spoilage risk scoring and mass-partitioning."""

from typing import Any

from pydantic import BaseModel, Field


class TelemetryStressIndices(BaseModel):
    transit_speed_kmh: float = Field(..., description="Average transit velocity in km/h")
    effective_temperature_c: float = Field(..., description="Internal cargo temperature considering vehicle insulation")
    mechanical_vibration_index: float = Field(..., description="Composite road roughness and packaging impact index")
    thermal_stress_index: float = Field(..., description="Degree-hours above 22°C threshold amplified by humidity")
    q10_respiration_factor: float = Field(..., description="Physiological respiration acceleration factor")


class RiskPredictionRequest(BaseModel):
    crop_name: str = Field(..., examples=["Tomato"], description="Crop name (e.g., Tomato, Big Onion, Cabbage, Okra)")
    payload_kg: float = Field(..., gt=0, examples=[1000.0], description="Total consignment weight in kilograms")
    distance_km: float = Field(..., gt=0, examples=[148.0], description="Total transit corridor distance in km")
    transit_hours: float = Field(..., gt=0, examples=[5.5], description="Total transport duration in hours")
    ambient_temperature_c: float = Field(..., examples=[32.5], description="Ambient air temperature in Celsius")
    ambient_humidity_pct: float = Field(..., ge=0, le=100, examples=[78.0], description="Relative humidity percentage")
    vehicle_type: str = Field(
        ...,
        examples=["OPEN_TRUCK"],
        description="Vehicle type: OPEN_TRUCK, COVERED_TRUCK, THREE_WHEELER, REFRIGERATED_VAN"
    )
    road_condition: str = Field(
        ...,
        examples=["POOR"],
        description="Road surface quality: GOOD, MODERATE, POOR"
    )
    packaging_type: str = Field(
        ...,
        examples=["POLYSACK_MESH"],
        description="Packaging container: PLASTIC_CRATE, VENTILATED_BOX, CARDBOARD_BOX, POLYSACK_MESH"
    )
    route: str | None = Field("DAMBULLA - COLOMBO", examples=["DAMBULLA - COLOMBO"], description="Transport route corridor")
    season: str | None = Field("YALA", examples=["YALA"], description="Cropping season: YALA, MAHA, DRY, WET")


class RiskPredictionResponse(BaseModel):
    crop_name: str
    total_payload_kg: float
    predicted_spoilage_loss_pct: float = Field(..., description="XGBoost predicted quantitative post-harvest loss %")
    risk_class: int = Field(..., description="0 = LOW (<15%), 1 = MEDIUM (15-20%), 2 = HIGH (>20%)")
    risk_tier: str = Field(..., description="Operational urgency tier: LOW, MEDIUM, HIGH")
    stream_1_fresh_produce_kg: float = Field(..., description="Healthy produce viable for commercial human consumption")
    stream_1_fresh_pct: float
    stream_1_recommended_channel: str = Field(..., description="Commercial retail routing channel")
    stream_2_bioeconomy_feedstock_kg: float = Field(..., description="Estimated cull waste mass diverted to bioeconomy")
    stream_2_waste_pct: float
    stream_2_destination: str = Field(..., description="AEROBIC_COMPOSTING or ANAEROBIC_BIOGAS_DIVERSION")
    biogas_fallback_trigger: int = Field(..., description="1 if extreme moisture/rot triggers biogas diversion, else 0")
    stress_indices: TelemetryStressIndices
    model_version: str = "XGBoost v3.4.1 (RMSE=1.44%, R2=0.9691)"


class ModelBenchmarkItem(BaseModel):
    model_name: str
    model_type: str
    accuracy_pct: float
    precision: float
    recall: float
    macro_f1: float
    rmse_pct: float
    mae_pct: float


class ModelBenchmarkResponse(BaseModel):
    benchmark_comparison: list[ModelBenchmarkItem]
    evaluation_dataset: str = "Test Holdout (N=1,199 trips)"
    target_objectives: dict[str, Any]
