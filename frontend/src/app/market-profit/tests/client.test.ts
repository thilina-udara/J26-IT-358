/**
 * Automated Unit & Integration Tests for Component 1 Frontend Library:
 * Types, Catalogs, Formatters, and Typed API Client.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  MASTER_CROPS,
  SUPPORTED_FRONTEND_CROPS,
  SRI_LANKA_DISTRICTS,
  STANDARD_MARKETS,
  PRICE_TYPES,
  DEFAULT_RISK_THRESHOLDS,
  DEFAULT_API_BASE_URL,
} from "../lib/constants";

import {
  formatLKR,
  formatKg,
  formatLKRPerKg,
  formatPercent,
  formatDateDisplay,
  parsePositiveNumber,
} from "../lib/formatters";

import { MarketProfitApiClient, ApiError } from "../lib/api";
import { validateStep1 } from "../lib/wizard";

import type {
  DemandForecastRequest,
  DemandForecastResponse,
  PriceForecastRequest,
  PriceForecastResponse,
  ProfitCalculationInput,
  ProfitCalculationResult,
  ProfitRiskAssessmentInput,
  ProfitRiskAssessmentResult,
  FarmerPlanningScenario,
} from "../lib/types";

// ============================================================================
// 1. Constants & Catalog Verification
// ============================================================================

test("Catalogs: Master crops catalog contains 7 registered crops", () => {
  assert.equal(MASTER_CROPS.length, 7);
  const cropIds = MASTER_CROPS.map((c) => c.crop_id);
  assert.ok(cropIds.includes("CR_TOMATO"));
  assert.ok(cropIds.includes("CR_CHILLI"));
  assert.ok(cropIds.includes("CR_MAIZE"));
  assert.ok(cropIds.includes("CR_BRINJAL"));
  assert.ok(cropIds.includes("CR_OKRA"));
  assert.ok(cropIds.includes("CR_PUMPKIN"));
  assert.ok(cropIds.includes("CR_MUNG_BEAN"));
});

test("Catalogs: Farmer-facing supported crops contains exactly 6 crops excluding Tomato", () => {
  assert.equal(SUPPORTED_FRONTEND_CROPS.length, 6);
  const cropIds = SUPPORTED_FRONTEND_CROPS.map((c) => c.crop_id);
  assert.equal(cropIds.includes("CR_TOMATO"), false);
  assert.deepEqual(cropIds, [
    "CR_OKRA",
    "CR_BRINJAL",
    "CR_PUMPKIN",
    "CR_MAIZE",
    "CR_MUNG_BEAN",
    "CR_CHILLI",
  ]);
  // Confirm all 6 have valid image asset names and alt text
  for (const crop of SUPPORTED_FRONTEND_CROPS) {
    assert.ok(crop.image_name && crop.image_name.endsWith(".jpg"));
    assert.ok(crop.alt_text && crop.alt_text.length > 5);
  }
});

test("Catalogs: Districts include Matara (LK-32) and Hambantota (LK-33) pilot districts", () => {
  assert.equal(SRI_LANKA_DISTRICTS.length, 25);
  const matara = SRI_LANKA_DISTRICTS.find((d) => d.id === "LK-32");
  const hambantota = SRI_LANKA_DISTRICTS.find((d) => d.id === "LK-33");

  assert.ok(matara, "Matara district must exist");
  assert.equal(matara.name, "Matara");
  assert.equal(matara.is_pilot, true);

  assert.ok(hambantota, "Hambantota district must exist");
  assert.equal(hambantota.name, "Hambantota");
  assert.equal(hambantota.is_pilot, true);
});

test("Catalogs: Markets include DEC_EMBILIPITIYA as recommended pilot hub", () => {
  assert.equal(STANDARD_MARKETS.length, 10);
  const embilipitiya = STANDARD_MARKETS.find((m) => m.id === "DEC_EMBILIPITIYA");
  assert.ok(embilipitiya);
  assert.equal(embilipitiya.is_pilot_recommended, true);
  assert.ok(embilipitiya.name.includes("Embilipitiya"));
});

test("Catalogs: Price types define wholesale and retail tiers", () => {
  assert.equal(PRICE_TYPES.length, 2);
  assert.equal(PRICE_TYPES[0].id, "wholesale");
  assert.equal(PRICE_TYPES[1].id, "retail");
});

test("Catalogs: Default risk thresholds match 25% ROI and 20% margin of safety", () => {
  assert.equal(DEFAULT_RISK_THRESHOLDS.min_roi_low_risk, 25.0);
  assert.equal(DEFAULT_RISK_THRESHOLDS.min_margin_safety_low_risk, 20.0);
});

// ============================================================================
// 2. Data Formatters Verification
// ============================================================================

test("Formatters: formatLKR formats numbers with LKR prefix and comma separators", () => {
  assert.equal(formatLKR(170000), "LKR 170,000.00");
  assert.equal(formatLKR("350000.5"), "LKR 350,000.50");
  assert.equal(formatLKR(0), "LKR 0.00");
  assert.equal(formatLKR(1234.56, { showCents: false }), "LKR 1,235");
  assert.equal(formatLKR(null), "—");
  assert.equal(formatLKR(undefined), "—");
  assert.equal(formatLKR("invalid"), "—");
});

test("Formatters: formatKg formats metric harvest weights in kilograms", () => {
  assert.equal(formatKg(2500), "2,500 kg");
  assert.equal(formatKg("1250.5"), "1,250.5 kg");
  assert.equal(formatKg(1000, { includeUnit: false }), "1,000");
  assert.equal(formatKg(null), "—");
});

test("Formatters: formatLKRPerKg formats commodity unit price", () => {
  assert.equal(formatLKRPerKg(140), "LKR 140.00 / kg");
  assert.equal(formatLKRPerKg("72.5"), "LKR 72.50 / kg");
  assert.equal(formatLKRPerKg(null), "—");
});

test("Formatters: formatPercent formats percentages and handles undefined ROI gracefully", () => {
  assert.equal(formatPercent(94.44), "94.44%");
  assert.equal(formatPercent("25"), "25.00%");
  assert.equal(formatPercent(-30), "-30.00%");
  assert.equal(formatPercent(null), "Undefined");
  assert.equal(formatPercent(undefined), "Undefined");
  assert.equal(formatPercent(null, { fallback: "N/A" }), "N/A");
});

test("Formatters: formatDateDisplay converts ISO dates to readable text", () => {
  assert.equal(formatDateDisplay("2026-12-15"), "Dec 15, 2026");
  assert.equal(formatDateDisplay(null), "—");
  assert.equal(formatDateDisplay(""), "—");
});

test("Formatters: parsePositiveNumber safely extracts numeric values", () => {
  assert.equal(parsePositiveNumber(2500), 2500);
  assert.equal(parsePositiveNumber("2,500"), 2500);
  assert.equal(parsePositiveNumber("-100"), 0);
  assert.equal(parsePositiveNumber("invalid"), 0);
});

// ============================================================================
// 3. API Client Verification
// ============================================================================

test("API Client: getDemandForecast preserves unavailable status and null values", async () => {
  const mockResponse: DemandForecastResponse = {
    crop_id: "CR_TOMATO",
    cultivation_district_id: "LK-32",
    target_market_id: "DEC_EMBILIPITIYA",
    forecast_target_date: "2026-12-15",
    prediction_status: "unavailable",
    projected_demand_volume_kg: null,
    projected_demand_level: null,
    status_message: "Machine learning demand prediction model is currently offline or undergoing training.",
  };

  const client = new MarketProfitApiClient({
    transport: async (url, init) => {
      assert.ok(String(url).endsWith("/api/v1/market-demands/forecast"));
      assert.equal(init?.method, "POST");
      const body = JSON.parse(String(init?.body));
      assert.equal(body.crop_id, "CR_TOMATO");
      assert.equal(body.cultivation_district_id, "LK-32");
      return new Response(JSON.stringify(mockResponse), { status: 200 });
    },
  });

  const res = await client.getDemandForecast({
    crop_id: "CR_TOMATO",
    cultivation_district_id: "LK-32",
    target_market_id: "DEC_EMBILIPITIYA",
    forecast_target_date: "2026-12-15",
  });

  assert.equal(res.prediction_status, "unavailable");
  assert.equal(res.projected_demand_volume_kg, null);
  assert.notEqual(res.projected_demand_volume_kg, 0);
  assert.equal(res.projected_demand_level, null);
});

test("API Client: getPriceForecast handles wholesale and retail price tiers", async () => {
  const mockResponse: PriceForecastResponse = {
    crop_id: "CR_TOMATO",
    cultivation_district_id: "LK-32",
    target_market_id: "DEC_EMBILIPITIYA",
    forecast_target_date: "2026-12-15",
    price_type: "wholesale",
    currency: "LKR",
    unit: "kg",
    prediction_status: "unavailable",
    forecasted_price_lkr_per_kg: null,
    status_message: "Machine learning price forecasting model is currently offline or undergoing training.",
  };

  const client = new MarketProfitApiClient({
    transport: async (url, init) => {
      assert.ok(String(url).endsWith("/api/v1/market-prices/forecast"));
      const body = JSON.parse(String(init?.body));
      assert.equal(body.price_type, "wholesale");
      return new Response(JSON.stringify(mockResponse), { status: 200 });
    },
  });

  const res = await client.getPriceForecast({
    crop_id: "CR_TOMATO",
    cultivation_district_id: "LK-32",
    target_market_id: "DEC_EMBILIPITIYA",
    forecast_target_date: "2026-12-15",
    price_type: "wholesale",
  });

  assert.equal(res.prediction_status, "unavailable");
  assert.equal(res.forecasted_price_lkr_per_kg, null);
  assert.equal(res.currency, "LKR");
  assert.equal(res.unit, "kg");
});

test("API Client: calculateProfit returns deterministic financial metrics", async () => {
  const mockResponse: ProfitCalculationResult = {
    expected_yield_kg: "2500.00",
    selling_price_lkr_per_kg: "140.00",
    total_cultivation_cost: "180000.00",
    gross_revenue: "350000.00",
    net_profit: "170000.00",
    roi_percentage: "94.44",
    breakeven_price_lkr_per_kg: "72.00",
    margin_of_safety_percentage: "48.57",
    currency: "LKR",
    price_source: "farmer_assumption",
    is_manual_price_assumption: true,
    assumptions_note: "Selling price is a user planning assumption, not an ML forecast.",
    calculation_notes: null,
  };

  const client = new MarketProfitApiClient({
    transport: async (url, init) => {
      assert.ok(String(url).endsWith("/api/v1/profit-analyses/calculate"));
      return new Response(JSON.stringify(mockResponse), { status: 200 });
    },
  });

  const res = await client.calculateProfit({
    expected_yield_kg: "2500.00",
    selling_price_lkr_per_kg: "140.00",
    total_cultivation_cost: "180000.00",
  });

  assert.equal(res.gross_revenue, "350000.00");
  assert.equal(res.net_profit, "170000.00");
  assert.equal(res.roi_percentage, "94.44");
  assert.equal(res.breakeven_price_lkr_per_kg, "72.00");
  assert.equal(res.margin_of_safety_percentage, "48.57");
  assert.equal(res.price_source, "farmer_assumption");
});

test("API Client: assessProfitRisk returns Low risk and heuristic disclaimers", async () => {
  const mockResponse: ProfitRiskAssessmentResult = {
    risk_level: "Low",
    assessment_type: "rule_based_heuristic",
    is_ml_prediction: false,
    disclaimer: "Preliminary rule-based heuristic classification based on user planning thresholds.",
    thresholds_applied: {
      min_roi_low_risk: "25.0",
      min_margin_safety_low_risk: "20.0",
    },
    factors: {
      net_profit: "170000.00",
      roi_percentage: "94.44",
      breakeven_price_lkr_per_kg: "72.00",
      margin_of_safety_percentage: "48.57",
      selling_price_lkr_per_kg: "140.00",
      expected_yield_kg: "2500.00",
      total_cultivation_cost: "180000.00",
      trigger_rule: "ROI >= 25.0% and Margin of Safety >= 20.0%",
      trigger_rationale: "ROI exceeds requirement and margin of safety provides cushion.",
    },
    profit_calculation: {
      expected_yield_kg: "2500.00",
      selling_price_lkr_per_kg: "140.00",
      total_cultivation_cost: "180000.00",
      gross_revenue: "350000.00",
      net_profit: "170000.00",
      roi_percentage: "94.44",
      breakeven_price_lkr_per_kg: "72.00",
      margin_of_safety_percentage: "48.57",
      currency: "LKR",
      price_source: "farmer_assumption",
      is_manual_price_assumption: true,
      assumptions_note: "Selling price is user assumption.",
      calculation_notes: null,
    },
  };

  const client = new MarketProfitApiClient({
    transport: async () => new Response(JSON.stringify(mockResponse), { status: 200 }),
  });

  const res = await client.assessProfitRisk({
    expected_yield_kg: "2500.00",
    selling_price_lkr_per_kg: "140.00",
    total_cultivation_cost: "180000.00",
  });

  assert.equal(res.risk_level, "Low");
  assert.equal(res.assessment_type, "rule_based_heuristic");
  assert.equal(res.is_ml_prediction, false);
  assert.ok(res.disclaimer.includes("Preliminary rule-based heuristic"));
});

test("API Client: Handles FastAPI 422 validation errors with field extraction", async () => {
  const errorResponse = {
    detail: [
      {
        loc: ["body", "expected_yield_kg"],
        msg: "expected_yield_kg must be greater than zero.",
        type: "value_error",
      },
      {
        loc: ["body", "selling_price_lkr_per_kg"],
        msg: "selling_price_lkr_per_kg must be greater than zero.",
        type: "value_error",
      },
    ],
  };

  const client = new MarketProfitApiClient({
    transport: async () => new Response(JSON.stringify(errorResponse), { status: 422 }),
  });

  await assert.rejects(
    async () => {
      await client.calculateProfit({
        expected_yield_kg: 0,
        selling_price_lkr_per_kg: 0,
      });
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiError);
      assert.equal(err.status, 422);
      assert.ok(err.message.includes("highlighted below"));
      assert.ok(err.fieldErrors["expected_yield_kg"].includes("greater than zero"));
      assert.ok(err.fieldErrors["selling_price_lkr_per_kg"].includes("greater than zero"));
      return true;
    }
  );
});

test("API Client: Handles backend network failure with port 8001 notice", async () => {
  const client = new MarketProfitApiClient({
    transport: async () => {
      throw new Error("ECONNREFUSED");
    },
  });

  await assert.rejects(
    async () => {
      await client.getDemandForecast({
        crop_id: "CR_TOMATO",
        cultivation_district_id: "LK-32",
        target_market_id: "DEC_EMBILIPITIYA",
        forecast_target_date: "2026-12-15",
      });
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiError);
      assert.equal(err.status, 0);
      assert.ok(err.message.includes("port 8001"));
      return true;
    }
  );
});

test("API Client: evaluateComprehensiveFarmerPlan executes all 4 endpoints concurrently", async () => {
  const client = new MarketProfitApiClient({
    transport: async (url) => {
      const u = String(url);
      if (u.includes("forecast") && u.includes("market-demands")) {
        return new Response(
          JSON.stringify({
            crop_id: "CR_TOMATO",
            cultivation_district_id: "LK-32",
            target_market_id: "DEC_EMBILIPITIYA",
            forecast_target_date: "2026-12-15",
            prediction_status: "unavailable",
            projected_demand_volume_kg: null,
            projected_demand_level: null,
            status_message: "ML model offline",
          }),
          { status: 200 }
        );
      }
      if (u.includes("forecast") && u.includes("market-prices")) {
        return new Response(
          JSON.stringify({
            crop_id: "CR_TOMATO",
            cultivation_district_id: "LK-32",
            target_market_id: "DEC_EMBILIPITIYA",
            forecast_target_date: "2026-12-15",
            price_type: "wholesale",
            currency: "LKR",
            unit: "kg",
            prediction_status: "unavailable",
            forecasted_price_lkr_per_kg: null,
            status_message: "ML model offline",
          }),
          { status: 200 }
        );
      }
      if (u.includes("calculate")) {
        return new Response(
          JSON.stringify({
            expected_yield_kg: "2500.00",
            selling_price_lkr_per_kg: "140.00",
            total_cultivation_cost: "180000.00",
            gross_revenue: "350000.00",
            net_profit: "170000.00",
            roi_percentage: "94.44",
            breakeven_price_lkr_per_kg: "72.00",
            margin_of_safety_percentage: "48.57",
            currency: "LKR",
            price_source: "farmer_assumption",
            is_manual_price_assumption: true,
            assumptions_note: "User assumption",
            calculation_notes: null,
          }),
          { status: 200 }
        );
      }
      if (u.includes("assess-risk")) {
        return new Response(
          JSON.stringify({
            risk_level: "Low",
            assessment_type: "rule_based_heuristic",
            is_ml_prediction: false,
            disclaimer: "Preliminary heuristic",
            thresholds_applied: { min_roi_low_risk: "25.0", min_margin_safety_low_risk: "20.0" },
            factors: {
              net_profit: "170000.00",
              roi_percentage: "94.44",
              breakeven_price_lkr_per_kg: "72.00",
              margin_of_safety_percentage: "48.57",
              selling_price_lkr_per_kg: "140.00",
              expected_yield_kg: "2500.00",
              total_cultivation_cost: "180000.00",
              trigger_rule: "Low risk threshold met",
              trigger_rationale: "Good margin",
            },
            profit_calculation: {
              expected_yield_kg: "2500.00",
              selling_price_lkr_per_kg: "140.00",
              total_cultivation_cost: "180000.00",
              gross_revenue: "350000.00",
              net_profit: "170000.00",
              roi_percentage: "94.44",
              breakeven_price_lkr_per_kg: "72.00",
              margin_of_safety_percentage: "48.57",
              currency: "LKR",
              price_source: "farmer_assumption",
              is_manual_price_assumption: true,
              assumptions_note: "User assumption",
              calculation_notes: null,
            },
          }),
          { status: 200 }
        );
      }
      return new Response("Not found", { status: 404 });
    },
  });

  const scenario: FarmerPlanningScenario = {
    crop_id: "CR_TOMATO",
    cultivation_district_id: "LK-32",
    target_market_id: "DEC_EMBILIPITIYA",
    forecast_target_date: "2026-12-15",
    price_type: "wholesale",
    land_extent_acres: 2.0,
    expected_yield_kg: 2500,
    selling_price_lkr_per_kg: 140,
    budget_mode: "quick",
    total_cultivation_cost: 180000,
  };

  const result = await client.evaluateComprehensiveFarmerPlan(scenario);

  assert.equal(result.scenario.crop_id, "CR_TOMATO");
  assert.equal(result.demandForecast.prediction_status, "unavailable");
  assert.equal(result.priceForecast.prediction_status, "unavailable");
  assert.equal(result.profitCalculation.net_profit, "170000.00");
  assert.equal(result.profitRisk.risk_level, "Low");
  assert.ok(result.evaluated_at);
});

// ============================================================================
// 5. Step 1 Wizard Validation & Selection Logic Tests
// ============================================================================

test("Wizard Step 1: Validates complete selection with supported crop and district", () => {
  const result = validateStep1({
    crop_id: "CR_OKRA",
    cultivation_district_id: "LK-32",
  });
  assert.equal(result.isValid, true);
  assert.equal(result.errors.crop_id, undefined);
  assert.equal(result.errors.cultivation_district_id, undefined);
});

test("Wizard Step 1: Detects missing crop and provides clear error", () => {
  const result = validateStep1({
    crop_id: "",
    cultivation_district_id: "LK-32",
  });
  assert.equal(result.isValid, false);
  assert.equal(result.errors.crop_id, "Please select a crop to proceed with the analysis.");
  assert.equal(result.errors.cultivation_district_id, undefined);
});

test("Wizard Step 1: Detects missing cultivation district and provides clear error", () => {
  const result = validateStep1({
    crop_id: "CR_MAIZE",
    cultivation_district_id: "",
  });
  assert.equal(result.isValid, false);
  assert.equal(result.errors.crop_id, undefined);
  assert.equal(result.errors.cultivation_district_id, "Please select a cultivation district in Sri Lanka.");
});

test("Wizard Step 1: Rejects excluded Tomato (CR_TOMATO) from frontend active catalog", () => {
  const result = validateStep1({
    crop_id: "CR_TOMATO",
    cultivation_district_id: "LK-33",
  });
  assert.equal(result.isValid, false);
  assert.equal(
    result.errors.crop_id,
    "The selected crop is not part of the active 6-crop pilot catalog."
  );
});

test("Wizard Step 1: Rejects unrecognized district code", () => {
  const result = validateStep1({
    crop_id: "CR_PUMPKIN",
    cultivation_district_id: "LK-999",
  });
  assert.equal(result.isValid, false);
  assert.equal(
    result.errors.cultivation_district_id,
    "The selected district code is not recognized in Sri Lanka districts."
  );
});

test("Wizard Step 1: All 6 supported frontend crops pass validation with pilot districts", () => {
  const pilotDistricts = ["LK-32", "LK-33"];
  for (const crop of SUPPORTED_FRONTEND_CROPS) {
    for (const districtId of pilotDistricts) {
      const result = validateStep1({
        crop_id: crop.crop_id,
        cultivation_district_id: districtId,
      });
      assert.equal(result.isValid, true, `Crop ${crop.crop_id} failed in district ${districtId}`);
    }
  }
});
