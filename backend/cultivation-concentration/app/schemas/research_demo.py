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


class HistoricalScenarioResponse(ClosedResponse):
    status: Literal["historical_result_withheld"]
    mode: str
    operational_status: Literal["risk_level_not_yet_validated"]
    simulated_plan: PublicSimulatedPlan
    model_metadata: PublicModelMetadata
    features: Dict[str, Optional[str | int | float]]
    prediction: ProtectedPrediction
    observation_availability: ProtectedAvailability
    concentration_indicators: ProtectedConcentration
    scenario_explanation: str
    recommendation_status: Literal["blocked_unvalidated_risk"]
    diagnostic_alternatives: List[Dict[str, Any]] = Field(default_factory=list, max_length=0)
    disclosure_status: Literal["collective_values_withheld"]
    reason_codes: List[str]
    governance_notice: str

    @model_validator(mode="after")
    def disclosure_contract(self):
        # Exact public inputs only; even numeric means/proxy classes are private.
        own = {"District": self.simulated_plan.district, "Crop": self.simulated_plan.crop,
               "Season": self.simulated_plan.season, "Land_Size_Acres": self.simulated_plan.land_size_acres,
               "Planting_Month": date.fromisoformat(self.simulated_plan.planting_date).month,
               "Harvest_Month": date.fromisoformat(self.simulated_plan.expected_harvest_date).month}
        if list(self.features) != self.model_metadata.feature_names:
            raise ValueError("Research feature disclosure contract mismatch")
        for key, value in self.features.items():
            if (key in own and value != own[key]) or (key not in own and value is not None):
                raise ValueError("Historical derived features cannot be disclosed")
        return self


class ResearchDemoStatusResponse(BaseModel):
    enabled: bool
    allowed_date_range: Dict[str, str]
    supported_districts: List[str]
    supported_crops: List[str]
    supported_models: List[str]
    benchmark_overview: Dict[str, Any]
    isolated_database: str
