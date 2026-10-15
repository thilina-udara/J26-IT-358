import asyncio
import json
import unittest
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import engine, get_db
from app.main import app
from app.models.market_price import MarketPrice
from app.models.market_demand import MarketDemand
from app.models.cultivation_cost import CultivationBudget
from app.models.profit_analysis import MarketProfitAnalysis


class BaseCRUDTestCase(unittest.TestCase):
    """
    Base test case with transaction rollback isolation.
    Opens a database connection, begins an outer transaction, and binds each request's session
    using a savepoint. On test tearDown, the outer transaction is rolled back, guaranteeing
    that zero test records persist in the shared database.
    """

    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.session = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        app.dependency_overrides[get_db] = lambda: self.session
        self.test_admin_key = "test-isolated-crud-key-temp"
        self.original_admin_key = settings.ADMIN_API_KEY
        settings.ADMIN_API_KEY = self.test_admin_key

    def tearDown(self):
        settings.ADMIN_API_KEY = self.original_admin_key
        app.dependency_overrides.clear()
        self.session.close()
        self.transaction.rollback()
        self.connection.close()

    def client_request(self, method: str, path: str, body: dict = None, params: dict = None, headers: dict = None, as_admin: bool = False):
        """Dispatch ASGI request directly through FastAPI application without external network calls."""
        body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
        query_string = urlencode(params).encode("ascii") if params else b""
        req_headers = [(b"host", b"localhost")]
        if body is not None:
            req_headers.append((b"content-type", b"application/json"))
        if as_admin:
            req_headers.append((b"x-admin-key", self.test_admin_key.encode("utf-8")))
        if headers:
            for k, v in headers.items():
                req_headers.append((k.lower().encode("utf-8"), v.encode("utf-8")))

        status_code = None
        body_parts = []

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query_string,
            "headers": req_headers,
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 80),
        }

        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        async def send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        asyncio.run(app(scope, receive, send))
        response_text = b"".join(body_parts).decode("utf-8")
        parsed_body = json.loads(response_text) if response_text else None
        return status_code, parsed_body


