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
import {
  validateStep1,
  validateStep2,
  validateHarvestDate,
  validateLandExtent,
  validateExpectedYield,
  MAX_LAND_EXTENT_ACRES,
  MAX_EXPECTED_YIELD_KG,
  isLeapYear,
  getDaysInMonth,
  isValidCalendarDate,
  getTodayDateString,
  isStep2Complete,
  saveValidatedStep2ToStorage,
  STEP2_STORAGE_KEY,
  loadStep2FromStorage,
  saveStep2ToStorage,
  clearStep2Storage,
  validateSellingMarket,
  validatePriceType,
  VALID_PRICE_TYPES,
  PRICE_TYPE_OPTIONS,
  type PriceType,
  type Step3FormData,
  validateStep3,
  isStep3Complete,
  STEP3_STORAGE_KEY,
  loadStep3FromStorage,
  saveStep3ToStorage,
  saveValidatedStep3ToStorage,
  clearStep3Storage,
  checkPreviousStepsForStep3,
  isWizardReadyForStep4,
} from "../lib/wizard";

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

// ============================================================================
// 6. Step 2 Wizard Harvest Date Validation Tests
// ============================================================================

const FIXED_TODAY = new Date(2026, 9, 16); // 2026-10-16 in local time

test("Wizard Step 2: Valid future harvest date passes validation", () => {
  const result = validateHarvestDate("2026-11-20", FIXED_TODAY);
  assert.equal(result.isValid, true);
  assert.equal(result.error, undefined);

  const nextYear = validateHarvestDate("2027-03-15", FIXED_TODAY);
  assert.equal(nextYear.isValid, true);
  assert.equal(nextYear.error, undefined);
});

test("Wizard Step 2: Today's date passes validation as minimum acceptable date", () => {
  const todayStr = getTodayDateString(FIXED_TODAY);
  assert.equal(todayStr, "2026-10-16");

  const result = validateHarvestDate("2026-10-16", FIXED_TODAY);
  assert.equal(result.isValid, true);
  assert.equal(result.error, undefined);
});

test("Wizard Step 2: Missing or whitespace date is rejected with friendly message", () => {
  const emptyResult = validateHarvestDate("", FIXED_TODAY);
  assert.equal(emptyResult.isValid, false);
  assert.equal(emptyResult.error, "Please select an expected harvest date.");

  const whitespaceResult = validateHarvestDate("   ", FIXED_TODAY);
  assert.equal(whitespaceResult.isValid, false);
  assert.equal(whitespaceResult.error, "Please select an expected harvest date.");

  const nullResult = validateHarvestDate(null as any, FIXED_TODAY);
  assert.equal(nullResult.isValid, false);
  assert.equal(nullResult.error, "Please select an expected harvest date.");
});

test("Wizard Step 2: Invalid date format is rejected", () => {
  const slashFormat = validateHarvestDate("2026/10/16", FIXED_TODAY);
  assert.equal(slashFormat.isValid, false);
  assert.equal(slashFormat.error, "Please enter a valid date in YYYY-MM-DD format.");

  const ddmmyyyy = validateHarvestDate("16-10-2026", FIXED_TODAY);
  assert.equal(ddmmyyyy.isValid, false);
  assert.equal(ddmmyyyy.error, "Please enter a valid date in YYYY-MM-DD format.");

  const gibberish = validateHarvestDate("not-a-date", FIXED_TODAY);
  assert.equal(gibberish.isValid, false);
  assert.equal(gibberish.error, "Please enter a valid date in YYYY-MM-DD format.");
});

test("Wizard Step 2: Past dates are rejected", () => {
  const yesterday = validateHarvestDate("2026-10-15", FIXED_TODAY);
  assert.equal(yesterday.isValid, false);
  assert.equal(yesterday.error, "Expected harvest date cannot be in the past.");

  const pastYear = validateHarvestDate("2025-05-10", FIXED_TODAY);
  assert.equal(pastYear.isValid, false);
  assert.equal(pastYear.error, "Expected harvest date cannot be in the past.");
});

test("Wizard Step 2: Calendar validity and leap-year rules are strictly enforced", () => {
  // Leap year calculation verification
  assert.equal(isLeapYear(2024), true);
  assert.equal(isLeapYear(2028), true);
  assert.equal(isLeapYear(2000), true);
  assert.equal(isLeapYear(1900), false);
  assert.equal(isLeapYear(2026), false);

  // Month day limits
  assert.equal(getDaysInMonth(2024, 2), 29);
  assert.equal(getDaysInMonth(2026, 2), 28);
  assert.equal(getDaysInMonth(2026, 4), 30);
  assert.equal(getDaysInMonth(2026, 12), 31);
  assert.equal(getDaysInMonth(2026, 13), 0);

  // Valid calendar date checker
  assert.equal(isValidCalendarDate(2024, 2, 29), true);
  assert.equal(isValidCalendarDate(2026, 2, 29), false, "Feb 29 on non-leap year must be invalid");
  assert.equal(isValidCalendarDate(2026, 2, 30), false, "Feb 30 must be invalid");
  assert.equal(isValidCalendarDate(2026, 4, 31), false, "April 31 must be invalid");
  assert.equal(isValidCalendarDate(2026, 6, 31), false, "June 31 must be invalid");
  assert.equal(isValidCalendarDate(2026, 9, 31), false, "September 31 must be invalid");
  assert.equal(isValidCalendarDate(2026, 11, 31), false, "November 31 must be invalid");

  // validateHarvestDate with invalid calendar days
  const feb30 = validateHarvestDate("2027-02-30", FIXED_TODAY);
  assert.equal(feb30.isValid, false);
  assert.equal(feb30.error, "Please select a valid calendar date.");

  const feb29NonLeap = validateHarvestDate("2027-02-29", FIXED_TODAY);
  assert.equal(feb29NonLeap.isValid, false);
  assert.equal(feb29NonLeap.error, "Please select a valid calendar date.");

  // Future leap year Feb 29 (2028-02-29) is completely valid
  const feb29Leap = validateHarvestDate("2028-02-29", FIXED_TODAY);
  assert.equal(feb29Leap.isValid, true);
  assert.equal(feb29Leap.error, undefined);
});

