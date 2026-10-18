/**
 * Typed API Client for Component 1 Backend (Port 8001):
 * Market Demand Analysis, Price Trend Forecasting & Profit Risk Assessment.
 */

import { DEFAULT_API_BASE_URL } from "./constants";
import {
  validateDemandForecastResponse,
  validatePriceForecastResponse,
  validateProfitCalculationResponse,
  validateProfitRiskAssessmentResponse,
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

export type ApiErrorType =
  | "connection"
  | "timeout"
  | "validation"
  | "server"
  | "malformed"
  | "unknown";

export interface ClassifiedApiError {
  type: ApiErrorType;
  badgeLabel: string;
  heading: string;
  message: string;
  actionGuidance: string;
  statusCode: number;
}

/**
 * Classifies an error into a farmer-friendly diagnosis distinguishing between
 * connection failures, timeouts, input validation errors, malformed responses, and server errors.
 */
export function classifyApiError(err: unknown, serviceName: string): ClassifiedApiError {
  if (err instanceof ApiError) {
    if (err.status === 408) {
      return {
        type: "timeout",
        badgeLabel: "Request Timed Out",
        heading: `Request Timed Out (${serviceName})`,
        message: err.message,
        actionGuidance:
          "The backend service took longer than expected to respond. Please check server responsiveness or retry.",
        statusCode: 408,
      };
    }
    if (err.status === 0) {
      return {
        type: "connection",
        badgeLabel: "Backend Connection Error",
        heading: `Cannot Connect to ${serviceName}`,
        message: err.message,
        actionGuidance:
          "Please verify that the FastAPI backend service is running on port 8001 (or configured via NEXT_PUBLIC_MARKET_PROFIT_API_URL).",
        statusCode: 0,
      };
    }
    if (err.status === 400 || err.status === 422) {
      return {
        type: "validation",
        badgeLabel: "Input Validation Error",
        heading: `Invalid Request Parameters (${serviceName})`,
        message: err.message,
        actionGuidance:
          "The request failed server-side validation. Please verify that your date, crop, district, and market inputs are valid.",
        statusCode: err.status,
      };
    }
    if (err.status === 502) {
      return {
        type: "malformed",
        badgeLabel: "Service Response Error",
        heading: `Malformed Response from ${serviceName}`,
        message: err.message,
        actionGuidance:
          "The backend service returned a response that did not adhere to the expected schema contract.",
        statusCode: 502,
      };
    }
    if (err.status >= 500) {
      return {
        type: "server",
        badgeLabel: "Calculation & Server Error",
        heading: `Server Processing Error (${serviceName})`,
        message: err.message,
        actionGuidance:
          `An unexpected internal error occurred on the backend service while evaluating ${serviceName} (HTTP ${err.status}).`,
        statusCode: err.status,
      };
    }
    return {
      type: "unknown",
      badgeLabel: `Error (HTTP ${err.status})`,
      heading: `Service Error (${serviceName})`,
      message: err.message,
      actionGuidance: `An unexpected HTTP ${err.status} error was returned by the service.`,
      statusCode: err.status,
    };
  }

  const msg = err instanceof Error ? err.message : String(err);
  return {
    type: "connection",
    badgeLabel: "Service Connection Error",
    heading: `Unable to Connect to ${serviceName}`,
    message: msg,
    actionGuidance:
      "Please verify backend server status on port 8001 and local network connectivity.",
    statusCode: 0,
  };
}

export interface ApiClientConfig {
  baseUrl?: string;
  transport?: typeof fetch;
  timeoutMs?: number;
}

export class MarketProfitApiClient {
  private baseUrl: string;
  private transport: typeof fetch;
  private timeoutMs: number;

  constructor(config: ApiClientConfig = {}) {
    const rawUrl =
      config.baseUrl ||
      (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_MARKET_PROFIT_API_URL) ||
      DEFAULT_API_BASE_URL;
    this.baseUrl = rawUrl.replace(/\/+$/, "");
    this.transport = config.transport || (typeof fetch !== "undefined" ? fetch.bind(globalThis) : (fetch as any));
    this.timeoutMs = config.timeoutMs ?? 15000;
  }

  private async postJson<TRequest, TResponse>(
    endpoint: string,
    payload: TRequest,
    signal?: AbortSignal
  ): Promise<TResponse> {
    const url = `${this.baseUrl}${endpoint}`;
    let res: Response;

    const controller = new AbortController();
    let isTimeout = false;
    const timeoutId = setTimeout(() => {
      isTimeout = true;
      controller.abort();
    }, this.timeoutMs);

    const onCallerAbort = () => {
      clearTimeout(timeoutId);
      controller.abort();
    };

    if (signal) {
      if (signal.aborted) {
        clearTimeout(timeoutId);
        const abortErr = new Error("Request was aborted");
        abortErr.name = "AbortError";
        throw abortErr;
      }
      signal.addEventListener("abort", onCallerAbort, { once: true });
    }

    try {
      res = await this.transport(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
    } catch (err: unknown) {
      clearTimeout(timeoutId);
      if (isTimeout) {
        throw new ApiError(
          408,
          `Request to ${endpoint} timed out after ${Math.round(this.timeoutMs / 1000)} seconds. Please verify server responsiveness.`
        );
      }
      if (signal?.aborted) {
        const abortErr = new Error("Request was aborted");
        abortErr.name = "AbortError";
        throw abortErr;
      }
      const errMsg = err instanceof Error ? err.message : String(err);
      throw new ApiError(
        0,
        `Cannot connect to Market-Profit service at ${this.baseUrl}. Please verify the backend is running on port 8001. (${errMsg})`
      );
    } finally {
      clearTimeout(timeoutId);
      if (signal) {
        signal.removeEventListener("abort", onCallerAbort);
      }
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
   * Rejects malformed or invalid response payloads.
   */
  public async calculateProfit(
    request: ProfitCalculationInput,
    signal?: AbortSignal
  ): Promise<ProfitCalculationResult> {
    const response = await this.postJson<ProfitCalculationInput, ProfitCalculationResult>(
      "/api/v1/profit-analyses/calculate",
      request,
      signal
    );

    const validation = validateProfitCalculationResponse(response);
    if (!validation.isValid) {
      throw new ApiError(
        502,
        `Malformed response received from profit calculation service: ${validation.error}`
      );
    }

    return response;
  }

  /**
   * Evaluate rule-based agricultural profit risk (Low, Medium, High, or insufficient_information).
   * Transparently explains trigger rules and preliminary heuristics.
   * Rejects malformed or invalid response payloads.
   */
  public async assessProfitRisk(
    request: ProfitRiskAssessmentInput,
    signal?: AbortSignal
  ): Promise<ProfitRiskAssessmentResult> {
    const response = await this.postJson<ProfitRiskAssessmentInput, ProfitRiskAssessmentResult>(
      "/api/v1/profit-analyses/assess-risk",
      request,
      signal
    );

    const validation = validateProfitRiskAssessmentResponse(response);
    if (!validation.isValid) {
      throw new ApiError(
        502,
        `Malformed response received from profit risk assessment service: ${validation.error}`
      );
    }

    return response;
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