class TestMarketPricesCRUD(BaseCRUDTestCase):
    """Test suite for /api/v1/market-prices CRUD endpoints."""

    def test_create_price_success(self):
        payload = {
            "crop_id": "CR_TOMATO",
            "market_id": "DEC_DAMBULLA",
            "market_name": "Dambulla Dedicated Economic Centre",
            "district_id": "LK-22",
            "price_date": "2026-10-14",
            "price_type": "wholesale",
            "price": 185.50,
            "unit": "kg",
            "currency": "LKR",
            "volume_traded_kg": 2500.0,
            "price_grade": "Grade 1",
            "data_source": "HARTI Daily Bulletin",
            "notes": "Peak morning arrivals"
        }
        status_code, body = self.client_request("POST", "/api/v1/market-prices", body=payload, as_admin=True)
        self.assertEqual(status_code, 201)
        self.assertIn("id", body)
        self.assertEqual(body["crop_id"], "CR_TOMATO")
        self.assertEqual(float(body["price"]), 185.50)
        self.assertEqual(body["price_type"], "wholesale")

    def test_create_price_duplicate_conflict_409(self):
        payload = {
            "crop_id": "CR_BRINJAL",
            "market_id": "DEC_MEEGODA",
            "market_name": "Meegoda Economic Centre",
            "district_id": "LK-11",
            "price_date": "2026-10-14",
            "price_type": "wholesale",
            "price": 220.00,
            "data_source": "HARTI"
        }
        status_code1, _ = self.client_request("POST", "/api/v1/market-prices", body=payload, as_admin=True)
        self.assertEqual(status_code1, 201)

        # Attempt duplicate insertion
        status_code2, err_body = self.client_request("POST", "/api/v1/market-prices", body=payload, as_admin=True)
        self.assertEqual(status_code2, 409)
        self.assertIn("already exists", err_body["detail"])

    def test_get_price_by_id(self):
        payload = {
            "crop_id": "CR_CHILLI",
            "market_id": "DEC_DAMBULLA",
            "market_name": "Dambulla DEC",
            "district_id": "LK-22",
            "price_date": "2026-10-12",
            "price_type": "retail",
            "price": 650.00,
            "data_source": "Retail Survey"
        }
        _, created = self.client_request("POST", "/api/v1/market-prices", body=payload, as_admin=True)
        price_id = created["id"]

        status_code, body = self.client_request("GET", f"/api/v1/market-prices/{price_id}")
        self.assertEqual(status_code, 200)
        self.assertEqual(body["id"], price_id)
        self.assertEqual(body["crop_id"], "CR_CHILLI")
        self.assertEqual(float(body["price"]), 650.00)

    def test_get_price_not_found_404(self):
        status_code, body = self.client_request("GET", "/api/v1/market-prices/999999")
        self.assertEqual(status_code, 404)
        self.assertIn("not found", body["detail"])

    def test_list_prices_filtering_and_pagination(self):
        prices = [
            {"crop_id": "CR_TOMATO", "market_id": "DEC_DAMBULLA", "market_name": "Dambulla", "district_id": "LK-22", "price_date": "2026-10-10", "price": 120.0, "data_source": "HARTI"},
            {"crop_id": "CR_TOMATO", "market_id": "DEC_DAMBULLA", "market_name": "Dambulla", "district_id": "LK-22", "price_date": "2026-10-11", "price": 130.0, "data_source": "HARTI"},
            {"crop_id": "CR_MAIZE", "market_id": "DEC_DAMBULLA", "market_name": "Dambulla", "district_id": "LK-22", "price_date": "2026-10-11", "price": 95.0, "data_source": "HARTI"},
        ]
        for p in prices:
            self.client_request("POST", "/api/v1/market-prices", body=p, as_admin=True)

        # Filter by crop_id
        status_code, body = self.client_request("GET", "/api/v1/market-prices", params={"crop_id": "CR_TOMATO", "page": 1, "page_size": 10})
        self.assertEqual(status_code, 200)
        self.assertEqual(body["meta"]["total"], 2)
        self.assertEqual(len(body["items"]), 2)
        for item in body["items"]:
            self.assertEqual(item["crop_id"], "CR_TOMATO")

    def test_list_prices_invalid_date_range_400(self):
        status_code, body = self.client_request(
            "GET",
            "/api/v1/market-prices",
            params={"start_date": "2026-10-15", "end_date": "2026-10-01"}
        )
        self.assertEqual(status_code, 400)
        self.assertIn("start_date cannot be later than end_date", body["detail"])

    def test_delete_price_success(self):
        payload = {
            "crop_id": "CR_OKRA",
            "market_id": "DEC_THAMBUTTEGAMA",
            "market_name": "Thambuttegama DEC",
            "district_id": "LK-71",
            "price_date": "2026-10-14",
            "price": 140.00,
            "data_source": "HARTI"
        }
        _, created = self.client_request("POST", "/api/v1/market-prices", body=payload, as_admin=True)
        price_id = created["id"]

        del_status, _ = self.client_request("DELETE", f"/api/v1/market-prices/{price_id}", as_admin=True)
        self.assertEqual(del_status, 204)

        get_status, _ = self.client_request("GET", f"/api/v1/market-prices/{price_id}")
        self.assertEqual(get_status, 404)

    def test_delete_price_not_found_404(self):
        status_code, body = self.client_request("DELETE", "/api/v1/market-prices/999999", as_admin=True)
        self.assertEqual(status_code, 404)

    def test_create_price_invalid_crop_422(self):
        payload = {
            "crop_id": "CR_UNREGISTERED_CROP",
            "market_id": "DEC_DAMBULLA",
            "market_name": "Dambulla DEC",
            "district_id": "LK-22",
            "price_date": "2026-10-14",
            "price": 150.00,
            "data_source": "HARTI"
        }
        status_code, body = self.client_request("POST", "/api/v1/market-prices", body=payload, as_admin=True)
        self.assertEqual(status_code, 422)