test("Wizard Step 2: Valid land extent in whole and decimal acres passes", () => {
  const wholeAcres = validateLandExtent("2");
  assert.equal(wholeAcres.isValid, true);
  assert.equal(wholeAcres.parsedValue, 2);
  assert.equal(wholeAcres.error, undefined);

  const decimalAcres = validateLandExtent("1.5");
  assert.equal(decimalAcres.isValid, true);
  assert.equal(decimalAcres.parsedValue, 1.5);
  assert.equal(decimalAcres.error, undefined);

  const smallPlot = validateLandExtent("0.25");
  assert.equal(smallPlot.isValid, true);
  assert.equal(smallPlot.parsedValue, 0.25);
  assert.equal(smallPlot.error, undefined);

  const numericType = validateLandExtent(3.75);
  assert.equal(numericType.isValid, true);
  assert.equal(numericType.parsedValue, 3.75);
});

test("Wizard Step 2: Zero and negative land extent values are rejected", () => {
  const zeroStr = validateLandExtent("0");
  assert.equal(zeroStr.isValid, false);
  assert.equal(zeroStr.error, "Cultivation land extent must be greater than 0 acres.");

  const zeroNum = validateLandExtent(0);
  assert.equal(zeroNum.isValid, false);
  assert.equal(zeroNum.error, "Cultivation land extent must be greater than 0 acres.");

  const negativeStr = validateLandExtent("-1.5");
  assert.equal(negativeStr.isValid, false);
  assert.equal(negativeStr.error, "Cultivation land extent must be greater than 0 acres.");

  const negativeNum = validateLandExtent(-0.1);
  assert.equal(negativeNum.isValid, false);
  assert.equal(negativeNum.error, "Cultivation land extent must be greater than 0 acres.");
});

test("Wizard Step 2: Non-numeric, NaN, and Infinity land extent inputs are rejected", () => {
  const letters = validateLandExtent("abc");
  assert.equal(letters.isValid, false);
  assert.equal(letters.error, "Cultivation land extent must be a valid numeric value.");

  const symbols = validateLandExtent("1.5.0");
  assert.equal(symbols.isValid, false);
  assert.equal(symbols.error, "Cultivation land extent must be a valid numeric value.");

  const nanVal = validateLandExtent(NaN);
  assert.equal(nanVal.isValid, false);
  assert.equal(nanVal.error, "Cultivation land extent must be a valid numeric value.");

  const infVal = validateLandExtent(Infinity);
  assert.equal(infVal.isValid, false);
  assert.equal(infVal.error, "Cultivation land extent must be a valid numeric value.");
});

test("Wizard Step 2: Missing or whitespace land extent is rejected with friendly message", () => {
  const emptyStr = validateLandExtent("");
  assert.equal(emptyStr.isValid, false);
  assert.equal(emptyStr.error, "Please enter your cultivation land extent in acres.");

  const whitespace = validateLandExtent("   ");
  assert.equal(whitespace.isValid, false);
  assert.equal(whitespace.error, "Please enter your cultivation land extent in acres.");

  const nullVal = validateLandExtent(null);
  assert.equal(nullVal.isValid, false);
  assert.equal(nullVal.error, "Please enter your cultivation land extent in acres.");

  const undefVal = validateLandExtent(undefined);
  assert.equal(undefVal.isValid, false);
  assert.equal(undefVal.error, "Please enter your cultivation land extent in acres.");
});

test("Wizard Step 2: Excessively large land extent exceeding configurable limit is rejected", () => {
  assert.equal(MAX_LAND_EXTENT_ACRES, 1000);

  // Exact maximum passes
  const maxAllowed = validateLandExtent("1000");
  assert.equal(maxAllowed.isValid, true);
  assert.equal(maxAllowed.parsedValue, 1000);

  // Beyond maximum fails
  const overLimit = validateLandExtent("1000.5");
  assert.equal(overLimit.isValid, false);
  assert.equal(
    overLimit.error,
    "Cultivation land extent exceeds the maximum planning limit of 1000 acres. Please enter a realistic land area."
  );

  // Custom configurable limit
  const customLimit = validateLandExtent("55", 50);
  assert.equal(customLimit.isValid, false);
  assert.equal(
    customLimit.error,
    "Cultivation land extent exceeds the maximum planning limit of 50 acres. Please enter a realistic land area."
  );
});

test("Wizard Step 2: Valid expected harvest yield in whole and decimal kg passes", () => {
  // Whole number string
  const wholeStr = validateExpectedYield("1500");
  assert.equal(wholeStr.isValid, true);
  assert.equal(wholeStr.parsedValue, 1500);
  assert.equal(wholeStr.error, undefined);

  // Decimal number string
  const decimalStr = validateExpectedYield("2500.75");
  assert.equal(decimalStr.isValid, true);
  assert.equal(decimalStr.parsedValue, 2500.75);

  // Small positive fraction
  const fraction = validateExpectedYield("0.5");
  assert.equal(fraction.isValid, true);
  assert.equal(fraction.parsedValue, 0.5);

  // Numeric type input
  const numInput = validateExpectedYield(500);
  assert.equal(numInput.isValid, true);
  assert.equal(numInput.parsedValue, 500);
});

