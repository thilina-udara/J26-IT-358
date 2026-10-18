/**
 * Typed API Client for Component 1 Backend (Port 8001):
 * Market Demand Analysis, Price Trend Forecasting & Profit Risk Assessment.
 */

import { DEFAULT_API_BASE_URL } from "./constants";
import {
  validateDemandForecastResponse,
  validatePriceForecastResponse,
} from "./wizard";
import type {
  CombinedAnalysisResult,
  DemandForecastRequest,
  DemandForecastResponse,
  FarmerPlanningScenario,
  FastApiErrorResponse,
  PriceForecastRequest,
  PriceForecastResponse,
  ProfitCalculationInput,
  ProfitCalculationResult,
  ProfitRiskAssessmentInput,
  ProfitRiskAssessmentResult,
} from "./types";

export class ApiError extends Error {
  public status: number;
  public fieldErrors: Record<string, string>;

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

/**
 * Parse FastAPI detail payload into user-facing message and field-specific errors.
 */
function parseFastApiError(detail: unknown): { message: string; fieldErrors: Record<string, string> } {
  const fieldErrors: Record<string, string> = {};

  if (typeof detail === "string") {
    return { message: detail, fieldErrors };
  }

  if (Array.isArray(detail)) {
    for (const item of detail) {
      if (item && Array.isArray(item.loc) && typeof item.msg === "string") {
        const fieldName = String(item.loc[item.loc.length - 1]);
        fieldErrors[fieldName] = item.msg;
      }
    }
    const hasFieldErrors = Object.keys(fieldErrors).length > 0;
    return {
      message: hasFieldErrors
        ? "Please correct the invalid fields highlighted below."
        : "The request could not be processed due to validation errors.",
      fieldErrors,
    };
  }

  return {
    message: "An unexpected error occurred while communicating with the service.",
    fieldErrors,
  };
}

export interface ApiClientConfig {
  baseUrl?: string;
  transport?: typeof fetch;
}

export class MarketProfitApiClient {
  private baseUrl: string;
  private transport: typeof fetch;

  constructor(config: ApiClientConfig = {}) {
    const rawUrl =
      config.baseUrl ||
      (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_MARKET_PROFIT_API_URL) ||
      DEFAULT_API_BASE_URL;
    this.baseUrl = rawUrl.replace(/\/+$/, "");
    this.transport = config.transport || (typeof fetch !== "undefined" ? fetch.bind(globalThis) : (fetch as any));
  }

  private async postJson<TRequest, TResponse>(
    endpoint: string,
    payload: TRequest,
    signal?: AbortSignal
  ): Promise<TResponse> {
    const url = `${this.baseUrl}${endpoint}`;
    let res: Response;

    try {
      res = await this.transport(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
        signal,
      });
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        throw err;
      }
      const errMsg = err instanceof Error ? err.message : String(err);
      throw new ApiError(
        0,
        `Cannot connect to Market-Profit service at ${this.baseUrl}. Please verify the backend is running on port 8001. (${errMsg})`
      );
    }

    let responseData: unknown;
    try {
      responseData = await res.json();
    } catch {
      throw new ApiError(res.status, `Invalid JSON response received from ${endpoint} (HTTP ${res.status}).`);
    }

    if (!res.ok) {
      const errorObj = responseData as FastApiErrorResponse;
      const { message, fieldErrors } = parseFastApiError(errorObj?.detail);
      throw new ApiError(res.status, message, fieldErrors);
    }

    return responseData as TResponse;
  }

  /**
   * Request commodity demand forecast (stateless ML inference endpoint).
   * Gracefully returns prediction_status = "unavailable" and null values when model is offline.
   * Rejects malformed or invalid response payloads.
   */
  public async getDemandForecast(
    request: DemandForecastRequest,
    signal?: AbortSignal
  ): Promise<DemandForecastResponse> {
    const response = await this.postJson<DemandForecastRequest, DemandForecastResponse>(
      "/api/v1/market-demands/forecast",
      request,
      signal
    );

    const validation = validateDemandForecastResponse(response);
    if (!validation.isValid) {
      throw new ApiError(
        502,
        `Malformed response received from demand forecast service: ${validation.error}`
      );
    }

    return response;
  }

  /**
   * Request wholesale or retail price forecast (stateless ML inference endpoint).
   * Gracefully returns prediction_status = "unavailable" and null values when model is offline.
   * Rejects malformed or invalid response payloads.
   */
  public async getPriceForecast(
    request: PriceForecastRequest,
    signal?: AbortSignal
  ): Promise<PriceForecastResponse> {
    const response = await this.postJson<PriceForecastRequest, PriceForecastResponse>(
      "/api/v1/market-prices/forecast",
      request,
      signal
    );

    const validation = validatePriceForecastResponse(response);
    if (!validation.isValid) {
      throw new ApiError(
        502,
        `Malformed response received from price forecast service: ${validation.error}`
      );
    }

    return response;
  }

  /**
   * Calculate deterministic gross revenue, net profit, ROI, breakeven price, and margin of safety.
   * Completely stateless, 0 database writes.
   */
  public async calculateProfit(request: ProfitCalculationInput): Promise<ProfitCalculationResult> {
    return this.postJson<ProfitCalculationInput, ProfitCalculationResult>(
      "/api/v1/profit-analyses/calculate",
      request
    );
  }

  /**
   * Evaluate rule-based agricultural profit risk (Low, Medium, High, or insufficient_information).
   * Transparently explains trigger rules and preliminary heuristics.
   */
  public async assessProfitRisk(request: ProfitRiskAssessmentInput): Promise<ProfitRiskAssessmentResult> {
    return this.postJson<ProfitRiskAssessmentInput, ProfitRiskAssessmentResult>(
      "/api/v1/profit-analyses/assess-risk",
      request
    );
  }

  /**
   * High-level coordinator: Evaluates all four endpoints concurrently for a given farmer planning scenario.
   * Dispatches demand forecast, price forecast, deterministic profit calculation, and risk assessment.
   */
  public async evaluateComprehensiveFarmerPlan(scenario: FarmerPlanningScenario): Promise<CombinedAnalysisResult> {
    const demandPromise = this.getDemandForecast({
      crop_id: scenario.crop_id,
      cultivation_district_id: scenario.cultivation_district_id,
      target_market_id: scenario.target_market_id,
      forecast_target_date: scenario.forecast_target_date,
    });

    const pricePromise = this.getPriceForecast({
      crop_id: scenario.crop_id,
      cultivation_district_id: scenario.cultivation_district_id,
      target_market_id: scenario.target_market_id,
      forecast_target_date: scenario.forecast_target_date,
      price_type: scenario.price_type,
    });

    const calcPromise = this.calculateProfit({
      expected_yield_kg: scenario.expected_yield_kg,
      selling_price_lkr_per_kg: scenario.selling_price_lkr_per_kg,
      total_cultivation_cost: scenario.total_cultivation_cost,
    });

    const riskPromise = this.assessProfitRisk({
      expected_yield_kg: scenario.expected_yield_kg,
      selling_price_lkr_per_kg: scenario.selling_price_lkr_per_kg,
      total_cultivation_cost: scenario.total_cultivation_cost,
    });

    const [demandForecast, priceForecast, profitCalculation, profitRisk] = await Promise.all([
      demandPromise,
      pricePromise,
      calcPromise,
      riskPromise,
    ]);

    return {
      scenario,
      demandForecast,
      priceForecast,
      profitCalculation,
      profitRisk,
      evaluated_at: new Date().toISOString(),
    };
  }
}

// Default export of singleton client instance
export const apiClient = new MarketProfitApiClient();
