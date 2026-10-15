
"""Schemas for historical research demo evaluation and diagnostics."""
from datetime import date
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class HistoricalScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    district: Literal["Matara", "Hambantota"]
    crop: Literal["Bandakka", "Brinjal", "Pumpkin", "Corn", "Mung Beans", "Chillies"]
    season: Literal["Maha", "Yala"]
    land_size_acres: float = Field(gt=0, le=100)
    planting_date: date
    expected_harvest_date: date
    decision_cutoff: Optional[date] = None
    model_name: Literal["XGBoost", "CatBoost", "Random Forest", "LinearSVC", "RBF SVC"] = "XGBoost"


class ClosedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ProtectedPrediction(ClosedResponse):
    historical_proxy_label: None = None
    predicted_risk_level: None = None
    class_probabilities: None = None
    overlapping_peer_count: None = None
    overlapping_peer_acres: None = None
    total_window_acres: None = None
    is_isolated_plan: None = None
    coverage_status: Literal["collective_values_withheld"]
    peer_explanation: str


class ProtectedAvailability(ClosedResponse):
    status: Literal["not_established"]
    replay_unknown_peer_records: None = None
    replay_unknown_prior_records: None = None
    source_provenance: str
    required_evidence: str


class ProtectedWindow(ClosedResponse):
    record_count: None = None
    acres: None = None
    disclosure_status: Literal["collective_values_withheld"]


class ProtectedConcentration(ClosedResponse):
    harvest_window_start: str
    harvest_window_end: str
    matching_scope: str
    historical_dataset_window: ProtectedWindow
    provably_available_window: ProtectedWindow
    availability_status: Literal["not_disclosed"]
    unknown_availability_count: None = None
    observed_after_cutoff_count: None = None
    interpretation: str


class FrozenBenchmark(ClosedResponse):
    accuracy: float = Field(ge=0, le=1)
    macro_f1: float = Field(ge=0, le=1)
    medium_recall: float = Field(ge=0, le=1)
    high_recall: float = Field(ge=0, le=1)


class PublicModelMetadata(ClosedResponse):
    model_name: Literal["XGBoost", "CatBoost", "Random Forest", "LinearSVC", "RBF SVC"]
    trained_through: int
    training_data_cutoff: str
    training_cutoff_basis: str
    model_available_at_cutoff: str
    simulated_target_year: int
    is_out_of_time_holdout: Literal[False]
    holdout_caveat: str
    benchmark_metrics: Optional[FrozenBenchmark]
    benchmark_scope: str
    feature_names: List[str]
    feature_count: int
    own_production_status: str
    probability_status: str


class PublicSimulatedPlan(ClosedResponse):
    district: str
    crop: str
    season: str
    land_size_acres: float
    planting_date: str
    expected_harvest_date: str
    target_year: int
    decision_cutoff: str
    cutoff_timestamp: str
    cutoff_source: str


class HistoricalScenarioResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str
    mode: str = "research_demo_simulation"
    operational_status: str = "risk_level_not_yet_validated"
    simulated_plan: Dict[str, Any]
    model_metadata: Dict[str, Any]
    features: Dict[str, Any]
    prediction: Dict[str, Any]
    observation_availability: Optional[Dict[str, Any]] = None
    concentration_indicators: Optional[Dict[str, Any]] = None
    scenario_explanation: Optional[str] = None
    recommendation_status: Optional[str] = "blocked_unvalidated_risk"
    diagnostic_alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    disclosure_status: Optional[str] = None
    reason_codes: Optional[List[str]] = None
    governance_notice: Optional[str] = None


class ResearchDemoStatusResponse(BaseModel):
    enabled: bool
    allowed_date_range: Dict[str, str]
    supported_districts: List[str]
    supported_crops: List[str]
    supported_models: List[str]
    benchmark_overview: Dict[str, Any]
    isolated_database: str
