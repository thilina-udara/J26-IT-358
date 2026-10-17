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
  validateCultivationCost,
  validateStep4,
  isStep4Complete,
  loadStep4FromStorage,
  saveStep4ToStorage,
  saveValidatedStep4ToStorage,
  clearStep4Storage,
  checkPreviousStepsForStep4,
  STEP4_STORAGE_KEY,
  type Step4FormData,
  type Step4ValidationResult,
  type BudgetMode,
  type DetailedExpensesData,
  type DetailedExpenseKey,
  DETAILED_EXPENSE_CATEGORIES,
  createDefaultDetailedExpenses,
  safeSumDecimalStrings,
  calculateDetailedCultivationTotal,
  validateDetailedExpenseField,
  validateDetailedExpenses,
  safeMultiplyDecimalStrings,
  calculatePredictedRevenue,
  calculatePredictedProfit,
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

// ============================================================================
// Wizard Step 4: Quick Cultivation Budget Tests
// ============================================================================

test("Wizard Step 4: Valid positive whole and decimal cultivation costs pass validation", () => {
  // Whole numbers
  const r1 = validateCultivationCost("150000");
  assert.equal(r1.isValid, true);
  assert.equal(r1.parsedValue, 150000);
  assert.equal(r1.isZeroCost, false);
  assert.equal(r1.warning, undefined);

  // Decimal amounts
  const r2 = validateCultivationCost("25450.75");
  assert.equal(r2.isValid, true);
  assert.equal(r2.parsedValue, 25450.75);
  assert.equal(r2.isZeroCost, false);

  // High production budget
  const r3 = validateCultivationCost(1200000);
  assert.equal(r3.isValid, true);
  assert.equal(r3.parsedValue, 1200000);
  assert.equal(r3.isZeroCost, false);

  // Preserves decimal precision in input string without silent rounding
  const rawDecimal = "45000.12345";
  const r4 = validateCultivationCost(rawDecimal);
  assert.equal(r4.isValid, true);
  assert.equal(r4.parsedValue, 45000.12345);
});

test("Wizard Step 4: Zero cost is accepted as valid but flags a clear advisory warning", () => {
  // String zero
  const r1 = validateCultivationCost("0");
  assert.equal(r1.isValid, true);
  assert.equal(r1.parsedValue, 0);
  assert.equal(r1.isZeroCost, true);
  assert.ok(r1.warning);
  assert.match(r1.warning, /profit percentage and risk evaluation may be unavailable when cost is zero/i);

  // Numeric zero
  const r2 = validateCultivationCost(0);
  assert.equal(r2.isValid, true);
  assert.equal(r2.parsedValue, 0);
  assert.equal(r2.isZeroCost, true);
  assert.ok(r2.warning);

  // Decimal zero
  const r3 = validateCultivationCost("0.00");
  assert.equal(r3.isValid, true);
  assert.equal(r3.parsedValue, 0);
  assert.equal(r3.isZeroCost, true);
  assert.ok(r3.warning);
});

test("Wizard Step 4: Missing, empty, or whitespace cultivation cost is rejected", () => {
  const r1 = validateCultivationCost("");
  assert.equal(r1.isValid, false);
  assert.match(r1.error!, /Please enter your total expected cultivation cost in LKR/i);

  const r2 = validateCultivationCost("   ");
  assert.equal(r2.isValid, false);
  assert.match(r2.error!, /Please enter your total expected cultivation cost in LKR/i);

  const r3 = validateCultivationCost(null);
  assert.equal(r3.isValid, false);

  const r4 = validateCultivationCost(undefined);
  assert.equal(r4.isValid, false);
});

test("Wizard Step 4: Negative cultivation cost is rejected", () => {
  const r1 = validateCultivationCost("-15000");
  assert.equal(r1.isValid, false);
  assert.match(r1.error!, /Cultivation cost cannot be negative/i);

  const r2 = validateCultivationCost(-1);
  assert.equal(r2.isValid, false);
  assert.match(r2.error!, /Cultivation cost cannot be negative/i);

  const r3 = validateCultivationCost("-0.01");
  assert.equal(r3.isValid, false);
  assert.match(r3.error!, /Cultivation cost cannot be negative/i);
});