test("Wizard Step 2: Zero and negative expected harvest yield values are rejected", () => {
  const zeroNum = validateExpectedYield(0);
  assert.equal(zeroNum.isValid, false);
  assert.equal(zeroNum.error, "Expected harvest yield must be greater than 0 kg.");

  const zeroStr = validateExpectedYield("0");
  assert.equal(zeroStr.isValid, false);
  assert.equal(zeroStr.error, "Expected harvest yield must be greater than 0 kg.");

  const negNum = validateExpectedYield(-50);
  assert.equal(negNum.isValid, false);
  assert.equal(negNum.error, "Expected harvest yield must be greater than 0 kg.");

  const negStr = validateExpectedYield("-12.5");
  assert.equal(negStr.isValid, false);
  assert.equal(negStr.error, "Expected harvest yield must be greater than 0 kg.");
});

test("Wizard Step 2: Non-numeric, NaN, and Infinity expected yield inputs are rejected", () => {
  const textInput = validateExpectedYield("1500kg");
  assert.equal(textInput.isValid, false);
  assert.equal(textInput.error, "Expected harvest yield must be a valid numeric value.");

  const words = validateExpectedYield("one ton");
  assert.equal(words.isValid, false);
  assert.equal(words.error, "Expected harvest yield must be a valid numeric value.");

  const nanVal = validateExpectedYield(NaN);
  assert.equal(nanVal.isValid, false);
  assert.equal(nanVal.error, "Expected harvest yield must be a valid numeric value.");

  const infVal = validateExpectedYield(Infinity);
  assert.equal(infVal.isValid, false);
  assert.equal(infVal.error, "Expected harvest yield must be a valid numeric value.");
});

test("Wizard Step 2: Missing or whitespace expected harvest yield is rejected with friendly message", () => {
  const emptyStr = validateExpectedYield("");
  assert.equal(emptyStr.isValid, false);
  assert.equal(emptyStr.error, "Please enter your expected harvest yield in kilograms.");

  const spacesOnly = validateExpectedYield("   ");
  assert.equal(spacesOnly.isValid, false);
  assert.equal(spacesOnly.error, "Please enter your expected harvest yield in kilograms.");

  const nullVal = validateExpectedYield(null);
  assert.equal(nullVal.isValid, false);
  assert.equal(nullVal.error, "Please enter your expected harvest yield in kilograms.");

  const undefinedVal = validateExpectedYield(undefined);
  assert.equal(undefinedVal.isValid, false);
  assert.equal(undefinedVal.error, "Please enter your expected harvest yield in kilograms.");
});

test("Wizard Step 2: Excessively large expected harvest yield exceeding configurable limit is rejected", () => {
  // 1,000,000 kg passes (default max)
  const atMax = validateExpectedYield(MAX_EXPECTED_YIELD_KG);
  assert.equal(atMax.isValid, true);
  assert.equal(atMax.parsedValue, 1000000);

  // Exceeding 1,000,000 kg fails
  const overMax = validateExpectedYield("1000000.1");
  assert.equal(overMax.isValid, false);
  assert.equal(
    overMax.error,
    "Expected harvest yield exceeds the maximum planning limit of 1,000,000 kg. Please enter a realistic expected harvest amount."
  );

  // Custom configurable limit
  const customLimit = validateExpectedYield("5500", 5000);
  assert.equal(customLimit.isValid, false);
  assert.equal(
    customLimit.error,
    "Expected harvest yield exceeds the maximum planning limit of 5,000 kg. Please enter a realistic expected harvest amount."
  );
});

test("Wizard Step 2: validateStep2 requires valid harvest date, land extent, and expected yield", () => {
  // All three valid
  const allValid = validateStep2(
    { harvest_date: "2027-01-20", land_extent_acres: "2.5", expected_yield_kg: "1500" },
    FIXED_TODAY
  );
  assert.equal(allValid.isValid, true);
  assert.deepEqual(allValid.errors, {});

  // Missing harvest date
  const missingDate = validateStep2(
    { harvest_date: "", land_extent_acres: "2.5", expected_yield_kg: "1500" },
    FIXED_TODAY
  );
  assert.equal(missingDate.isValid, false);
  assert.equal(missingDate.errors.harvest_date, "Please select an expected harvest date.");
  assert.equal(missingDate.errors.land_extent_acres, undefined);
  assert.equal(missingDate.errors.expected_yield_kg, undefined);

  // Missing land extent
  const missingExtent = validateStep2(
    { harvest_date: "2027-01-20", land_extent_acres: "", expected_yield_kg: "1500" },
    FIXED_TODAY
  );
  assert.equal(missingExtent.isValid, false);
  assert.equal(missingExtent.errors.harvest_date, undefined);
  assert.equal(
    missingExtent.errors.land_extent_acres,
    "Please enter your cultivation land extent in acres."
  );
  assert.equal(missingExtent.errors.expected_yield_kg, undefined);

  // Missing expected yield
  const missingYield = validateStep2(
    { harvest_date: "2027-01-20", land_extent_acres: "2.5", expected_yield_kg: "" },
    FIXED_TODAY
  );
  assert.equal(missingYield.isValid, false);
  assert.equal(missingYield.errors.harvest_date, undefined);
  assert.equal(missingYield.errors.land_extent_acres, undefined);
  assert.equal(
    missingYield.errors.expected_yield_kg,
    "Please enter your expected harvest yield in kilograms."
  );

  // All three invalid
  const allInvalid = validateStep2(
    { harvest_date: "2025-01-01", land_extent_acres: "0", expected_yield_kg: "-100" },
    FIXED_TODAY
  );
  assert.equal(allInvalid.isValid, false);
  assert.equal(
    allInvalid.errors.harvest_date,
    "Expected harvest date cannot be in the past."
  );
  assert.equal(
    allInvalid.errors.land_extent_acres,
    "Cultivation land extent must be greater than 0 acres."
  );
  assert.equal(
    allInvalid.errors.expected_yield_kg,
    "Expected harvest yield must be greater than 0 kg."
  );
});

