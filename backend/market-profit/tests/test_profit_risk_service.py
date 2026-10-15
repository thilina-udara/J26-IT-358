from decimal import Decimal
import unittest
from pydantic import ValidationError
from app.schemas.profit_calculation import ProfitCalculationResult
from app.schemas.profit_risk import (
    ProfitRiskAssessmentInput,
    ProfitRiskAssessmentResult,
    ProfitRiskCategory,
    ProfitRiskFactors,
    ProfitRiskThresholds,
)
from app.services.profit_calculation_service import calculate_deterministic_profit
from app.services.profit_risk_service import (
    assess_profit_risk,
    assess_profit_risk_from_input,
    assess_profit_risk_from_parameters,
)


class TestProfitRiskAssessmentService(unittest.TestCase):
    """
    Unit tests for the rule-based Profit Risk Assessment Service.
    Verifies classification across loss, breakeven, medium, and low risk,
    boundary condition handling, zero-cost handling, threshold customization,
    and methodological transparency disclaimers.
    """

    def test_financial_loss_high_risk(self):
        """Net loss (revenue < cost, ROI < 0%) must be classified as High Risk."""
        result = assess_profit_risk_from_parameters(
            expected_yield_kg=Decimal("1000.00"),
            selling_price_lkr_per_kg=Decimal("80.00"),
            total_cultivation_cost=Decimal("100000.00")
        )

        self.assertIsInstance(result, ProfitRiskAssessmentResult)
        self.assertEqual(result.risk_level, ProfitRiskCategory.HIGH)
        self.assertEqual(result.risk_level.value, "High")
        self.assertEqual(result.assessment_type, "rule_based_heuristic")
        self.assertFalse(result.is_ml_prediction)
        self.assertIn("not a machine learning prediction", result.disclaimer.lower())
        self.assertIn("not been scientifically validated", result.disclaimer.lower())
        self.assertIn("net_profit < 0", result.factors.trigger_rule)
        self.assertEqual(result.factors.net_profit, Decimal("-20000.00"))
        self.assertEqual(result.factors.roi_percentage, Decimal("-20.00"))

    def test_exact_breakeven_medium_risk(self):
        """Exact breakeven (net profit = 0, ROI = 0%) must be Medium Risk."""
        result = assess_profit_risk_from_parameters(
            expected_yield_kg=Decimal("1000.00"),
            selling_price_lkr_per_kg=Decimal("100.00"),
            total_cultivation_cost=Decimal("100000.00")
        )

        self.assertEqual(result.risk_level, ProfitRiskCategory.MEDIUM)
        self.assertEqual(result.factors.net_profit, Decimal("0.00"))
        self.assertEqual(result.factors.roi_percentage, Decimal("0.00"))
        self.assertEqual(result.factors.margin_of_safety_percentage, Decimal("0.00"))
        self.assertIn("below the 25.0% Low Risk threshold", result.factors.trigger_rationale)

    def test_exact_low_risk_boundary(self):
        """
        Exact threshold boundary:
        ROI == 25.0% and Margin of Safety == 20.0% must evaluate as Low Risk.
        (Revenue = 125,000, Cost = 100,000 -> Net = 25,000, ROI = 25%, Margin = 20%).
        """
        result = assess_profit_risk_from_parameters(
            expected_yield_kg=Decimal("1000.00"),
            selling_price_lkr_per_kg=Decimal("125.00"),
            total_cultivation_cost=Decimal("100000.00")
        )

        self.assertEqual(result.risk_level, ProfitRiskCategory.LOW)
        self.assertEqual(result.factors.roi_percentage, Decimal("25.00"))
        self.assertEqual(result.factors.margin_of_safety_percentage, Decimal("20.00"))
        self.assertIn("meets or exceeds", result.factors.trigger_rationale)

    def test_clearly_low_risk(self):
        """Robust returns (ROI = 100%, Margin of Safety = 50%) evaluate as Low Risk."""
        result = assess_profit_risk_from_parameters(
            expected_yield_kg=Decimal("2000.00"),
            selling_price_lkr_per_kg=Decimal("150.00"),
            total_cultivation_cost=Decimal("150000.00")
        )

        self.assertEqual(result.risk_level, ProfitRiskCategory.LOW)
        self.assertEqual(result.factors.roi_percentage, Decimal("100.00"))
        self.assertEqual(result.factors.margin_of_safety_percentage, Decimal("50.00"))

    def test_just_below_low_risk_boundary_medium_risk(self):
        """Values immediately below the 25%/20% boundary evaluate as Medium Risk."""
        # Yield = 1000, Price = 124.90, Cost = 100,000 -> ROI = 24.90% (< 25.0%)
        result = assess_profit_risk_from_parameters(
            expected_yield_kg=Decimal("1000.00"),
            selling_price_lkr_per_kg=Decimal("124.90"),
            total_cultivation_cost=Decimal("100000.00")
        )

        self.assertEqual(result.risk_level, ProfitRiskCategory.MEDIUM)
        self.assertEqual(result.factors.roi_percentage, Decimal("24.90"))
        self.assertEqual(result.factors.margin_of_safety_percentage, Decimal("19.94"))

    def test_zero_cultivation_cost_insufficient_information(self):
        """
        Zero cultivation cost (ROI undefined):
        Must return 'insufficient_information' instead of fabricating Low/Medium/High.
        """
        result = assess_profit_risk_from_parameters(
            expected_yield_kg=Decimal("1500.00"),
            selling_price_lkr_per_kg=Decimal("90.00"),
            total_cultivation_cost=Decimal("0.00")
        )

        self.assertEqual(result.risk_level, ProfitRiskCategory.INSUFFICIENT_INFORMATION)
        self.assertEqual(result.risk_level.value, "insufficient_information")
        self.assertIsNone(result.factors.roi_percentage)
        self.assertIn("Total cultivation cost is zero", result.factors.trigger_rationale)
        self.assertIn("insufficient to compute financial risk", result.factors.trigger_rationale)

    def test_configurable_threshold_overrides(self):
        """Custom threshold parameters are respected."""
        custom_thresholds = ProfitRiskThresholds(
            min_roi_low_risk=Decimal("50.0"),
            min_margin_safety_low_risk=Decimal("30.0")
        )

        # ROI = 40.0%, Margin = 28.57%
        # Under default thresholds (25% / 20%), this would be Low Risk.
        # Under custom thresholds (50% / 30%), this evaluates as Medium Risk.
        result = assess_profit_risk_from_parameters(
            expected_yield_kg=Decimal("1000.00"),
            selling_price_lkr_per_kg=Decimal("140.00"),
            total_cultivation_cost=Decimal("100000.00"),
            thresholds=custom_thresholds
        )

        self.assertEqual(result.risk_level, ProfitRiskCategory.MEDIUM)
        self.assertEqual(result.thresholds_applied.min_roi_low_risk, Decimal("50.0"))
        self.assertEqual(result.thresholds_applied.min_margin_safety_low_risk, Decimal("30.0"))

    def test_reuse_existing_profit_calculation_result(self):
        """Passing a precomputed ProfitCalculationResult produces identical results."""
        profit_calc = calculate_deterministic_profit(
            expected_yield_kg=Decimal("1000.00"),
            selling_price_lkr_per_kg=Decimal("130.00"),
            total_cultivation_cost=Decimal("100000.00")
        )
        direct_result = assess_profit_risk(profit_calc)
        param_result = assess_profit_risk_from_parameters(
            expected_yield_kg=Decimal("1000.00"),
            selling_price_lkr_per_kg=Decimal("130.00"),
            total_cultivation_cost=Decimal("100000.00")
        )

        self.assertEqual(direct_result.risk_level, param_result.risk_level)
        self.assertEqual(direct_result.factors.net_profit, param_result.factors.net_profit)
        self.assertEqual(direct_result.factors.roi_percentage, param_result.factors.roi_percentage)

    def test_assess_profit_risk_from_input_model(self):
        """Convenience method accepting validated Pydantic model."""
        inp = ProfitRiskAssessmentInput(
            expected_yield_kg=Decimal("2000.00"),
            selling_price_lkr_per_kg=Decimal("150.00"),
            total_cultivation_cost=Decimal("180000.00")
        )
        res = assess_profit_risk_from_input(inp)
        # Revenue = 300,000, Net = 120,000, ROI = 66.67%, Margin = 40.0% -> Low Risk
        self.assertEqual(res.risk_level, ProfitRiskCategory.LOW)
        self.assertEqual(res.factors.net_profit, Decimal("120000.00"))


