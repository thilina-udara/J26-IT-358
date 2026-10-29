"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Image, { StaticImageData } from "next/image";
import {
  ArrowLeft,
  ArrowRight,
  Sprout,
  Calendar,
  MapPin,
  Store,
  Tag,
  Scale,
  Compass,
  Wallet,
  Receipt,
  TrendingUp,
  Coins,
  ShieldCheck,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Edit3,
  RotateCcw,
  Loader2,
  Printer,
  Info,
} from "lucide-react";

import {
  SUPPORTED_FRONTEND_CROPS,
  SRI_LANKA_DISTRICTS,
  STANDARD_MARKETS,
  FrontendCropMetadata,
  DistrictMetadata,
  MarketMetadata,
} from "../lib/constants";
import { formatDateDisplay, formatKg, formatLKR, formatPercent } from "../lib/formatters";
import { MarketProfitApiClient, classifyApiError, type ClassifiedApiError } from "../lib/api";
import type {
  DemandForecastRequest,
  DemandForecastResponse,
  PriceForecastRequest,
  PriceForecastResponse,
  ProfitCalculationResult,
  ProfitRiskAssessmentResult,
} from "../lib/types";
import {
  ValidatedAnalysisSnapshot,
  loadAnalysisSnapshot,
  loadAndValidateWizardFromStorage,
  saveAnalysisSnapshot,
  clearAnalysisSnapshot,
  DETAILED_EXPENSE_CATEGORIES,
  buildDemandForecastRequest,
  isPredictionAvailable,
  isPredictionUnavailable,
  buildPriceForecastRequest,
  isPricePredictionAvailable,
  isPricePredictionUnavailable,
  buildProfitRiskAssessmentRequest,
} from "../lib/wizard";

// Statically import verified crop photographs
import okraImg from "../assets/crops/okra.jpg";
import brinjalImg from "../assets/crops/brinjal.jpg";
import pumpkinImg from "../assets/crops/pumpkin.jpg";
import maizeImg from "../assets/crops/maize.jpg";
import mungBeanImg from "../assets/crops/mung-bean.jpg";
import chilliImg from "../assets/crops/chilli.jpg";

const CROP_IMAGE_MAP: Record<string, StaticImageData> = {
  CR_OKRA: okraImg,
  CR_BRINJAL: brinjalImg,
  CR_PUMPKIN: pumpkinImg,
  CR_MAIZE: maizeImg,
  CR_MUNG_BEAN: mungBeanImg,
  CR_CHILLI: chilliImg,
};

function calculateHorizonWeeks(targetDateStr: string): {
  weeks: number;
  isSupportedRange: boolean;
  days: number;
} {
  try {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const target = new Date(targetDateStr);
    target.setHours(0, 0, 0, 0);
    const diffMs = target.getTime() - today.getTime();
    const days = Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
    const weeks = Math.max(1, Math.round(days / 7));
    return {
      weeks,
      isSupportedRange: weeks >= 1 && weeks <= 16,
      days,
    };
  } catch {
    return { weeks: 1, isSupportedRange: true, days: 0 };
  }
}