class TestMarketDemandsCRUD(BaseCRUDTestCase):
    """Test suite for /api/v1/market-demands CRUD endpoints."""

    def test_create_observed_demand_success(self):
        payload = {
            "crop_id": "CR_TOMATO",
            "district_id": "LK-22",
            "market_id": "DEC_DAMBULLA",
            "period_start_date": "2026-10-01",
            "period_end_date": "2026-10-07",
            "demand_volume_kg": 25000.0,
            "unit": "kg",
            "record_type": "observed",
            "demand_level": "High",
            "confidence_score": 0.95,
            "is_training_eligible": True,
            "data_source": "DEC Wholesale Ledger"
        }
        status_code, body = self.client_request("POST", "/api/v1/market-demands", body=payload, as_admin=True)
        self.assertEqual(status_code, 201)
        self.assertIn("id", body)
        self.assertEqual(body["record_type"], "observed")
        self.assertTrue(body["is_training_eligible"])
        self.assertEqual(float(body["demand_volume_kg"]), 25000.0)

    def test_create_synthetic_demand_enforces_non_training(self):
        payload = {
            "crop_id": "CR_MUNG_BEAN",
            "district_id": "LK-72",
            "market_id": "DEC_DAMBULLA",
            "period_start_date": "2026-10-01",
            "period_end_date": "2026-10-07",
            "demand_volume_kg": 15000.0,
            "unit": "kg",
            "record_type": "synthetic",
            "demand_level": "Medium",
            "is_training_eligible": True,  # Attemping to mark synthetic as training eligible
            "data_source": "Monte Carlo Simulation"
        }
        status_code, body = self.client_request("POST", "/api/v1/market-demands", body=payload, as_admin=True)
        self.assertEqual(status_code, 201)
        self.assertFalse(body["is_training_eligible"], "Synthetic demand records must never be training eligible")

    def test_get_demand_by_id(self):
        payload = {
            "crop_id": "CR_PUMPKIN",
            "district_id": "LK-71",
            "market_id": "DEC_THAMBUTTEGAMA",
            "period_start_date": "2026-09-01",
            "period_end_date": "2026-09-30",
            "demand_volume_kg": 18000.0,
            "record_type": "estimated",
            "demand_level": "Medium",
            "data_source": "Agrarian Services Department"
        }
        _, created = self.client_request("POST", "/api/v1/market-demands", body=payload, as_admin=True)
        demand_id = created["id"]

        status_code, body = self.client_request("GET", f"/api/v1/market-demands/{demand_id}")
        self.assertEqual(status_code, 200)
        self.assertEqual(body["id"], demand_id)
        self.assertEqual(body["crop_id"], "CR_PUMPKIN")

    def test_get_demand_not_found_404(self):
        status_code, body = self.client_request("GET", "/api/v1/market-demands/999999")
        self.assertEqual(status_code, 404)

    def test_list_demands_filtering(self):
        d1 = {
            "crop_id": "CR_CHILLI",
            "district_id": "LK-71",
            "period_start_date": "2026-10-01",
            "period_end_date": "2026-10-07",
            "demand_volume_kg": 5000.0,
            "record_type": "observed",
            "data_source": "Survey"
        }
        d2 = {
            "crop_id": "CR_CHILLI",
            "district_id": "LK-71",
            "period_start_date": "2026-10-08",
            "period_end_date": "2026-10-14",
            "demand_volume_kg": 6000.0,
            "record_type": "synthetic",
            "data_source": "Sim"
        }
        self.client_request("POST", "/api/v1/market-demands", body=d1, as_admin=True)
        self.client_request("POST", "/api/v1/market-demands", body=d2, as_admin=True)

        status_code, body = self.client_request(
            "GET",
            "/api/v1/market-demands",
            params={"crop_id": "CR_CHILLI", "record_type": "synthetic"}
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["meta"]["total"], 1)
        self.assertEqual(body["items"][0]["record_type"], "synthetic")

    def test_delete_demand_success(self):
        payload = {
            "crop_id": "CR_BRINJAL",
            "district_id": "LK-22",
            "period_start_date": "2026-10-01",
            "period_end_date": "2026-10-07",
            "demand_volume_kg": 7500.0,
            "record_type": "observed",
            "data_source": "Survey"
        }
        _, created = self.client_request("POST", "/api/v1/market-demands", body=payload, as_admin=True)
        demand_id = created["id"]

        del_status, _ = self.client_request("DELETE", f"/api/v1/market-demands/{demand_id}", as_admin=True)
        self.assertEqual(del_status, 204)

        get_status, _ = self.client_request("GET", f"/api/v1/market-demands/{demand_id}")
        self.assertEqual(get_status, 404)

    def test_create_demand_invalid_period_dates_422(self):
        payload = {
            "crop_id": "CR_TOMATO",
            "district_id": "LK-22",
            "period_start_date": "2026-10-15",
            "period_end_date": "2026-10-01",  # Invalid chronology
            "demand_volume_kg": 5000.0,
            "record_type": "observed",
            "data_source": "Survey"
        }
        status_code, body = self.client_request("POST", "/api/v1/market-demands", body=payload, as_admin=True)
        self.assertEqual(status_code, 422)