class TestProfitRiskInputValidation(unittest.TestCase):
    """Validation tests for invalid quantities, negative thresholds, and boundary constraints."""

    def test_invalid_yield_and_price_rejected(self):
        """Yield <= 0 and price <= 0 are rejected with ValueError."""
        with self.assertRaises(ValueError):
            assess_profit_risk_from_parameters(
                expected_yield_kg=Decimal("0.0"),
                selling_price_lkr_per_kg=Decimal("100.0"),
                total_cultivation_cost=Decimal("50000.0")
            )

        with self.assertRaises(ValueError):
            assess_profit_risk_from_parameters(
                expected_yield_kg=Decimal("1000.0"),
                selling_price_lkr_per_kg=Decimal("-10.0"),
                total_cultivation_cost=Decimal("50000.0")
            )

    def test_negative_cost_rejected(self):
        """Negative cost is rejected with ValueError."""
        with self.assertRaises(ValueError):
            assess_profit_risk_from_parameters(
                expected_yield_kg=Decimal("1000.0"),
                selling_price_lkr_per_kg=Decimal("100.0"),
                total_cultivation_cost=Decimal("-100.0")
            )

    def test_nan_and_inf_rejected(self):
        """NaN and Infinity are rejected with ValueError."""
        with self.assertRaises(ValueError):
            assess_profit_risk_from_parameters(
                expected_yield_kg="NaN",
                selling_price_lkr_per_kg=Decimal("100.0"),
                total_cultivation_cost=Decimal("50000.0")
            )

        with self.assertRaises(ValueError):
            assess_profit_risk_from_parameters(
                expected_yield_kg=Decimal("1000.0"),
                selling_price_lkr_per_kg="Infinity",
                total_cultivation_cost=Decimal("50000.0")
            )

    def test_negative_roi_threshold_rejected(self):
        """Threshold ROI cannot be negative."""
        with self.assertRaises(ValidationError):
            ProfitRiskThresholds(min_roi_low_risk=Decimal("-5.0"))

    def test_margin_safety_threshold_range(self):
        """Margin of safety threshold must be between 0.0 and 100.0%."""
        with self.assertRaises(ValidationError):
            ProfitRiskThresholds(min_margin_safety_low_risk=Decimal("-1.0"))

        with self.assertRaises(ValidationError):
            ProfitRiskThresholds(min_margin_safety_low_risk=Decimal("105.0"))


if __name__ == "__main__":
    unittest.main()