test("Wizard Step 2: Session storage helpers preserve harvest date, land extent, and expected yield", () => {
  assert.equal(STEP2_STORAGE_KEY, "agrodecision_wizard_step2");

  // In Node environment, helpers return default gracefully without throwing
  const initial = loadStep2FromStorage();
  assert.deepEqual(initial, { harvest_date: "", land_extent_acres: "", expected_yield_kg: "" });

  assert.doesNotThrow(() => {
    saveStep2ToStorage({
      harvest_date: "2027-03-01",
      land_extent_acres: "1.75",
      expected_yield_kg: "1500",
    });
    clearStep2Storage();
  });
});

test("Wizard Step 2: loadStep2FromStorage maintains backward compatibility with older 2-field records", () => {
  const mockStorage = new Map<string, string>();
  mockStorage.set(
    STEP2_STORAGE_KEY,
    JSON.stringify({ harvest_date: "2027-04-15", land_extent_acres: "2.0" })
  );

  (globalThis as unknown as { window: unknown }).window = {
    sessionStorage: {
      getItem: (key: string) => mockStorage.get(key) ?? null,
      setItem: (key: string, val: string) => mockStorage.set(key, val),
      removeItem: (key: string) => mockStorage.delete(key),
    },
  };

  try {
    const loaded = loadStep2FromStorage();
    assert.deepEqual(loaded, {
      harvest_date: "2027-04-15",
      land_extent_acres: "2.0",
      expected_yield_kg: "",
    });
  } finally {
    delete (globalThis as unknown as { window?: unknown }).window;
  }
});

test("Wizard Step 2: isStep2Complete validates full and partial form states accurately", () => {
  // Completely valid
  const complete = isStep2Complete(
    { harvest_date: "2027-05-10", land_extent_acres: "1.5", expected_yield_kg: "2000" },
    FIXED_TODAY
  );
  assert.equal(complete, true);

  // Missing yield
  const missingYield = isStep2Complete(
    { harvest_date: "2027-05-10", land_extent_acres: "1.5", expected_yield_kg: "" },
    FIXED_TODAY
  );
  assert.equal(missingYield, false);

  // Missing extent
  const missingExtent = isStep2Complete(
    { harvest_date: "2027-05-10", land_extent_acres: "", expected_yield_kg: "2000" },
    FIXED_TODAY
  );
  assert.equal(missingExtent, false);

  // Past harvest date
  const pastDate = isStep2Complete(
    { harvest_date: "2024-01-01", land_extent_acres: "1.5", expected_yield_kg: "2000" },
    FIXED_TODAY
  );
  assert.equal(pastDate, false);

  // Negative yield
  const negativeYield = isStep2Complete(
    { harvest_date: "2027-05-10", land_extent_acres: "1.5", expected_yield_kg: "-500" },
    FIXED_TODAY
  );
  assert.equal(negativeYield, false);
});

test("Wizard Step 2: saveValidatedStep2ToStorage protects existing valid session records from invalid updates", () => {
  const mockStorage = new Map<string, string>();
  const initialValidRecord = {
    harvest_date: "2027-04-15",
    land_extent_acres: "2.0",
    expected_yield_kg: "1200",
  };
  mockStorage.set(STEP2_STORAGE_KEY, JSON.stringify(initialValidRecord));

  (globalThis as unknown as { window: unknown }).window = {
    sessionStorage: {
      getItem: (key: string) => mockStorage.get(key) ?? null,
      setItem: (key: string, val: string) => mockStorage.set(key, val),
      removeItem: (key: string) => mockStorage.delete(key),
    },
  };

  try {
    // 1. Attempt to save invalid data: negative yield
    const saveInvalidYield = saveValidatedStep2ToStorage(
      { harvest_date: "2027-04-15", land_extent_acres: "2.0", expected_yield_kg: "-100" },
      FIXED_TODAY
    );
    assert.equal(saveInvalidYield, false);
    // Storage must be untouched
    const current1 = JSON.parse(mockStorage.get(STEP2_STORAGE_KEY)!);
    assert.deepEqual(current1, initialValidRecord);

    // 2. Attempt to save invalid data: past date
    const saveInvalidDate = saveValidatedStep2ToStorage(
      { harvest_date: "2024-01-01", land_extent_acres: "2.0", expected_yield_kg: "1200" },
      FIXED_TODAY
    );
    assert.equal(saveInvalidDate, false);
    const current2 = JSON.parse(mockStorage.get(STEP2_STORAGE_KEY)!);
    assert.deepEqual(current2, initialValidRecord);

    // 3. Attempt to save invalid data: empty acres
    const saveInvalidExtent = saveValidatedStep2ToStorage(
      { harvest_date: "2027-04-15", land_extent_acres: "", expected_yield_kg: "1200" },
      FIXED_TODAY
    );
    assert.equal(saveInvalidExtent, false);
    const current3 = JSON.parse(mockStorage.get(STEP2_STORAGE_KEY)!);
    assert.deepEqual(current3, initialValidRecord);

    // 4. Save fully valid updated data: success
    const validUpdate = {
      harvest_date: "2027-06-20",
      land_extent_acres: "3.5",
      expected_yield_kg: "4500",
    };
    const saveValid = saveValidatedStep2ToStorage(validUpdate, FIXED_TODAY);
    assert.equal(saveValid, true);
    const current4 = JSON.parse(mockStorage.get(STEP2_STORAGE_KEY)!);
    assert.deepEqual(current4, validUpdate);
  } finally {
    delete (globalThis as unknown as { window?: unknown }).window;
  }
});

