import contextlib
import io
import unittest
from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command
from app.models import (
    Base,
    CultivationBudget,
    MarketDemand,
    MarketPrice,
    MarketProfitAnalysis,
)


class TestAlembicMigrationSetup(unittest.TestCase):
    """Verify Alembic migration configuration, revision history, and static SQL preview."""

    def setUp(self):
        self.market_profit_dir = Path(__file__).resolve().parent.parent
        self.alembic_ini_path = self.market_profit_dir / "alembic.ini"
        self.alembic_dir = self.market_profit_dir / "alembic"
        self.alembic_cfg = Config(str(self.alembic_ini_path))
        self.alembic_cfg.set_main_option("script_location", str(self.alembic_dir))

    def test_alembic_ini_and_directory_structure(self):
        """Verify presence of configuration file, template, and migration scripts."""
        self.assertTrue(self.alembic_ini_path.exists(), "alembic.ini must exist in service root")
        self.assertTrue(self.alembic_dir.exists(), "alembic directory must exist")
        self.assertTrue((self.alembic_dir / "env.py").exists(), "alembic/env.py must exist")
        self.assertTrue((self.alembic_dir / "script.py.mako").exists(), "script.py.mako must exist")

    def test_migration_revisions_present(self):
        """Verify initial migration file is detected and head revision matches."""
        script = ScriptDirectory.from_config(self.alembic_cfg)
        heads = script.get_heads()
        self.assertEqual(len(heads), 1)
        self.assertEqual(heads[0], "0001_initial_market_profit")

    def test_offline_sql_preview_generation(self):
        """
        Generate offline migration SQL without connecting to the database.
        Verify dedicated version table, all 4 target tables, constraints, and absence of DROP statements.
        """
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            command.upgrade(self.alembic_cfg, "head", sql=True)

        generated_sql = buf.getvalue()

        # 1. Dedicated version table to isolate Component 1 from other microservices
        self.assertIn("alembic_version_market_profit", generated_sql)

        # 2. All four Component 1 tables are generated
        self.assertIn("CREATE TABLE cultivation_budgets", generated_sql)
        self.assertIn("CREATE TABLE market_prices", generated_sql)
        self.assertIn("CREATE TABLE market_demand_records", generated_sql)
        self.assertIn("CREATE TABLE market_profit_analyses", generated_sql)

        # 3. Foreign key relationship from analysis to budget with SET NULL
        self.assertIn("FOREIGN KEY(cultivation_budget_id) REFERENCES cultivation_budgets (id) ON DELETE SET NULL", generated_sql)

        # 4. Unique constraint on market prices
        self.assertIn("uq_market_price_entry UNIQUE", generated_sql)

        # 5. Dedicated indexes created
        self.assertIn("CREATE INDEX ix_cultivation_budgets_crop_district_season", generated_sql)
        self.assertIn("CREATE INDEX ix_market_prices_crop_date", generated_sql)
        self.assertIn("CREATE INDEX ix_market_demand_type_eligible", generated_sql)
        self.assertIn("CREATE INDEX ix_profit_analysis_crop_market_date", generated_sql)

        # 6. Strict check: No destructive operations
        self.assertNotIn("DROP TABLE", generated_sql.upper())
        self.assertNotIn("DROP SCHEMA", generated_sql.upper())
        self.assertNotIn("TRUNCATE", generated_sql.upper())

    def test_target_metadata_models_match(self):
        """Verify that Base.metadata strictly contains only Component 1 tables."""
        table_names = set(Base.metadata.tables.keys())
        expected = {
            "cultivation_budgets",
            "market_prices",
            "market_demand_records",
            "market_profit_analyses",
        }
        self.assertEqual(table_names, expected)


if __name__ == "__main__":
    unittest.main()
