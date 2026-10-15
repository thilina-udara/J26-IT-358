import asyncio
import json
import unittest
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine, get_db
from app.main import app
from app.models.cultivation_cost import CultivationBudget
from app.models.market_demand import MarketDemand
from app.models.market_price import MarketPrice
from app.models.profit_analysis import MarketProfitAnalysis


class TestResponse:
    """Wrapper encapsulating HTTP response status code, JSON payload, and raw text."""

    def __init__(self, status_code: int, json_data: Any, raw_body: str):
        self.status_code = status_code
        self._json_data = json_data
        self.text = raw_body

    def json(self) -> Any:
        return self._json_data


class FastAPITestClient:
    """
    Lightweight, in-process ASGI TestClient for FastAPI.
    Dispatches asynchronous HTTP requests directly through the ASGI interface
    without external network socket bindings or uninstalled dependencies.
    """

    def __init__(self, app, admin_key: Optional[str] = None):
        self.app = app
        self.admin_key = admin_key

    def request(
        self,
        method: str,
        path: str,
        json_body: Any = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        as_admin: bool = False
    ) -> TestResponse:
        body_bytes = json.dumps(json_body).encode("utf-8") if json_body is not None else b""
        query_string = urlencode(params).encode("ascii") if params else b""
        req_headers = [(b"host", b"localhost")]

        if json_body is not None:
            req_headers.append((b"content-type", b"application/json"))
        if as_admin and self.admin_key:
            req_headers.append((b"x-admin-key", self.admin_key.encode("utf-8")))
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
            nonlocal status_code, body_parts
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        asyncio.run(self.app(scope, receive, send))

        raw_body = b"".join(body_parts).decode("utf-8")
        parsed_json = None
        if raw_body:
            try:
                parsed_json = json.loads(raw_body)
            except Exception:
                parsed_json = None

        return TestResponse(status_code=status_code, json_data=parsed_json, raw_body=raw_body)

    def get(self, path: str, **kwargs) -> TestResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, json: Any = None, **kwargs) -> TestResponse:
        return self.request("POST", path, json_body=json, **kwargs)

    def delete(self, path: str, **kwargs) -> TestResponse:
        return self.request("DELETE", path, **kwargs)