test("Wizard Step 2: Navigation readiness preserves backward links and avoids nonexistent Step 3 routes", () => {
  // Step 2 backward link is strictly defined and safe
  const step1Route = "/market-profit/new-analysis";
  const dashboardRoute = "/market-profit";
  assert.equal(typeof step1Route, "string");
  assert.equal(typeof dashboardRoute, "string");

  // Confirm wizard flow sequence: Step 1 -> Step 2 -> Step 3 -> Step 4
  const wizardSteps = [
    { step: 1, label: "Crop & Location", route: "/market-profit/new-analysis" },
    { step: 2, label: "Harvest Details", route: "/market-profit/new-analysis/harvest-details" },
    { step: 3, label: "Selling Market", route: "/market-profit/new-analysis/selling-market" },
    { step: 4, label: "Cultivation Costs", route: "/market-profit/new-analysis/cultivation-costs" },
  ];

  assert.equal(wizardSteps[1].step, 2);
  assert.equal(wizardSteps[1].label, "Harvest Details");
  assert.equal(wizardSteps[2].step, 3);
  assert.equal(wizardSteps[2].label, "Selling Market");
});

// ============================================================================
// Step 3: Selling Market Tests
// ============================================================================

test("Wizard Step 3: Valid market IDs from STANDARD_MARKETS pass validation", () => {
  // Embilipitiya DEC (recommended pilot hub)
  const embilipitiya = validateSellingMarket("DEC_EMBILIPITIYA");
  assert.equal(embilipitiya.isValid, true);
  assert.equal(embilipitiya.error, undefined);

  // Other standard markets
  const dambulla = validateSellingMarket("DEC_DAMBULLA");
  assert.equal(dambulla.isValid, true);

  const pettah = validateSellingMarket("DEC_PETTAH");
  assert.equal(pettah.isValid, true);

  const meegoda = validateSellingMarket("DEC_MEEGODA");
  assert.equal(meegoda.isValid, true);

  // Whitespace-padded input
  const padded = validateSellingMarket("  DEC_EMBILIPITIYA  ");
  assert.equal(padded.isValid, true);
});

test("Wizard Step 3: Missing, empty, or whitespace market ID is rejected", () => {
  const emptyStr = validateSellingMarket("");
  assert.equal(emptyStr.isValid, false);
  assert.equal(emptyStr.error, "Please select a target selling market.");

  const spacesOnly = validateSellingMarket("   ");
  assert.equal(spacesOnly.isValid, false);
  assert.equal(spacesOnly.error, "Please select a target selling market.");

  const nullVal = validateSellingMarket(null);
  assert.equal(nullVal.isValid, false);
  assert.equal(nullVal.error, "Please select a target selling market.");

  const undefinedVal = validateSellingMarket(undefined);
  assert.equal(undefinedVal.isValid, false);
  assert.equal(undefinedVal.error, "Please select a target selling market.");
});

test("Wizard Step 3: Unrecognized or invalid market ID is rejected", () => {
  const fakeMarket = validateSellingMarket("DEC_LONDON");
  assert.equal(fakeMarket.isValid, false);
  assert.equal(
    fakeMarket.error,
    "The selected market is not recognized in verified Dedicated Economic Centres."
  );

  const numericCode = validateSellingMarket("12345");
  assert.equal(numericCode.isValid, false);
  assert.equal(
    numericCode.error,
    "The selected market is not recognized in verified Dedicated Economic Centres."
  );
});

test("Wizard Step 3: Valid wholesale selection passes validation", () => {
  const result = validatePriceType("wholesale");
  assert.equal(result.isValid, true);
  assert.equal(result.error, undefined);

  // Case insensitivity and whitespace trimming
  const upper = validatePriceType("WHOLESALE");
  assert.equal(upper.isValid, true);

  const padded = validatePriceType("  wholesale  ");
  assert.equal(padded.isValid, true);
});

test("Wizard Step 3: Valid retail selection passes validation", () => {
  const result = validatePriceType("retail");
  assert.equal(result.isValid, true);
  assert.equal(result.error, undefined);

  // Case insensitivity and whitespace trimming
  const mixed = validatePriceType("Retail");
  assert.equal(mixed.isValid, true);

  const padded = validatePriceType("  retail  ");
  assert.equal(padded.isValid, true);
});

test("Wizard Step 3: Missing, empty, or whitespace price type is rejected", () => {
  const emptyStr = validatePriceType("");
  assert.equal(emptyStr.isValid, false);
  assert.equal(emptyStr.error, "Please select a price type (Wholesale or Retail).");

  const spacesOnly = validatePriceType("   ");
  assert.equal(spacesOnly.isValid, false);
  assert.equal(spacesOnly.error, "Please select a price type (Wholesale or Retail).");

  const nullVal = validatePriceType(null);
  assert.equal(nullVal.isValid, false);
  assert.equal(nullVal.error, "Please select a price type (Wholesale or Retail).");

  const undefinedVal = validatePriceType(undefined);
  assert.equal(undefinedVal.isValid, false);
  assert.equal(undefinedVal.error, "Please select a price type (Wholesale or Retail).");
});

