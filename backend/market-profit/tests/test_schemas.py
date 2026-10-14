from datetime import date
from decimal import Decimal
import unittest
from pydantic import ValidationError
from app.schemas import (
    BudgetEntryMode,
    CultivationBudgetCreate,
    CultivationCostBreakdown,
    DemandLevel,
    DemandRecordType,
    FarmerAnalysisInput,
    MarketDemandCreate,
    MarketPriceCreate,
    PredictionResultResponse,
    PredictionStatus,
    PriceType,
    ProfitRiskLevel,
    SeasonEnum,
)


class TestCatalogAndInputValidation(unittest.TestCase):
    """Test crop ID, district ID, and numeric validation."""

    def test_valid_crop_and_district_pass(self):
        item = MarketPriceCreate(
            crop_id="CR_TOMATO",
            market_id="DEC_DAMBULLA",
            market_name="Dambulla Dedicated Economic Centre",
            district_id="LK-22",
            price_date=date(2026, 10, 14),
            price=Decimal("150.00"),
            data_source="HARTI"
        )
        self.assertEqual(item.crop_id, "CR_TOMATO")
        self.assertEqual(item.district_id, "LK-22")

    def test_invalid_crop_id_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            MarketPriceCreate(
                crop_id="CR_INVALID_CROP",
                market_id="DEC_DAMBULLA",
                market_name="Dambulla DEC",
                price_date=date(2026, 10, 14),
                price=Decimal("100.00"),
                data_source="HARTI"
            )
        self.assertIn("Invalid crop_id", str(ctx.exception))

    def test_invalid_district_id_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            MarketDemandCreate(
                crop_id="CR_MAIZE",
                district_id="LK-99",  # Invalid district
                period_start_date=date(2026, 10, 1),
                period_end_date=date(2026, 10, 7),
                demand_volume_kg=Decimal("5000.00"),
                record_type=DemandRecordType.OBSERVED,
                data_source="DEC Ledger"
            )
        self.assertIn("Invalid district_id", str(ctx.exception))

    def test_non_positive_price_fails(self):
        with self.assertRaises(ValidationError):
            MarketPriceCreate(
                crop_id="CR_TOMATO",
                market_id="DEC_DAMBULLA",
                market_name="Dambulla DEC",
                price_date=date(2026, 10, 14),
                price=Decimal("0.00"),  # Zero price rejected
                data_source="HARTI"
            )

        with self.assertRaises(ValidationError):
            MarketPriceCreate(
                crop_id="CR_TOMATO",
                market_id="DEC_DAMBULLA",
                market_name="Dambulla DEC",
                price_date=date(2026, 10, 14),
                price=Decimal("-50.00"),  # Negative price rejected
                data_source="HARTI"
            )


class TestMarketDemandSchemas(unittest.TestCase):
    """Test demand records, date ranges, and training eligibility rules."""

    def test_period_dates_chronology(self):
        # Invalid when end date is before start date
        with self.assertRaises(ValidationError) as ctx:
            MarketDemandCreate(
                crop_id="CR_CHILLI",
                district_id="LK-71",
                period_start_date=date(2026, 10, 15),
                period_end_date=date(2026, 10, 10),
                demand_volume_kg=Decimal("2000.00"),
                record_type=DemandRecordType.OBSERVED,
                data_source="HARTI"
            )
        self.assertIn("cannot precede period_start_date", str(ctx.exception))

    def test_synthetic_demand_not_training_eligible(self):
        demand = MarketDemandCreate(
            crop_id="CR_MUNG_BEAN",
            district_id="LK-82",
            period_start_date=date(2026, 10, 1),
            period_end_date=date(2026, 10, 31),
            demand_volume_kg=Decimal("12000.00"),
            record_type=DemandRecordType.SYNTHETIC,
            demand_level=DemandLevel.MEDIUM,
            is_training_eligible=True,  # Attempting to mark synthetic as training eligible
            data_source="Copula Generator"
        )
        # Model validator must enforce False for synthetic records
        self.assertFalse(demand.is_training_eligible)


