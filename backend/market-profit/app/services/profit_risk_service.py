from decimal import Decimal
from typing import Optional, Union
from app.schemas.profit_calculation import ProfitCalculationResult
from app.schemas.profit_risk import (
    ProfitRiskAssessmentInput,
    ProfitRiskAssessmentResult,
    ProfitRiskCategory,
    ProfitRiskFactors,
    ProfitRiskThresholds,
)
from app.services.profit_calculation_service import calculate_deterministic_profit

ZERO = Decimal("0.0")
DEFAULT_THRESHOLDS = ProfitRiskThresholds()


def assess_profit_risk(
    profit_calc: ProfitCalculationResult,
    thresholds: Optional[ProfitRiskThresholds] = None
) -> ProfitRiskAssessmentResult:
    """
    Evaluate agricultural profit risk using deterministic preliminary rules.
    Decoupled from ML inference; transparently explains all applied criteria.

    Rules:
        1. Zero Cultivation Cost:
           When total_cultivation_cost == 0, ROI is undefined.
           Returns 'insufficient_information' rather than inventing a Low/Medium/High category.
        2. High Risk:
           Net profit < 0 or ROI < 0%.
        3. Low Risk:
           ROI >= min_roi_low_risk AND margin_of_safety >= min_margin_safety_low_risk.
        4. Medium Risk:
           Net profit >= 0 AND (ROI < min_roi_low_risk OR margin_of_safety < min_margin_safety_low_risk).

    Boundary Values:
        - Breakeven (net_profit == 0, ROI == 0%): Classified as Medium Risk (0% < 25%).
        - Exact thresholds (ROI == 25.0%, Margin of Safety == 20.0%): Classified as Low Risk.
    """
    applied_thresholds = thresholds or DEFAULT_THRESHOLDS
    net_profit = profit_calc.net_profit
    roi = profit_calc.roi_percentage
    margin_of_safety = profit_calc.margin_of_safety_percentage

    # Rule 1: Zero Cultivation Cost -> Insufficient Information
    if profit_calc.total_cultivation_cost == ZERO or roi is None:
        risk_level = ProfitRiskCategory.INSUFFICIENT_INFORMATION
        trigger_rule = "total_cultivation_cost == 0 (ROI undefined)"
        trigger_rationale = (
            "Total cultivation cost is zero, making ROI mathematically undefined. "
            "Cultivation expenditure data is insufficient to compute financial risk."
        )

    # Rule 2: Financial Loss -> High Risk
    elif net_profit < ZERO or roi < ZERO:
        risk_level = ProfitRiskCategory.HIGH
        trigger_rule = f"net_profit < 0 (LKR {net_profit}) or ROI < 0% ({roi}%)"
        trigger_rationale = (
            f"Expected revenue fails to recover cultivation expenditure, resulting in a net loss of "
            f"LKR {net_profit} (ROI: {roi}%). Cultivation operates at a direct financial deficit."
        )

    # Rule 3: Low Risk -> ROI >= threshold AND Margin of Safety >= threshold
    elif roi >= applied_thresholds.min_roi_low_risk and margin_of_safety >= applied_thresholds.min_margin_safety_low_risk:
        risk_level = ProfitRiskCategory.LOW
        trigger_rule = (
            f"ROI >= {applied_thresholds.min_roi_low_risk}% ({roi}%) and "
            f"Margin of Safety >= {applied_thresholds.min_margin_safety_low_risk}% ({margin_of_safety}%)"
        )
        trigger_rationale = (
            f"ROI of {roi}% meets or exceeds the {applied_thresholds.min_roi_low_risk}% requirement, and "
            f"margin of safety of {margin_of_safety}% provides adequate cushion against price or yield declines."
        )

    # Rule 4: Medium Risk -> Non-negative profit but falls below Low Risk thresholds
    else:
        risk_level = ProfitRiskCategory.MEDIUM
        failed_criteria = []
        if roi < applied_thresholds.min_roi_low_risk:
            failed_criteria.append(
                f"ROI of {roi}% is below the {applied_thresholds.min_roi_low_risk}% Low Risk threshold"
            )
        if margin_of_safety < applied_thresholds.min_margin_safety_low_risk:
            failed_criteria.append(
                f"Margin of Safety of {margin_of_safety}% is below the "
                f"{applied_thresholds.min_margin_safety_low_risk}% Low Risk threshold"
            )
        trigger_rule = "Net profit >= 0 but ROI < threshold or Margin of Safety < threshold"
        trigger_rationale = (
            f"Cultivation produces a non-negative net profit of LKR {net_profit}, but "
            f"{'; '.join(failed_criteria)}. The safety margin against market volatility is limited."
        )

    factors = ProfitRiskFactors(
        net_profit=net_profit,
        roi_percentage=roi,
        breakeven_price_lkr_per_kg=profit_calc.breakeven_price_lkr_per_kg,
        margin_of_safety_percentage=margin_of_safety,
        selling_price_lkr_per_kg=profit_calc.selling_price_lkr_per_kg,
        expected_yield_kg=profit_calc.expected_yield_kg,
        total_cultivation_cost=profit_calc.total_cultivation_cost,
        trigger_rule=trigger_rule,
        trigger_rationale=trigger_rationale,
    )

    return ProfitRiskAssessmentResult(
        risk_level=risk_level,
        assessment_type="rule_based_heuristic",
        is_ml_prediction=False,
        disclaimer=(
            "Preliminary rule-based heuristic classification based on user planning thresholds. "
            "This is NOT a machine learning prediction and these preliminary thresholds have NOT been scientifically validated."
        ),
        thresholds_applied=applied_thresholds,
        factors=factors,
        profit_calculation=profit_calc,
    )


def assess_profit_risk_from_parameters(
    expected_yield_kg: Union[Decimal, float, int, str],
    selling_price_lkr_per_kg: Union[Decimal, float, int, str],
    total_cultivation_cost: Union[Decimal, float, int, str] = Decimal("0.0"),
    thresholds: Optional[ProfitRiskThresholds] = None,
    round_result: bool = True
) -> ProfitRiskAssessmentResult:
    """
    Convenience method: calculates deterministic profit and evaluates rule-based risk.
    Reuses calculate_deterministic_profit without duplicating financial formulas.
    """
    profit_calc = calculate_deterministic_profit(
        expected_yield_kg=expected_yield_kg,
        selling_price_lkr_per_kg=selling_price_lkr_per_kg,
        total_cultivation_cost=total_cultivation_cost,
        round_result=round_result,
    )
    return assess_profit_risk(profit_calc=profit_calc, thresholds=thresholds)


def assess_profit_risk_from_input(
    input_data: ProfitRiskAssessmentInput,
    round_result: bool = True
) -> ProfitRiskAssessmentResult:
    """Convenience adapter evaluating rule-based risk from validated Pydantic input."""
    return assess_profit_risk_from_parameters(
        expected_yield_kg=input_data.expected_yield_kg,
        selling_price_lkr_per_kg=input_data.selling_price_lkr_per_kg,
        total_cultivation_cost=input_data.total_cultivation_cost,
        thresholds=input_data.thresholds,
        round_result=round_result,
    )