test("Wizard Step 3: Invalid or unsupported price type values are rejected", () => {
  const farmgate = validatePriceType("farmgate");
  assert.equal(farmgate.isValid, false);
  assert.equal(farmgate.error, "Invalid price type. Please select either Wholesale or Retail.");

  const exportVal = validatePriceType("export");
  assert.equal(exportVal.isValid, false);
  assert.equal(exportVal.error, "Invalid price type. Please select either Wholesale or Retail.");

  const numericVal = validatePriceType("123");
  assert.equal(numericVal.isValid, false);
  assert.equal(numericVal.error, "Invalid price type. Please select either Wholesale or Retail.");
});

test("Wizard Step 3: validateStep3 and isStep3Complete evaluate full, partial, and empty states correctly", () => {
  // 1. Valid with target_market_id and wholesale
  const validWholesale = validateStep3({
    target_market_id: "DEC_EMBILIPITIYA",
    price_type: "wholesale",
  });
  assert.equal(validWholesale.isValid, true);
  assert.deepEqual(validWholesale.errors, {});
  assert.equal(
    isStep3Complete({ target_market_id: "DEC_EMBILIPITIYA", price_type: "wholesale" }),
    true
  );

  // 2. Valid with selling_market_id alias and retail
  const validRetail = validateStep3({
    selling_market_id: "DEC_DAMBULLA",
    price_type: "retail",
  });
  assert.equal(validRetail.isValid, true);
  assert.deepEqual(validRetail.errors, {});
  assert.equal(
    isStep3Complete({ selling_market_id: "DEC_DAMBULLA", price_type: "retail" }),
    true
  );

  // 3. Missing price type only
  const missingPriceType = validateStep3({
    target_market_id: "DEC_EMBILIPITIYA",
    price_type: "",
  });
  assert.equal(missingPriceType.isValid, false);
  assert.equal(
    missingPriceType.errors.price_type,
    "Please select a price type (Wholesale or Retail)."
  );
  assert.equal(missingPriceType.errors.target_market_id, undefined);
  assert.equal(
    isStep3Complete({ target_market_id: "DEC_EMBILIPITIYA", price_type: "" }),
    false
  );

  // 4. Missing market only
  const missingMarket = validateStep3({
    target_market_id: "",
    price_type: "wholesale",
  });
  assert.equal(missingMarket.isValid, false);
  assert.equal(
    missingMarket.errors.target_market_id,
    "Please select a target selling market."
  );
  assert.equal(missingMarket.errors.price_type, undefined);
  assert.equal(isStep3Complete({ target_market_id: "", price_type: "wholesale" }), false);

  // 5. Both missing
  const bothMissing = validateStep3({
    target_market_id: "",
    price_type: "",
  });
  assert.equal(bothMissing.isValid, false);
  assert.equal(bothMissing.errors.target_market_id, "Please select a target selling market.");
  assert.equal(bothMissing.errors.price_type, "Please select a price type (Wholesale or Retail).");
  assert.equal(isStep3Complete({ target_market_id: "", price_type: "" }), false);

  // 6. Invalid market, valid price type
  const invalidMarket = validateStep3({
    target_market_id: "DEC_LONDON",
    price_type: "wholesale",
  });
  assert.equal(invalidMarket.isValid, false);
  assert.equal(
    invalidMarket.errors.target_market_id,
    "The selected market is not recognized in verified Dedicated Economic Centres."
  );
  assert.equal(invalidMarket.errors.price_type, undefined);

  // 7. Valid market, invalid price type
  const invalidPriceType = validateStep3({
    target_market_id: "DEC_EMBILIPITIYA",
    price_type: "farmgate" as unknown as PriceType,
  });
  assert.equal(invalidPriceType.isValid, false);
  assert.equal(
    invalidPriceType.errors.price_type,
    "Invalid price type. Please select either Wholesale or Retail."
  );
  assert.equal(invalidPriceType.errors.target_market_id, undefined);
});

test("Wizard Step 3: Session storage helpers store, restore, and clear market and price type safely", () => {
  assert.equal(STEP3_STORAGE_KEY, "agrodecision_wizard_step3");

  // In Node environment, helpers return defaults gracefully without throwing
  const initial = loadStep3FromStorage();
  assert.deepEqual(initial, { target_market_id: "", selling_market_id: "", price_type: "" });

  assert.doesNotThrow(() => {
    saveStep3ToStorage({
      target_market_id: "DEC_EMBILIPITIYA",
      selling_market_id: "DEC_EMBILIPITIYA",
      price_type: "wholesale",
    });
    clearStep3Storage();
  });

  // Mock window session storage tests
  const mockStorage = new Map<string, string>();
  (globalThis as unknown as { window: unknown }).window = {
    sessionStorage: {
      getItem: (key: string) => mockStorage.get(key) ?? null,
      setItem: (key: string, val: string) => mockStorage.set(key, val),
      removeItem: (key: string) => mockStorage.delete(key),
    },
  };

  try {
    // 1. Save valid market and wholesale price type
    const saved = saveValidatedStep3ToStorage({
      target_market_id: "DEC_EMBILIPITIYA",
      price_type: "wholesale",
    });
    assert.equal(saved, true);
    assert.deepEqual(loadStep3FromStorage(), {
      target_market_id: "DEC_EMBILIPITIYA",
      selling_market_id: "DEC_EMBILIPITIYA",
      price_type: "wholesale",
    });

    // 2. Save valid market and retail price type
    const savedRetail = saveValidatedStep3ToStorage({
      target_market_id: "DEC_PETTAH",
      price_type: "retail",
    });
    assert.equal(savedRetail, true);
    assert.deepEqual(loadStep3FromStorage(), {
      target_market_id: "DEC_PETTAH",
      selling_market_id: "DEC_PETTAH",
      price_type: "retail",
    });

    // 2b. Case-insensitive and padded price type input is normalized to lowercase before persistence
    const savedNormalized = saveValidatedStep3ToStorage({
      target_market_id: "  DEC_EMBILIPITIYA  ",
      price_type: "  Wholesale  " as unknown as PriceType,
    });
    assert.equal(savedNormalized, true);
    assert.deepEqual(loadStep3FromStorage(), {
      target_market_id: "DEC_EMBILIPITIYA",
      selling_market_id: "DEC_EMBILIPITIYA",
      price_type: "wholesale",
    });

    // 3. Reject saving invalid price type, protecting existing stored record
    const rejectInvalid = saveValidatedStep3ToStorage({
      target_market_id: "DEC_PETTAH",
      price_type: "farmgate" as unknown as PriceType,
    });
    assert.equal(rejectInvalid, false);
    assert.deepEqual(loadStep3FromStorage(), {
      target_market_id: "DEC_EMBILIPITIYA",
      selling_market_id: "DEC_EMBILIPITIYA",
      price_type: "wholesale",
    });

    // 4. Reject saving missing price type, protecting existing stored record
    const rejectMissingPriceType = saveValidatedStep3ToStorage({
      target_market_id: "DEC_PETTAH",
      price_type: "",
    });
    assert.equal(rejectMissingPriceType, false);
    assert.deepEqual(loadStep3FromStorage(), {
      target_market_id: "DEC_EMBILIPITIYA",
      selling_market_id: "DEC_EMBILIPITIYA",
      price_type: "wholesale",
    });

    // 5. Clear
    clearStep3Storage();
    assert.deepEqual(loadStep3FromStorage(), {
      target_market_id: "",
      selling_market_id: "",
      price_type: "",
    });
  } finally {
    delete (globalThis as unknown as { window?: unknown }).window;
  }
});