test("Wizard Step 4: Non-numeric values, NaN, and Infinity are rejected", () => {
  const r1 = validateCultivationCost("abc");
  assert.equal(r1.isValid, false);
  assert.match(r1.error!, /must be a valid numeric amount/i);

  const r2 = validateCultivationCost("15,000 LKR");
  assert.equal(r2.isValid, false);

  const r3 = validateCultivationCost(NaN);
  assert.equal(r3.isValid, false);

  const r4 = validateCultivationCost("NaN");
  assert.equal(r4.isValid, false);

  const r5 = validateCultivationCost(Infinity);
  assert.equal(r5.isValid, false);

  const r6 = validateCultivationCost("-Infinity");
  assert.equal(r6.isValid, false);
});

test("Wizard Step 4: validateStep4 and isStep4Complete evaluate valid, zero, and invalid states", () => {
  // Valid positive cost
  const v1 = validateStep4({ total_cultivation_cost_lkr: "175000" });
  assert.equal(v1.isValid, true);
  assert.equal(v1.parsedCost, 175000);
  assert.equal(v1.isZeroCost, false);
  assert.equal(isStep4Complete({ total_cultivation_cost_lkr: "175000" }), true);

  // Valid zero cost with warning
  const v2 = validateStep4({ total_cultivation_cost_lkr: "0" });
  assert.equal(v2.isValid, true);
  assert.equal(v2.isZeroCost, true);
  assert.ok(v2.warnings?.total_cultivation_cost_lkr);
  assert.equal(isStep4Complete({ total_cultivation_cost_lkr: "0" }), true);

  // Invalid missing cost
  const v3 = validateStep4({ total_cultivation_cost_lkr: "" });
  assert.equal(v3.isValid, false);
  assert.ok(v3.errors.total_cultivation_cost_lkr);
  assert.equal(isStep4Complete({ total_cultivation_cost_lkr: "" }), false);

  // Invalid negative cost
  const v4 = validateStep4({ total_cultivation_cost_lkr: "-500" });
  assert.equal(v4.isValid, false);
  assert.ok(v4.errors.total_cultivation_cost_lkr);
  assert.equal(isStep4Complete({ total_cultivation_cost_lkr: "-500" }), false);
});

test("Wizard Step 4: Session storage helpers save, restore, clear, and guard against invalid overwrite", () => {
  const mockStorage: Record<string, string> = {};
  const originalWindow = globalThis.window;

  // Mock sessionStorage in Node environment
  (globalThis as unknown as { window: unknown }).window = {
    sessionStorage: {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, val: string) => {
        mockStorage[key] = val;
      },
      removeItem: (key: string) => {
        delete mockStorage[key];
      },
    },
  };

  try {
    // 1. Initial empty storage
    const initial = loadStep4FromStorage();
    assert.equal(initial.total_cultivation_cost_lkr, "");

    // 2. Save valid budget
    saveStep4ToStorage({ total_cultivation_cost_lkr: "185000.50" });
    const loaded = loadStep4FromStorage();
    assert.equal(loaded.total_cultivation_cost_lkr, "185000.50");

    // 3. saveValidatedStep4ToStorage with invalid cost protects existing storage
    const invalidResult = saveValidatedStep4ToStorage({ total_cultivation_cost_lkr: "-500" });
    assert.equal(invalidResult, false);
    // Previous valid budget must be retained
    assert.equal(loadStep4FromStorage().total_cultivation_cost_lkr, "185000.50");

    // 4. saveValidatedStep4ToStorage with valid zero cost saves successfully
    const zeroResult = saveValidatedStep4ToStorage({ total_cultivation_cost_lkr: "0" });
    assert.equal(zeroResult, true);
    assert.equal(loadStep4FromStorage().total_cultivation_cost_lkr, "0");

    // 5. Clear storage
    clearStep4Storage();
    assert.equal(loadStep4FromStorage().total_cultivation_cost_lkr, "");
  } finally {
    (globalThis as unknown as { window: unknown }).window = originalWindow;
  }
});

