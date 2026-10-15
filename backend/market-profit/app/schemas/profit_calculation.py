import math
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


def to_decimal(val: Any, field_name: str) -> Decimal:
    """
    Safely convert numeric input to Python Decimal.
    Rejects None, booleans, NaN, and infinite values.
    """
    if val is None:
        raise ValueError(f"{field_name} cannot be None.")
    if isinstance(val, bool):
        raise ValueError(f"{field_name} cannot be a boolean value.")

    if isinstance(val, float):
        if math.isnan(val):
            raise ValueError(f"{field_name} cannot be NaN.")
        if math.isinf(val):
            raise ValueError(f"{field_name} cannot be infinite.")
        val = str(val)

    try:
        d = Decimal(str(val).strip())
    except (InvalidOperation, ValueError, TypeError) as e:
        raise ValueError(f"{field_name} must be a valid numeric value.") from e

    if d.is_nan():
        raise ValueError(f"{field_name} cannot be NaN.")
    if d.is_infinite():
        raise ValueError(f"{field_name} cannot be infinite.")

    return d


class ProfitCalculationInput(BaseModel):
    """
    Input payload for deterministic agricultural profit calculation.
    Strictly validates numeric values, positive yield/price, and non-negative cost.
    """
    expected_yield_kg: Decimal = Field(
        ...,
        description="Anticipated crop harvest volume in kilograms (must be > 0)"
    )
    selling_price_lkr_per_kg: Decimal = Field(
        ...,
        description="Farmer-assumed selling price in LKR per kg (must be > 0)"
    )
    total_cultivation_cost: Decimal = Field(
        default=Decimal("0.0"),
        description="Total cultivation expenditure in LKR (must be >= 0)"
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


class ProfitCalculationResult(BaseModel):
    """
    Structured outcome of deterministic agricultural profit calculation.
    Clearly marks the selling price as a farmer assumption rather than an ML forecast.
    Decoupled from ML inference and heuristic risk classifications.
    """
    expected_yield_kg: Decimal = Field(..., description="Expected harvest yield in kg")
    selling_price_lkr_per_kg: Decimal = Field(..., description="Selling price per kg in LKR")
    total_cultivation_cost: Decimal = Field(..., description="Total cultivation cost in LKR")
    gross_revenue: Decimal = Field(..., description="Gross revenue (Expected Yield × Selling Price)")
    net_profit: Decimal = Field(..., description="Net profit (Gross Revenue − Total Cost)")
    roi_percentage: Optional[Decimal] = Field(
        None,
        description="Return on investment percentage ((Net Profit / Total Cost) × 100); null when total cost is zero"
    )
    breakeven_price_lkr_per_kg: Decimal = Field(
        ...,
        description="Cost per kg / breakeven selling price (Total Cost / Expected Yield)"
    )
    margin_of_safety_percentage: Decimal = Field(
        ...,
        description="Margin of safety percentage (((Selling Price − Breakeven Price) / Selling Price) × 100)"
    )
    price_source: str = Field(
        default="farmer_assumption",
        description="Identifies source of selling price: 'farmer_assumption'"
    )
    is_manual_price_assumption: bool = Field(
        default=True,
        description="Flag confirming price is a user-entered planning assumption, not an ML forecast"
    )
    assumptions_note: str = Field(
        default="Selling price is a user-provided planning assumption, not a machine learning market price forecast.",
        description="Explicit methodological transparency disclaimer"
    )
    calculation_notes: Optional[str] = Field(
        None,
        description="Contextual calculation notes (e.g., zero-cost explanation)"
    )

    model_config = ConfigDict(from_attributes=True)
