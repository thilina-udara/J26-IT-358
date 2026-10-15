from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.profit_calculation import (
    ProfitCalculationInput,
    ProfitCalculationResult,
    to_decimal,
)


class ProfitRiskCategory(str, Enum):
    """
    Standardized categorical profit risk levels.
    Includes explicit 'insufficient_information' when inputs lack necessary data for risk assessment.
    """
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class ProfitRiskThresholds(BaseModel):
    """
    Configurable deterministic thresholds for rule-based profit risk evaluation.
    Preliminary heuristic thresholds; not scientifically validated or trained ML weights.
    """
    min_roi_low_risk: Decimal = Field(
        default=Decimal("25.0"),
        description="Minimum ROI percentage required for Low Risk classification"
    )
    min_margin_safety_low_risk: Decimal = Field(
        default=Decimal("20.0"),
        description="Minimum Margin of Safety percentage required for Low Risk classification"
    )

    @field_validator("min_roi_low_risk", mode="before")
    @classmethod
    def validate_roi_threshold(cls, v: Any) -> Decimal:
        d = to_decimal(v, "min_roi_low_risk")
        if d < Decimal("0.0"):
            raise ValueError("min_roi_low_risk cannot be negative.")
        return d

    @field_validator("min_margin_safety_low_risk", mode="before")
    @classmethod
    def validate_margin_threshold(cls, v: Any) -> Decimal:
        d = to_decimal(v, "min_margin_safety_low_risk")
        if d < Decimal("0.0") or d > Decimal("100.0"):
            raise ValueError("min_margin_safety_low_risk must be between 0.0 and 100.0%.")
        return d


class ProfitRiskAssessmentInput(BaseModel):
    """
    Input schema for evaluating profit risk.
    Accepts cultivation financial parameters along with optional threshold overrides.
    """
    expected_yield_kg: Decimal = Field(..., description="Expected harvest production in kg (> 0)")
    selling_price_lkr_per_kg: Decimal = Field(..., description="Farmer-assumed selling price in LKR/kg (> 0)")
    total_cultivation_cost: Decimal = Field(
        default=Decimal("0.0"),
        description="Total cultivation cost in LKR (>= 0)"
    )
    thresholds: Optional[ProfitRiskThresholds] = Field(
        default=None,
        description="Optional custom thresholds for heuristic risk evaluation"
    )

    @field_validator("expected_yield_kg", mode="before")
    @classmethod
    def validate_yield(cls, v: Any) -> Decimal:
        d = to_decimal(v, "expected_yield_kg")
        if d <= Decimal("0.0"):
            raise ValueError("expected_yield_kg must be greater than zero.")
        return d

    @field_validator("selling_price_lkr_per_kg", mode="before")
    @classmethod
    def validate_price(cls, v: Any) -> Decimal:
        d = to_decimal(v, "selling_price_lkr_per_kg")
        if d <= Decimal("0.0"):
            raise ValueError("selling_price_lkr_per_kg must be greater than zero.")
        return d

    @field_validator("total_cultivation_cost", mode="before")
    @classmethod
    def validate_cost(cls, v: Any) -> Decimal:
        d = to_decimal(v, "total_cultivation_cost")
        if d < Decimal("0.0"):
            raise ValueError("total_cultivation_cost cannot be negative.")
        return d


class ProfitRiskFactors(BaseModel):
    """
    Transparent breakdown of quantitative indicators and triggered decision rules.
    """
    net_profit: Decimal = Field(..., description="Calculated net profit in LKR")
    roi_percentage: Optional[Decimal] = Field(None, description="ROI percentage; None when total cost is zero")
    breakeven_price_lkr_per_kg: Decimal = Field(..., description="Breakeven selling price in LKR per kg")
    margin_of_safety_percentage: Decimal = Field(..., description="Margin of safety percentage")
    selling_price_lkr_per_kg: Decimal = Field(..., description="Selling price evaluated in LKR per kg")
    expected_yield_kg: Decimal = Field(..., description="Harvest production evaluated in kg")
    total_cultivation_cost: Decimal = Field(..., description="Total cultivation cost evaluated in LKR")
    trigger_rule: str = Field(..., description="Specific rule condition that determined the risk level")
    trigger_rationale: str = Field(..., description="Detailed rationale explaining the assessment outcome")

    model_config = ConfigDict(from_attributes=True)


class ProfitRiskAssessmentResult(BaseModel):
    """
    Output model of rule-based agricultural profit risk evaluation.
    Clearly identifies the assessment as a heuristic rule, NOT an ML prediction,
    and states that thresholds are preliminary and not scientifically validated.
    """
    risk_level: ProfitRiskCategory = Field(
        ...,
        description="Assessed risk level: Low, Medium, High, or insufficient_information"
    )
    assessment_type: str = Field(
        default="rule_based_heuristic",
        description="Categorization method identifier: 'rule_based_heuristic'"
    )
    is_ml_prediction: bool = Field(
        default=False,
        description="Explicit flag confirming this is NOT a machine learning prediction"
    )
    disclaimer: str = Field(
        default=(
            "Preliminary rule-based heuristic classification based on user planning thresholds. "
            "This is NOT a machine learning prediction and these preliminary thresholds have NOT been scientifically validated."
        ),
        description="Mandatory transparency and non-validation disclaimer"
    )
    thresholds_applied: ProfitRiskThresholds = Field(
        ...,
        description="The exact numerical thresholds applied for this evaluation"
    )
    factors: ProfitRiskFactors = Field(
        ...,
        description="Quantitative indicators and specific rule evaluation details"
    )
    profit_calculation: ProfitCalculationResult = Field(
        ...,
        description="Underlying deterministic profit calculation result"
    )

    model_config = ConfigDict(from_attributes=True)