test("Wizard Step 4: checkPreviousStepsForStep4 identifies earliest incomplete step and redirect target", () => {
  const FIXED_TODAY = new Date(2026, 9, 17); // October 17, 2026

  const validStep1 = { crop_id: "CR_OKRA", cultivation_district_id: "LK-82" };
  const validStep2 = { harvest_date: "2027-05-15", land_extent_acres: "2.5", expected_yield_kg: "1500" };
  const validStep3 = { target_market_id: "DEC_EMBILIPITIYA", price_type: "wholesale" as PriceType };

  // All 3 previous steps valid
  const resAllValid = checkPreviousStepsForStep4(validStep1, validStep2, validStep3, FIXED_TODAY);
  assert.equal(resAllValid.isValid, true);
  assert.equal(resAllValid.earliestIncompleteStep, undefined);
  assert.equal(resAllValid.redirectTarget, undefined);

  // Incomplete Step 1 -> points to /market-profit/new-analysis
  const resMissingStep1 = checkPreviousStepsForStep4({ crop_id: "" }, validStep2, validStep3, FIXED_TODAY);
  assert.equal(resMissingStep1.isValid, false);
  assert.equal(resMissingStep1.earliestIncompleteStep, 1);
  assert.equal(resMissingStep1.redirectTarget, "/market-profit/new-analysis");

  // Valid Step 1 but incomplete Step 2 -> points to /market-profit/new-analysis/harvest-details
  const resMissingStep2 = checkPreviousStepsForStep4(validStep1, { harvest_date: "" }, validStep3, FIXED_TODAY);
  assert.equal(resMissingStep2.isValid, false);
  assert.equal(resMissingStep2.earliestIncompleteStep, 2);
  assert.equal(resMissingStep2.redirectTarget, "/market-profit/new-analysis/harvest-details");

  // Valid Step 1 & 2 but missing market in Step 3 -> points to /market-profit/new-analysis/selling-market
  const resMissingMarket = checkPreviousStepsForStep4(validStep1, validStep2, { target_market_id: "", price_type: "wholesale" }, FIXED_TODAY);
  assert.equal(resMissingMarket.isValid, false);
  assert.equal(resMissingMarket.earliestIncompleteStep, 3);
  assert.equal(resMissingMarket.redirectTarget, "/market-profit/new-analysis/selling-market");

  // Valid Step 1 & 2 but missing price type in Step 3 -> points to /market-profit/new-analysis/selling-market
  const resMissingPriceType = checkPreviousStepsForStep4(validStep1, validStep2, { target_market_id: "DEC_EMBILIPITIYA", price_type: "" }, FIXED_TODAY);
  assert.equal(resMissingPriceType.isValid, false);
  assert.equal(resMissingPriceType.earliestIncompleteStep, 3);
  assert.equal(resMissingPriceType.redirectTarget, "/market-profit/new-analysis/selling-market");
});

// ============================================================================
// Wizard Step 4: Detailed Cultivation Budget Tests
// ============================================================================

test("Wizard Step 4 Detailed Budget: safeSumDecimalStrings avoids floating-point drift", () => {
  // Classic JS floating point hazard: 0.1 + 0.2 = 0.30000000000000004
  const r1 = safeSumDecimalStrings(["0.1", "0.2"]);
  assert.equal(r1.sumString, "0.3");
  assert.equal(r1.sumNumber, 0.3);

  // Currency cents summation
  const r2 = safeSumDecimalStrings(["10000.25", "25000.50", "4500.25"]);
  assert.equal(r2.sumString, "39501");
  assert.equal(r2.sumNumber, 39501);

  // Mixed decimal precision
  const r3 = safeSumDecimalStrings(["12.5", "8.25", "0.125"]);
  assert.equal(r3.sumString, "20.875");
  assert.equal(r3.sumNumber, 20.875);

  // Empty or whitespace strings treated as zero
  const r4 = safeSumDecimalStrings(["", "   ", "5000", ""]);
  assert.equal(r4.sumString, "5000");
  assert.equal(r4.sumNumber, 5000);

  // All empty strings
  const r5 = safeSumDecimalStrings([]);
  assert.equal(r5.sumString, "0");
  assert.equal(r5.sumNumber, 0);
});

test("Wizard Step 4 Detailed Budget: Correct sum across all 10 expense categories", () => {
  const fullDetailed: DetailedExpensesData = {
    seeds: "15000",
    fertilizer: "25000",
    pesticides: "12000",
    labour: "45000",
    irrigation: "10000",
    harvesting: "20000",
    packaging: "8000",
    transportation: "15000",
    market_commission: "5000",
    other_expenses: "5000",
  };

  const calc = calculateDetailedCultivationTotal(fullDetailed);
  // Sum: 15+25+12+45+10+20+8+15+5+5 = 160,000
  assert.equal(calc.totalCultivationCost, 160000);
  assert.equal(calc.totalString, "160000");
  assert.equal(calc.isZeroCost, false);
  assert.equal(calc.nonZeroCount, 10);
  assert.equal(calc.hasAnyEnteredValue, true);
});