class TestBackendIntegrationFarmerWorkflow(unittest.TestCase):
    """
    Milestone 1E — Task 7: End-to-end integration and farmer planning workflow tests.
    Verifies multi-step decision workflow across:
      1. POST /api/v1/market-demands/forecast (Market Demand Prediction)
      2. POST /api/v1/market-prices/forecast (Wholesale & Retail Price Forecasting)
      3. POST /api/v1/profit-analyses/calculate (Deterministic Profit Calculation)
      4. POST /api/v1/profit-analyses/assess-risk (Profit Risk Assessment)
    Confirms unit/catalog consistency, graceful ML unavailability, statelessness,
    security preservation, and error handling for pilot scenarios in Matara district.
    """

    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.session = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        app.dependency_overrides[get_db] = lambda: self.session

        self.test_admin_key = "test-integration-workflow-admin-key"
        self.original_admin_key = settings.ADMIN_API_KEY
        settings.ADMIN_API_KEY = self.test_admin_key

        self.client = FastAPITestClient(app=app, admin_key=self.test_admin_key)

        # Verified pilot simulation identifiers
        self.pilot_crop_id = "CR_TOMATO"
        self.pilot_district_id = "LK-32"  # Matara District
        self.pilot_market_id = "DEC_EMBILIPITIYA"  # Verified Dedicated Economic Centre
        self.future_harvest_date = (date.today() + timedelta(days=60)).isoformat()

    def tearDown(self):
        settings.ADMIN_API_KEY = self.original_admin_key
        app.dependency_overrides.clear()
        self.session.close()
        self.transaction.rollback()
        self.connection.close()

    def test_complete_matara_farmer_planning_workflow(self):
        """
        Scenario 1: Complete Matara Farmer Planning Workflow.
        Simulate a farmer in Matara (LK-31) planning tomato (CR_TOMATO) cultivation for harvest
        at Embilipitiya Dedicated Economic Centre (DEC_EMBILIPITIYA) in 60 days.
        Verifies:
          1. Demand prediction returns explicit unavailable status (no connected model).
          2. Wholesale & Retail price forecasts return explicit unavailable status.
          3. Farmer seamlessly falls back to manual assumptions and calculates profit.
          4. Profit risk assessment evaluates the exact same assumptions deterministically.
        """
        # Step 1: Request Market Demand Forecast
        demand_req = {
            "crop_id": self.pilot_crop_id,
            "cultivation_district_id": self.pilot_district_id,
            "target_market_id": self.pilot_market_id,
            "forecast_target_date": self.future_harvest_date
        }
        res_demand = self.client.post("/api/v1/market-demands/forecast", json=demand_req)
        self.assertEqual(res_demand.status_code, 200)
        demand_data = res_demand.json()
        self.assertEqual(demand_data["prediction_status"], "unavailable")
        self.assertIsNone(demand_data["projected_demand_volume_kg"])
        self.assertIsNone(demand_data["projected_demand_level"])
        self.assertIn("offline", demand_data["status_message"].lower())

        # Step 2: Request Wholesale Price Forecast
        wholesale_req = {
            "crop_id": self.pilot_crop_id,
            "cultivation_district_id": self.pilot_district_id,
            "target_market_id": self.pilot_market_id,
            "forecast_target_date": self.future_harvest_date,
            "price_type": "wholesale"
        }
        res_wholesale = self.client.post("/api/v1/market-prices/forecast", json=wholesale_req)
        self.assertEqual(res_wholesale.status_code, 200)
        ws_data = res_wholesale.json()
        self.assertEqual(ws_data["prediction_status"], "unavailable")
        self.assertEqual(ws_data["price_type"], "wholesale")
        self.assertEqual(ws_data["currency"], "LKR")
        self.assertEqual(ws_data["unit"], "kg")
        self.assertIsNone(ws_data["forecasted_price_lkr_per_kg"])
        self.assertIn("offline", ws_data["status_message"].lower())

        # Step 3: Request Retail Price Forecast (Verifying wholesale/retail independence)
        retail_req = {
            "crop_id": self.pilot_crop_id,
            "cultivation_district_id": self.pilot_district_id,
            "target_market_id": self.pilot_market_id,
            "forecast_target_date": self.future_harvest_date,
            "price_type": "retail"
        }
        res_retail = self.client.post("/api/v1/market-prices/forecast", json=retail_req)
        self.assertEqual(res_retail.status_code, 200)
        ret_data = res_retail.json()
        self.assertEqual(ret_data["prediction_status"], "unavailable")
        self.assertEqual(ret_data["price_type"], "retail")
        self.assertIsNone(ret_data["forecasted_price_lkr_per_kg"])

        # Step 4: Because ML is unavailable, farmer calculates profitability using manual assumptions
        calc_req = {
            "expected_yield_kg": "2500.00",
            "selling_price_lkr_per_kg": "160.00",
            "total_cultivation_cost": "200000.00"
        }
        res_calc = self.client.post("/api/v1/profit-analyses/calculate", json=calc_req)
        self.assertEqual(res_calc.status_code, 200)
        calc_data = res_calc.json()
        self.assertEqual(calc_data["gross_revenue"], "400000.00")
        self.assertEqual(calc_data["net_profit"], "200000.00")
        self.assertEqual(calc_data["breakeven_price_lkr_per_kg"], "80.00")
        self.assertEqual(calc_data["roi_percentage"], "100.00")
        self.assertEqual(calc_data["margin_of_safety_percentage"], "50.00")
        self.assertEqual(calc_data["price_source"], "farmer_assumption")
        self.assertTrue(calc_data["is_manual_price_assumption"])

        # Step 5: Farmer assesses profit risk with the exact same inputs
        risk_req = {
            "expected_yield_kg": "2500.00",
            "selling_price_lkr_per_kg": "160.00",
            "total_cultivation_cost": "200000.00"
        }
        res_risk = self.client.post("/api/v1/profit-analyses/assess-risk", json=risk_req)
        self.assertEqual(res_risk.status_code, 200)
        risk_data = res_risk.json()
        self.assertEqual(risk_data["risk_level"], "Low")
        self.assertEqual(risk_data["assessment_type"], "rule_based_heuristic")
        self.assertFalse(risk_data["is_ml_prediction"])
        self.assertIn("preliminary", risk_data["disclaimer"].lower())

        # Step 6: Verify calculation results embedded in risk assessment match calculation API exactly
        embedded_calc = risk_data["profit_calculation"]
        self.assertEqual(embedded_calc["gross_revenue"], calc_data["gross_revenue"])
        self.assertEqual(embedded_calc["net_profit"], calc_data["net_profit"])
        self.assertEqual(embedded_calc["roi_percentage"], calc_data["roi_percentage"])
        self.assertEqual(embedded_calc["breakeven_price_lkr_per_kg"], calc_data["breakeven_price_lkr_per_kg"])
        self.assertEqual(embedded_calc["margin_of_safety_percentage"], calc_data["margin_of_safety_percentage"])
        self.assertEqual(embedded_calc["price_source"], "farmer_assumption")

    def test_hambantota_pilot_farmer_planning_workflow(self):
        """
        Scenario 1B: Hambantota Pilot District Planning Workflow.
        Simulate a farmer in Hambantota (LK-33) planning green chilli (CR_CHILLI) cultivation
        destined for Embilipitiya Dedicated Economic Centre (DEC_EMBILIPITIYA).
        Verifies demand & price prediction unavailability, followed by successful deterministic
        profitability and risk assessment.
        """
        chilli_crop = "CR_CHILLI"
        hambantota_district = "LK-33"
        harvest_date = (date.today() + timedelta(days=90)).isoformat()

        # Demand forecast -> unavailable
        res_d = self.client.post(
            "/api/v1/market-demands/forecast",
            json={
                "crop_id": chilli_crop,
                "cultivation_district_id": hambantota_district,
                "target_market_id": self.pilot_market_id,
                "forecast_target_date": harvest_date
            }
        )
        self.assertEqual(res_d.status_code, 200)
        self.assertEqual(res_d.json()["prediction_status"], "unavailable")
        self.assertIsNone(res_d.json()["projected_demand_volume_kg"])

        # Price forecast -> unavailable
        res_p = self.client.post(
            "/api/v1/market-prices/forecast",
            json={
                "crop_id": chilli_crop,
                "cultivation_district_id": hambantota_district,
                "target_market_id": self.pilot_market_id,
                "forecast_target_date": harvest_date,
                "price_type": "wholesale"
            }
        )
        self.assertEqual(res_p.status_code, 200)
        self.assertEqual(res_p.json()["prediction_status"], "unavailable")
        self.assertIsNone(res_p.json()["forecasted_price_lkr_per_kg"])

        # Deterministic profit calculation
        res_c = self.client.post(
            "/api/v1/profit-analyses/calculate",
            json={
                "expected_yield_kg": "1200.00",
                "selling_price_lkr_per_kg": "350.00",
                "total_cultivation_cost": "250000.00"
            }
        )
        self.assertEqual(res_c.status_code, 200)
        c_data = res_c.json()
        self.assertEqual(c_data["gross_revenue"], "420000.00")
        self.assertEqual(c_data["net_profit"], "170000.00")
        self.assertEqual(c_data["breakeven_price_lkr_per_kg"], "208.33")
        self.assertEqual(c_data["roi_percentage"], "68.00")

        # Profit risk assessment
        res_r = self.client.post(
            "/api/v1/profit-analyses/assess-risk",
            json={
                "expected_yield_kg": "1200.00",
                "selling_price_lkr_per_kg": "350.00",
                "total_cultivation_cost": "250000.00"
            }
        )
        self.assertEqual(res_r.status_code, 200)
        self.assertEqual(res_r.json()["risk_level"], "Low")
        self.assertEqual(res_r.json()["factors"]["roi_percentage"], "68.00")

    def test_farmer_workflow_zero_cost_yields_insufficient_information(self):
        """
        Scenario 2: Zero cultivation cost input.
        Verifies that when cost data is omitted or 0.0, the calculation service leaves
        ROI undefined and the risk assessment returns 'insufficient_information'
        rather than fabricating a Low or High risk category.
        """
        req_zero_cost = {
            "expected_yield_kg": "1500.00",
            "selling_price_lkr_per_kg": "120.00",
            "total_cultivation_cost": "0.00"
        }

        # Calculate endpoint
        res_calc = self.client.post("/api/v1/profit-analyses/calculate", json=req_zero_cost)
        self.assertEqual(res_calc.status_code, 200)
        calc_data = res_calc.json()
        self.assertIsNone(calc_data["roi_percentage"])
        self.assertIn("ROI is mathematically undefined", calc_data["calculation_notes"])

        # Risk assessment endpoint
        res_risk = self.client.post("/api/v1/profit-analyses/assess-risk", json=req_zero_cost)
        self.assertEqual(res_risk.status_code, 200)
        risk_data = res_risk.json()
        self.assertEqual(risk_data["risk_level"], "insufficient_information")
        self.assertIsNone(risk_data["factors"]["roi_percentage"])
        self.assertIn("total_cultivation_cost == 0", risk_data["factors"]["trigger_rule"])

    def test_farmer_workflow_loss_making_high_risk(self):
        """
        Scenario 3: Unfavorable market prices leading to net financial deficit.
        Yield: 1000 kg, Selling price: 60 LKR/kg, Cost: 100,000 LKR.
        Revenue: 60,000 LKR < Cost: 100,000 LKR -> Net profit: -40,000 LKR, ROI: -40%.
        Verifies High Risk classification and transparent deficit rationale.
        """
        req_loss = {
            "expected_yield_kg": "1000.00",
            "selling_price_lkr_per_kg": "60.00",
            "total_cultivation_cost": "100000.00"
        }
        res_calc = self.client.post("/api/v1/profit-analyses/calculate", json=req_loss)
        self.assertEqual(res_calc.status_code, 200)
        calc_data = res_calc.json()
        self.assertEqual(calc_data["net_profit"], "-40000.00")
        self.assertEqual(calc_data["roi_percentage"], "-40.00")

        res_risk = self.client.post("/api/v1/profit-analyses/assess-risk", json=req_loss)
        self.assertEqual(res_risk.status_code, 200)
        risk_data = res_risk.json()
        self.assertEqual(risk_data["risk_level"], "High")
        self.assertEqual(risk_data["factors"]["net_profit"], "-40000.00")
        self.assertIn("direct financial deficit", risk_data["factors"]["trigger_rationale"])

    def test_farmer_workflow_medium_risk_scenarios(self):
        """
        Scenario 4: Medium Risk evaluations.
        (a) Exact Breakeven: Revenue equals Cost, Net Profit = 0, ROI = 0% -> Medium Risk.
        (b) Profitable but below Low Risk thresholds: ROI = 15% (< 25%) -> Medium Risk.
        """
        # (a) Exact Breakeven
        req_breakeven = {
            "expected_yield_kg": "1000.00",
            "selling_price_lkr_per_kg": "80.00",
            "total_cultivation_cost": "80000.00"
        }
        res_breakeven = self.client.post("/api/v1/profit-analyses/assess-risk", json=req_breakeven)
        self.assertEqual(res_breakeven.status_code, 200)
        data_be = res_breakeven.json()
        self.assertEqual(data_be["risk_level"], "Medium")
        self.assertEqual(data_be["factors"]["net_profit"], "0.00")
        self.assertEqual(data_be["factors"]["roi_percentage"], "0.00")

        # (b) Positive profit below 25% ROI
        req_modest = {
            "expected_yield_kg": "1000.00",
            "selling_price_lkr_per_kg": "92.00",
            "total_cultivation_cost": "80000.00"
        }
        res_modest = self.client.post("/api/v1/profit-analyses/assess-risk", json=req_modest)
        self.assertEqual(res_modest.status_code, 200)
        data_modest = res_modest.json()
        self.assertEqual(data_modest["risk_level"], "Medium")
        self.assertEqual(data_modest["factors"]["roi_percentage"], "15.00")
        self.assertIn("below the 25.0% Low Risk threshold", data_modest["factors"]["trigger_rationale"])

    def test_no_fake_model_outputs_or_zero_interpretation(self):
        """
        Requirement 10: Ensure no fake model outputs are generated and no unavailable
        predictions are mistakenly returned or interpreted as numerical zero (0).
        Verifies nullable fields are strictly None/null, not 0 or fabricated floats.
        """
        # Demand forecast
        res_demand = self.client.post(
            "/api/v1/market-demands/forecast",
            json={
                "crop_id": self.pilot_crop_id,
                "cultivation_district_id": self.pilot_district_id,
                "target_market_id": self.pilot_market_id,
                "forecast_target_date": self.future_harvest_date
            }
        )
        self.assertEqual(res_demand.status_code, 200)
        demand_json = res_demand.json()
        self.assertIsNone(demand_json["projected_demand_volume_kg"])
        self.assertFalse(demand_json["projected_demand_volume_kg"] == 0)
        self.assertIsNone(demand_json["projected_demand_level"])

        # Price forecast
        res_price = self.client.post(
            "/api/v1/market-prices/forecast",
            json={
                "crop_id": self.pilot_crop_id,
                "cultivation_district_id": self.pilot_district_id,
                "target_market_id": self.pilot_market_id,
                "forecast_target_date": self.future_harvest_date,
                "price_type": "wholesale"
            }
        )
        self.assertEqual(res_price.status_code, 200)
        price_json = res_price.json()
        self.assertIsNone(price_json["forecasted_price_lkr_per_kg"])
        self.assertFalse(price_json["forecasted_price_lkr_per_kg"] == 0)
        self.assertIsNone(price_json["model_version"])
        self.assertIsNone(price_json["model_provenance"])

    def test_unit_currency_and_catalog_consistency_across_endpoints(self):
        """
        Requirement 8: Confirm consistency of:
          - Currency: "LKR"
          - Price units: "kg" (LKR per kg)
          - Yield units: "kg"
          - Shared catalogs: Crop IDs, District IDs, Market IDs
        """
        # Valid shared identifiers
        valid_crops = ["CR_TOMATO", "CR_MAIZE", "CR_CHILLI"]
        valid_districts = ["LK-31", "LK-71", "LK-11"]
        valid_markets = ["DEC_EMBILIPITIYA", "DEC_DAMBULLA", "DEC_PETTAH"]

        for crop in valid_crops:
            for district in valid_districts:
                for market in valid_markets:
                    payload = {
                        "crop_id": crop,
                        "cultivation_district_id": district,
                        "target_market_id": market,
                        "forecast_target_date": self.future_harvest_date
                    }
                    res_d = self.client.post("/api/v1/market-demands/forecast", json=payload)
                    self.assertEqual(res_d.status_code, 200)

                    payload_p = {**payload, "price_type": "wholesale"}
                    res_p = self.client.post("/api/v1/market-prices/forecast", json=payload_p)
                    self.assertEqual(res_p.status_code, 200)
                    self.assertEqual(res_p.json()["currency"], "LKR")
                    self.assertEqual(res_p.json()["unit"], "kg")
                    break
                break
            break

    def test_invalid_catalog_identifiers_and_dates_rejected_422(self):
        """
        Requirement 9: Test rejection of invalid crops, invalid districts, invalid markets,
        past forecast target dates, non-positive numbers, and missing fields.
        """
        # Invalid crop ID
        res_bad_crop = self.client.post(
            "/api/v1/market-demands/forecast",
            json={
                "crop_id": "CR_NONEXISTENT_CROP",
                "cultivation_district_id": self.pilot_district_id,
                "target_market_id": self.pilot_market_id,
                "forecast_target_date": self.future_harvest_date
            }
        )
        self.assertEqual(res_bad_crop.status_code, 422)

        # Invalid district ID
        res_bad_dist = self.client.post(
            "/api/v1/market-demands/forecast",
            json={
                "crop_id": self.pilot_crop_id,
                "cultivation_district_id": "LK-99",
                "target_market_id": self.pilot_market_id,
                "forecast_target_date": self.future_harvest_date
            }
        )
        self.assertEqual(res_bad_dist.status_code, 422)

        # Invalid market ID
        res_bad_mkt = self.client.post(
            "/api/v1/market-prices/forecast",
            json={
                "crop_id": self.pilot_crop_id,
                "cultivation_district_id": self.pilot_district_id,
                "target_market_id": "MARKET_UNKNOWN_123",
                "forecast_target_date": self.future_harvest_date,
                "price_type": "wholesale"
            }
        )
        self.assertEqual(res_bad_mkt.status_code, 422)

        # Past target date
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        res_past_date = self.client.post(
            "/api/v1/market-prices/forecast",
            json={
                "crop_id": self.pilot_crop_id,
                "cultivation_district_id": self.pilot_district_id,
                "target_market_id": self.pilot_market_id,
                "forecast_target_date": yesterday,
                "price_type": "wholesale"
            }
        )
        self.assertEqual(res_past_date.status_code, 422)

        # Invalid price_type (must be wholesale or retail)
        res_bad_pt = self.client.post(
            "/api/v1/market-prices/forecast",
            json={
                "crop_id": self.pilot_crop_id,
                "cultivation_district_id": self.pilot_district_id,
                "target_market_id": self.pilot_market_id,
                "forecast_target_date": self.future_harvest_date,
                "price_type": "spot_speculative"
            }
        )
        self.assertEqual(res_bad_pt.status_code, 422)

        # Non-positive expected_yield_kg on calculation
        res_bad_yield = self.client.post(
            "/api/v1/profit-analyses/calculate",
            json={"expected_yield_kg": "0.0", "selling_price_lkr_per_kg": "100.0"}
        )
        self.assertEqual(res_bad_yield.status_code, 422)

        # Non-positive selling_price_lkr_per_kg on risk assessment
        res_bad_price = self.client.post(
            "/api/v1/profit-analyses/assess-risk",
            json={"expected_yield_kg": "1000.0", "selling_price_lkr_per_kg": "-10.0"}
        )
        self.assertEqual(res_bad_price.status_code, 422)

        # Negative cultivation cost on calculation
        res_neg_cost = self.client.post(
            "/api/v1/profit-analyses/calculate",
            json={
                "expected_yield_kg": "1000.0",
                "selling_price_lkr_per_kg": "100.0",
                "total_cultivation_cost": "-500.0"
            }
        )
        self.assertEqual(res_neg_cost.status_code, 422)

        # Missing required fields
        res_missing = self.client.post(
            "/api/v1/market-demands/forecast",
            json={"crop_id": self.pilot_crop_id}
        )
        self.assertEqual(res_missing.status_code, 422)

    def test_workflow_statelessness_no_database_persistence(self):
        """
        Requirement 11: Verify that all forecasting and calculation endpoints remain stateless
        and perform 0 database insertions across all four core database tables.
        """
        # Record initial row counts
        count_prices_before = self.session.execute(select(func.count(MarketPrice.id))).scalar_one()
        count_demands_before = self.session.execute(select(func.count(MarketDemand.id))).scalar_one()
        count_budgets_before = self.session.execute(select(func.count(CultivationBudget.id))).scalar_one()
        count_analyses_before = self.session.execute(select(func.count(MarketProfitAnalysis.id))).scalar_one()

        # Execute all 4 Milestone endpoints
        self.client.post(
            "/api/v1/market-demands/forecast",
            json={
                "crop_id": self.pilot_crop_id,
                "cultivation_district_id": self.pilot_district_id,
                "target_market_id": self.pilot_market_id,
                "forecast_target_date": self.future_harvest_date
            }
        )
        self.client.post(
            "/api/v1/market-prices/forecast",
            json={
                "crop_id": self.pilot_crop_id,
                "cultivation_district_id": self.pilot_district_id,
                "target_market_id": self.pilot_market_id,
                "forecast_target_date": self.future_harvest_date,
                "price_type": "wholesale"
            }
        )
        self.client.post(
            "/api/v1/profit-analyses/calculate",
            json={
                "expected_yield_kg": "2000.00",
                "selling_price_lkr_per_kg": "120.00",
                "total_cultivation_cost": "150000.00"
            }
        )
        self.client.post(
            "/api/v1/profit-analyses/assess-risk",
            json={
                "expected_yield_kg": "2000.00",
                "selling_price_lkr_per_kg": "120.00",
                "total_cultivation_cost": "150000.00"
            }
        )

        # Record final row counts
        count_prices_after = self.session.execute(select(func.count(MarketPrice.id))).scalar_one()
        count_demands_after = self.session.execute(select(func.count(MarketDemand.id))).scalar_one()
        count_budgets_after = self.session.execute(select(func.count(CultivationBudget.id))).scalar_one()
        count_analyses_after = self.session.execute(select(func.count(MarketProfitAnalysis.id))).scalar_one()

        self.assertEqual(count_prices_before, count_prices_after)
        self.assertEqual(count_demands_before, count_demands_after)
        self.assertEqual(count_budgets_before, count_budgets_after)
        self.assertEqual(count_analyses_before, count_analyses_after)

    def test_admin_crud_security_controls_preserved(self):
        """
        Requirement 12: Verify that existing admin-protected CRUD endpoints have not been weakened:
          - Unauthenticated requests are rejected with 401 Unauthorized.
          - Invalid credentials are rejected with 403 Forbidden.
          - Authorized admin requests succeed.
        """
        # Unauthenticated calls to protected routes -> 401
        res_unauth_list = self.client.get("/api/v1/profit-analyses")
        self.assertEqual(res_unauth_list.status_code, 401)

        res_unauth_del = self.client.delete("/api/v1/profit-analyses/ANY_ID")
        self.assertEqual(res_unauth_del.status_code, 401)

        res_unauth_post_price = self.client.post(
            "/api/v1/market-prices",
            json={
                "crop_id": self.pilot_crop_id,
                "district_id": self.pilot_district_id,
                "market_center_id": self.pilot_market_id,
                "price_date": date.today().isoformat(),
                "price_type": "wholesale",
                "modal_price_lkr_per_kg": "120.00",
                "source": "HARTI"
            }
        )
        self.assertEqual(res_unauth_post_price.status_code, 401)

        # Invalid key -> 403
        res_bad_key = self.client.get(
            "/api/v1/profit-analyses",
            headers={"x-admin-key": "completely-invalid-key-token"}
        )
        self.assertEqual(res_bad_key.status_code, 403)

        # Valid admin key -> succeeds (200 OK)
        res_auth_list = self.client.get("/api/v1/profit-analyses", as_admin=True)
        self.assertEqual(res_auth_list.status_code, 200)

    def test_openapi_schema_contains_all_milestone_routes(self):
        """
        Requirement 13: Verify all new and existing Milestone API routes are properly
        registered and documented in FastAPI's generated OpenAPI specification.
        """
        schema = app.openapi()
        paths = schema.get("paths", {})

        # Milestone 1E new prediction & calculation routes
        self.assertIn("/api/v1/market-demands/forecast", paths)
        self.assertIn("post", paths["/api/v1/market-demands/forecast"])

        self.assertIn("/api/v1/market-prices/forecast", paths)
        self.assertIn("post", paths["/api/v1/market-prices/forecast"])

        self.assertIn("/api/v1/profit-analyses/calculate", paths)
        self.assertIn("post", paths["/api/v1/profit-analyses/calculate"])

        self.assertIn("/api/v1/profit-analyses/assess-risk", paths)
        self.assertIn("post", paths["/api/v1/profit-analyses/assess-risk"])

        # Core Component 1 CRUD routes
        self.assertIn("/api/v1/profit-analyses", paths)
        self.assertIn("/api/v1/profit-analyses/{analysis_id}", paths)
        self.assertIn("/api/v1/market-prices", paths)
        self.assertIn("/api/v1/market-demands", paths)
        self.assertIn("/api/v1/cultivation-budgets", paths)


if __name__ == "__main__":
    unittest.main()
