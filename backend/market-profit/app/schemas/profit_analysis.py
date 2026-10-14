import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.common import (
    BudgetEntryMode,
    DemandLevel,
    PredictionStatus,
    ProfitRiskLevel,
    STANDARD_MARKETS,
    validate_crop_id_value,
    validate_district_id_value,
)
from app.schemas.cultivation_cost import CultivationCostBreakdown


class FarmerAnalysisInput(BaseModel):
    """
    Farmer or planner input payload requesting harvest price forecasting,
    demand evaluation, and profit risk classification.
    """
    crop_id: str = Field(..., description="Target candidate crop identifier")
    cultivation_district_id: str = Field(..., description="District where cultivation takes place (e.g., 'LK-71')")
    target_market_id: str = Field(..., description="Target selling market center (e.g., 'DEC_DAMBULLA')")
    target_market_name: Optional[str] = Field(None, description="Optional custom market name")
    forecast_target_date: date = Field(..., description="Expected harvest / market arrival date")
    forecast_horizon_days: int = Field(default=90, gt=0, le=365, description="Forecast window in days")
    cultivation_extent_acres: Decimal = Field(..., gt=Decimal("0.0"), description="Cultivated land extent in acres")
    estimated_production_kg: Decimal = Field(..., gt=Decimal("0.0"), description="Anticipated harvest yield in kg")

    # Budget specification (supports quick or detailed mode)
    budget_entry_mode: BudgetEntryMode = Field(default=BudgetEntryMode.QUICK, description="Budget input mode")
    cultivation_budget_id: Optional[int] = Field(None, description="Optional ID of existing saved budget")
    quick_total_cost: Optional[Decimal] = Field(None, gt=Decimal("0.0"), description="Total cost in LKR (quick mode)")
    budget_breakdown: Optional[CultivationCostBreakdown] = Field(None, description="Detailed category breakdown")

    @field_validator("crop_id")
    @classmethod
    def check_crop(cls, v: str) -> str:
        return validate_crop_id_value(v)

    @field_validator("cultivation_district_id")
    @classmethod
    def check_district(cls, v: str) -> str:
        return validate_district_id_value(v)

    @model_validator(mode="after")
    def resolve_market_and_budget(self) -> "FarmerAnalysisInput":
        # Auto-fill market name if standard market ID is given
        if not self.target_market_name and self.target_market_id in STANDARD_MARKETS:
            self.target_market_name = STANDARD_MARKETS[self.target_market_id]

        # Verify budget input consistency
        if self.budget_entry_mode == BudgetEntryMode.QUICK:
            if not self.cultivation_budget_id and (self.quick_total_cost is None or self.quick_total_cost <= Decimal("0.0")):
                raise ValueError("In 'quick' budget mode, either quick_total_cost or cultivation_budget_id must be provided.")
        elif self.budget_entry_mode == BudgetEntryMode.DETAILED:
            if not self.cultivation_budget_id and self.budget_breakdown is None:
                raise ValueError("In 'detailed' budget mode, a budget_breakdown must be supplied.")

        return self

    def resolve_total_cost(self) -> Decimal:
        """Helper to get effective total cultivation cost."""
        if self.budget_entry_mode == BudgetEntryMode.QUICK and self.quick_total_cost:
            return self.quick_total_cost
        if self.budget_entry_mode == BudgetEntryMode.DETAILED and self.budget_breakdown:
            return self.budget_breakdown.sum_provided()
        return Decimal("0.0")


class PredictionResultResponse(BaseModel):
    """
    Standardized analysis and prediction response.
    All ML-derived fields are strictly nullable when prediction_status != COMPLETED.
    """
    analysis_reference: str = Field(..., description="Unique tracking reference for this analysis")
    prediction_status: PredictionStatus = Field(..., description="pending, completed, unavailable, or failed")
    crop_id: str
    cultivation_district_id: str
    target_market_id: str
    target_market_name: Optional[str] = None
    forecast_target_date: date
    forecast_horizon_days: int
    cultivation_extent_acres: Decimal
    estimated_production_kg: Decimal
    estimated_total_cost: Decimal

    # ML-dependent forecasted fields (nullable until inference succeeds)
    forecasted_wholesale_price: Optional[Decimal] = None
    price_confidence_lower: Optional[Decimal] = None
    price_confidence_upper: Optional[Decimal] = None
    projected_demand_volume_kg: Optional[Decimal] = None
    projected_demand_level: Optional[DemandLevel] = None
    projected_revenue: Optional[Decimal] = None
    projected_net_profit: Optional[Decimal] = None
    projected_roi_percentage: Optional[Decimal] = None
    profit_risk_level: Optional[ProfitRiskLevel] = None
    risk_score: Optional[Decimal] = None
    risk_factors: Optional[Dict[str, Any]] = None

    # Agnostic ML provenance and diagnostics
    model_version: Optional[str] = None
    model_provenance: Optional[Dict[str, Any]] = None
    status_message: str = Field(default="Analysis request received")
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def create_unavailable(
        cls,
        analysis_input: FarmerAnalysisInput,
        reason: str = "ML inference models are currently offline or undergoing scheduled retraining."
    ) -> "PredictionResultResponse":
        """Factory for generating explicit model-unavailable responses."""
        return cls(
            analysis_reference=f"REF-{uuid.uuid4().hex[:10].upper()}",
            prediction_status=PredictionStatus.UNAVAILABLE,
            crop_id=analysis_input.crop_id,
            cultivation_district_id=analysis_input.cultivation_district_id,
            target_market_id=analysis_input.target_market_id,
            target_market_name=analysis_input.target_market_name,
            forecast_target_date=analysis_input.forecast_target_date,
            forecast_horizon_days=analysis_input.forecast_horizon_days,
            cultivation_extent_acres=analysis_input.cultivation_extent_acres,
            estimated_production_kg=analysis_input.estimated_production_kg,
            estimated_total_cost=analysis_input.resolve_total_cost(),
            status_message="Machine learning models are currently unavailable.",
            error_message=reason,
            created_at=datetime.now()
        )

    @classmethod
    def create_failed(
        cls,
        analysis_input: FarmerAnalysisInput,
        error_detail: str
    ) -> "PredictionResultResponse":
        """Factory for generating explicit failed prediction responses."""
        return cls(
            analysis_reference=f"REF-{uuid.uuid4().hex[:10].upper()}",
            prediction_status=PredictionStatus.FAILED,
            crop_id=analysis_input.crop_id,
            cultivation_district_id=analysis_input.cultivation_district_id,
            target_market_id=analysis_input.target_market_id,
            target_market_name=analysis_input.target_market_name,
            forecast_target_date=analysis_input.forecast_target_date,
            forecast_horizon_days=analysis_input.forecast_horizon_days,
            cultivation_extent_acres=analysis_input.cultivation_extent_acres,
            estimated_production_kg=analysis_input.estimated_production_kg,
            estimated_total_cost=analysis_input.resolve_total_cost(),
            status_message="Prediction execution failed during processing.",
            error_message=error_detail,
            created_at=datetime.now()
        )