test("Wizard Step 4 Detailed Budget: Decimal values and exact precision preservation", () => {
  const decimalDetailed: Partial<DetailedExpensesData> = {
    seeds: "12500.50",
    fertilizer: "18250.75",
    pesticides: "4500.25",
  };

  const calc = calculateDetailedCultivationTotal(decimalDetailed);
  // 12500.50 + 18250.75 + 4500.25 = 35251.50
  assert.equal(calc.totalCultivationCost, 35251.5);
  assert.equal(calc.totalString, "35251.5");
  assert.equal(calc.nonZeroCount, 3);
});

test("Wizard Step 4 Detailed Budget: Empty optional fields treated as zero for calculation", () => {
  // Only 2 fields populated, others empty
  const partialDetailed: Partial<DetailedExpensesData> = {
    seeds: "10000",
    labour: "20000",
    fertilizer: "",
    pesticides: "   ",
  };

  const calc = calculateDetailedCultivationTotal(partialDetailed);
  assert.equal(calc.totalCultivationCost, 30000);
  assert.equal(calc.totalString, "30000");
  assert.equal(calc.nonZeroCount, 2);

  const validation = validateDetailedExpenses(partialDetailed);
  assert.equal(validation.isValid, true);
  assert.equal(Object.keys(validation.errors).length, 0);
  assert.equal(validation.totalCultivationCost, 30000);
});

test("Wizard Step 4 Detailed Budget: Zero cost across all categories flags advisory warning", () => {
  // All empty / zero
  const emptyDetailed = createDefaultDetailedExpenses();
  const validation = validateDetailedExpenses(emptyDetailed);

  assert.equal(validation.isValid, true);
  assert.equal(validation.totalCultivationCost, 0);
  assert.equal(validation.isZeroCost, true);
  assert.ok(validation.warning);
  assert.match(validation.warning, /profit percentage and risk evaluation may be unavailable when cost is zero/i);

  // Explicit zeroes
  const explicitZeroes: Partial<DetailedExpensesData> = {
    seeds: "0",
    fertilizer: "0.00",
  };
  const valExplicit = validateDetailedExpenses(explicitZeroes);
  assert.equal(valExplicit.isValid, true);
  assert.equal(valExplicit.totalCultivationCost, 0);
  assert.equal(valExplicit.isZeroCost, true);
  assert.ok(valExplicit.warning);
});

test("Wizard Step 4 Detailed Budget: Negative values in any category are rejected with field error", () => {
  const invalidNegative: Partial<DetailedExpensesData> = {
    seeds: "15000",
    fertilizer: "-500",
    transportation: "-0.50",
  };

  const validation = validateDetailedExpenses(invalidNegative);
  assert.equal(validation.isValid, false);
  assert.equal(validation.errors.seeds, undefined); // seeds is valid
  assert.ok(validation.errors.fertilizer);
  assert.match(validation.errors.fertilizer!, /cannot be negative/i);
  assert.ok(validation.errors.transportation);
  assert.match(validation.errors.transportation!, /cannot be negative/i);
});

test("Wizard Step 4 Detailed Budget: Non-numeric, NaN, and Infinity in any category are rejected", () => {
  const invalidNonNumeric: Partial<DetailedExpensesData> = {
    seeds: "Fifteen Thousand",
    fertilizer: "NaN",
    labour: "Infinity",
  };

  const validation = validateDetailedExpenses(invalidNonNumeric);
  assert.equal(validation.isValid, false);
  assert.ok(validation.errors.seeds);
  assert.match(validation.errors.seeds!, /must be a valid numeric amount in LKR/i);
  assert.ok(validation.errors.fertilizer);
  assert.match(validation.errors.fertilizer!, /must be a valid numeric amount in LKR/i);
  assert.ok(validation.errors.labour);
  assert.match(validation.errors.labour!, /must be a valid numeric amount in LKR/i);
});