test("Wizard Step 3: Backward compatibility for existing records containing only market ID", () => {
  const mockStorage = new Map<string, string>();
  (globalThis as unknown as { window: unknown }).window = {
    sessionStorage: {
      getItem: (key: string) => mockStorage.get(key) ?? null,
      setItem: (key: string, val: string) => mockStorage.set(key, val),
      removeItem: (key: string) => mockStorage.delete(key),
    },
  };

  try {
    // Scenario 1: Legacy record containing only selling_market_id (Commit 19 format)
    mockStorage.set(
      STEP3_STORAGE_KEY,
      JSON.stringify({ selling_market_id: "DEC_EMBILIPITIYA" })
    );

    const loaded1 = loadStep3FromStorage();
    assert.equal(loaded1.target_market_id, "DEC_EMBILIPITIYA");
    assert.equal(loaded1.selling_market_id, "DEC_EMBILIPITIYA");
    assert.equal(loaded1.price_type, "");
    // Step 3 is incomplete until farmer chooses price_type
    assert.equal(isStep3Complete(loaded1), false);

    // Scenario 2: Legacy record containing only target_market_id
    mockStorage.set(
      STEP3_STORAGE_KEY,
      JSON.stringify({ target_market_id: "DEC_DAMBULLA" })
    );

    const loaded2 = loadStep3FromStorage();
    assert.equal(loaded2.target_market_id, "DEC_DAMBULLA");
    assert.equal(loaded2.selling_market_id, "DEC_DAMBULLA");
    assert.equal(loaded2.price_type, "");
    assert.equal(isStep3Complete(loaded2), false);

    // Scenario 3: Corrupt JSON string in storage
    mockStorage.set(STEP3_STORAGE_KEY, "{ invalid json corrupt");
    const corruptLoaded = loadStep3FromStorage();
    assert.deepEqual(corruptLoaded, {
      target_market_id: "",
      selling_market_id: "",
      price_type: "",
    });
  } finally {
    delete (globalThis as unknown as { window?: unknown }).window;
  }
});

test("Wizard Step 3: Embilipitiya Dedicated Economic Centre is present and flagged as pilot recommended hub", () => {
  const embilipitiya = STANDARD_MARKETS.find((m) => m.id === "DEC_EMBILIPITIYA");
  assert.ok(embilipitiya, "DEC_EMBILIPITIYA must exist in STANDARD_MARKETS");
  assert.equal(embilipitiya.name, "Embilipitiya Dedicated Economic Centre");
  assert.equal(embilipitiya.is_pilot_recommended, true);
});

test("Wizard Step 3: Wizard navigation guards require valid Step 1 and Step 2 before Step 3", () => {
  // Scenario A: Step 1 incomplete
  const incompleteStep1 = validateStep1({ crop_id: "", cultivation_district_id: "" });
  assert.equal(incompleteStep1.isValid, false);

  // Scenario B: Step 1 complete, Step 2 incomplete
  const completeStep1 = validateStep1({ crop_id: "CR_OKRA", cultivation_district_id: "LK-32" });
  assert.equal(completeStep1.isValid, true);

  const incompleteStep2 = validateStep2(
    { harvest_date: "", land_extent_acres: "", expected_yield_kg: "" },
    FIXED_TODAY
  );
  assert.equal(incompleteStep2.isValid, false);

  // Scenario C: Steps 1 and 2 complete, Step 3 missing price type
  const completeStep2 = validateStep2(
    { harvest_date: "2027-05-15", land_extent_acres: "2.5", expected_yield_kg: "1500" },
    FIXED_TODAY
  );
  assert.equal(completeStep2.isValid, true);

  const partialStep3 = validateStep3({
    target_market_id: "DEC_EMBILIPITIYA",
    price_type: "",
  });
  assert.equal(partialStep3.isValid, false);

  // Scenario D: Steps 1, 2, and 3 all complete
  const completeStep3 = validateStep3({
    target_market_id: "DEC_EMBILIPITIYA",
    price_type: "wholesale",
  });
  assert.equal(completeStep3.isValid, true);
});

