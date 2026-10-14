import datetime
from decimal import Decimal
import unittest
from sqlalchemy import BigInteger, Date, DateTime, Numeric, String
from app.models import (
    Base,
    CultivationBudget,
    MarketDemand,
    MarketPrice,
    MarketProfitAnalysis,
)


class TestSQLAlchemyModelMetadata(unittest.TestCase):
    """Verify table names, column constraints, and schema metadata."""

    def test_market_prices_table_metadata(self):
        table = MarketPrice.__table__
        self.assertEqual(table.name, "market_prices")
        self.assertIn("crop_id", table.c)
        self.assertIn("market_id", table.c)
        self.assertIn("price_type", table.c)
        self.assertIn("price", table.c)
        self.assertIn("volume_traded_kg", table.c)
        self.assertIn("data_quality_flag", table.c)

        # Nullable check
        self.assertTrue(table.c.volume_traded_kg.nullable)
        self.assertTrue(table.c.district_id.nullable)
        self.assertFalse(table.c.price.nullable)
        self.assertFalse(table.c.price_date.nullable)

    def test_market_demand_table_metadata(self):
        table = MarketDemand.__table__
        self.assertEqual(table.name, "market_demand_records")
        self.assertIn("crop_id", table.c)
        self.assertIn("district_id", table.c)
        self.assertIn("record_type", table.c)
        self.assertIn("is_training_eligible", table.c)
        self.assertFalse(table.c.is_training_eligible.nullable)
        self.assertTrue(table.c.confidence_score.nullable)

    def test_cultivation_budgets_table_metadata(self):
        table = CultivationBudget.__table__
        self.assertEqual(table.name, "cultivation_budgets")
        self.assertIn("entry_mode", table.c)
        self.assertIn("total_cost", table.c)
        self.assertIn("seeds_plants_cost", table.c)
        self.assertIn("fertilizer_cost", table.c)
        self.assertIn("labor_cost", table.c)

        # In quick mode, breakdown costs are nullable (NULL, not 0)
        self.assertTrue(table.c.seeds_plants_cost.nullable)
        self.assertTrue(table.c.fertilizer_cost.nullable)
        self.assertTrue(table.c.labor_cost.nullable)
        self.assertFalse(table.c.total_cost.nullable)

    def test_market_profit_analyses_table_metadata(self):
        table = MarketProfitAnalysis.__table__
        self.assertEqual(table.name, "market_profit_analyses")
        self.assertIn("analysis_reference", table.c)
        self.assertIn("cultivation_district_id", table.c)
        self.assertIn("target_market_id", table.c)
        self.assertIn("prediction_status", table.c)

        # ML-dependent fields must be nullable until inference succeeds
        self.assertTrue(table.c.forecasted_wholesale_price.nullable)
        self.assertTrue(table.c.price_confidence_lower.nullable)
        self.assertTrue(table.c.projected_demand_volume_kg.nullable)
        self.assertTrue(table.c.projected_net_profit.nullable)
        self.assertTrue(table.c.profit_risk_level.nullable)
        self.assertTrue(table.c.model_version.nullable)
        self.assertTrue(table.c.model_provenance.nullable)


class TestSQLAlchemyModelInstantiation(unittest.TestCase):
    """Verify in-memory model instantiation and relationships without database IO."""

    def test_market_price_instantiation_incomplete_observation(self):
        price_record = MarketPrice(
            crop_id="CR_TOMATO",
            market_id="DEC_DAMBULLA",
            market_name="Dambulla Dedicated Economic Centre",
            district_id="LK-22",
            price_date=datetime.date(2026, 10, 14),
            price_type="wholesale",
            price=Decimal("280.50"),
            unit="kg",
            currency="LKR",
            volume_traded_kg=None,  # Incomplete observation preserved
            price_grade="Standard",
            data_source="HARTI Daily Food Commodities Bulletin",
            data_quality_flag="verified"
        )
        self.assertEqual(price_record.crop_id, "CR_TOMATO")
        self.assertEqual(price_record.price, Decimal("280.50"))
        self.assertIsNone(price_record.volume_traded_kg)
        self.assertIn("CR_TOMATO", repr(price_record))

    def test_market_demand_synthetic_provenance(self):
        demand_record = MarketDemand(
            crop_id="CR_CHILLI",
            district_id="LK-11",
            market_id="DEC_PETTAH",
            period_start_date=datetime.date(2026, 10, 1),
            period_end_date=datetime.date(2026, 10, 7),
            demand_volume_kg=Decimal("150000.00"),
            unit="kg",
            record_type="synthetic",
            demand_level="High",
            confidence_score=Decimal("0.850"),
            estimation_method="CTGAN_Copula_v1",
            is_training_eligible=False,  # Excluded from training set
            data_source="AgriSense Synthetic Generator"
        )
        self.assertEqual(demand_record.record_type, "synthetic")
        self.assertFalse(demand_record.is_training_eligible)
        self.assertEqual(demand_record.demand_level, "High")

    def test_cultivation_budget_quick_mode_null_categories(self):
        budget = CultivationBudget(
            crop_id="CR_MAIZE",
            district_id="LK-71",
            season="Maha",
            year=2026,
            entry_mode="quick",
            land_extent_acres=Decimal("2.50"),
            total_cost=Decimal("185000.00"),
            land_preparation_cost=None,  # Must remain None, not 0.00
            seeds_plants_cost=None,
            fertilizer_cost=None,
            expected_yield_kg=Decimal("4500.00"),
            data_source="Farmer Self-Reported"
        )
        self.assertEqual(budget.entry_mode, "quick")
        self.assertEqual(budget.total_cost, Decimal("185000.00"))
        self.assertIsNone(budget.fertilizer_cost)

    def test_profit_analysis_lifecycle_and_relationship(self):
        budget = CultivationBudget(
            id=101,
            crop_id="CR_TOMATO",
            district_id="LK-71",
            season="Yala",
            year=2026,
            entry_mode="quick",
            land_extent_acres=Decimal("1.00"),
            total_cost=Decimal("120000.00"),
            expected_yield_kg=Decimal("3000.00")
        )

        analysis = MarketProfitAnalysis(
            analysis_reference="REF-202610-TEST01",
            crop_id="CR_TOMATO",
            cultivation_district_id="LK-71",  # Farm district
            target_market_id="DEC_DAMBULLA",  # Target market center
            target_market_name="Dambulla Dedicated Economic Centre",
            prediction_status="unavailable",   # Model offline state
            forecast_target_date=datetime.date(2027, 1, 15),
            forecast_horizon_days=90,
            cultivation_extent_acres=Decimal("1.00"),
            estimated_production_kg=Decimal("3000.00"),
            estimated_total_cost=Decimal("120000.00"),
            forecasted_wholesale_price=None,  # Nullable while unavailable
            projected_net_profit=None,
            profit_risk_level=None,
            error_message="Model inference endpoint is undergoing maintenance.",
            cultivation_budget=budget
        )

        self.assertEqual(analysis.prediction_status, "unavailable")
        self.assertIsNone(analysis.forecasted_wholesale_price)
        self.assertEqual(analysis.cultivation_district_id, "LK-71")
        self.assertEqual(analysis.target_market_id, "DEC_DAMBULLA")
        self.assertEqual(analysis.cultivation_budget.total_cost, Decimal("120000.00"))
        self.assertIn(analysis, budget.analyses)


if __name__ == "__main__":
    unittest.main()
