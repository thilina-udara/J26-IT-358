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
  Sparkles,
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
} from "lucide-react";

import {
  SUPPORTED_FRONTEND_CROPS,
  SRI_LANKA_DISTRICTS,
  STANDARD_MARKETS,
  FrontendCropMetadata,
  DistrictMetadata,
  MarketMetadata,
  DEFAULT_API_BASE_URL,
} from "../lib/constants";
import { formatDateDisplay, formatKg, formatLKR, formatPercent } from "../lib/formatters";
import { MarketProfitApiClient, ApiError } from "../lib/api";
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
          "Please complete all four wizard steps before viewing analysis results."
      );
    }
  }, []);

  // Live Market Demand Analysis state
  const [demandState, setDemandState] = useState<{
    status: "idle" | "loading" | "available" | "unavailable" | "error";
    response: DemandForecastResponse | null;
    errorMessage: string | null;
    requestPayload: DemandForecastRequest | null;
  }>({
    status: "idle",
    response: null,
    errorMessage: null,
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
          requestPayload: payload,
        });
      } else if (isPredictionUnavailable(result)) {
        setDemandState({
          status: "unavailable",
          response: result,
          errorMessage: null,
          requestPayload: payload,
        });
      } else {
        setDemandState({
          status: "unavailable",
          response: result,
          errorMessage: null,
          requestPayload: payload,
        });
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : String(err);
      setDemandState({
        status: "error",
        response: null,
        errorMessage: msg,
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

  // Live Price Trend Forecast state (POST /api/v1/market-prices/forecast)
  const [priceState, setPriceState] = useState<{
    status: "idle" | "loading" | "available" | "unavailable" | "error";
    response: PriceForecastResponse | null;
    errorMessage: string | null;
    requestPayload: PriceForecastRequest | null;
  }>({
    status: "idle",
    response: null,
    errorMessage: null,
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
          requestPayload: payload,
        });
      } else if (isPricePredictionUnavailable(result)) {
        setPriceState({
          status: "unavailable",
          response: result,
          errorMessage: null,
          requestPayload: payload,
        });
      } else {
        setPriceState({
          status: "unavailable",
          response: result,
          errorMessage: null,
          requestPayload: payload,
        });
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : String(err);
      setPriceState({
        status: "error",
        response: null,
        errorMessage: msg,
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

  // Live Profit & Risk Assessment state (POST /api/v1/profit-analyses/assess-risk)
  const [profitState, setProfitState] = useState<{
    status: "idle" | "loading" | "available" | "unavailable" | "error";
    calculation: ProfitCalculationResult | null;
    risk: ProfitRiskAssessmentResult | null;
    errorMessage: string | null;
    predictedPriceUsed: number | null;
  }>({
    status: "idle",
    calculation: null,
    risk: null,
    errorMessage: null,
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
        predictedPriceUsed: predictedPrice,
      });
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : String(err);
      setProfitState({
        status: "error",
        calculation: null,
        risk: null,
        errorMessage: msg,
        predictedPriceUsed: null,
      });
    } finally {
      profitInFlightRef.current = false;
    }
  };

  useEffect(() => {
    if (!snapshot) return;

    // Prerequisite check: requires valid completed price forecast
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

  // Handler to start a new analysis
  const handleStartNewAnalysis = () => {
    clearAnalysisSnapshot();
    router.push("/market-profit/new-analysis");
  };

  // 1. Loading State
  if (status === "loading") {
    return (
      <div className="w-full max-w-5xl mx-auto py-16 text-center space-y-4">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-[#15803d] animate-pulse">
          <Sprout className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Loading Analysis Parameters...
        </h2>
        <p className="text-xs text-slate-500">
          Verifying farm inputs and session integrity.
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
            Wizard Steps Incomplete
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
            <span>Complete Required Step</span>
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

  const isPilotDistrict = Boolean(districtMeta?.is_pilot);
  const isPilotMarket = Boolean(marketMeta?.is_pilot_recommended);
  const isZeroCost = snapshot.metadata.is_zero_cultivation_cost;

  // Active non-zero detailed expenses if detailed mode
  const activeDetailedItems =
    snapshot.metadata.budget_mode === "detailed" && snapshot.metadata.detailed_expenses
      ? DETAILED_EXPENSE_CATEGORIES.map((cat) => ({
          label: cat.label,
          key: cat.key,
          value: snapshot.metadata.detailed_expenses?.[cat.key] || "0",
        })).filter((item) => Number(item.value) > 0)
      : [];

  return (
    <div className="w-full max-w-5xl mx-auto pb-16 space-y-8 animate-in fade-in duration-300">
      {/* Top Header & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-[#15803d] tracking-wide uppercase">
            <span>AgroDecision</span>
            <span>•</span>
            <span>Analysis Overview</span>
            <span>•</span>
            <span>Handoff Stage</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mt-1">
            Analysis Results Overview
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl leading-relaxed">
            Your cultivation plan has been verified across all 4 wizard steps. Below are your confirmed farm inputs and the status of upcoming machine learning analysis sections.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <Link
            href="/market-profit/new-analysis/cultivation-costs"
            className="inline-flex items-center gap-2 text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 py-2.5 px-3.5 rounded-xl transition-all shadow-2xs"
          >
            <Edit3 className="h-3.5 w-3.5 text-slate-500" />
            <span>Edit Wizard Inputs</span>
          </Link>
          <button
            type="button"
            onClick={handleStartNewAnalysis}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-800 bg-emerald-50 hover:bg-emerald-100/80 border border-emerald-200 py-2.5 px-3.5 rounded-xl transition-all cursor-pointer shadow-2xs"
          >
            <RotateCcw className="h-3.5 w-3.5 text-emerald-700" />
            <span>Start Fresh</span>
          </button>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* SECTION 1: CONFIRMED FARMER INPUTS (All 8 verified parameters)       */}
      {/* ===================================================================== */}
      <div className="rounded-3xl border border-emerald-200/90 bg-white p-6 sm:p-7 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-[#15803d]">
              <CheckCircle2 className="h-5 w-5 stroke-[2.3]" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 tracking-tight">
                Confirmed Farm Parameters
              </h2>
              <p className="text-xs text-slate-500">
                All 4 wizard steps validated and preserved in session storage
              </p>
            </div>
          </div>

          <span className="text-xs font-extrabold uppercase tracking-wide bg-emerald-100 text-[#166534] px-3 py-1 rounded-full border border-emerald-200 self-start sm:self-auto">
            4 of 4 Steps Complete
          </span>
        </div>

        {/* 8 Farmer Inputs Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {/* 1. Crop */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                1. Candidate Crop
              </span>
              <Sprout className="h-4 w-4 text-[#15803d]" />
            </div>
            <div className="flex items-center gap-3">
              {cropImage && (
                <div className="relative h-11 w-11 rounded-xl overflow-hidden shrink-0 border border-emerald-200">
                  <Image
                    src={cropImage}
                    alt={cropMeta?.name_en || snapshot.crop_id}
                    fill
                    className="object-cover"
                  />
                </div>
              )}
              <div className="min-w-0">
                <span className="text-sm font-bold text-slate-900 block truncate">
                  {cropMeta?.name_en || snapshot.crop_id}
                </span>
                <span className="text-xs text-slate-500 block truncate">
                  {cropMeta?.name_si} • {cropMeta?.category}
                </span>
              </div>
            </div>
          </div>

          {/* 2. District */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                2. District
              </span>
              <MapPin className="h-4 w-4 text-[#15803d]" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 truncate">
                {districtMeta?.name || snapshot.cultivation_district_id}
              </div>
              <div className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
                <span>{districtMeta?.zone}</span>
                {isPilotDistrict && (
                  <span className="text-[10px] font-bold bg-emerald-100 text-[#166534] px-1.5 py-0.2 rounded">
                    Pilot
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* 3. Expected Harvest Date */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                3. Harvest Date
              </span>
              <Calendar className="h-4 w-4 text-[#15803d]" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 truncate">
                {formatDateDisplay(snapshot.harvest_date)}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Date: {snapshot.harvest_date}
              </div>
            </div>
          </div>

          {/* 4. Land Extent */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                4. Cultivation Extent
              </span>
              <Compass className="h-4 w-4 text-[#15803d]" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 truncate">
                {snapshot.metadata.land_extent_acres_string} Acres
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Farm area under cultivation
              </div>
            </div>
          </div>

          {/* 5. Expected Yield */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                5. Expected Yield
              </span>
              <Scale className="h-4 w-4 text-[#15803d]" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 truncate">
                {formatKg(snapshot.expected_yield_kg)}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Total planned harvest volume
              </div>
            </div>
          </div>

          {/* 6. Selling Market */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                6. Selling Market
              </span>
              <Store className="h-4 w-4 text-[#15803d]" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 truncate">
                {marketMeta?.name || snapshot.target_market_id}
              </div>
              <div className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
                <span>{marketMeta?.region || "Economic Centre"}</span>
                {isPilotMarket && (
                  <span className="text-[10px] font-bold bg-emerald-100 text-[#166534] px-1.5 py-0.2 rounded">
                    Pilot Hub
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* 7. Price Type */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                7. Price Type
              </span>
              <Tag className="h-4 w-4 text-[#15803d]" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 capitalize truncate">
                {snapshot.price_type} Price
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                {snapshot.price_type === "retail" ? "Consumer Market" : "Trade / Bulk Market"}
              </div>
            </div>
          </div>

          {/* 8. Cultivation Budget */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                8. Cultivation Cost
              </span>
              {snapshot.metadata.budget_mode === "detailed" ? (
                <Receipt className="h-4 w-4 text-[#15803d]" />
              ) : (
                <Wallet className="h-4 w-4 text-[#15803d]" />
              )}
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 truncate">
                {formatLKR(snapshot.total_cultivation_cost)}
              </div>
              <div className="text-xs text-slate-500 mt-0.5 capitalize">
                {snapshot.metadata.budget_mode === "detailed" ? "Detailed Budget" : "Quick Budget"}
              </div>
            </div>
          </div>
        </div>

        {/* Zero-Cost Advisory Warning */}
        {isZeroCost && (
          <div className="flex items-start gap-2.5 p-3.5 rounded-2xl bg-amber-50 border border-amber-200 text-amber-800 text-xs">
            <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
            <div>
              <span className="font-bold block">Advisory Note on Zero Cultivation Cost:</span>
              <span>
                Cultivation cost is recorded as Rs. 0. Profit margins, return on investment (ROI), and margin of safety evaluations will be unavailable or limited when financial analysis calculations activate.
              </span>
            </div>
          </div>
        )}

        {/* Detailed Cost Breakdown preview (if detailed mode and active categories exist) */}
        {activeDetailedItems.length > 0 && (
          <div className="pt-2 border-t border-slate-100">
            <span className="text-xs font-bold text-slate-700 block mb-2">
              Itemized Expenses Breakdown ({activeDetailedItems.length} categories):
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
              {activeDetailedItems.map((item) => (
                <div
                  key={item.key}
                  className="p-2 rounded-xl bg-slate-50 border border-slate-200/60 text-[11px]"
                >
                  <span className="text-slate-500 block truncate">{item.label}</span>
                  <span className="font-bold text-slate-900 block">{formatLKR(item.value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ===================================================================== */}
      {/* SECTION 2: TRANSPARENCY NOTICE (No fake data statement)              */}
      {/* ===================================================================== */}
      <div className="flex items-start gap-3.5 p-4 sm:p-5 rounded-2xl bg-slate-100/80 border border-slate-200 text-slate-700 text-xs leading-relaxed">
        <Sparkles className="h-5 w-5 text-[#15803d] shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-slate-900 block text-sm mb-0.5">
            Upcoming Machine Learning &amp; Risk Analytics Integration
          </span>
          <p className="text-slate-600">
            All four wizard steps are now complete, validated, and stored in your session. In the next milestone, AgroDecision&apos;s machine learning models will connect to forecast seasonal demand volumes, predict economic centre market prices, and assess financial feasibility.
            <strong className="text-slate-900 ml-1">
              No mock, invented, or fabricated prediction data is displayed on this page.
            </strong>
          </p>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* SECTION 3: MARKET DEMAND ANALYSIS (LIVE FASTAPI INTEGRATION)         */}
      {/* ===================================================================== */}
      <div className="space-y-4">
        <div>
          <span className="text-xs font-bold text-[#15803d] uppercase tracking-wider">
            Analytical Pipeline 1 of 3
          </span>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight mt-0.5">
            Market Demand Analysis
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Live integration with FastAPI ML prediction pipeline (<code>POST /api/v1/market-demands/forecast</code>)
          </p>
        </div>

        {/* Featured Market Demand Analysis Card */}
        <div className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-7 shadow-xs space-y-6">
          {/* Card Header & Status Badge */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-[#15803d]">
                <TrendingUp className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Harvest Arrival Demand Projection
                </h3>
                <span className="text-xs text-slate-500">
                  Target Destination: {marketMeta?.name || snapshot.target_market_id}
                </span>
              </div>
            </div>

            {/* Live State Badge */}
            <div>
              {demandState.status === "loading" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-sky-800 bg-sky-100/90 px-3 py-1.5 rounded-full border border-sky-200">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-600" />
                  <span>Querying Model...</span>
                </span>
              )}
              {demandState.status === "available" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-800 bg-emerald-100 px-3 py-1.5 rounded-full border border-emerald-300">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-700" />
                  <span>Prediction Available</span>
                </span>
              )}
              {demandState.status === "unavailable" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-800 bg-amber-100/90 px-3 py-1.5 rounded-full border border-amber-300">
                  <Clock className="h-3.5 w-3.5 text-amber-700" />
                  <span>Model Offline / Training</span>
                </span>
              )}
              {demandState.status === "error" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-rose-800 bg-rose-100 px-3 py-1.5 rounded-full border border-rose-300">
                  <AlertTriangle className="h-3.5 w-3.5 text-rose-700" />
                  <span>Service Connection Error</span>
                </span>
              )}
              {demandState.status === "idle" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
                  <Clock className="h-3.5 w-3.5 text-slate-500" />
                  <span>Initializing...</span>
                </span>
              )}
            </div>
          </div>

          {/* 4 Confirmed Farm Input Parameters Required for Demand Analysis (Task 2) */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
              Forecasting Parameters
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Selected Crop</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                  {cropMeta?.name_en || snapshot.crop_id}
                </span>
                <span className="text-[11px] text-slate-500 block truncate">
                  {cropMeta?.name_si}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Cultivation District</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                  {districtMeta?.name || snapshot.cultivation_district_id}
                </span>
                <span className="text-[11px] text-slate-500 block truncate">
                  {districtMeta?.zone}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Expected Harvest Date</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                  {formatDateDisplay(snapshot.harvest_date)}
                </span>
                <span className="text-[11px] text-slate-500 block font-mono text-[10px]">
                  {snapshot.harvest_date}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Target Selling Market</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                  {marketMeta?.short_name || marketMeta?.name || snapshot.target_market_id}
                </span>
                <span className="text-[11px] text-slate-500 block truncate">
                  {marketMeta?.region || "Economic Centre"}
                </span>
              </div>
            </div>
          </div>

          {/* Dynamic State Views */}
          {/* State 1: Loading */}
          {demandState.status === "loading" && (
            <div className="p-5 rounded-2xl bg-sky-50/70 border border-sky-200/80 flex items-start gap-4 animate-in fade-in duration-150">
              <Loader2 className="h-5 w-5 text-sky-600 animate-spin shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="text-sm font-bold text-sky-950">
                  Querying Market Demand Analysis API...
                </div>
                <p className="text-xs text-sky-800 leading-relaxed">
                  Connecting to <code>POST /api/v1/market-demands/forecast</code> for {cropMeta?.name_en || "your crop"} at {marketMeta?.name || "your target market"}. Evaluating arrival dates and regional demand pressure.
                </p>
              </div>
            </div>
          )}

          {/* State 2: Prediction Available */}
          {demandState.status === "available" && demandState.response && (
            <div className="space-y-4 animate-in fade-in duration-200">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Demand Level Card */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50/60 space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Categorical Demand Level
                  </span>
                  <div>
                    {demandState.response.projected_demand_level === "High" && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300">
                        High Demand
                      </span>
                    )}
                    {demandState.response.projected_demand_level === "Medium" && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-extrabold bg-blue-100 text-blue-800 border border-blue-300">
                        Medium Demand
                      </span>
                    )}
                    {demandState.response.projected_demand_level === "Low" && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-extrabold bg-amber-100 text-amber-800 border border-amber-300">
                        Low Demand
                      </span>
                    )}
                    {!demandState.response.projected_demand_level && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold bg-slate-200 text-slate-700">
                        Not Classified
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed pt-1">
                    {demandState.response.projected_demand_level === "High" &&
                      "Strong buyer purchasing interest expected at market hub on harvest date."}
                    {demandState.response.projected_demand_level === "Medium" &&
                      "Balanced market demand and steady buyer activity anticipated."}
                    {demandState.response.projected_demand_level === "Low" &&
                      "Lower buyer demand pressure or potential market surplus projected."}
                    {!demandState.response.projected_demand_level &&
                      "Model did not return a categorical demand tier."}
                  </p>
                </div>

                {/* Projected Demand Volume Card */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50/60 space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Projected Demand Volume (kg)
                  </span>
                  <div className="text-xl font-extrabold text-slate-900">
                    {demandState.response.projected_demand_volume_kg !== null &&
                    demandState.response.projected_demand_volume_kg !== undefined
                      ? formatKg(demandState.response.projected_demand_volume_kg)
                      : "Not specified by model"}
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Estimated total commodity volume absorbed by buyer arrivals at the destination market centre.
                  </p>
                </div>
              </div>

              {/* Model Provenance & Status Note */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3.5 rounded-2xl bg-emerald-50/60 border border-emerald-200/80 text-xs text-emerald-900">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-700 shrink-0" />
                  <span>
                    Model Version:{" "}
                    <strong>{demandState.response.model_version || "Default ML Pipeline"}</strong>
                  </span>
                </div>
                <span className="text-emerald-700 text-[11px]">
                  {demandState.response.status_message}
                </span>
              </div>
            </div>
          )}

          {/* State 3: Prediction Unavailable */}
          {demandState.status === "unavailable" && (
            <div className="space-y-4 animate-in fade-in duration-200">
              <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 sm:p-5 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                  <Clock className="h-4 w-4 text-amber-700" />
                  <span>Machine Learning Demand Prediction Model is Currently Offline</span>
                </div>
                <p className="text-xs text-amber-900 leading-relaxed">
                  {demandState.response?.status_message ||
                    "Machine learning demand prediction model is currently offline or undergoing training."}
                </p>
                <p className="text-[11px] text-amber-800 leading-relaxed pt-1 border-t border-amber-200/60">
                  Our machine learning pipeline will categorize buyer demand pressure (High, Medium, Low) and estimate demand volumes for {cropMeta?.name_en || "your crop"} at {marketMeta?.name || "the market"} once trained weights are deployed.
                  <strong className="text-amber-950 ml-1">
                    In accordance with our research integrity guidelines, no mock, synthetic, or estimated demand figures are displayed.
                  </strong>
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
                  <span className="text-xs text-slate-500">Projected Demand Volume:</span>
                  <span className="text-xs font-bold text-slate-400">Unavailable (Model Offline)</span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
                  <span className="text-xs text-slate-500">Demand Category:</span>
                  <span className="text-xs font-bold text-slate-400">Unavailable (Model Offline)</span>
                </div>
              </div>
            </div>
          )}

          {/* State 4: Request Failed (Error) */}
          {demandState.status === "error" && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-4 sm:p-5 space-y-3 animate-in fade-in duration-200">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="text-sm font-bold text-rose-950">
                    Unable to Connect to Demand Forecasting Service
                  </div>
                  <p className="text-xs text-rose-800 leading-relaxed">
                    {demandState.errorMessage}
                  </p>
                  <p className="text-[11px] text-rose-700 pt-1">
                    Please verify that the FastAPI backend service is running on port 8001 (or configured via <code>NEXT_PUBLIC_MARKET_PROFIT_API_URL</code>).
                  </p>
                </div>
              </div>
              <div className="pt-2 flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleRetryDemand}
                  className="inline-flex items-center gap-2 rounded-xl bg-rose-700 hover:bg-rose-800 active:scale-95 text-white px-4 py-2 text-xs font-bold shadow-xs transition-all cursor-pointer"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>Retry Demand Analysis</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ===================================================================== */}
      {/* SECTION 4: PRICE TREND FORECAST (LIVE FASTAPI INTEGRATION)           */}
      {/* ===================================================================== */}
      <div className="space-y-4">
        <div>
          <span className="text-xs font-bold text-[#15803d] uppercase tracking-wider">
            Analytical Pipeline 2 of 3
          </span>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight mt-0.5">
            Price Trend Forecast
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Live integration with FastAPI ML prediction pipeline (<code>POST /api/v1/market-prices/forecast</code>)
          </p>
        </div>

        {/* Featured Price Trend Forecast Card */}
        <div className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-7 shadow-xs space-y-6">
          {/* Card Header & Status Badge */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
                <Coins className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Harvest Price Trend Projection
                </h3>
                <span className="text-xs text-slate-500">
                  Target Destination: {marketMeta?.name || snapshot.target_market_id} &bull; Valuation:{" "}
                  {snapshot.price_type === "retail" ? "Retail Consumer Tier" : "Wholesale Trading Tier"}
                </span>
              </div>
            </div>

            {/* Live State Badge */}
            <div>
              {priceState.status === "loading" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-sky-800 bg-sky-100/90 px-3 py-1.5 rounded-full border border-sky-200">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-600" />
                  <span>Querying Model...</span>
                </span>
              )}
              {priceState.status === "available" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-800 bg-emerald-100 px-3 py-1.5 rounded-full border border-emerald-300">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-700" />
                  <span>Prediction Available</span>
                </span>
              )}
              {priceState.status === "unavailable" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-800 bg-amber-100/90 px-3 py-1.5 rounded-full border border-amber-300">
                  <Clock className="h-3.5 w-3.5 text-amber-700" />
                  <span>Model Offline / Training</span>
                </span>
              )}
              {priceState.status === "error" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-rose-800 bg-rose-100 px-3 py-1.5 rounded-full border border-rose-300">
                  <AlertTriangle className="h-3.5 w-3.5 text-rose-700" />
                  <span>Service Connection Error</span>
                </span>
              )}
              {priceState.status === "idle" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
                  <Clock className="h-3.5 w-3.5 text-slate-500" />
                  <span>Initializing...</span>
                </span>
              )}
            </div>
          </div>

          {/* 4 Confirmed Forecasting Parameters for Price Forecasting */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
              Forecasting Parameters
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Selected Crop</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                  {cropMeta?.name_en || snapshot.crop_id}
                </span>
                <span className="text-[11px] text-slate-500 block truncate">
                  {cropMeta?.name_si}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Selling Market</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                  {marketMeta?.short_name || marketMeta?.name || snapshot.target_market_id}
                </span>
                <span className="text-[11px] text-slate-500 block truncate">
                  {marketMeta?.region || "Economic Centre"}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Expected Harvest Date</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                  {formatDateDisplay(snapshot.harvest_date)}
                </span>
                <span className="text-[11px] text-slate-500 block font-mono text-[10px]">
                  {snapshot.harvest_date}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Price Valuation Tier</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5 capitalize">
                  {snapshot.price_type} Price
                </span>
                <span className="text-[11px] text-slate-500 block truncate">
                  {snapshot.price_type === "retail" ? "Consumer Market Tier" : "Wholesale Trading Tier"}
                </span>
              </div>
            </div>
          </div>

          {/* Dynamic State Views */}
          {/* State 1: Loading */}
          {priceState.status === "loading" && (
            <div className="p-5 rounded-2xl bg-sky-50/70 border border-sky-200/80 flex items-start gap-4 animate-in fade-in duration-150">
              <Loader2 className="h-5 w-5 text-sky-600 animate-spin shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="text-sm font-bold text-sky-950">
                  Querying Price Trend Forecasting API...
                </div>
                <p className="text-xs text-sky-800 leading-relaxed">
                  Connecting to <code>POST /api/v1/market-prices/forecast</code> for {cropMeta?.name_en || "your crop"} at {marketMeta?.name || "your target market"}. Evaluating seasonal {snapshot.price_type} price fluctuations and arrival date trends.
                </p>
              </div>
            </div>
          )}

          {/* State 2: Prediction Available */}
          {priceState.status === "available" && priceState.response && (
            <div className="space-y-4 animate-in fade-in duration-200">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Predicted Price Card */}
                <div className="p-4 rounded-2xl border border-emerald-200 bg-emerald-50/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">
                      AI Forecasted Selling Price
                    </span>
                    <span className="text-[10px] font-extrabold uppercase bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-md border border-emerald-300">
                      {priceState.response.price_type || snapshot.price_type} Tier
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <div className="text-2xl sm:text-3xl font-extrabold text-slate-900">
                      {formatLKR(Number(priceState.response.forecasted_price_lkr_per_kg))}
                    </div>
                    <span className="text-xs font-bold text-slate-500">per kg</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed pt-1">
                    Machine-learning projected {snapshot.price_type} selling price per kilogram for {cropMeta?.name_en || "the crop"} upon arrival at {marketMeta?.name || "the market"}.
                  </p>
                </div>

                {/* Estimated Gross Harvest Valuation */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50/60 space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Estimated Gross Harvest Valuation
                  </span>
                  <div className="text-2xl sm:text-3xl font-extrabold text-slate-900">
                    {formatLKR(
                      Number(priceState.response.forecasted_price_lkr_per_kg) * snapshot.expected_yield_kg
                    )}
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Gross revenue projection based on your planned yield of {formatKg(snapshot.expected_yield_kg)} &times; {formatLKR(Number(priceState.response.forecasted_price_lkr_per_kg))}/kg.
                  </p>
                </div>
              </div>

              {/* Model Provenance & Status Note */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3.5 rounded-2xl bg-emerald-50/60 border border-emerald-200/80 text-xs text-emerald-900">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-700 shrink-0" />
                  <span>
                    Model Version:{" "}
                    <strong>{priceState.response.model_version || "Default ML Pipeline"}</strong>
                  </span>
                </div>
                <span className="text-emerald-700 text-[11px]">
                  {priceState.response.status_message}
                </span>
              </div>
            </div>
          )}

          {/* State 3: Prediction Unavailable */}
          {priceState.status === "unavailable" && (
            <div className="space-y-4 animate-in fade-in duration-200">
              <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 sm:p-5 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                  <Clock className="h-4 w-4 text-amber-700" />
                  <span>Machine Learning Price Forecasting Model is Currently Offline</span>
                </div>
                <p className="text-xs text-amber-900 leading-relaxed">
                  {priceState.response?.status_message ||
                    "Machine learning price forecasting model is currently offline or undergoing training."}
                </p>
                <p className="text-[11px] text-amber-800 leading-relaxed pt-1 border-t border-amber-200/60">
                  Our machine learning pipeline will forecast commodity prices ({snapshot.price_type} LKR/kg) for {cropMeta?.name_en || "your crop"} at {marketMeta?.name || "the market"} once trained time-series weights are deployed.
                  <strong className="text-amber-950 ml-1">
                    In accordance with our research integrity guidelines, no mock, synthetic, or estimated selling prices are displayed.
                  </strong>
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
                  <span className="text-xs text-slate-500">Forecasted Price (LKR/kg):</span>
                  <span className="text-xs font-bold text-slate-400">Unavailable (Model Offline)</span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
                  <span className="text-xs text-slate-500">Valuation Tier:</span>
                  <span className="text-xs font-bold text-slate-700 capitalize">{snapshot.price_type} Price</span>
                </div>
              </div>
            </div>
          )}

          {/* State 4: Request Failed (Error) */}
          {priceState.status === "error" && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-4 sm:p-5 space-y-3 animate-in fade-in duration-200">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="text-sm font-bold text-rose-950">
                    Unable to Connect to Price Forecasting Service
                  </div>
                  <p className="text-xs text-rose-800 leading-relaxed">
                    {priceState.errorMessage}
                  </p>
                  <p className="text-[11px] text-rose-700 pt-1">
                    Please verify that the FastAPI backend service is running on port 8001 (or configured via <code>NEXT_PUBLIC_MARKET_PROFIT_API_URL</code>).
                  </p>
                </div>
              </div>
              <div className="pt-2 flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleRetryPrice}
                  className="inline-flex items-center gap-2 rounded-xl bg-rose-700 hover:bg-rose-800 active:scale-95 text-white px-4 py-2 text-xs font-bold shadow-xs transition-all cursor-pointer"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>Retry Price Forecast</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ===================================================================== */}
      {/* SECTION 5: PROFIT & RISK ASSESSMENT (LIVE FASTAPI INTEGRATION)       */}
      {/* ===================================================================== */}
      <div className="space-y-4">
        <div>
          <span className="text-xs font-bold text-[#15803d] uppercase tracking-wider">
            Analytical Pipeline 3 of 3
          </span>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight mt-0.5">
            Profit &amp; Risk Assessment
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Live integration with FastAPI deterministic profit &amp; rule-based risk engines (<code>POST /api/v1/profit-analyses/assess-risk</code>)
          </p>
        </div>

        {/* Profit & Risk Assessment Card */}
        <div className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-7 shadow-xs space-y-6">
          {/* Card Header & Status Badge */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Financial Return &amp; Feasibility Risk
                </h3>
                <span className="text-xs text-slate-500">
                  Target Destination: {marketMeta?.name || snapshot.target_market_id} &bull; Total Cultivation Budget: {formatLKR(snapshot.total_cultivation_cost)}
                </span>
              </div>
            </div>

            {/* Live State / Risk Classification Badge */}
            <div>
              {profitState.status === "loading" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-sky-800 bg-sky-100/90 px-3 py-1.5 rounded-full border border-sky-200">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-600" />
                  <span>Evaluating Returns...</span>
                </span>
              )}
              {profitState.status === "available" && profitState.risk && (
                <>
                  {profitState.risk.risk_level === "Low" && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-800 bg-emerald-100 px-3 py-1.5 rounded-full border border-emerald-300">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-700" />
                      <span>Low Risk Classification</span>
                    </span>
                  )}
                  {profitState.risk.risk_level === "Medium" && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-800 bg-amber-100 px-3 py-1.5 rounded-full border border-amber-300">
                      <AlertTriangle className="h-3.5 w-3.5 text-amber-700" />
                      <span>Medium Risk Classification</span>
                    </span>
                  )}
                  {profitState.risk.risk_level === "High" && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-bold text-rose-800 bg-rose-100 px-3 py-1.5 rounded-full border border-rose-300">
                      <AlertCircle className="h-3.5 w-3.5 text-rose-700" />
                      <span>High Risk Classification</span>
                    </span>
                  )}
                  {profitState.risk.risk_level === "insufficient_information" && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-700 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-300">
                      <Clock className="h-3.5 w-3.5 text-slate-500" />
                      <span>Insufficient Cost Data (ROI Undefined)</span>
                    </span>
                  )}
                </>
              )}
              {profitState.status === "unavailable" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-800 bg-amber-100/90 px-3 py-1.5 rounded-full border border-amber-300">
                  <Clock className="h-3.5 w-3.5 text-amber-700" />
                  <span>Awaiting Price Forecast</span>
                </span>
              )}
              {profitState.status === "error" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-rose-800 bg-rose-100 px-3 py-1.5 rounded-full border border-rose-300">
                  <AlertTriangle className="h-3.5 w-3.5 text-rose-700" />
                  <span>Calculation Error</span>
                </span>
              )}
              {profitState.status === "idle" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
                  <Clock className="h-3.5 w-3.5 text-slate-500" />
                  <span>Awaiting Price Forecast...</span>
                </span>
              )}
            </div>
          </div>

          {/* 4 Financial Assessment Parameters */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
              Assessment Inputs
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Expected Yield</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                  {formatKg(snapshot.expected_yield_kg)}
                </span>
                <span className="text-[11px] text-slate-500 block truncate">
                  Planned harvest volume
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Forecasted Price Basis</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                  {profitState.predictedPriceUsed !== null
                    ? `${formatLKR(profitState.predictedPriceUsed)} / kg`
                    : "Awaiting ML Price"}
                </span>
                <span className="text-[11px] text-slate-500 block truncate capitalize">
                  {snapshot.price_type} valuation tier
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Total Cultivation Budget</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                  {formatLKR(snapshot.total_cultivation_cost)}
                </span>
                <span className="text-[11px] text-slate-500 block truncate capitalize">
                  {snapshot.metadata.budget_mode === "detailed" ? "Detailed Budget" : "Quick Budget"}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Selling Market</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                  {marketMeta?.short_name || marketMeta?.name || snapshot.target_market_id}
                </span>
                <span className="text-[11px] text-slate-500 block truncate">
                  {marketMeta?.region || "Economic Centre"}
                </span>
              </div>
            </div>
          </div>

          {/* Dynamic State Views */}
          {/* State 1: Loading */}
          {profitState.status === "loading" && (
            <div className="p-5 rounded-2xl bg-sky-50/70 border border-sky-200/80 flex items-start gap-4 animate-in fade-in duration-150">
              <Loader2 className="h-5 w-5 text-sky-600 animate-spin shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="text-sm font-bold text-sky-950">
                  Evaluating Financial Feasibility &amp; Risk Assessment...
                </div>
                <p className="text-xs text-sky-800 leading-relaxed">
                  Connecting to <code>POST /api/v1/profit-analyses/assess-risk</code> for {cropMeta?.name_en || "your crop"}. Evaluating net profit, return on investment (ROI), breakeven selling price, and margin of safety against preliminary thresholds.
                </p>
              </div>
            </div>
          )}

          {/* State 2: Prediction Available (Real Backend Calculated Results) */}
          {profitState.status === "available" && profitState.calculation && profitState.risk && (
            <div className="space-y-5 animate-in fade-in duration-200">
              {/* 6 Deterministic Financial Metrics Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
                {/* 1. Gross Revenue */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50/70 space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Projected Gross Revenue
                  </span>
                  <div className="text-2xl font-extrabold text-slate-900">
                    {formatLKR(Number(profitState.calculation.gross_revenue))}
                  </div>
                  <p className="text-[11px] text-slate-500 leading-tight">
                    {formatKg(snapshot.expected_yield_kg)} &times; {formatLKR(Number(profitState.calculation.selling_price_lkr_per_kg))}/kg
                  </p>
                </div>

                {/* 2. Total Cultivation Cost */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50/70 space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Total Cultivation Cost
                  </span>
                  <div className="text-2xl font-extrabold text-slate-900">
                    {formatLKR(Number(profitState.calculation.total_cultivation_cost))}
                  </div>
                  <p className="text-[11px] text-slate-500 leading-tight capitalize">
                    {snapshot.metadata.budget_mode} budget expenditure
                  </p>
                </div>

                {/* 3. Estimated Net Profit */}
                <div
                  className={`p-4 rounded-2xl border space-y-1.5 ${
                    Number(profitState.calculation.net_profit) >= 0
                      ? "border-emerald-200 bg-emerald-50/60 text-emerald-950"
                      : "border-rose-200 bg-rose-50/70 text-rose-950"
                  }`}
                >
                  <span className="text-[10px] font-bold uppercase tracking-wider block opacity-75">
                    Estimated Net Profit / Return
                  </span>
                  <div className="text-2xl font-extrabold">
                    {formatLKR(Number(profitState.calculation.net_profit))}
                  </div>
                  <p className="text-[11px] opacity-75 leading-tight">
                    Projected Revenue &minus; Total Cultivation Cost
                  </p>
                </div>

                {/* 4. ROI Percentage */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50/70 space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Return on Investment (ROI)
                  </span>
                  <div className="text-2xl font-extrabold text-slate-900">
                    {profitState.calculation.roi_percentage !== null &&
                    profitState.calculation.roi_percentage !== undefined
                      ? `${Number(profitState.calculation.roi_percentage) >= 0 ? "+" : ""}${formatPercent(
                          Number(profitState.calculation.roi_percentage)
                        )}`
                      : "Undefined"}
                  </div>
                  <p className="text-[11px] text-slate-500 leading-tight">
                    {profitState.calculation.roi_percentage !== null
                      ? "(Net Profit ÷ Total Cost) × 100"
                      : "Total cost is Rs. 0 (mathematically undefined)"}
                  </p>
                </div>

                {/* 5. Break-Even Price */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50/70 space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Break-Even Selling Price
                  </span>
                  <div className="text-2xl font-extrabold text-slate-900">
                    {formatLKR(Number(profitState.calculation.breakeven_price_lkr_per_kg))}
                    <span className="text-xs font-semibold text-slate-400 ml-1">/ kg</span>
                  </div>
                  <p className="text-[11px] text-slate-500 leading-tight">
                    Minimum price required to recover all costs
                  </p>
                </div>

                {/* 6. Profit Margin */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50/70 space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Profit Margin (%)
                  </span>
                  <div className="text-2xl font-extrabold text-slate-900">
                    {formatPercent(Number(profitState.calculation.margin_of_safety_percentage))}
                  </div>
                  <p className="text-[11px] text-slate-500 leading-tight">
                    Net profit as a percentage of gross revenue
                  </p>
                </div>
              </div>

              {/* Rule-Based Risk Evaluation Rationale Box */}
              <div
                className={`p-4 sm:p-5 rounded-2xl border space-y-2.5 ${
                  profitState.risk.risk_level === "Low"
                    ? "bg-emerald-50/70 border-emerald-300 text-emerald-950"
                    : profitState.risk.risk_level === "Medium"
                    ? "bg-amber-50/70 border-amber-300 text-amber-950"
                    : profitState.risk.risk_level === "High"
                    ? "bg-rose-50/70 border-rose-300 text-rose-950"
                    : "bg-slate-50 border-slate-300 text-slate-900"
                }`}
              >
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 shrink-0" />
                  <span className="text-sm font-bold">
                    Risk Classification Rationale ({profitState.risk.risk_level} Risk)
                  </span>
                </div>
                <div className="text-xs space-y-1">
                  <p className="leading-relaxed">
                    <strong>Evaluation Outcome:</strong> {profitState.risk.factors.trigger_rationale}
                  </p>
                  <p className="text-[11px] opacity-80 pt-1 border-t border-black/10">
                    <strong>Rule Evaluated:</strong> <code>{profitState.risk.factors.trigger_rule}</code>
                  </p>
                </div>
              </div>

              {/* Methodological Transparency Notice */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 space-y-1.5">
                <div className="flex items-center gap-1.5 font-bold text-slate-800">
                  <Sparkles className="h-4 w-4 text-[#15803d]" />
                  <span>Methodological Transparency &amp; Planning Advisory</span>
                </div>
                <p className="leading-relaxed">
                  {profitState.risk.disclaimer}
                </p>
                <p className="text-[11px] text-slate-500 pt-1 border-t border-slate-200/60">
                  All figures are projections based on AI commodity price forecasts and your planning inputs. They do not constitute guaranteed financial earnings or insurance underwriting.
                </p>
              </div>
            </div>
          )}

          {/* State 3: Prediction Unavailable */}
          {profitState.status === "unavailable" && (
            <div className="space-y-4 animate-in fade-in duration-200">
              <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 sm:p-5 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                  <Clock className="h-4 w-4 text-amber-700" />
                  <span>Profit &amp; Risk Assessment is Awaiting Price Trend Forecast</span>
                </div>
                <p className="text-xs text-amber-900 leading-relaxed">
                  Financial feasibility calculations, gross revenue, net profit, and risk classifications require a validated machine-learning predicted selling price from Pipeline 2.
                </p>
                <p className="text-[11px] text-amber-800 leading-relaxed pt-1 border-t border-amber-200/60">
                  Because the price forecasting model is currently offline or undergoing training, financial returns and risk levels cannot be computed without making speculative assumptions.
                  <strong className="text-amber-950 ml-1">
                    In accordance with our research integrity guidelines, no fallback prices, sample profits, or fabricated risk labels are displayed.
                  </strong>
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Projected Gross Revenue:</span>
                  <span className="text-xs font-bold text-slate-400 mt-1">Awaiting Price Forecast</span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Estimated Net Profit:</span>
                  <span className="text-xs font-bold text-slate-400 mt-1">Awaiting Price Forecast</span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Feasibility Risk Category:</span>
                  <span className="text-xs font-bold text-slate-400 mt-1">Awaiting Price Forecast</span>
                </div>
              </div>
            </div>
          )}

          {/* State 4: Request Failed (Error) */}
          {profitState.status === "error" && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-4 sm:p-5 space-y-3 animate-in fade-in duration-200">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="text-sm font-bold text-rose-950">
                    Unable to Complete Profit &amp; Risk Assessment
                  </div>
                  <p className="text-xs text-rose-800 leading-relaxed">
                    {profitState.errorMessage}
                  </p>
                  <p className="text-[11px] text-rose-700 pt-1">
                    Please verify that the FastAPI backend service is running on port 8001 (or configured via <code>NEXT_PUBLIC_MARKET_PROFIT_API_URL</code>).
                  </p>
                </div>
              </div>
              <div className="pt-2 flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleRetryProfit}
                  className="inline-flex items-center gap-2 rounded-xl bg-rose-700 hover:bg-rose-800 active:scale-95 text-white px-4 py-2 text-xs font-bold shadow-xs transition-all cursor-pointer"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>Retry Profit &amp; Risk Assessment</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ===================================================================== */}
      {/* SECTION 4: NAVIGATION & ACTION BUTTONS                               */}
      {/* ===================================================================== */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-200">
        <Link
          href="/market-profit/new-analysis/cultivation-costs"
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 px-6 py-3 text-sm font-bold shadow-2xs transition-all text-center"
        >
          <ArrowLeft className="h-4 w-4 text-slate-500" />
          <span>Back to Cultivation Costs</span>
        </Link>

        <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
          <Link
            href="/market-profit"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 px-6 py-3 text-sm font-bold shadow-2xs transition-all text-center"
          >
            <span>Return to Dashboard</span>
          </Link>
          <button
            type="button"
            onClick={handleStartNewAnalysis}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-[#15803d] hover:bg-[#166534] active:scale-95 text-white px-7 py-3 text-sm font-bold shadow-sm shadow-emerald-800/20 transition-all cursor-pointer text-center"
          >
            <RotateCcw className="h-4 w-4" />
            <span>Plan Another Crop</span>
          </button>
        </div>
      </div>
    </div>
  );
}