class TestCultivationBudgetsCRUD(BaseCRUDTestCase):
    """Test suite for /api/v1/cultivation-budgets CRUD endpoints."""

    def test_create_quick_mode_budget(self):
        payload = {
            "crop_id": "CR_TOMATO",
            "district_id": "LK-71",
            "season": "Maha",
            "year": 2026,
            "entry_mode": "quick",
            "land_extent_acres": 1.50,
            "total_cost": 275000.00,
            "expected_yield_kg": 9000.00,
            "data_source": "Farmer Direct"
        }
        status_code, body = self.client_request("POST", "/api/v1/cultivation-budgets", body=payload)
        self.assertEqual(status_code, 201)
        self.assertIn("id", body)
        self.assertEqual(body["entry_mode"], "quick")
        self.assertEqual(float(body["total_cost"]), 275000.00)
        # Verify itemized breakdown remains null
        self.assertIsNone(body["land_preparation_cost"])
        self.assertIsNone(body["seeds_plants_cost"])
        self.assertIsNone(body["fertilizer_cost"])
        self.assertIsNone(body["labor_cost"])

    def test_create_detailed_mode_budget(self):
        payload = {
            "crop_id": "CR_CHILLI",
            "district_id": "LK-71",
            "season": "Yala",
            "year": 2026,
            "entry_mode": "detailed",
            "land_extent_acres": 1.00,
            "expected_yield_kg": 3500.00,
            "breakdown": {
                "land_preparation_cost": 30000.00,
                "seeds_plants_cost": 25000.00,
                "fertilizer_cost": 50000.00,
                "pesticide_weedicide_cost": 20000.00,
                "labor_cost": 75000.00,
                "machinery_fuel_cost": 15000.00,
                "transport_packaging_cost": 10000.00,
                "miscellaneous_cost": 5000.00
            }
        }
        status_code, body = self.client_request("POST", "/api/v1/cultivation-budgets", body=payload)
        self.assertEqual(status_code, 201)
        self.assertEqual(body["entry_mode"], "detailed")
        expected_total = 30000 + 25000 + 50000 + 20000 + 75000 + 15000 + 10000 + 5000
        self.assertEqual(float(body["total_cost"]), float(expected_total))
        self.assertEqual(float(body["land_preparation_cost"]), 30000.00)
        self.assertEqual(float(body["labor_cost"]), 75000.00)

    def test_create_detailed_mode_mismatch_422(self):
        payload = {
            "crop_id": "CR_CHILLI",
            "district_id": "LK-71",
            "season": "Yala",
            "year": 2026,
            "entry_mode": "detailed",
            "land_extent_acres": 1.00,
            "total_cost": 999999.00,  # Deliberate mismatch
            "expected_yield_kg": 3500.00,
            "breakdown": {
                "land_preparation_cost": 30000.00,
                "seeds_plants_cost": 20000.00
            }
        }
        status_code, body = self.client_request("POST", "/api/v1/cultivation-budgets", body=payload)
        self.assertEqual(status_code, 422)

    def test_get_budget_by_id(self):
        payload = {
            "crop_id": "CR_MAIZE",
            "district_id": "LK-71",
            "season": "Maha",
            "year": 2026,
            "entry_mode": "quick",
            "total_cost": 120000.00,
            "expected_yield_kg": 4000.00
        }
        _, created = self.client_request("POST", "/api/v1/cultivation-budgets", body=payload)
        budget_id = created["id"]

        status_code, body = self.client_request("GET", f"/api/v1/cultivation-budgets/{budget_id}", as_admin=True)
        self.assertEqual(status_code, 200)
        self.assertEqual(body["id"], budget_id)
        self.assertEqual(body["crop_id"], "CR_MAIZE")

    def test_get_budget_not_found_404(self):
        status_code, body = self.client_request("GET", "/api/v1/cultivation-budgets/999999", as_admin=True)
        self.assertEqual(status_code, 404)

    def test_list_budgets_filtering(self):
        b1 = {
            "crop_id": "CR_BRINJAL", "district_id": "LK-22", "season": "Maha", "year": 2026,
            "entry_mode": "quick", "total_cost": 150000.00, "expected_yield_kg": 5000.00
        }
        b2 = {
            "crop_id": "CR_BRINJAL", "district_id": "LK-22", "season": "Yala", "year": 2026,
            "entry_mode": "quick", "total_cost": 140000.00, "expected_yield_kg": 4800.00
        }
        self.client_request("POST", "/api/v1/cultivation-budgets", body=b1)
        self.client_request("POST", "/api/v1/cultivation-budgets", body=b2)

        status_code, body = self.client_request(
            "GET",
            "/api/v1/cultivation-budgets",
            params={"crop_id": "CR_BRINJAL", "season": "Maha"},
            as_admin=True
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["meta"]["total"], 1)
        self.assertEqual(body["items"][0]["season"], "Maha")

    def test_delete_budget_success(self):
        payload = {
            "crop_id": "CR_OKRA", "district_id": "LK-71", "season": "Year-round", "year": 2026,
            "entry_mode": "quick", "total_cost": 90000.00, "expected_yield_kg": 3000.00
        }
        _, created = self.client_request("POST", "/api/v1/cultivation-budgets", body=payload)
        budget_id = created["id"]

        del_status, _ = self.client_request("DELETE", f"/api/v1/cultivation-budgets/{budget_id}", as_admin=True)
        self.assertEqual(del_status, 204)

        get_status, _ = self.client_request("GET", f"/api/v1/cultivation-budgets/{budget_id}", as_admin=True)
        self.assertEqual(get_status, 404)


