from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional, Union
from app.schemas.profit_calculation import (
    ProfitCalculationInput,
    ProfitCalculationResult,
    to_decimal,
)

TWO_PLACES = Decimal("0.01")
HUNDRED = Decimal("100")
ZERO = Decimal("0.0")


def calculate_deterministic_profit(
    expected_yield_kg: Union[Decimal, float, int, str],
    selling_price_lkr_per_kg: Union[Decimal, float, int, str],
    total_cultivation_cost: Union[Decimal, float, int, str] = Decimal("0.0"),
    round_result: bool = True
) -> ProfitCalculationResult:
    """
    Perform deterministic agricultural profit calculation using Python Decimal arithmetic.

    Formulas:
        Gross Revenue = Expected Yield (kg) × Selling Price (LKR/kg)
        Net Profit = Gross Revenue − Total Cultivation Cost
        ROI (%) = (Net Profit / Total Cost) × 100  (None if Total Cost == 0)
        Breakeven Price = Total Cost / Expected Yield
        Margin of Safety (%) = ((Selling Price − Breakeven Price) / Selling Price) × 100

    Rules:
        - expected_yield_kg must be > 0.
        - selling_price_lkr_per_kg must be > 0.
        - total_cultivation_cost must be >= 0.
        - NaN, infinite, non-numeric, and boolean values are rejected.
        - If total_cultivation_cost == 0, ROI is returned as None (null) and noted.
        - Selling price is explicitly marked as a user-provided assumption.
        - Risk classification is NOT performed by this service (decoupled).
    """
    # 1. Validation & Safe Decimal Conversion
    yield_dec = to_decimal(expected_yield_kg, "expected_yield_kg")
    if yield_dec <= ZERO:
        raise ValueError("expected_yield_kg must be greater than zero.")

    price_dec = to_decimal(selling_price_lkr_per_kg, "selling_price_lkr_per_kg")
    if price_dec <= ZERO:
        raise ValueError("selling_price_lkr_per_kg must be greater than zero.")

    cost_dec = to_decimal(total_cultivation_cost, "total_cultivation_cost")
    if cost_dec < ZERO:
        raise ValueError("total_cultivation_cost cannot be negative.")

    # 2. Deterministic Financial Arithmetic
    gross_revenue = yield_dec * price_dec
    net_profit = gross_revenue - cost_dec
    breakeven_price = cost_dec / yield_dec
    margin_of_safety = ((price_dec - breakeven_price) / price_dec) * HUNDRED

    calculation_notes: Optional[str] = None
    if cost_dec == ZERO:
        roi_percentage: Optional[Decimal] = None
        calculation_notes = "Total cultivation cost is zero. ROI is mathematically undefined."
    else:
        roi_percentage = (net_profit / cost_dec) * HUNDRED

    # 3. Precision & Rounding (ROUND_HALF_UP to 2 decimal places if enabled)
    if round_result:
        gross_revenue_out = gross_revenue.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        net_profit_out = net_profit.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        breakeven_out = breakeven_price.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        margin_of_safety_out = margin_of_safety.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        roi_out = (
            roi_percentage.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if roi_percentage is not None
            else None
        )
        yield_out = yield_dec.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        price_out = price_dec.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        cost_out = cost_dec.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    else:
        gross_revenue_out = gross_revenue
        net_profit_out = net_profit
        breakeven_out = breakeven_price
        margin_of_safety_out = margin_of_safety
        roi_out = roi_percentage
        yield_out = yield_dec
        price_out = price_dec
        cost_out = cost_dec

    return ProfitCalculationResult(
        expected_yield_kg=yield_out,
        selling_price_lkr_per_kg=price_out,
        total_cultivation_cost=cost_out,
        gross_revenue=gross_revenue_out,
        net_profit=net_profit_out,
        roi_percentage=roi_out,
        breakeven_price_lkr_per_kg=breakeven_out,
        margin_of_safety_percentage=margin_of_safety_out,
        price_source="farmer_assumption",
        is_manual_price_assumption=True,
        assumptions_note="Selling price is a user-provided planning assumption, not a machine learning market price forecast.",
        calculation_notes=calculation_notes,
    )


def calculate_profit_from_input(
    input_data: ProfitCalculationInput,
    round_result: bool = True
) -> ProfitCalculationResult:
    """Convenience adapter calculating deterministic profit from validated Pydantic input."""
    return calculate_deterministic_profit(
        expected_yield_kg=input_data.expected_yield_kg,
        selling_price_lkr_per_kg=input_data.selling_price_lkr_per_kg,
        total_cultivation_cost=input_data.total_cultivation_cost,
        round_result=round_result,
    )