test("Wizard Step 4 Detailed Budget: Mode switching preserves entered values without double-counting", () => {
  // Farmer enters 150,000 in Quick Budget
  const quickInput = "150000";

  // Farmer enters 40,000 in Detailed Budget
  const detailedInput: DetailedExpensesData = {
    ...createDefaultDetailedExpenses(),
    seeds: "15000",
    fertilizer: "25000",
  };

  // 1. In Quick Budget Mode: effective total must be 150,000 (NOT 190,000)
  const quickState: Step4FormData = {
    budget_mode: "quick",
    quick_total_cultivation_cost_lkr: quickInput,
    detailed_expenses: detailedInput,
    effective_total_cultivation_cost_lkr: quickInput,
    total_cultivation_cost_lkr: quickInput,
  };

  const quickVal = validateStep4(quickState);
  assert.equal(quickVal.isValid, true);
  assert.equal(quickVal.budget_mode, "quick");
  assert.equal(quickVal.effectiveTotalString, "150000");
  assert.equal(quickVal.parsedCost, 150000);

  // 2. In Detailed Budget Mode: effective total must be 40,000 (NOT 190,000)
  const detailedState: Step4FormData = {
    budget_mode: "detailed",
    quick_total_cultivation_cost_lkr: quickInput,
    detailed_expenses: detailedInput,
    effective_total_cultivation_cost_lkr: "40000",
    total_cultivation_cost_lkr: "40000",
  };

  const detailedVal = validateStep4(detailedState);
  assert.equal(detailedVal.isValid, true);
  assert.equal(detailedVal.budget_mode, "detailed");
  assert.equal(detailedVal.effectiveTotalString, "40000");
  assert.equal(detailedVal.parsedCost, 40000);

  // Confirm NO double-counting occurs: total is never sum of both modes
  assert.notEqual(quickVal.parsedCost, 190000);
  assert.notEqual(detailedVal.parsedCost, 190000);
});

test("Wizard Step 4 Detailed Budget: Session storage persistence and backward compatibility", () => {
  const mockStorage: Record<string, string> = {};
  const originalWindow = globalThis.window;

  // Mock sessionStorage in Node environment
  (globalThis as unknown as { window: unknown }).window = {
    sessionStorage: {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, val: string) => {
        mockStorage[key] = val;
      },
      removeItem: (key: string) => {
        delete mockStorage[key];
      },
    },
  };

  try {
    // Test 1: Backward compatibility with older single-field records
    mockStorage[STEP4_STORAGE_KEY] = JSON.stringify({
      total_cultivation_cost_lkr: "175000",
    });

    const legacyLoaded = loadStep4FromStorage();
    assert.equal(legacyLoaded.budget_mode, "quick");
    assert.equal(legacyLoaded.quick_total_cultivation_cost_lkr, "175000");
    assert.equal(legacyLoaded.effective_total_cultivation_cost_lkr, "175000");
    assert.equal(legacyLoaded.total_cultivation_cost_lkr, "175000");
    assert.equal(legacyLoaded.detailed_expenses.seeds, "");

    // Test 2: Save and restore detailed budget record
    const detailedData: Step4FormData = {
      budget_mode: "detailed",
      quick_total_cultivation_cost_lkr: "175000",
      detailed_expenses: {
        ...createDefaultDetailedExpenses(),
        seeds: "20000",
        fertilizer: "30000",
        labour: "40000",
      },
      effective_total_cultivation_cost_lkr: "90000",
      total_cultivation_cost_lkr: "90000",
    };

    saveStep4ToStorage(detailedData);
    const restored = loadStep4FromStorage();
    assert.equal(restored.budget_mode, "detailed");
    assert.equal(restored.quick_total_cultivation_cost_lkr, "175000");
    assert.equal(restored.detailed_expenses.seeds, "20000");
    assert.equal(restored.detailed_expenses.fertilizer, "30000");
    assert.equal(restored.detailed_expenses.labour, "40000");
    assert.equal(restored.effective_total_cultivation_cost_lkr, "90000");
    assert.equal(restored.total_cultivation_cost_lkr, "90000");

    // Test 3: saveValidatedStep4ToStorage protects storage when detailed entries are invalid
    const invalidDetailed: Step4FormData = {
      ...detailedData,
      detailed_expenses: {
        ...detailedData.detailed_expenses,
        seeds: "-9999",
      },
    };

    const saveResult = saveValidatedStep4ToStorage(invalidDetailed);
    assert.equal(saveResult, false);
    // Old valid storage must remain untouched
    const afterInvalid = loadStep4FromStorage();
    assert.equal(afterInvalid.detailed_expenses.seeds, "20000");

    // Test 4: Clear storage
    clearStep4Storage();
    assert.equal(loadStep4FromStorage().total_cultivation_cost_lkr, "");
  } finally {
    (globalThis as unknown as { window: unknown }).window = originalWindow;
  }
});

// ============================================================================
// Wizard Step 4: Research Alignment & ML Price Forecasting Readiness (Commit 24 Revision)
// ============================================================================