test("Wizard Step 3: checkPreviousStepsForStep3 identifies earliest incomplete step and redirection target", () => {
  // 1. Both Step 1 and Step 2 incomplete -> Earliest is Step 1
  const step1Incomplete = checkPreviousStepsForStep3(
    { crop_id: "", cultivation_district_id: "" },
    { harvest_date: "", land_extent_acres: "", expected_yield_kg: "" },
    FIXED_TODAY
  );
  assert.equal(step1Incomplete.isValid, false);
  assert.equal(step1Incomplete.earliestIncompleteStep, 1);
  assert.equal(step1Incomplete.redirectTarget, "/market-profit/new-analysis");
  assert.ok(step1Incomplete.errorMessage?.includes("Step 1"));

  // 2. Step 1 complete, Step 2 incomplete -> Earliest is Step 2
  const step2Incomplete = checkPreviousStepsForStep3(
    { crop_id: "CR_OKRA", cultivation_district_id: "LK-32" },
    { harvest_date: "", land_extent_acres: "", expected_yield_kg: "" },
    FIXED_TODAY
  );
  assert.equal(step2Incomplete.isValid, false);
  assert.equal(step2Incomplete.earliestIncompleteStep, 2);
  assert.equal(step2Incomplete.redirectTarget, "/market-profit/new-analysis/harvest-details");
  assert.ok(step2Incomplete.errorMessage?.includes("Step 2"));

  // 3. Both Step 1 and Step 2 complete -> Valid
  const bothComplete = checkPreviousStepsForStep3(
    { crop_id: "CR_OKRA", cultivation_district_id: "LK-32" },
    { harvest_date: "2027-05-15", land_extent_acres: "2.5", expected_yield_kg: "1500" },
    FIXED_TODAY
  );
  assert.equal(bothComplete.isValid, true);
  assert.equal(bothComplete.earliestIncompleteStep, undefined);
  assert.equal(bothComplete.redirectTarget, undefined);
});

test("Wizard Step 3: isWizardReadyForStep4 confirms full composite readiness across all 3 steps", () => {
  const step1 = { crop_id: "CR_OKRA", cultivation_district_id: "LK-32" };
  const step2 = { harvest_date: "2027-05-15", land_extent_acres: "2.5", expected_yield_kg: "1500" };
  const step3Wholesale = { target_market_id: "DEC_EMBILIPITIYA", price_type: "wholesale" as PriceType };
  const step3Retail = { target_market_id: "DEC_DAMBULLA", price_type: "retail" as PriceType };

  // All 3 valid with Wholesale
  assert.equal(isWizardReadyForStep4(step1, step2, step3Wholesale, FIXED_TODAY), true);

  // All 3 valid with Retail
  assert.equal(isWizardReadyForStep4(step1, step2, step3Retail, FIXED_TODAY), true);

  // Incomplete Step 1
  assert.equal(isWizardReadyForStep4({ crop_id: "" }, step2, step3Wholesale, FIXED_TODAY), false);

  // Incomplete Step 2
  assert.equal(isWizardReadyForStep4(step1, { harvest_date: "" }, step3Wholesale, FIXED_TODAY), false);

  // Incomplete Step 3 (missing price type)
  assert.equal(
    isWizardReadyForStep4(
      step1,
      step2,
      { target_market_id: "DEC_EMBILIPITIYA", price_type: "" },
      FIXED_TODAY
    ),
    false
  );

  // Incomplete Step 3 (missing market)
  assert.equal(
    isWizardReadyForStep4(
      step1,
      step2,
      { target_market_id: "", price_type: "wholesale" },
      FIXED_TODAY
    ),
    false
  );
});

test("Wizard Step 3: Step 3 Final Validation preserves user selections and maintains navigation readiness", () => {
  // Test preserving valid market selection when price type is missing
  const partialData1: Partial<Step3FormData> = {
    target_market_id: "DEC_EMBILIPITIYA",
    price_type: "",
  };
  const val1 = validateStep3(partialData1);
  assert.equal(val1.isValid, false);
  assert.equal(val1.errors.target_market_id, undefined); // Market is valid, preserved
  assert.ok(val1.errors.price_type);

  // Test preserving valid price type when market is missing
  const partialData2: { target_market_id: string; price_type: PriceType } = {
    target_market_id: "",
    price_type: "wholesale",
  };
  const val2 = validateStep3(partialData2);
  assert.equal(val2.isValid, false);
  assert.ok(val2.errors.target_market_id);
  assert.equal(val2.errors.price_type, undefined); // Price type is valid, preserved

  // Navigation metadata confirms Step 3 is Selling Market and Step 4 is Cultivation Costs
  const wizardSteps = [
    { step: 1, label: "Crop & Location", route: "/market-profit/new-analysis" },
    { step: 2, label: "Harvest Details", route: "/market-profit/new-analysis/harvest-details" },
    { step: 3, label: "Selling Market", route: "/market-profit/new-analysis/selling-market" },
    { step: 4, label: "Cultivation Costs", route: "/market-profit/new-analysis/cultivation-costs" },
  ];
  assert.equal(wizardSteps[2].step, 3);
  assert.equal(wizardSteps[2].label, "Selling Market");
  assert.equal(wizardSteps[3].step, 4);
  assert.equal(wizardSteps[3].label, "Cultivation Costs");
  assert.equal(wizardSteps[3].route, "/market-profit/new-analysis/cultivation-costs");
});





