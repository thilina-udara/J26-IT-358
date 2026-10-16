/**
 * TypeScript request and response types for Component 1:
 * Market Demand Analysis, Price Trend Forecasting & Profit Risk Assessment.
 * Strictly aligns with backend FastAPI Pydantic contracts (Milestone 1E).
 */

export type PredictionStatus = "pending" | "completed" | "unavailable" | "failed";

export type DemandLevel = "High" | "Medium" | "Low";

export type ForecastPriceType = "wholesale" | "retail";

export type ProfitRiskCategory = "Low" | "Medium" | "High" | "insufficient_information";

// ============================================================================
// 1. Market Demand Forecasting (POST /api/v1/market-demands/forecast)
// ============================================================================

export interface DemandForecastRequest {
  crop_id: string;
  cultivation_district_id: string;
  target_market_id: string;
  forecast_target_date: string; // YYYY-MM-DD
}

export interface DemandForecastResponse {
  crop_id: string;
  cultivation_district_id: string;
  target_market_id: string;
  target_market_name?: string | null;
  forecast_target_date: string;
  prediction_status: PredictionStatus;
  projected_demand_volume_kg: number | string | null;
  projected_demand_level: DemandLevel | null;
  model_version?: string | null;
  model_provenance?: Record<string, unknown> | null;
  status_message: string;
  created_at?: string | null;
}

// ============================================================================
// 2. Market Price Forecasting (POST /api/v1/market-prices/forecast)
// ============================================================================

export interface PriceForecastRequest {
  crop_id: string;
  cultivation_district_id: string;
  target_market_id: string;
  forecast_target_date: string; // YYYY-MM-DD
  price_type: ForecastPriceType;
}

export interface PriceForecastResponse {
  crop_id: string;
  cultivation_district_id: string;
  target_market_id: string;
  target_market_name?: string | null;
  forecast_target_date: string;
  price_type: ForecastPriceType;
  currency: "LKR";
  unit: "kg";
  prediction_status: PredictionStatus;
  forecasted_price_lkr_per_kg: number | string | null;
  model_version?: string | null;
  model_provenance?: Record<string, unknown> | null;
  status_message: string;
  created_at?: string | null;
}

// ============================================================================
// 3. Deterministic Profit Calculation (POST /api/v1/profit-analyses/calculate)
// ============================================================================

export interface ProfitCalculationInput {
  expected_yield_kg: number | string;
  selling_price_lkr_per_kg: number | string;
  total_cultivation_cost?: number | string;
}

export interface ProfitCalculationResult {
  expected_yield_kg: string;
  selling_price_lkr_per_kg: string;
  total_cultivation_cost: string;
  gross_revenue: string;
  net_profit: string;
  roi_percentage: string | null;
  breakeven_price_lkr_per_kg: string;
  margin_of_safety_percentage: string;
  currency: "LKR";
  price_source: "farmer_assumption";
  is_manual_price_assumption: true;
  assumptions_note: string;
  calculation_notes?: string | null;
}

// ============================================================================
// 4. Profit Risk Assessment (POST /api/v1/profit-analyses/assess-risk)
// ============================================================================

export interface ProfitRiskThresholds {
  min_roi_low_risk?: number | string;
  min_margin_safety_low_risk?: number | string;
}

export interface ProfitRiskAssessmentInput {
  expected_yield_kg: number | string;
  selling_price_lkr_per_kg: number | string;
  total_cultivation_cost?: number | string;
  thresholds?: ProfitRiskThresholds;
}

export interface ProfitRiskFactors {
  net_profit: string;
  roi_percentage: string | null;
  breakeven_price_lkr_per_kg: string;
  margin_of_safety_percentage: string;
  selling_price_lkr_per_kg: string;
  expected_yield_kg: string;
  total_cultivation_cost: string;
  trigger_rule: string;
  trigger_rationale: string;
}

export interface ProfitRiskAssessmentResult {
  risk_level: ProfitRiskCategory;
  assessment_type: "rule_based_heuristic";
  is_ml_prediction: false;
  disclaimer: string;
  thresholds_applied: {
    min_roi_low_risk: string;
    min_margin_safety_low_risk: string;
  };
  factors: ProfitRiskFactors;
  profit_calculation: ProfitCalculationResult;
}

// ============================================================================
// 5. Frontend Multi-Step Scenario & Combined Evaluation
// ============================================================================

export interface DetailedCostItems {
  seeds: number;
  fertilizer: number;
  pesticides: number;
  labour: number;
  irrigation: number;
  harvesting_packaging: number;
  transportation: number;
  other_expenses: number;
}

export interface FarmerPlanningScenario {
  scenario_id?: string;
  crop_id: string;
  cultivation_district_id: string;
  target_market_id: string;
  forecast_target_date: string;
  price_type: ForecastPriceType;
  land_extent_acres: number;
  expected_yield_kg: number;
  selling_price_lkr_per_kg: number;
  budget_mode: "quick" | "detailed";
  total_cultivation_cost: number;
  detailed_costs?: DetailedCostItems;
  created_at?: string;
}

export interface CombinedAnalysisResult {
  scenario: FarmerPlanningScenario;
  demandForecast: DemandForecastResponse;
  priceForecast: PriceForecastResponse;
  profitCalculation: ProfitCalculationResult;
  profitRisk: ProfitRiskAssessmentResult;
  evaluated_at: string;
}

// ============================================================================
// 6. API Error Protocol
// ============================================================================

export interface FastApiValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface FastApiErrorResponse {
  detail?: string | FastApiValidationErrorItem[];
}