class TestProfitAnalysesCRUD(BaseCRUDTestCase):
    """Test suite for /api/v1/profit-analyses CRUD endpoints."""

    def test_create_profit_analysis_quick_mode_model_unavailable(self):
        payload = {
            "crop_id": "CR_TOMATO",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": "2026-12-15",
            "forecast_horizon_days": 90,
            "cultivation_extent_acres": 2.0,
            "estimated_production_kg": 8000.0,
            "budget_entry_mode": "quick",
            "quick_total_cost": 320000.0
        }
        status_code, body = self.client_request("POST", "/api/v1/profit-analyses", body=payload)
        self.assertEqual(status_code, 201)
        self.assertTrue(body["analysis_reference"].startswith("REF-"))
        self.assertEqual(body["prediction_status"], "unavailable")
        self.assertEqual(body["status_message"], "Machine learning models are currently unavailable.")
        self.assertIsNotNone(body["error_message"])
        # Ensure ML forecasted fields are not fabricated
        self.assertIsNone(body["forecasted_wholesale_price"])
        self.assertIsNone(body["projected_revenue"])
        self.assertIsNone(body["projected_net_profit"])
        self.assertIsNone(body["profit_risk_level"])

    def test_create_profit_analysis_with_saved_budget(self):
        budget_payload = {
            "crop_id": "CR_CHILLI",
            "district_id": "LK-71",
            "season": "Maha",
            "year": 2026,
            "entry_mode": "quick",
            "total_cost": 210000.00,
            "expected_yield_kg": 4000.00
        }
        _, budget = self.client_request("POST", "/api/v1/cultivation-budgets", body=budget_payload)
        budget_id = budget["id"]

        analysis_payload = {
            "crop_id": "CR_CHILLI",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": "2026-11-20",
            "cultivation_extent_acres": 1.0,
            "estimated_production_kg": 4000.0,
            "budget_entry_mode": "quick",
            "cultivation_budget_id": budget_id
        }
        status_code, body = self.client_request("POST", "/api/v1/profit-analyses", body=analysis_payload)
        self.assertEqual(status_code, 201)
        self.assertEqual(float(body["estimated_total_cost"]), 210000.00)

    def test_create_profit_analysis_invalid_budget_id_404(self):
        payload = {
            "crop_id": "CR_TOMATO",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": "2026-12-01",
            "cultivation_extent_acres": 1.0,
            "estimated_production_kg": 5000.0,
            "budget_entry_mode": "quick",
            "cultivation_budget_id": 999999
        }
        status_code, body = self.client_request("POST", "/api/v1/profit-analyses", body=payload)
        self.assertEqual(status_code, 404)
        self.assertIn("does not exist", body["detail"])

    def test_get_profit_analysis_by_id_and_reference(self):
        payload = {
            "crop_id": "CR_MAIZE",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": "2026-12-30",
            "cultivation_extent_acres": 3.0,
            "estimated_production_kg": 12000.0,
            "budget_entry_mode": "quick",
            "quick_total_cost": 280000.0
        }
        _, created = self.client_request("POST", "/api/v1/profit-analyses", body=payload)
        ref = created["analysis_reference"]

        # Retrieve by reference string
        status_ref, body_ref = self.client_request("GET", f"/api/v1/profit-analyses/{ref}", as_admin=True)
        self.assertEqual(status_ref, 200)
        self.assertEqual(body_ref["analysis_reference"], ref)

        # Also retrieve through database ID
        db_record = self.session.query(MarketProfitAnalysis).filter_by(analysis_reference=ref).first()
        status_id, body_id = self.client_request("GET", f"/api/v1/profit-analyses/{db_record.id}", as_admin=True)
        self.assertEqual(status_id, 200)
        self.assertEqual(body_id["analysis_reference"], ref)

    def test_get_profit_analysis_not_found_404(self):
        status_code, body = self.client_request("GET", "/api/v1/profit-analyses/REF-NONEXISTENT", as_admin=True)
        self.assertEqual(status_code, 404)

    def test_list_profit_analyses_filtering(self):
        a1 = {
            "crop_id": "CR_TOMATO", "cultivation_district_id": "LK-71", "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": "2026-11-01", "cultivation_extent_acres": 1.0, "estimated_production_kg": 4000.0,
            "budget_entry_mode": "quick", "quick_total_cost": 150000.0
        }
        a2 = {
            "crop_id": "CR_BRINJAL", "cultivation_district_id": "LK-22", "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": "2026-11-15", "cultivation_extent_acres": 1.5, "estimated_production_kg": 6000.0,
            "budget_entry_mode": "quick", "quick_total_cost": 190000.0
        }
        self.client_request("POST", "/api/v1/profit-analyses", body=a1)
        self.client_request("POST", "/api/v1/profit-analyses", body=a2)

        status_code, body = self.client_request(
            "GET",
            "/api/v1/profit-analyses",
            params={"crop_id": "CR_TOMATO", "prediction_status": "unavailable"},
            as_admin=True
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["meta"]["total"], 1)
        self.assertEqual(body["items"][0]["crop_id"], "CR_TOMATO")

    def test_delete_profit_analysis_success(self):
        payload = {
            "crop_id": "CR_OKRA", "cultivation_district_id": "LK-71", "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": "2026-12-05", "cultivation_extent_acres": 1.0, "estimated_production_kg": 3000.0,
            "budget_entry_mode": "quick", "quick_total_cost": 110000.0
        }
        _, created = self.client_request("POST", "/api/v1/profit-analyses", body=payload)
        ref = created["analysis_reference"]

        del_status, _ = self.client_request("DELETE", f"/api/v1/profit-analyses/{ref}", as_admin=True)
        self.assertEqual(del_status, 204)

        get_status, _ = self.client_request("GET", f"/api/v1/profit-analyses/{ref}", as_admin=True)
        self.assertEqual(get_status, 404)