test("Wizard Step 4 Research Alignment: No manual expected selling price is required from the farmer", () => {
  // Scenario 1: Quick Budget without manual selling price -> COMPLETES
  const quickData: Partial<Step4FormData> = {
    budget_mode: "quick",
    quick_total_cultivation_cost_lkr: "185000",
  };
  const valQuick = validateStep4(quickData);
  assert.equal(valQuick.isValid, true);
  assert.equal(valQuick.budget_mode, "quick");
  assert.equal(valQuick.parsedCost, 185000);
  assert.equal(isStep4Complete(quickData), true);

  // Scenario 2: Detailed Budget without manual selling price -> COMPLETES
  const detailedData: Partial<Step4FormData> = {
    budget_mode: "detailed",
    detailed_expenses: {
      ...createDefaultDetailedExpenses(),
      seeds: "20000",
      fertilizer: "30000",
      labour: "40000",
    },
  };
  const valDetailed = validateStep4(detailedData);
  assert.equal(valDetailed.isValid, true);
  assert.equal(valDetailed.budget_mode, "detailed");
  assert.equal(valDetailed.parsedCost, 90000);
  assert.equal(isStep4Complete(detailedData), true);
});

test("Wizard Step 4 ML Price Forecast Readiness: safeMultiplyDecimalStrings performs exact decimal arithmetic", () => {
  // Integer multiplication
  const r1 = safeMultiplyDecimalStrings("1500", "140");
  assert.equal(r1.productString, "210000");
  assert.equal(r1.productNumber, 210000);

  // Decimal multiplication without floating-point precision loss
  // 1250.5 * 120.25 = 150372.625
  const r2 = safeMultiplyDecimalStrings("1250.5", "120.25");
  assert.equal(r2.productString, "150372.625");
  assert.equal(r2.productNumber, 150372.625);

  // Sub-unit multiplication: 0.5 * 0.5 = 0.25
  const r3 = safeMultiplyDecimalStrings("0.5", "0.5");
  assert.equal(r3.productString, "0.25");
  assert.equal(r3.productNumber, 0.25);

  // Zero product
  const r4 = safeMultiplyDecimalStrings("0", "140");
  assert.equal(r4.productString, "0");
  assert.equal(r4.productNumber, 0);

  // Empty input handling
  const r5 = safeMultiplyDecimalStrings("", "140");
  assert.equal(r5.productString, "0");
  assert.equal(r5.productNumber, 0);
});

test("Wizard Step 4 ML Price Forecast Readiness: calculatePredictedRevenue integrates future ML price predictions without mock data", () => {
  // 1. Valid ML Predicted Price (Rs. 135.50/kg) and Harvest Yield (1,500 kg)
  // Revenue = 135.50 * 1500 = 203,250 LKR
  const validRev = calculatePredictedRevenue("135.50", "1500");
  assert.equal(validRev.isAvailable, true);
  assert.equal(validRev.revenueNumber, 203250);
  assert.equal(validRev.revenueString, "203250");

  // Numeric arguments also accepted
  const numRev = calculatePredictedRevenue(140, 2000);
  assert.equal(numRev.isAvailable, true);
  assert.equal(numRev.revenueNumber, 280000);

  // 2. Unavailable predictions return isAvailable: false (strictly NO invented or mock values)
  const nullPrice = calculatePredictedRevenue(null, "1500");
  assert.equal(nullPrice.isAvailable, false);
  assert.equal(nullPrice.revenueNumber, 0);

  const undefinedPrice = calculatePredictedRevenue(undefined, "1500");
  assert.equal(undefinedPrice.isAvailable, false);
  assert.equal(undefinedPrice.revenueNumber, 0);

  const emptyPrice = calculatePredictedRevenue("", "1500");
  assert.equal(emptyPrice.isAvailable, false);
  assert.equal(emptyPrice.revenueNumber, 0);

  const missingYield = calculatePredictedRevenue("140", undefined);
  assert.equal(missingYield.isAvailable, false);
  assert.equal(missingYield.revenueNumber, 0);

  // Non-positive or non-numeric values
  const zeroPrice = calculatePredictedRevenue("0", "1500");
  assert.equal(zeroPrice.isAvailable, false);

  const negPrice = calculatePredictedRevenue("-50", "1500");
  assert.equal(negPrice.isAvailable, false);

  const nonNumPrice = calculatePredictedRevenue("abc", "1500");
  assert.equal(nonNumPrice.isAvailable, false);
});

