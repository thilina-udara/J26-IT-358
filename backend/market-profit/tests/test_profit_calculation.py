from decimal import Decimal
import math
import unittest
from pydantic import ValidationError
from app.schemas.profit_calculation import (
    ProfitCalculationInput,
    ProfitCalculationResult,
)
from app.services.profit_calculation_service import (
    calculate_deterministic_profit,
    calculate_profit_from_input,
)


class TestDeterministicProfitCalculation(unittest.TestCase):
    """
    Unit tests for standalone deterministic profit calculation service.
    Verifies financial arithmetic, Python Decimal precision, zero-cost edge cases,
    loss scenarios, input validation, and assumption provenance labeling.
    """

    def test_standard_profitable_scenario(self):
        """Verify calculation for a standard profitable cultivation scenario."""
        result = calculate_deterministic_profit(
            expected_yield_kg=Decimal("2000.00"),
            selling_price_lkr_per_kg=Decimal("120.00"),
            total_cultivation_cost=Decimal("150000.00"),
        )

        self.assertIsInstance(result, ProfitCalculationResult)
        # Gross Revenue = 2000 * 120 = 240,000.00
        self.assertEqual(result.gross_revenue, Decimal("240000.00"))
        # Net Profit = 240,000 - 150,000 = 90,000.00
        self.assertEqual(result.net_profit, Decimal("90000.00"))
        # Breakeven Price = 150,000 / 2,000 = 75.00
        self.assertEqual(result.breakeven_price_lkr_per_kg, Decimal("75.00"))
        # ROI = (90,000 / 150,000) * 100 = 60.00%
        self.assertEqual(result.roi_percentage, Decimal("60.00"))
        # Margin of Safety = ((120 - 75) / 120) * 100 = 37.50%
        self.assertEqual(result.margin_of_safety_percentage, Decimal("37.50"))
        # Provenance metadata
        self.assertEqual(result.price_source, "farmer_assumption")
        self.assertTrue(result.is_manual_price_assumption)
        self.assertIn("planning assumption", result.assumptions_note)
        self.assertIsNone(result.calculation_notes)

    def test_exact_breakeven_scenario(self):
        """Verify scenario where revenue exactly matches total cultivation cost."""
        result = calculate_deterministic_profit(
            expected_yield_kg=Decimal("1000.00"),
            selling_price_lkr_per_kg=Decimal("100.00"),
            total_cultivation_cost=Decimal("100000.00"),
        )

        self.assertEqual(result.gross_revenue, Decimal("100000.00"))
        self.assertEqual(result.net_profit, Decimal("0.00"))
        self.assertEqual(result.breakeven_price_lkr_per_kg, Decimal("100.00"))
        self.assertEqual(result.roi_percentage, Decimal("0.00"))
        self.assertEqual(result.margin_of_safety_percentage, Decimal("0.00"))

    def test_zero_cultivation_cost_scenario(self):
        """
        Verify that zero cultivation cost is supported:
        ROI must be null (None), Breakeven is 0, Margin of Safety is 100%,
        and an explanatory note is recorded.
        """
        result = calculate_deterministic_profit(
            expected_yield_kg=Decimal("1500.00"),
            selling_price_lkr_per_kg=Decimal("80.00"),
            total_cultivation_cost=Decimal("0.00"),
        )

        self.assertEqual(result.gross_revenue, Decimal("120000.00"))
        self.assertEqual(result.net_profit, Decimal("120000.00"))
        self.assertEqual(result.breakeven_price_lkr_per_kg, Decimal("0.00"))
        self.assertIsNone(result.roi_percentage)
        self.assertEqual(result.margin_of_safety_percentage, Decimal("100.00"))
        self.assertIsNotNone(result.calculation_notes)
        self.assertIn("ROI is mathematically undefined", result.calculation_notes)

    def test_negative_profit_loss_scenario(self):
        """Verify calculations when selling price is below breakeven (net loss)."""
        result = calculate_deterministic_profit(
            expected_yield_kg=Decimal("1000.00"),
            selling_price_lkr_per_kg=Decimal("60.00"),
            total_cultivation_cost=Decimal("90000.00"),
        )

        # Revenue = 1000 * 60 = 60,000.00
        self.assertEqual(result.gross_revenue, Decimal("60000.00"))
        # Net Profit = 60,000 - 90,000 = -30,000.00
        self.assertEqual(result.net_profit, Decimal("-30000.00"))
        # Breakeven Price = 90,000 / 1000 = 90.00
        self.assertEqual(result.breakeven_price_lkr_per_kg, Decimal("90.00"))
        # ROI = (-30,000 / 90,000) * 100 = -33.33%
        self.assertEqual(result.roi_percentage, Decimal("-33.33"))
        # Margin of Safety = ((60 - 90) / 60) * 100 = -50.00%
        self.assertEqual(result.margin_of_safety_percentage, Decimal("-50.00"))

    def test_decimal_precision_and_unrounded_mode(self):
        """Verify precision with repeating fractions and unrounded mode."""
        # Unrounded
        raw = calculate_deterministic_profit(
            expected_yield_kg=Decimal("3000"),
            selling_price_lkr_per_kg=Decimal("33.33"),
            total_cultivation_cost=Decimal("70000"),
            round_result=False,
        )
        self.assertEqual(raw.gross_revenue, Decimal("99990.00"))
        self.assertEqual(raw.net_profit, Decimal("29990.00"))
        # Breakeven has fractional repeating decimal
        self.assertEqual(raw.breakeven_price_lkr_per_kg, Decimal("70000") / Decimal("3000"))

        # Rounded (default)
        rounded = calculate_deterministic_profit(
            expected_yield_kg=Decimal("3000"),
            selling_price_lkr_per_kg=Decimal("33.33"),
            total_cultivation_cost=Decimal("70000"),
            round_result=True,
        )
        self.assertEqual(rounded.breakeven_price_lkr_per_kg, Decimal("23.33"))
        self.assertEqual(rounded.roi_percentage, Decimal("42.84"))

    def test_flexible_input_types(self):
        """Verify service accepts ints, strings, and floats with safe Decimal conversion."""
        res_str = calculate_deterministic_profit("1000", "75.50", "50000")
        self.assertEqual(res_str.gross_revenue, Decimal("75500.00"))

        res_int = calculate_deterministic_profit(1000, 75, 50000)
        self.assertEqual(res_int.gross_revenue, Decimal("75000.00"))

        res_float = calculate_deterministic_profit(1000.0, 75.5, 50000.0)
        self.assertEqual(res_float.gross_revenue, Decimal("75500.00"))

    def test_calculate_profit_from_input_model(self):
        """Verify convenience helper with validated Pydantic model."""
        inp = ProfitCalculationInput(
            expected_yield_kg=Decimal("500.00"),
            selling_price_lkr_per_kg=Decimal("150.00"),
            total_cultivation_cost=Decimal("45000.00"),
        )
        res = calculate_profit_from_input(inp)
        self.assertEqual(res.gross_revenue, Decimal("75000.00"))
        self.assertEqual(res.net_profit, Decimal("30000.00"))
        self.assertEqual(res.roi_percentage, Decimal("66.67"))

    def test_decoupled_from_risk_classification(self):
        """Verify Task 1 result does NOT include heuristic risk fields."""
        res = calculate_deterministic_profit(
            expected_yield_kg=Decimal("1000.00"),
            selling_price_lkr_per_kg=Decimal("100.00"),
            total_cultivation_cost=Decimal("50000.00"),
        )
        # Ensure fields from future risk classification tasks are not present
        self.assertFalse(hasattr(res, "profit_risk_level"))
        self.assertFalse(hasattr(res, "risk_score"))
        self.assertFalse(hasattr(res, "risk_factors"))