class TestOpenAPIAndDocumentation(unittest.TestCase):
    """Verify that OpenAPI schema exposes all 4 resource routes and all Pydantic schemas."""

    def test_openapi_contains_all_crud_routes(self):
        schema = app.openapi()
        paths = schema.get("paths", {})

        required_endpoints = [
            "/api/v1/market-prices",
            "/api/v1/market-prices/{price_id}",
            "/api/v1/market-demands",
            "/api/v1/market-demands/{demand_id}",
            "/api/v1/cultivation-budgets",
            "/api/v1/cultivation-budgets/{budget_id}",
            "/api/v1/profit-analyses",
            "/api/v1/profit-analyses/{analysis_id}",
        ]
        for ep in required_endpoints:
            self.assertIn(ep, paths, f"OpenAPI specification missing expected endpoint '{ep}'")

    def test_openapi_schemas_registered(self):
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})

        required_schemas = [
            "MarketPriceCreate",
            "MarketPriceResponse",
            "PaginatedMarketPriceResponse",
            "MarketDemandCreate",
            "MarketDemandResponse",
            "PaginatedMarketDemandResponse",
            "CultivationBudgetCreate",
            "CultivationBudgetResponse",
            "PaginatedCultivationBudgetResponse",
            "FarmerAnalysisInput",
            "PredictionResultResponse",
            "PaginatedProfitAnalysisResponse",
            "PaginationMeta"
        ]
        for sc in required_schemas:
            self.assertIn(sc, schemas, f"OpenAPI components/schemas missing '{sc}'")


if __name__ == "__main__":
    unittest.main()