test("Wizard Step 4 ML Price Forecast Readiness: calculatePredictedProfit computes net return based on predicted revenue and cultivation cost", () => {
  // 1. Profitable harvest scenario
  // Revenue = 250,000 LKR, Cultivation Cost = 150,000 LKR -> Net Profit = 100,000 LKR
  const profit1 = calculatePredictedProfit(250000, 150000);
  assert.equal(profit1.isAvailable, true);
  assert.equal(profit1.profitNumber, 100000);
  assert.equal(profit1.profitString, "100000");

  // 2. Breakeven scenario
  const breakeven = calculatePredictedProfit(150000, 150000);
  assert.equal(breakeven.isAvailable, true);
  assert.equal(breakeven.profitNumber, 0);

  // 3. Loss-making scenario
  // Revenue = 120,000 LKR, Cultivation Cost = 160,000 LKR -> Net Loss = -40,000 LKR
  const loss = calculatePredictedProfit(120000, 160000);
  assert.equal(loss.isAvailable, true);
  assert.equal(loss.profitNumber, -40000);

  // 4. Missing inputs return isAvailable: false
  const nullRev = calculatePredictedProfit(null, 150000);
  assert.equal(nullRev.isAvailable, false);
  assert.equal(nullRev.profitNumber, 0);

  const undefCost = calculatePredictedProfit(250000, undefined);
  assert.equal(undefCost.isAvailable, false);
  assert.equal(undefCost.profitNumber, 0);

  const nanCost = calculatePredictedProfit(250000, NaN);
  assert.equal(nanCost.isAvailable, false);
});

test("Wizard Step 4 Session Storage: Saves, restores, and isolates budget modes without manual selling price", () => {
  const mockStorage: Record<string, string> = {};
  const originalWindow = globalThis.window;

  (globalThis as unknown as { window: unknown }).window = {
    sessionStorage: {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, val: string) => {
        mockStorage[key] = val;
      },
      removeItem: (key: string) => {
        delete mockStorage[key];
      },
    },
  };

  try {
    // 1. Save Quick Budget
    const quickData: Partial<Step4FormData> = {
      budget_mode: "quick",
      quick_total_cultivation_cost_lkr: "175000.50",
    };
    saveStep4ToStorage(quickData);

    const loadedQuick = loadStep4FromStorage();
    assert.equal(loadedQuick.budget_mode, "quick");
    assert.equal(loadedQuick.quick_total_cultivation_cost_lkr, "175000.50");
    assert.equal(loadedQuick.effective_total_cultivation_cost_lkr, "175000.50");
    assert.equal(isStep4Complete(loadedQuick), true);

    // 2. Save Detailed Budget
    const detailedData: Partial<Step4FormData> = {
      budget_mode: "detailed",
      quick_total_cultivation_cost_lkr: "175000.50",
      detailed_expenses: {
        ...createDefaultDetailedExpenses(),
        seeds: "20000",
        fertilizer: "35000",
      },
    };
    saveStep4ToStorage(detailedData);

    const loadedDetailed = loadStep4FromStorage();
    assert.equal(loadedDetailed.budget_mode, "detailed");
    assert.equal(loadedDetailed.detailed_expenses.seeds, "20000");
    assert.equal(loadedDetailed.detailed_expenses.fertilizer, "35000");
    assert.equal(loadedDetailed.effective_total_cultivation_cost_lkr, "55000");
    // Quick budget input was preserved in storage without double counting
    assert.equal(loadedDetailed.quick_total_cultivation_cost_lkr, "175000.50");
    assert.equal(isStep4Complete(loadedDetailed), true);

    // 3. Clear storage
    clearStep4Storage();
    const emptyLoaded = loadStep4FromStorage();
    assert.equal(emptyLoaded.quick_total_cultivation_cost_lkr, "");
    assert.equal(emptyLoaded.effective_total_cultivation_cost_lkr, "");
    assert.equal(isStep4Complete(emptyLoaded), false);
  } finally {
    (globalThis as unknown as { window: unknown }).window = originalWindow;
  }
});