class TestCultivationBudgetModes(unittest.TestCase):
    """Test quick and detailed cultivation budget entry modes."""

    def test_quick_mode_success(self):
        budget = CultivationBudgetCreate(
            crop_id="CR_PUMPKIN",
            district_id="LK-71",
            season=SeasonEnum.MAHA,
            year=2026,
            entry_mode=BudgetEntryMode.QUICK,
            land_extent_acres=Decimal("2.00"),
            total_cost=Decimal("145000.00"),
            expected_yield_kg=Decimal("6000.00")
        )
        self.assertEqual(budget.entry_mode, BudgetEntryMode.QUICK)
        self.assertEqual(budget.total_cost, Decimal("145000.00"))
        self.assertIsNone(budget.breakdown)

    def test_quick_mode_missing_total_cost_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            CultivationBudgetCreate(
                crop_id="CR_PUMPKIN",
                district_id="LK-71",
                season=SeasonEnum.MAHA,
                year=2026,
                entry_mode=BudgetEntryMode.QUICK,
                land_extent_acres=Decimal("2.00"),
                expected_yield_kg=Decimal("6000.00")
            )
        self.assertIn("positive total_cost must be explicitly specified", str(ctx.exception))

    def test_detailed_mode_auto_computes_total_cost(self):
        breakdown = CultivationCostBreakdown(
            land_preparation_cost=Decimal("25000.00"),
            seeds_plants_cost=Decimal("15000.00"),
            fertilizer_cost=Decimal("40000.00"),
            labor_cost=Decimal("35000.00")
            # remaining categories are None (unexpended / unrecorded)
        )
        budget = CultivationBudgetCreate(
            crop_id="CR_BRINJAL",
            district_id="LK-22",
            season=SeasonEnum.YALA,
            year=2026,
            entry_mode=BudgetEntryMode.DETAILED,
            land_extent_acres=Decimal("1.00"),
            breakdown=breakdown,
            expected_yield_kg=Decimal("4000.00")
        )
        # Total cost should be automatically computed from breakdown
        self.assertEqual(budget.total_cost, Decimal("115000.00"))
        self.assertIsNone(budget.breakdown.machinery_fuel_cost)

    def test_detailed_mode_mismatched_total_cost_fails(self):
        breakdown = CultivationCostBreakdown(
            fertilizer_cost=Decimal("30000.00"),
            labor_cost=Decimal("20000.00")
        )
        with self.assertRaises(ValidationError) as ctx:
            CultivationBudgetCreate(
                crop_id="CR_OKRA",
                district_id="LK-33",
                season=SeasonEnum.YALA,
                year=2026,
                entry_mode=BudgetEntryMode.DETAILED,
                land_extent_acres=Decimal("1.00"),
                total_cost=Decimal("99999.00"),  # Mismatches 50000.00
                breakdown=breakdown,
                expected_yield_kg=Decimal("2500.00")
            )
        self.assertIn("does not match the sum of itemized breakdown categories", str(ctx.exception))


class TestPredictionSchemas(unittest.TestCase):
    """Test farmer request inputs, market separation, and explicit model-unavailable responses."""

    def test_farmer_input_separate_district_and_market(self):
        farmer_req = FarmerAnalysisInput(
            crop_id="CR_TOMATO",
            cultivation_district_id="LK-71",   # Anuradhapura (farm)
            target_market_id="DEC_DAMBULLA",   # Dambulla DEC (target market)
            forecast_target_date=date(2027, 2, 1),
            cultivation_extent_acres=Decimal("1.50"),
            estimated_production_kg=Decimal("4500.00"),
            budget_entry_mode=BudgetEntryMode.QUICK,
            quick_total_cost=Decimal("180000.00")
        )
        self.assertEqual(farmer_req.cultivation_district_id, "LK-71")
        self.assertEqual(farmer_req.target_market_id, "DEC_DAMBULLA")
        self.assertEqual(farmer_req.target_market_name, "Dambulla Dedicated Economic Centre")
        self.assertEqual(farmer_req.resolve_total_cost(), Decimal("180000.00"))

    def test_prediction_response_unavailable_factory(self):
        farmer_req = FarmerAnalysisInput(
            crop_id="CR_CHILLI",
            cultivation_district_id="LK-82",
            target_market_id="DEC_PETTAH",
            forecast_target_date=date(2027, 3, 1),
            cultivation_extent_acres=Decimal("0.75"),
            estimated_production_kg=Decimal("1200.00"),
            budget_entry_mode=BudgetEntryMode.QUICK,
            quick_total_cost=Decimal("95000.00")
        )

        res = PredictionResultResponse.create_unavailable(
            farmer_req,
            reason="Price forecasting model is currently offline for scheduled retraining."
        )

        self.assertEqual(res.prediction_status, PredictionStatus.UNAVAILABLE)
        self.assertIsNone(res.forecasted_wholesale_price)
        self.assertIsNone(res.projected_net_profit)
        self.assertIsNone(res.profit_risk_level)
        self.assertIn("Price forecasting model is currently offline", res.error_message)

    def test_prediction_response_completed_with_standard_categories(self):
        completed_res = PredictionResultResponse(
            analysis_reference="REF-202610-8A3F",
            prediction_status=PredictionStatus.COMPLETED,
            crop_id="CR_TOMATO",
            cultivation_district_id="LK-71",
            target_market_id="DEC_DAMBULLA",
            target_market_name="Dambulla Dedicated Economic Centre",
            forecast_target_date=date(2027, 1, 20),
            forecast_horizon_days=90,
            cultivation_extent_acres=Decimal("1.00"),
            estimated_production_kg=Decimal("3000.00"),
            estimated_total_cost=Decimal("120000.00"),
            forecasted_wholesale_price=Decimal("85.00"),
            price_confidence_lower=Decimal("70.00"),
            price_confidence_upper=Decimal("100.00"),
            projected_demand_volume_kg=Decimal("450000.00"),
            projected_demand_level=DemandLevel.HIGH,
            projected_revenue=Decimal("255000.00"),
            projected_net_profit=Decimal("135000.00"),
            projected_roi_percentage=Decimal("112.50"),
            profit_risk_level=ProfitRiskLevel.LOW,
            risk_score=Decimal("0.1850"),
            model_version="v1.0-baseline",
            status_message="Inference completed successfully"
        )
        self.assertEqual(completed_res.prediction_status, PredictionStatus.COMPLETED)
        self.assertEqual(completed_res.profit_risk_level, ProfitRiskLevel.LOW)
        self.assertEqual(completed_res.projected_demand_level, DemandLevel.HIGH)
        self.assertEqual(completed_res.projected_net_profit, Decimal("135000.00"))


if __name__ == "__main__":
    unittest.main()