export default function AnalysisResultsPage() {
  const router = useRouter();
  const [snapshot, setSnapshot] = useState<ValidatedAnalysisSnapshot | null>(null);
  const [status, setStatus] = useState<"loading" | "valid" | "incomplete">("loading");
  const [redirectTarget, setRedirectTarget] = useState<string>("/market-profit/new-analysis");
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    // 1. First attempt to load stored analysis snapshot
    const storedSnapshot = loadAnalysisSnapshot();
    if (storedSnapshot) {
      setSnapshot(storedSnapshot);
      setStatus("valid");
      return;
    }

    // 2. If no snapshot exists, validate current wizard session storage
    const wizardValidation = loadAndValidateWizardFromStorage();
    if (wizardValidation.isValid && wizardValidation.snapshot) {
      saveAnalysisSnapshot(wizardValidation.snapshot);
      setSnapshot(wizardValidation.snapshot);
      setStatus("valid");
    } else {
      setStatus("incomplete");
      setRedirectTarget(wizardValidation.redirectTarget || "/market-profit/new-analysis");
      setErrorMessage(
        wizardValidation.errorMessage ||
          "Please complete your farm details before viewing analysis results."
      );
    }
  }, []);

  // Live Market Demand Analysis state
  const [demandState, setDemandState] = useState<{
    status: "idle" | "loading" | "available" | "unavailable" | "error";
    response: DemandForecastResponse | null;
    errorMessage: string | null;
    classifiedError: ClassifiedApiError | null;
    requestPayload: DemandForecastRequest | null;
  }>({
    status: "idle",
    response: null,
    errorMessage: null,
    classifiedError: null,
    requestPayload: null,
  });

  const inFlightRef = React.useRef(false);
  const lastFetchedSignatureRef = React.useRef<string | null>(null);
  const abortControllerRef = React.useRef<AbortController | null>(null);

  const executeDemandForecast = async (
    targetSnapshot: ValidatedAnalysisSnapshot,
    activeSignal?: AbortSignal
  ) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;

    const payload = buildDemandForecastRequest(targetSnapshot);
    setDemandState((prev) => ({
      ...prev,
      status: "loading",
      errorMessage: null,
      classifiedError: null,
      requestPayload: payload,
    }));

    try {
      const client = new MarketProfitApiClient();
      const result = await client.getDemandForecast(payload, activeSignal);

      if (isPredictionAvailable(result)) {
        setDemandState({
          status: "available",
          response: result,
          errorMessage: null,
          classifiedError: null,
          requestPayload: payload,
        });
      } else {
        setDemandState({
          status: "unavailable",
          response: result,
          errorMessage: null,
          classifiedError: null,
          requestPayload: payload,
        });
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      const classified = classifyApiError(err, "Market Demand");
      setDemandState({
        status: "error",
        response: null,
        errorMessage: classified.message,
        classifiedError: classified,
        requestPayload: payload,
      });
    } finally {
      inFlightRef.current = false;
    }
  };

  useEffect(() => {
    if (!snapshot) return;

    const currentSignature = `${snapshot.crop_id}:${snapshot.cultivation_district_id}:${snapshot.target_market_id}:${snapshot.forecast_target_date || snapshot.harvest_date}`;

    if (lastFetchedSignatureRef.current === currentSignature) {
      return;
    }

    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    lastFetchedSignatureRef.current = currentSignature;

    executeDemandForecast(snapshot, controller.signal);

    return () => {
      controller.abort();
    };
  }, [snapshot]);

  const handleRetryDemand = () => {
    if (!snapshot) return;
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    executeDemandForecast(snapshot, controller.signal);
  };

  // Live Price Trend Forecast state
  const [priceState, setPriceState] = useState<{
    status: "idle" | "loading" | "available" | "unavailable" | "error";
    response: PriceForecastResponse | null;
    errorMessage: string | null;
    classifiedError: ClassifiedApiError | null;
    requestPayload: PriceForecastRequest | null;
  }>({
    status: "idle",
    response: null,
    errorMessage: null,
    classifiedError: null,
    requestPayload: null,
  });

  const priceInFlightRef = React.useRef(false);
  const priceLastFetchedSignatureRef = React.useRef<string | null>(null);
  const priceAbortControllerRef = React.useRef<AbortController | null>(null);

  const executePriceForecast = async (
    targetSnapshot: ValidatedAnalysisSnapshot,
    activeSignal?: AbortSignal
  ) => {
    if (priceInFlightRef.current) return;
    priceInFlightRef.current = true;

    const payload = buildPriceForecastRequest(targetSnapshot);
    setPriceState((prev) => ({
      ...prev,
      status: "loading",
      errorMessage: null,
      classifiedError: null,
      requestPayload: payload,
    }));

    try {
      const client = new MarketProfitApiClient();
      const result = await client.getPriceForecast(payload, activeSignal);

      if (isPricePredictionAvailable(result)) {
        setPriceState({
          status: "available",
          response: result,
          errorMessage: null,
          classifiedError: null,
          requestPayload: payload,
        });
      } else {
        setPriceState({
          status: "unavailable",
          response: result,
          errorMessage: null,
          classifiedError: null,
          requestPayload: payload,
        });
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      const classified = classifyApiError(err, "Price Forecast");
      setPriceState({
        status: "error",
        response: null,
        errorMessage: classified.message,
        classifiedError: classified,
        requestPayload: payload,
      });
    } finally {
      priceInFlightRef.current = false;
    }
  };

  useEffect(() => {
    if (!snapshot) return;

    const currentSignature = `${snapshot.crop_id}:${snapshot.cultivation_district_id}:${snapshot.target_market_id}:${snapshot.forecast_target_date || snapshot.harvest_date}:${snapshot.price_type}`;

    if (priceLastFetchedSignatureRef.current === currentSignature) {
      return;
    }

    priceAbortControllerRef.current?.abort();
    const controller = new AbortController();
    priceAbortControllerRef.current = controller;
    priceLastFetchedSignatureRef.current = currentSignature;

    executePriceForecast(snapshot, controller.signal);

    return () => {
      controller.abort();
    };
  }, [snapshot]);

  const handleRetryPrice = () => {
    if (!snapshot) return;
    priceAbortControllerRef.current?.abort();
    const controller = new AbortController();
    priceAbortControllerRef.current = controller;
    executePriceForecast(snapshot, controller.signal);
  };

  // Live Profit Risk Assessment state
  const [profitState, setProfitState] = useState<{
    status: "idle" | "loading" | "available" | "unavailable" | "error";
    calculation: ProfitCalculationResult | null;
    risk: ProfitRiskAssessmentResult | null;
    errorMessage: string | null;
    classifiedError: ClassifiedApiError | null;
    predictedPriceUsed: number | null;
  }>({
    status: "idle",
    calculation: null,
    risk: null,
    errorMessage: null,
    classifiedError: null,
    predictedPriceUsed: null,
  });

  const profitInFlightRef = React.useRef(false);
  const profitLastFetchedSignatureRef = React.useRef<string | null>(null);
  const profitAbortControllerRef = React.useRef<AbortController | null>(null);

  const executeProfitRiskAssessment = async (
    targetSnapshot: ValidatedAnalysisSnapshot,
    predictedPrice: number,
    activeSignal?: AbortSignal
  ) => {
    if (profitInFlightRef.current) return;
    profitInFlightRef.current = true;

    setProfitState((prev) => ({
      ...prev,
      status: "loading",
      errorMessage: null,
      classifiedError: null,
    }));

    try {
      const payload = buildProfitRiskAssessmentRequest(targetSnapshot, predictedPrice);
      const client = new MarketProfitApiClient();
      const result = await client.assessProfitRisk(payload, activeSignal);

      setProfitState({
        status: "available",
        calculation: result.profit_calculation,
        risk: result,
        errorMessage: null,
        classifiedError: null,
        predictedPriceUsed: predictedPrice,
      });
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      const classified = classifyApiError(err, "Profit Risk");
      setProfitState({
        status: "error",
        calculation: null,
        risk: null,
        errorMessage: classified.message,
        classifiedError: classified,
        predictedPriceUsed: null,
      });
    } finally {
      profitInFlightRef.current = false;
    }
  };

  useEffect(() => {
    if (!snapshot) return;

    if (priceState.status === "loading") {
      setProfitState((prev) => (prev.status !== "idle" ? { ...prev, status: "idle" } : prev));
      return;
    }

    if (priceState.status === "unavailable" || priceState.status === "idle") {
      profitAbortControllerRef.current?.abort();
      setProfitState({
        status: "unavailable",
        calculation: null,
        risk: null,
        errorMessage: null,
        classifiedError: null,
        predictedPriceUsed: null,
      });
      profitLastFetchedSignatureRef.current = null;
      return;
    }

    if (priceState.status === "error") {
      profitAbortControllerRef.current?.abort();
      setProfitState({
        status: "unavailable",
        calculation: null,
        risk: null,
        errorMessage: null,
        classifiedError: null,
        predictedPriceUsed: null,
      });
      profitLastFetchedSignatureRef.current = null;
      return;
    }

    if (priceState.status === "available" && priceState.response && isPricePredictionAvailable(priceState.response)) {
      const priceVal = Number(priceState.response.forecasted_price_lkr_per_kg);
      const currentSignature = `${snapshot.crop_id}:${snapshot.expected_yield_kg}:${snapshot.total_cultivation_cost}:${priceVal}`;

      if (profitLastFetchedSignatureRef.current === currentSignature) {
        return;
      }

      profitAbortControllerRef.current?.abort();
      const controller = new AbortController();
      profitAbortControllerRef.current = controller;
      profitLastFetchedSignatureRef.current = currentSignature;

      executeProfitRiskAssessment(snapshot, priceVal, controller.signal);

      return () => {
        controller.abort();
      };
    }
  }, [snapshot, priceState.status, priceState.response]);

  const handleRetryProfit = () => {
    if (!snapshot || !priceState.response || !isPricePredictionAvailable(priceState.response)) return;
    const priceVal = Number(priceState.response.forecasted_price_lkr_per_kg);
    profitAbortControllerRef.current?.abort();
    const controller = new AbortController();
    profitAbortControllerRef.current = controller;
    executeProfitRiskAssessment(snapshot, priceVal, controller.signal);
  };

  const handleStartNewAnalysis = () => {
    clearAnalysisSnapshot();
    router.push("/market-profit/new-analysis");
  };

  const handlePrint = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  // 1. Loading State
  if (status === "loading") {
    return (
      <div className="w-full max-w-4xl mx-auto py-16 text-center space-y-4">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-[#15803d] animate-pulse">
          <Sprout className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Getting your results...
        </h2>
        <p className="text-xs text-slate-500">
          Loading your farm inputs and calculations.
        </p>
      </div>
    );
  }

  // 2. Incomplete State (Validation Guard)
  if (status === "incomplete" || !snapshot) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-5 animate-in fade-in duration-200">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-700 shadow-2xs">
          <AlertCircle className="h-7 w-7" />
        </div>
        <div className="space-y-1.5">
          <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Please Complete Farm Details First
          </h2>
          <p className="text-sm text-slate-600 max-w-md mx-auto leading-relaxed">
            {errorMessage}
          </p>
        </div>
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href={redirectTarget}
            className="inline-flex items-center gap-2 rounded-xl bg-[#15803d] px-6 py-3 text-sm font-bold text-white hover:bg-[#166534] shadow-sm transition-all"
          >
            <span>Complete Farm Details</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/market-profit"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <span>Return to Dashboard</span>
          </Link>
        </div>
      </div>
    );
  }

  // Metadata resolution
  const cropMeta: FrontendCropMetadata | undefined =
    SUPPORTED_FRONTEND_CROPS.find((c) => c.crop_id === snapshot.crop_id);
  const districtMeta: DistrictMetadata | undefined =
    SRI_LANKA_DISTRICTS.find((d) => d.id === snapshot.cultivation_district_id);
  const marketMeta: MarketMetadata | undefined =
    STANDARD_MARKETS.find((m) => m.id === snapshot.target_market_id);
  const cropImage = CROP_IMAGE_MAP[snapshot.crop_id] || null;

  // Calculate planning horizon details without silent clamping
  const horizon = calculateHorizonWeeks(snapshot.harvest_date);

  // Active non-zero detailed expenses if detailed mode
  const activeDetailedItems =
    snapshot.metadata.budget_mode === "detailed" && snapshot.metadata.detailed_expenses
      ? DETAILED_EXPENSE_CATEGORIES.map((cat) => ({
          label: cat.label,
          key: cat.key,
          value: snapshot.metadata.detailed_expenses?.[cat.key] || "0",
        })).filter((item) => Number(item.value) > 0)
      : [];

  const netProfitValue = profitState.calculation ? Number(profitState.calculation.net_profit) : null;
  const isLoss = netProfitValue !== null && netProfitValue < 0;
  const isBreakEven = netProfitValue !== null && netProfitValue === 0;
  const absLoss = netProfitValue !== null ? Math.abs(netProfitValue) : 0;

  return (
    <div className="w-full max-w-4xl mx-auto pb-16 space-y-6 sm:space-y-8 animate-in fade-in duration-300">
      {/* Top Header & Fast Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 print:border-none">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Your Cultivation Results
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Expected market demand, selling price, and profit for your planned harvest.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto print:hidden">
          <Link
            href="/market-profit/new-analysis/cultivation-costs"
            className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 py-2.5 px-3.5 rounded-xl transition-all shadow-2xs"
          >
            <Edit3 className="h-4 w-4 text-slate-500" />
            <span>Change inputs</span>
          </Link>
          <button
            type="button"
            onClick={handleStartNewAnalysis}
            className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-bold text-emerald-800 bg-emerald-50 hover:bg-emerald-100/80 border border-emerald-200 py-2.5 px-3.5 rounded-xl transition-all cursor-pointer shadow-2xs"
          >
            <RotateCcw className="h-4 w-4 text-emerald-700" />
            <span>Start new analysis</span>
          </button>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* 1. TOP SUMMARY BAR: CROP PHOTOGRAPH BESIDE NAME & SUMMARY DETAILS     */}
      {/* ===================================================================== */}
      <section className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="flex items-center gap-4">
            {/* Dynamic Crop Photograph - Exactly 64px mobile, 80px desktop */}
            <div className="relative h-16 w-16 sm:h-20 sm:w-20 rounded-2xl overflow-hidden shrink-0 border-2 border-[#22A06B]/30 shadow-xs bg-slate-100">
              {cropImage ? (
                <Image
                  src={cropImage}
                  alt={cropMeta?.name_en || snapshot.crop_id}
                  fill
                  priority
                  sizes="(max-width: 640px) 64px, 80px"
                  className="object-cover"
                />
              ) : (
                <div className="h-full w-full flex items-center justify-center bg-emerald-50 text-[#166534]">
                  <Sprout className="h-8 w-8" />
                </div>
              )}
            </div>

            <div>
              <div className="flex items-baseline gap-2.5">
                <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                  {cropMeta?.name_en || snapshot.crop_id}
                </h2>
                <span className="text-sm sm:text-base font-bold text-[#166534]">
                  ({cropMeta?.name_si})
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs sm:text-sm text-slate-600 mt-1">
                <span className="font-semibold text-slate-800">{districtMeta?.name} District</span>
                <span>•</span>
                <span>{marketMeta?.name || snapshot.target_market_id}</span>
                <span>•</span>
                <span className="capitalize font-medium text-slate-700">{snapshot.price_type} price</span>
              </div>
            </div>
          </div>

          <div className="flex sm:flex-col items-start sm:items-end justify-between border-t sm:border-t-0 pt-3 sm:pt-0 border-slate-100 text-xs sm:text-sm">
            <span className="text-slate-500 font-medium">Expected Harvest</span>
            <div className="flex items-center gap-1.5 font-bold text-slate-900 sm:mt-0.5">
              <Calendar className="h-4 w-4 text-[#15803d]" />
              <span>{formatDateDisplay(snapshot.harvest_date)}</span>
            </div>
            <span className="text-xs text-[#166534] font-semibold mt-0.5">
              {horizon.weeks} {horizon.weeks === 1 ? "week" : "weeks"} ahead
              {!horizon.isSupportedRange ? " (outside 1–16 week forecast window)" : ""}
            </span>
          </div>
        </div>
      </section>

      {/* ===================================================================== */}
      {/* 2. THREE FULL-WIDTH PANELS STACKED VERTICALLY                         */}
      {/* ===================================================================== */}
      <div className="space-y-6">
        {/* =================================================================== */}
        {/* PANEL 1: MARKET DEMAND ANALYSIS                                     */}
        {/* =================================================================== */}
        <section className="rounded-3xl border border-slate-200/90 bg-white p-6 sm:p-7 shadow-xs space-y-5">
          {/* Section Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded-xl bg-[#E7F5EB] text-[#166534] flex items-center justify-center">
                <TrendingUp className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight">
                  Market Demand Analysis
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Projected wholesale buyer demand for your regional market.
                </p>
              </div>
            </div>
            {demandState.status === "available" && (
              <span className="hidden sm:inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-[#E7F5EB] text-[#166534]">
                Regional Forecast
              </span>
            )}
          </div>

          {/* Loading State */}
          {demandState.status === "loading" && (
            <div className="py-8 text-center space-y-3">
              <Loader2 className="h-8 w-8 animate-spin text-[#166534] mx-auto" />
              <p className="text-sm font-bold text-slate-700">Getting demand forecast...</p>
            </div>
          )}

          {/* Available State: Prominent Demand Status Area */}
          {demandState.status === "available" && demandState.response && (
            <div className="space-y-4">
              {/* Prominent Visual Status Card */}
              <div
                className={`p-5 sm:p-6 rounded-2xl border-2 flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                  demandState.response.projected_demand_level === "High"
                    ? "bg-gradient-to-r from-emerald-50 via-emerald-100/50 to-emerald-50 border-emerald-300 text-[#166534]"
                    : demandState.response.projected_demand_level === "Medium"
                    ? "bg-gradient-to-r from-blue-50 via-blue-100/50 to-blue-50 border-blue-300 text-blue-900"
                    : "bg-gradient-to-r from-amber-50 via-amber-100/50 to-amber-50 border-amber-300 text-amber-950"
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className="shrink-0">
                    {demandState.response.projected_demand_level === "High" && (
                      <div className="h-12 w-12 rounded-2xl bg-white text-[#166534] shadow-xs flex items-center justify-center">
                        <CheckCircle2 className="h-7 w-7" />
                      </div>
                    )}
                    {demandState.response.projected_demand_level === "Medium" && (
                      <div className="h-12 w-12 rounded-2xl bg-white text-blue-700 shadow-xs flex items-center justify-center">
                        <Info className="h-7 w-7" />
                      </div>
                    )}
                    {demandState.response.projected_demand_level === "Low" && (
                      <div className="h-12 w-12 rounded-2xl bg-white text-amber-700 shadow-xs flex items-center justify-center">
                        <AlertTriangle className="h-7 w-7" />
                      </div>
                    )}
                  </div>
                  <div>
                    <span className="text-xs uppercase font-extrabold tracking-wider opacity-75 block">
                      Market Demand Result
                    </span>
                    <span className="text-2xl sm:text-3xl font-black tracking-tight block">
                      {demandState.response.projected_demand_level === "High"
                        ? "High Demand"
                        : demandState.response.projected_demand_level === "Medium"
                        ? "Medium Demand"
                        : "Low Demand"}
                    </span>
                  </div>
                </div>

                <div className="sm:text-right max-w-sm">
                  <p className="text-xs sm:text-sm font-medium leading-relaxed">
                    {demandState.response.projected_demand_level === "High" &&
                      `Strong wholesale buyer demand expected at ${marketMeta?.name || "the market"} around your harvest date.`}
                    {demandState.response.projected_demand_level === "Medium" &&
                      `Steady buyer demand expected at ${marketMeta?.name || "the market"} around your harvest date.`}
                    {demandState.response.projected_demand_level === "Low" &&
                      `Lower buyer demand expected at ${marketMeta?.name || "the market"}. Consider harvest timing carefully.`}
                  </p>
                </div>
              </div>

              {/* Context Details Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-xs">
                  <span className="text-slate-400 font-bold uppercase block text-[10px]">
                    Reference Trading Hub
                  </span>
                  <span className="font-bold text-slate-900 block mt-0.5">
                    {marketMeta?.name || snapshot.target_market_id}
                  </span>
                  <span className="text-slate-500 text-[11px] block mt-0.5">
                    Forecast for harvest week ({formatDateDisplay(snapshot.harvest_date)})
                  </span>
                </div>

                {demandState.response.projected_demand_volume_kg !== null &&
                demandState.response.projected_demand_volume_kg !== undefined ? (
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-xs">
                    <span className="text-slate-400 font-bold uppercase block text-[10px]">
                      Estimated Market Arrival
                    </span>
                    <span className="font-bold text-slate-900 block mt-0.5">
                      {formatKg(demandState.response.projected_demand_volume_kg)}
                    </span>
                    <span className="text-slate-500 text-[11px] block mt-0.5 leading-tight">
                      Estimated regional market supply (not your individual harvest quantity or guaranteed purchases).
                    </span>
                  </div>
                ) : (
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-xs">
                    <span className="text-slate-400 font-bold uppercase block text-[10px]">
                      Demand Classification
                    </span>
                    <span className="font-bold text-slate-900 block mt-0.5">
                      Standard regional market evaluation complete
                    </span>
                    <span className="text-slate-500 text-[11px] block mt-0.5">
                      High demand indicates active buyer interest.
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Unavailable State */}
          {demandState.status === "unavailable" && (
            <div className="p-5 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-900 space-y-1.5">
              <span className="font-bold block text-sm">Prediction unavailable</span>
              <p className="text-slate-600 leading-relaxed">
                {demandState.response?.status_message ||
                  "Demand prediction is currently unavailable for this crop, market, or date."}
              </p>
            </div>
          )}

          {/* Error State */}
          {demandState.status === "error" && (
            <div className="p-5 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-900 space-y-2">
              <span className="font-bold block text-sm">Could not load market demand</span>
              <p className="text-slate-600 leading-relaxed">
                {demandState.errorMessage || "Unable to reach the forecasting service."}
              </p>
              <button
                type="button"
                onClick={handleRetryDemand}
                className="inline-flex items-center gap-1.5 font-bold text-xs text-rose-700 hover:text-rose-900 underline cursor-pointer"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Retry demand analysis</span>
              </button>
            </div>
          )}

          {demandState.status === "idle" && (
            <p className="text-xs text-slate-400 py-3 text-center">Waiting to start demand analysis...</p>
          )}
        </section>

        {/* =================================================================== */}
        {/* PANEL 2: PRICE TREND FORECAST                                       */}
        {/* =================================================================== */}
        <section className="rounded-3xl border border-slate-200/90 bg-white p-6 sm:p-7 shadow-xs space-y-5">
          {/* Section Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center">
                <Coins className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight">
                  Price Trend Forecast
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Expected regional selling price for your reference trading centre on your harvest date.
                </p>
              </div>
            </div>
            {priceState.status === "available" && (
              <span className="hidden sm:inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200">
                {snapshot.price_type === "retail" ? "Retail Tier" : "Wholesale Tier"}
              </span>
            )}
          </div>

          {/* Loading State */}
          {priceState.status === "loading" && (
            <div className="py-8 text-center space-y-3">
              <Loader2 className="h-8 w-8 animate-spin text-amber-600 mx-auto" />
              <p className="text-sm font-bold text-slate-700">Getting price forecast...</p>
            </div>
          )}

          {/* Available State: Prominent Forecasted Price */}
          {priceState.status === "available" && priceState.response && (
            <div className="space-y-4">
              <div className="p-5 sm:p-6 rounded-2xl border-2 border-amber-200 bg-gradient-to-r from-amber-50/80 via-white to-amber-50/40 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <span className="text-xs uppercase font-extrabold tracking-wider text-slate-500 block mb-1">
                    Forecasted price per kg
                  </span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
                      {formatLKR(Number(priceState.response.forecasted_price_lkr_per_kg))}
                    </span>
                    <span className="text-base sm:text-lg font-bold text-slate-600">/ kg</span>
                    <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 capitalize">
                      {snapshot.price_type}
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm text-slate-600 mt-1.5 leading-relaxed">
                    Projected regional selling price for {cropMeta?.name_en || "your crop"} at {marketMeta?.name || "the reference market"}.
                  </p>
                </div>

                <div className="sm:text-right border-t sm:border-t-0 pt-3 sm:pt-0 border-amber-100">
                  <div className="text-xs text-slate-500">Forecast Horizon</div>
                  <div className="text-sm font-bold text-slate-900 mt-0.5">
                    {horizon.weeks} {horizon.weeks === 1 ? "week" : "weeks"} ahead
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Target: {formatDateDisplay(snapshot.harvest_date)}
                  </div>
                </div>
              </div>

              {/* Context Details Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70 text-xs">
                  <span className="text-slate-400 font-bold uppercase block text-[10px]">
                    Commodity
                  </span>
                  <span className="font-bold text-slate-900 block mt-0.5 truncate">
                    {cropMeta?.name_en}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70 text-xs">
                  <span className="text-slate-400 font-bold uppercase block text-[10px]">
                    Reference Market
                  </span>
                  <span className="font-bold text-slate-900 block mt-0.5 truncate">
                    {marketMeta?.short_name || marketMeta?.name}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70 text-xs">
                  <span className="text-slate-400 font-bold uppercase block text-[10px]">
                    Price Tier
                  </span>
                  <span className="font-bold text-slate-900 block mt-0.5 capitalize truncate">
                    {snapshot.price_type} tier
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70 text-xs">
                  <span className="text-slate-400 font-bold uppercase block text-[10px]">
                    Currency &amp; Unit
                  </span>
                  <span className="font-bold text-slate-900 block mt-0.5 truncate">
                    LKR / 1 Kilogram
                  </span>
                </div>
              </div>

              {/* Regional Forecasting Note */}
              <div className="rounded-xl border border-amber-200/90 bg-amber-50/70 p-3 text-xs text-amber-950 flex items-center gap-2 shadow-2xs">
                <Info className="h-4 w-4 text-amber-700 shrink-0" />
                <span>Predictions are based on available regional historical data for Matara and Hambantota.</span>
              </div>
            </div>
          )}

          {/* Unavailable State */}
          {priceState.status === "unavailable" && (
            <div className="p-5 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-900 space-y-1.5">
              <span className="font-bold block text-sm">Prediction unavailable</span>
              <p className="text-slate-600 leading-relaxed">
                {priceState.response?.status_message ||
                  "Price forecast is currently unavailable for this crop, market, or date."}
              </p>
            </div>
          )}

          {/* Error State */}
          {priceState.status === "error" && (
            <div className="p-5 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-900 space-y-2">
              <span className="font-bold block text-sm">Could not load price</span>
              <p className="text-slate-600 leading-relaxed">
                {priceState.errorMessage || "Unable to reach the price forecasting service."}
              </p>
              <button
                type="button"
                onClick={handleRetryPrice}
                className="inline-flex items-center gap-1.5 font-bold text-xs text-rose-700 hover:text-rose-900 underline cursor-pointer"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Retry price forecast</span>
              </button>
            </div>
          )}

          {priceState.status === "idle" && (
            <p className="text-xs text-slate-400 py-3 text-center">Waiting to start price forecast...</p>
          )}
        </section>

        {/* =================================================================== */}
        {/* PANEL 3: PROFIT RISK ASSESSMENT                                     */}
        {/* =================================================================== */}
        <section className="rounded-3xl border border-slate-200/90 bg-white p-6 sm:p-7 shadow-xs space-y-5">
          {/* Section Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded-xl bg-[#E7F5EB] text-[#166534] flex items-center justify-center">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight">
                  Profit Risk Assessment
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Financial outcome, farming income, cultivation cost, and risk evaluation.
                </p>
              </div>
            </div>
            {profitState.status === "available" && profitState.risk && (
              <span
                className={`hidden sm:inline-flex items-center px-3 py-1 rounded-full text-xs font-bold ${
                  profitState.risk.risk_level === "Low"
                    ? "bg-[#E7F5EB] text-[#166534]"
                    : profitState.risk.risk_level === "Medium"
                    ? "bg-amber-100 text-amber-800"
                    : profitState.risk.risk_level === "High"
                    ? "bg-rose-100 text-rose-700"
                    : "bg-slate-100 text-slate-700"
                }`}
              >
                {profitState.risk.risk_level === "insufficient_information"
                  ? "Zero Cost Input"
                  : `${profitState.risk.risk_level} Risk Category`}
              </span>
            )}
          </div>

          {/* Loading State */}
          {profitState.status === "loading" && (
            <div className="py-8 text-center space-y-3">
              <Loader2 className="h-8 w-8 animate-spin text-[#166534] mx-auto" />
              <p className="text-sm font-bold text-slate-700">Calculating profit &amp; risk...</p>
            </div>
          )}

          {/* Available State: Both Risk Category & Profit/Loss Substantial & Prominent */}
          {profitState.status === "available" && profitState.calculation && profitState.risk && (
            <div className="space-y-4">
              {/* Dual Hero Cards: Risk Level (Card 1) & Estimated Outcome (Card 2) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 1. Substantial Profit Risk Category Card */}
                <div
                  className={`p-5 sm:p-6 rounded-2xl border-2 flex flex-col justify-between ${
                    profitState.risk.risk_level === "Low"
                      ? "bg-gradient-to-br from-emerald-50 via-white to-emerald-50/60 border-emerald-300"
                      : profitState.risk.risk_level === "Medium"
                      ? "bg-gradient-to-br from-amber-50 via-white to-amber-50/60 border-amber-300"
                      : profitState.risk.risk_level === "High"
                      ? "bg-gradient-to-br from-rose-50 via-white to-rose-50/60 border-rose-300"
                      : "bg-gradient-to-br from-slate-50 via-white to-slate-50/60 border-slate-300"
                  }`}
                >
                  <div>
                    <span className="text-xs uppercase font-extrabold tracking-wider text-slate-500 block mb-2">
                      Profit Risk Level
                    </span>
                    <div className="flex items-center gap-3">
                      <div
                        className={`h-11 w-11 rounded-xl flex items-center justify-center shrink-0 ${
                          profitState.risk.risk_level === "Low"
                            ? "bg-[#166534] text-white"
                            : profitState.risk.risk_level === "Medium"
                            ? "bg-amber-600 text-white"
                            : profitState.risk.risk_level === "High"
                            ? "bg-rose-600 text-white"
                            : "bg-slate-600 text-white"
                        }`}
                      >
                        {profitState.risk.risk_level === "Low" && <ShieldCheck className="h-6 w-6" />}
                        {profitState.risk.risk_level === "Medium" && <AlertTriangle className="h-6 w-6" />}
                        {profitState.risk.risk_level === "High" && <AlertCircle className="h-6 w-6" />}
                        {profitState.risk.risk_level === "insufficient_information" && <Info className="h-6 w-6" />}
                      </div>

                      <span
                        className={`text-2xl sm:text-3xl font-black tracking-tight ${
                          profitState.risk.risk_level === "Low"
                            ? "text-[#166534]"
                            : profitState.risk.risk_level === "Medium"
                            ? "text-amber-900"
                            : profitState.risk.risk_level === "High"
                            ? "text-rose-700"
                            : "text-slate-800"
                        }`}
                      >
                        {profitState.risk.risk_level === "insufficient_information"
                          ? "Needs Cost Details"
                          : `${profitState.risk.risk_level} Risk`}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs sm:text-sm text-slate-600 mt-3 pt-3 border-t border-slate-200/70 leading-relaxed font-medium">
                    {profitState.risk.risk_level === "Low" &&
                      "Strong profit safety margin against unexpected market price drops."}
                    {profitState.risk.risk_level === "Medium" &&
                      "Profitable, but profit margin is sensitive to market price drops."}
                    {profitState.risk.risk_level === "High" &&
                      "High financial risk. Expected income may not cover cultivation costs."}
                    {profitState.risk.risk_level === "insufficient_information" &&
                      "Farming cost entered as Rs. 0. Enter your costs to calculate financial risk."}
                  </p>
                </div>

                {/* 2. Substantial Estimated Profit / Estimated Loss Card */}
                <div
                  className={`p-5 sm:p-6 rounded-2xl border-2 flex flex-col justify-between ${
                    isLoss
                      ? "bg-gradient-to-br from-rose-50 via-white to-rose-50/60 border-rose-300"
                      : isBreakEven
                      ? "bg-gradient-to-br from-slate-50 via-white to-slate-50/60 border-slate-300"
                      : "bg-gradient-to-br from-emerald-50 via-white to-emerald-50/60 border-emerald-300"
                  }`}
                >
                  <div>
                    <span className="text-xs uppercase font-extrabold tracking-wider text-slate-500 block mb-2">
                      {isLoss ? "Estimated Loss" : isBreakEven ? "Estimated Outcome" : "Estimated Profit"}
                    </span>
                    <div
                      className={`text-2xl sm:text-3xl font-black tracking-tight ${
                        isLoss
                          ? "text-rose-600"
                          : isBreakEven
                          ? "text-slate-800"
                          : "text-[#166534]"
                      }`}
                    >
                      {isLoss
                        ? formatLKR(absLoss)
                        : isBreakEven
                        ? "Rs. 0 (Break-even)"
                        : `+${formatLKR(netProfitValue || 0)}`}
                    </div>
                  </div>

                  <p className="text-xs sm:text-sm mt-3 pt-3 border-t border-slate-200/70 leading-relaxed font-medium">
                    {isLoss ? (
                      <span className="text-rose-700">
                        Your expected income is below your farming cost.
                      </span>
                    ) : isBreakEven ? (
                      <span className="text-slate-600">
                        Expected income exactly covers your farming cost.
                      </span>
                    ) : (
                      <span className="text-slate-600">
                        Calculated from your planned harvest yield and forecasted price.
                      </span>
                    )}
                  </p>
                </div>
              </div>

              {/* Financial Breakdown Bar */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-xs flex justify-between sm:flex-col sm:justify-start">
                  <span className="text-slate-500 uppercase font-bold text-[10px]">
                    Expected Income
                  </span>
                  <span className="font-extrabold text-slate-900 text-sm mt-0.5">
                    {formatLKR(Number(profitState.calculation.gross_revenue))}
                  </span>
                  <span className="text-[11px] text-slate-400 hidden sm:block mt-0.5">
                    {formatKg(snapshot.expected_yield_kg)} planned yield
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-xs flex justify-between sm:flex-col sm:justify-start">
                  <span className="text-slate-500 uppercase font-bold text-[10px]">
                    Total Farming Cost
                  </span>
                  <span className="font-extrabold text-slate-900 text-sm mt-0.5">
                    {formatLKR(Number(profitState.calculation.total_cultivation_cost))}
                  </span>
                  <span className="text-[11px] text-slate-400 hidden sm:block mt-0.5 capitalize">
                    {snapshot.metadata.budget_mode} budget mode
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-xs flex justify-between sm:flex-col sm:justify-start">
                  <span className="text-slate-500 uppercase font-bold text-[10px]">
                    Planned Land Extent
                  </span>
                  <span className="font-extrabold text-slate-900 text-sm mt-0.5">
                    {snapshot.metadata.land_extent_acres_string} Acres
                  </span>
                  <span className="text-[11px] text-slate-400 hidden sm:block mt-0.5">
                    {districtMeta?.name} District
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Unavailable State */}
          {profitState.status === "unavailable" && (
            <div className="p-5 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-900 space-y-1.5">
              <span className="font-bold block text-sm">Prediction unavailable</span>
              <p className="text-slate-600 leading-relaxed">
                Profit and risk calculation requires a valid selling price forecast.
              </p>
            </div>
          )}

          {/* Error State */}
          {profitState.status === "error" && (
            <div className="p-5 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-900 space-y-2">
              <span className="font-bold block text-sm">Could not calculate profit</span>
              <p className="text-slate-600 leading-relaxed">
                {profitState.errorMessage || "Unable to reach the calculation service."}
              </p>
              <button
                type="button"
                onClick={handleRetryProfit}
                className="inline-flex items-center gap-1.5 font-bold text-xs text-rose-700 hover:text-rose-900 underline cursor-pointer"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Retry profit calculation</span>
              </button>
            </div>
          )}

          {profitState.status === "idle" && (
            <p className="text-xs text-slate-400 py-3 text-center">Waiting for price forecast before calculating profit...</p>
          )}
        </section>
      </div>

      {/* ===================================================================== */}
      {/* 3. MORE DETAILS (SECONDARY INFORMATION ACCORDION)                     */}
      {/* ===================================================================== */}
      <details className="group rounded-3xl border border-slate-200 bg-white p-5 sm:p-6 shadow-xs">
        <summary className="flex items-center justify-between font-bold text-sm text-slate-800 cursor-pointer list-none select-none">
          <span className="flex items-center gap-2">
            <Info className="h-4 w-4 text-[#166534]" />
            <span>More details</span>
          </span>
          <span className="text-xs text-[#166534] font-semibold group-open:hidden">
            Show details &darr;
          </span>
          <span className="text-xs text-[#166534] font-semibold hidden group-open:inline">
            Hide details &uarr;
          </span>
        </summary>

        <div className="pt-5 mt-4 border-t border-slate-100 space-y-5 text-xs text-slate-700 animate-in fade-in duration-200">
          {/* Farm Details Grid */}
          <div>
            <h4 className="font-bold text-slate-900 text-sm mb-3">Your farm details</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Candidate Crop</span>
                <span className="font-bold text-slate-900 block mt-0.5">{cropMeta?.name_en || snapshot.crop_id}</span>
                <span className="text-[11px] text-slate-500 block">{cropMeta?.category}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">District</span>
                <span className="font-bold text-slate-900 block mt-0.5">{districtMeta?.name}</span>
                <span className="text-[11px] text-slate-500 block">{districtMeta?.zone}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Land Extent</span>
                <span className="font-bold text-slate-900 block mt-0.5">{snapshot.metadata.land_extent_acres_string} Acres</span>
                <span className="text-[11px] text-slate-500 block">Planned field size</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Expected Yield</span>
                <span className="font-bold text-slate-900 block mt-0.5">{formatKg(snapshot.expected_yield_kg)}</span>
                <span className="text-[11px] text-slate-500 block">Total production</span>
              </div>
            </div>
          </div>

          {/* Break-Even Minimum Selling Price */}
          {profitState.calculation?.breakeven_price_lkr_per_kg && (
            <div className="p-3.5 rounded-xl bg-[#E7F5EB]/60 border border-[#22A06B]/30 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span className="font-bold text-slate-900 block">
                  Minimum selling price needed to cover costs
                </span>
                <span className="text-slate-600 text-[11.5px] block mt-0.5">
                  You need to sell at or above this price to cover your farming costs.
                </span>
              </div>
              <div className="text-lg font-extrabold text-[#166534]">
                {formatLKR(Number(profitState.calculation.breakeven_price_lkr_per_kg))} / kg
              </div>
            </div>
          )}

          {/* Itemized Cost Breakdown (If Detailed Budget Mode was Used) */}
          {activeDetailedItems.length > 0 && (
            <div>
              <h4 className="font-bold text-slate-900 text-sm mb-2">Itemized farming costs</h4>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                {activeDetailedItems.map((item) => (
                  <div
                    key={item.key}
                    className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/70"
                  >
                    <span className="text-[10px] text-slate-500 uppercase block truncate">
                      {item.label}
                    </span>
                    <span className="font-bold text-slate-900 block mt-0.5">
                      {formatLKR(item.value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Return on Investment and Margin */}
          {profitState.calculation && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70 flex justify-between items-center">
                <span className="text-slate-600">Return on investment (ROI):</span>
                <strong className="text-slate-900">
                  {profitState.calculation.roi_percentage !== null &&
                  profitState.calculation.roi_percentage !== undefined
                    ? `${Number(profitState.calculation.roi_percentage) >= 0 ? "+" : ""}${formatPercent(
                        Number(profitState.calculation.roi_percentage)
                      )}`
                    : "Undefined (cost Rs. 0)"}
                </strong>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70 flex justify-between items-center">
                <span className="text-slate-600">Profit margin:</span>
                <strong className="text-slate-900">
                  {formatPercent(Number(profitState.calculation.margin_of_safety_percentage))}
                </strong>
              </div>
            </div>
          )}
        </div>
      </details>

      {/* Brief Reminder Notice */}
      <div className="text-center py-2">
        <p className="text-xs text-slate-500 font-medium">
          These are estimates. Actual prices and harvest may change.
        </p>
      </div>

      {/* ===================================================================== */}
      {/* 4. ACTIONS BAR                                                        */}
      {/* ===================================================================== */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-slate-200 print:hidden">
        <Link
          href="/market-profit/new-analysis/cultivation-costs"
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 px-6 py-3 text-sm font-bold shadow-2xs transition-all text-center"
        >
          <ArrowLeft className="h-4 w-4 text-slate-500" />
          <span>Change inputs</span>
        </Link>

        <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
          <button
            type="button"
            onClick={handlePrint}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 px-5 py-3 text-sm font-bold shadow-2xs transition-all text-center cursor-pointer"
          >
            <Printer className="h-4 w-4 text-slate-500" />
            <span>Print / Save PDF</span>
          </button>
          <button
            type="button"
            onClick={handleStartNewAnalysis}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-[#15803d] hover:bg-[#166534] active:scale-95 text-white px-7 py-3 text-sm font-bold shadow-sm shadow-emerald-800/20 transition-all cursor-pointer text-center"
          >
            <RotateCcw className="h-4 w-4" />
            <span>Start new analysis</span>
          </button>
        </div>
      </div>
    </div>
  );
}