test("Wizard Step 4 Backward Compatibility: Legacy records with obsolete manual_selling_price load safely", () => {
  const mockStorage: Record<string, string> = {};
  const originalWindow = globalThis.window;

  (globalThis as unknown as { window: unknown }).window = {
    sessionStorage: {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, val: string) => {
        mockStorage[key] = val;
      },
      removeItem: (key: string) => {
        delete mockStorage[key];
      },
    },
  };

  try {
    // 1. Session record containing obsolete manual_selling_price_lkr_per_kg
    mockStorage[STEP4_STORAGE_KEY] = JSON.stringify({
      budget_mode: "quick",
      quick_total_cultivation_cost_lkr: "160000",
      total_cultivation_cost_lkr: "160000",
      manual_selling_price_lkr_per_kg: "140.00",
    });

    const loaded = loadStep4FromStorage();
    assert.equal(loaded.budget_mode, "quick");
    assert.equal(loaded.quick_total_cultivation_cost_lkr, "160000");
    assert.equal(loaded.effective_total_cultivation_cost_lkr, "160000");
    // Obsolete manual selling price is preserved or ignored safely without crashing
    assert.equal(loaded.manual_selling_price_lkr_per_kg, "140.00");
    assert.equal(isStep4Complete(loaded), true);

    // 2. Corrupt JSON in storage returns safe defaults
    mockStorage[STEP4_STORAGE_KEY] = "{ corrupted json payload";
    const corruptLoaded = loadStep4FromStorage();
    assert.equal(corruptLoaded.budget_mode, "quick");
    assert.equal(corruptLoaded.quick_total_cultivation_cost_lkr, "");
    assert.equal(isStep4Complete(corruptLoaded), false);
  } finally {
    (globalThis as unknown as { window: unknown }).window = originalWindow;
  }
});

test("Wizard Step 4 Storage Protection: saveValidatedStep4ToStorage guards against invalid budget overwrites", () => {
  const mockStorage: Record<string, string> = {};
  const originalWindow = globalThis.window;

  (globalThis as unknown as { window: unknown }).window = {
    sessionStorage: {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, val: string) => {
        mockStorage[key] = val;
      },
      removeItem: (key: string) => {
        delete mockStorage[key];
      },
    },
  };

  try {
    // 1. Seed valid session storage
    const validData: Partial<Step4FormData> = {
      budget_mode: "quick",
      quick_total_cultivation_cost_lkr: "175000",
      effective_total_cultivation_cost_lkr: "175000",
    };
    const saved = saveValidatedStep4ToStorage(validData);
    assert.equal(saved, true);
    assert.equal(loadStep4FromStorage().quick_total_cultivation_cost_lkr, "175000");

    // 2. Attempt save with negative cost -> MUST REJECT and preserve previous valid data
    const invalidNegative = {
      budget_mode: "quick" as BudgetMode,
      quick_total_cultivation_cost_lkr: "-500",
    };
    const rejectNegative = saveValidatedStep4ToStorage(invalidNegative);
    assert.equal(rejectNegative, false);
    assert.equal(loadStep4FromStorage().quick_total_cultivation_cost_lkr, "175000");

    // 3. Attempt save with non-numeric cost -> MUST REJECT
    const rejectNonNum = saveValidatedStep4ToStorage({
      budget_mode: "quick" as BudgetMode,
      quick_total_cultivation_cost_lkr: "not-a-number",
    });
    assert.equal(rejectNonNum, false);
    assert.equal(loadStep4FromStorage().quick_total_cultivation_cost_lkr, "175000");

    // 4. Attempt save with negative category in Detailed mode -> MUST REJECT
    const rejectDetailedNeg = saveValidatedStep4ToStorage({
      budget_mode: "detailed" as BudgetMode,
      detailed_expenses: {
        ...createDefaultDetailedExpenses(),
        seeds: "-2000",
      },
    });
    assert.equal(rejectDetailedNeg, false);
    assert.equal(loadStep4FromStorage().quick_total_cultivation_cost_lkr, "175000");

    // 5. Valid update with Detailed Budget -> SUCCESS
    const validDetailedUpdate = saveValidatedStep4ToStorage({
      budget_mode: "detailed" as BudgetMode,
      quick_total_cultivation_cost_lkr: "175000",
      detailed_expenses: {
        ...createDefaultDetailedExpenses(),
        seeds: "25000",
        fertilizer: "40000",
      },
    });
    assert.equal(validDetailedUpdate, true);
    const loadedAfter = loadStep4FromStorage();
    assert.equal(loadedAfter.budget_mode, "detailed");
    assert.equal(loadedAfter.detailed_expenses.seeds, "25000");
    assert.equal(loadedAfter.effective_total_cultivation_cost_lkr, "65000");
  } finally {
    (globalThis as unknown as { window: unknown }).window = originalWindow;
  }
});







