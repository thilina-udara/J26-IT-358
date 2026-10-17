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
} from "lucide-react";

import {
  SUPPORTED_FRONTEND_CROPS,
  SRI_LANKA_DISTRICTS,
  STANDARD_MARKETS,
  FrontendCropMetadata,
  DistrictMetadata,
  MarketMetadata,
} from "../lib/constants";
import { formatDateDisplay, formatKg, formatLKR } from "../lib/formatters";
import {
  ValidatedAnalysisSnapshot,
  loadAnalysisSnapshot,
  loadAndValidateWizardFromStorage,
  saveAnalysisSnapshot,
  clearAnalysisSnapshot,
  DETAILED_EXPENSE_CATEGORIES,
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
      {/* SECTION 3: THREE PENDING ANALYSIS MODULES                             */}
      {/* ===================================================================== */}
      <div className="space-y-4">
        <div>
          <span className="text-xs font-bold text-[#15803d] uppercase tracking-wider">
            Analysis Modules Status
          </span>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight mt-0.5">
            Component 1 Analytical Pipelines
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* 1. Market Demand Analysis Card */}
          <div className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-6 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
                  <TrendingUp className="h-5 w-5" />
                </div>
                <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-amber-800 bg-amber-100/80 px-2.5 py-1 rounded-full border border-amber-200">
                  <Clock className="h-3 w-3" />
                  <span>Pending ML</span>
                </span>
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Market Demand Analysis
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Demand forecasting for target harvest date
                </p>
              </div>

              {/* Strict Requirement Notice */}
              <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-3.5 space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900">
                  <AlertCircle className="h-3.5 w-3.5 text-amber-700" />
                  <span>Analysis results are not available yet.</span>
                </div>
                <p className="text-[11px] text-amber-800 leading-relaxed">
                  Our machine learning model will classify buyer demand pressure (High, Medium, Low) and estimate demand volumes for {cropMeta?.name_en || "your crop"} on {formatDateDisplay(snapshot.harvest_date)}.
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 space-y-1">
              <div className="flex justify-between">
                <span>Projected Demand Volume:</span>
                <span className="font-semibold text-slate-500">Pending ML</span>
              </div>
              <div className="flex justify-between">
                <span>Demand Category:</span>
                <span className="font-semibold text-slate-500">Pending ML</span>
              </div>
            </div>
          </div>

          {/* 2. Price Trend Forecast Card */}
          <div className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-6 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
                  <Coins className="h-5 w-5" />
                </div>
                <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-amber-800 bg-amber-100/80 px-2.5 py-1 rounded-full border border-amber-200">
                  <Clock className="h-3 w-3" />
                  <span>Pending ML</span>
                </span>
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Price Trend Forecast
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Time-series price prediction at {marketMeta?.name || "DEC"}
                </p>
              </div>

              {/* Strict Requirement Notice */}
              <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-3.5 space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900">
                  <AlertCircle className="h-3.5 w-3.5 text-amber-700" />
                  <span>Analysis results are not available yet.</span>
                </div>
                <p className="text-[11px] text-amber-800 leading-relaxed">
                  The price forecasting engine will evaluate seasonal price trends at {marketMeta?.name || "your target economic centre"} to forecast expected {snapshot.price_type} price per kg.
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 space-y-1">
              <div className="flex justify-between">
                <span>Forecasted Price (LKR/kg):</span>
                <span className="font-semibold text-slate-500">Pending ML</span>
              </div>
              <div className="flex justify-between">
                <span>Valuation Basis:</span>
                <span className="font-semibold text-slate-700 capitalize">{snapshot.price_type} Price</span>
              </div>
            </div>
          </div>

          {/* 3. Profit & Risk Assessment Card */}
          <div className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-6 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-amber-800 bg-amber-100/80 px-2.5 py-1 rounded-full border border-amber-200">
                  <Clock className="h-3 w-3" />
                  <span>Pending ML</span>
                </span>
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Profit &amp; Risk Assessment
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Revenue, net profit, and feasibility risk
                </p>
              </div>

              {/* Strict Requirement Notice */}
              <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-3.5 space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900">
                  <AlertCircle className="h-3.5 w-3.5 text-amber-700" />
                  <span>Analysis results are not available yet.</span>
                </div>
                <p className="text-[11px] text-amber-800 leading-relaxed">
                  Once ML predicted selling prices are generated, revenue ({formatKg(snapshot.expected_yield_kg)} × Forecasted Price), net profit, and risk level will calculate deterministically.
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 space-y-1">
              <div className="flex justify-between">
                <span>Projected Revenue:</span>
                <span className="font-semibold text-slate-500">Awaiting Price</span>
              </div>
              <div className="flex justify-between">
                <span>Risk Classification:</span>
                <span className="font-semibold text-slate-500">Awaiting Price</span>
              </div>
            </div>
          </div>
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