class TestProfitCalculationInputValidation(unittest.TestCase):
    """Unit tests for invalid input rejection (yield <= 0, price <= 0, cost < 0, NaN, Inf)."""

    def test_zero_or_negative_yield_rejected(self):
        """Expected yield must be > 0."""
        with self.assertRaises(ValueError):
            calculate_deterministic_profit(
                expected_yield_kg=Decimal("0.0"),
                selling_price_lkr_per_kg=Decimal("100.0"),
                total_cultivation_cost=Decimal("50000.0"),
            )

        with self.assertRaises(ValueError):
            calculate_deterministic_profit(
                expected_yield_kg=Decimal("-10.0"),
                selling_price_lkr_per_kg=Decimal("100.0"),
                total_cultivation_cost=Decimal("50000.0"),
            )

        with self.assertRaises(ValidationError):
            ProfitCalculationInput(
                expected_yield_kg=Decimal("0.0"),
                selling_price_lkr_per_kg=Decimal("100.0"),
                total_cultivation_cost=Decimal("50000.0"),
            )

    def test_zero_or_negative_selling_price_rejected(self):
        """Selling price must be > 0."""
        with self.assertRaises(ValueError):
            calculate_deterministic_profit(
                expected_yield_kg=Decimal("1000.0"),
                selling_price_lkr_per_kg=Decimal("0.0"),
                total_cultivation_cost=Decimal("50000.0"),
            )

        with self.assertRaises(ValueError):
            calculate_deterministic_profit(
                expected_yield_kg=Decimal("1000.0"),
                selling_price_lkr_per_kg=Decimal("-50.0"),
                total_cultivation_cost=Decimal("50000.0"),
            )

        with self.assertRaises(ValidationError):
            ProfitCalculationInput(
                expected_yield_kg=Decimal("1000.0"),
                selling_price_lkr_per_kg=Decimal("-10.0"),
                total_cultivation_cost=Decimal("50000.0"),
            )

    def test_negative_total_cost_rejected(self):
        """Total cultivation cost cannot be negative."""
        with self.assertRaises(ValueError):
            calculate_deterministic_profit(
                expected_yield_kg=Decimal("1000.0"),
                selling_price_lkr_per_kg=Decimal("100.0"),
                total_cultivation_cost=Decimal("-500.0"),
            )

        with self.assertRaises(ValidationError):
            ProfitCalculationInput(
                expected_yield_kg=Decimal("1000.0"),
                selling_price_lkr_per_kg=Decimal("100.0"),
                total_cultivation_cost=Decimal("-1.0"),
            )

    def test_nan_values_rejected(self):
        """NaN values must be rejected."""
        nan_inputs = [Decimal("NaN"), float("nan"), "NaN", "nan"]
        for val in nan_inputs:
            with self.subTest(val=val):
                with self.assertRaises(ValueError):
                    calculate_deterministic_profit(
                        expected_yield_kg=val,
                        selling_price_lkr_per_kg=Decimal("100.0"),
                        total_cultivation_cost=Decimal("1000.0"),
                    )

                with self.assertRaises(ValueError):
                    calculate_deterministic_profit(
                        expected_yield_kg=Decimal("1000.0"),
                        selling_price_lkr_per_kg=val,
                        total_cultivation_cost=Decimal("1000.0"),
                    )

                with self.assertRaises(ValueError):
                    calculate_deterministic_profit(
                        expected_yield_kg=Decimal("1000.0"),
                        selling_price_lkr_per_kg=Decimal("100.0"),
                        total_cultivation_cost=val,
                    )

    def test_infinite_values_rejected(self):
        """Infinite values must be rejected."""
        inf_inputs = [
            Decimal("Infinity"), Decimal("-Infinity"),
            float("inf"), float("-inf"),
            "inf", "-Infinity"
        ]
        for val in inf_inputs:
            with self.subTest(val=val):
                with self.assertRaises(ValueError):
                    calculate_deterministic_profit(
                        expected_yield_kg=val,
                        selling_price_lkr_per_kg=Decimal("100.0"),
                        total_cultivation_cost=Decimal("1000.0"),
                    )

                with self.assertRaises(ValueError):
                    calculate_deterministic_profit(
                        expected_yield_kg=Decimal("1000.0"),
                        selling_price_lkr_per_kg=val,
                        total_cultivation_cost=Decimal("1000.0"),
                    )

                with self.assertRaises(ValueError):
                    calculate_deterministic_profit(
                        expected_yield_kg=Decimal("1000.0"),
                        selling_price_lkr_per_kg=Decimal("100.0"),
                        total_cultivation_cost=val,
                    )

    def test_none_values_rejected(self):
        """None values must be rejected."""
        with self.assertRaises(ValueError):
            calculate_deterministic_profit(None, Decimal("100.0"), Decimal("1000.0"))
        with self.assertRaises(ValueError):
            calculate_deterministic_profit(Decimal("1000.0"), None, Decimal("1000.0"))
        with self.assertRaises(ValueError):
            calculate_deterministic_profit(Decimal("1000.0"), Decimal("100.0"), None)

    def test_boolean_values_rejected(self):
        """Booleans must not be accepted as numeric quantities."""
        with self.assertRaises(ValueError):
            calculate_deterministic_profit(True, Decimal("100.0"), Decimal("1000.0"))
        with self.assertRaises(ValueError):
            calculate_deterministic_profit(Decimal("1000.0"), False, Decimal("1000.0"))

    def test_non_numeric_strings_rejected(self):
        """Malformed strings must be rejected with ValueError."""
        with self.assertRaises(ValueError):
            calculate_deterministic_profit("invalid", Decimal("100.0"), Decimal("1000.0"))
        with self.assertRaises(ValueError):
            calculate_deterministic_profit(Decimal("1000.0"), "free", Decimal("1000.0"))
        with self.assertRaises(ValueError):
            calculate_deterministic_profit(Decimal("1000.0"), Decimal("100.0"), "unknown")


if __name__ == "__main__":
    unittest.main()
