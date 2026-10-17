"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Image, { StaticImageData } from "next/image";
import {
  ArrowLeft,
  ArrowRight,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Compass,
  Scale,
  Sprout,
  MapPin,
  Store,
  Tag,
  Coins,
  Wallet,
  Info,
  Check,
} from "lucide-react";

import { WizardProgress } from "../../components/WizardProgress";
import {
  SUPPORTED_FRONTEND_CROPS,
  SRI_LANKA_DISTRICTS,
  STANDARD_MARKETS,
  FrontendCropMetadata,
  DistrictMetadata,
  MarketMetadata,
} from "../../lib/constants";
import { formatDateDisplay, formatKg, formatLKR } from "../../lib/formatters";
import {
  validateStep1,
  loadStep1FromStorage,
  Step1FormData,
  validateStep2,
  loadStep2FromStorage,
  Step2FormData,
  validateStep3,
  loadStep3FromStorage,
  Step3FormData,
  validateCultivationCost,
  validateStep4,
  isStep4Complete,
  loadStep4FromStorage,
  saveValidatedStep4ToStorage,
  checkPreviousStepsForStep4,
  PriceType,
} from "../../lib/wizard";

// Statically import verified crop photographs for the summary badge
import okraImg from "../../assets/crops/okra.jpg";
import brinjalImg from "../../assets/crops/brinjal.jpg";
import pumpkinImg from "../../assets/crops/pumpkin.jpg";
import maizeImg from "../../assets/crops/maize.jpg";
import mungBeanImg from "../../assets/crops/mung-bean.jpg";
import chilliImg from "../../assets/crops/chilli.jpg";

const CROP_IMAGE_MAP: Record<string, StaticImageData> = {
  CR_OKRA: okraImg,
  CR_BRINJAL: brinjalImg,
  CR_PUMPKIN: pumpkinImg,
  CR_MAIZE: maizeImg,
  CR_MUNG_BEAN: mungBeanImg,
  CR_CHILLI: chilliImg,
};

export default function CultivationCostsPage() {
  const router = useRouter();
  const costInputRef = useRef<HTMLInputElement>(null);

  // Wizard state from Step 1, Step 2, and Step 3
  const [step1Data, setStep1Data] = useState<Step1FormData>({
    crop_id: "",
    cultivation_district_id: "",
  });
  const [step2Data, setStep2Data] = useState<Step2FormData>({
    harvest_date: "",
    land_extent_acres: "",
    expected_yield_kg: "",
  });
  const [step3Data, setStep3Data] = useState<Step3FormData>({
    target_market_id: "",
    selling_market_id: "",
    price_type: "",
  });

  // Guard state
  const [guardStatus, setGuardStatus] = useState<"checking" | "invalid_step1" | "invalid_step2" | "invalid_step3" | "ready">("checking");
  const [guardMessage, setGuardMessage] = useState<string>("");
  const [guardTarget, setGuardTarget] = useState<string>("");

  // Step 4 state: Quick Cultivation Budget
  const [costInput, setCostInput] = useState<string>("");
  const [costError, setCostError] = useState<string | undefined>(undefined);
  const [costWarning, setCostWarning] = useState<string | undefined>(undefined);
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [isStep4Saved, setIsStep4Saved] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validate Step 1, 2, and 3 prerequisites on mount
  useEffect(() => {
    const s1 = loadStep1FromStorage();
    const s2 = loadStep2FromStorage();
    const s3 = loadStep3FromStorage();

    const integrity = checkPreviousStepsForStep4(s1, s2, s3);

    if (!integrity.isValid) {
      if (integrity.earliestIncompleteStep === 1) {
        setGuardStatus("invalid_step1");
      } else if (integrity.earliestIncompleteStep === 2) {
        setGuardStatus("invalid_step2");
      } else {
        setGuardStatus("invalid_step3");
      }
      setGuardMessage(integrity.errorMessage || "Previous steps are incomplete.");
      setGuardTarget(integrity.redirectTarget || "/market-profit/new-analysis");

      const timer = setTimeout(() => {
        router.replace(integrity.redirectTarget || "/market-profit/new-analysis");
      }, 2500);
      return () => clearTimeout(timer);
    }

    setStep1Data(s1);
    setStep2Data(s2);
    setStep3Data(s3);
    setGuardStatus("ready");

    // Restore Step 4 if previously saved
    const s4 = loadStep4FromStorage();
    if (s4.total_cultivation_cost_lkr) {
      setCostInput(s4.total_cultivation_cost_lkr);
      const validation = validateStep4(s4);
      if (validation.isValid) {
        setIsStep4Saved(true);
        if (validation.warnings?.total_cultivation_cost_lkr) {
          setCostWarning(validation.warnings.total_cultivation_cost_lkr);
        }
      }
    }
  }, [router]);

  // Handle budget input change
  const handleCostChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setCostInput(value);
    setIsStep4Saved(false);

    if (hasAttemptedSubmit) {
      const validation = validateStep4({ total_cultivation_cost_lkr: value });
      setCostError(validation.errors.total_cultivation_cost_lkr);
      setCostWarning(validation.warnings?.total_cultivation_cost_lkr);
    } else {
      // Live warning evaluation for zero cost
      const validation = validateStep4({ total_cultivation_cost_lkr: value });
      setCostWarning(validation.warnings?.total_cultivation_cost_lkr);
      if (validation.isValid) {
        setCostError(undefined);
      }
    }
  };

  // Handle Step 4 submission
  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    setIsSubmitting(true);
    setHasAttemptedSubmit(true);

    try {
      // 1. Re-verify earlier steps integrity
      const s1 = loadStep1FromStorage();
      const s2 = loadStep2FromStorage();
      const s3 = loadStep3FromStorage();
      const integrity = checkPreviousStepsForStep4(s1, s2, s3);

      if (!integrity.isValid) {
        router.replace(integrity.redirectTarget || "/market-profit/new-analysis");
        return;
      }

      // 2. Validate Step 4 input
      const validation = validateStep4({
        total_cultivation_cost_lkr: costInput,
      });

      setCostError(validation.errors.total_cultivation_cost_lkr);
      setCostWarning(validation.warnings?.total_cultivation_cost_lkr);

      if (!validation.isValid) {
        setIsStep4Saved(false);
        costInputRef.current?.focus();
        costInputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }

      // 3. Persist valid cost preserving decimal precision
      saveValidatedStep4ToStorage({
        total_cultivation_cost_lkr: costInput,
      });
      setIsStep4Saved(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Find metadata for summary cards
  const selectedCropMeta: FrontendCropMetadata | undefined =
    SUPPORTED_FRONTEND_CROPS.find((c) => c.crop_id === step1Data.crop_id);
  const selectedDistrictMeta: DistrictMetadata | undefined =
    SRI_LANKA_DISTRICTS.find((d) => d.id === step1Data.cultivation_district_id);
  const targetMarketId = step3Data.target_market_id || step3Data.selling_market_id;
  const selectedMarketMeta: MarketMetadata | undefined =
    STANDARD_MARKETS.find((m) => m.id === targetMarketId);
  const cropImage = step1Data.crop_id ? CROP_IMAGE_MAP[step1Data.crop_id] : null;

  // Render redirect notice if prerequisites are not met
  if (guardStatus === "invalid_step1" || guardStatus === "invalid_step2" || guardStatus === "invalid_step3") {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-4">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-100 text-amber-700">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Previous Steps Required
        </h2>
        <p className="text-sm text-slate-600 max-w-md mx-auto leading-relaxed">
          {guardMessage}
        </p>
        <div className="pt-2">
          <Link
            href={guardTarget || "/market-profit/new-analysis"}
            className="inline-flex items-center gap-2 rounded-xl bg-[#15803d] px-5 py-2.5 text-xs font-bold text-white hover:bg-[#166534] transition-colors"
          >
            <span>Complete Required Step</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    );
  }

  // Parse numeric amount for live preview if valid
  const parsedCost = parseFloat(costInput);
  const isNumberValid = !Number.isNaN(parsedCost) && Number.isFinite(parsedCost) && parsedCost >= 0;

  return (
    <div className="w-full max-w-5xl mx-auto pb-16 space-y-8">
      {/* Top Header & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-[#15803d] tracking-wide uppercase">
            <span>New Analysis</span>
            <span>•</span>
            <span>Step 4 of 4</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mt-1">
            Cultivation Costs
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl">
            Enter your planned cultivation expenses. This cost is used to determine your breakeven price and profit margin.
          </p>
        </div>

        <Link
          href="/market-profit/new-analysis/selling-market"
          className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-[#15803d] transition-colors self-start sm:self-auto py-2 px-3 rounded-lg hover:bg-slate-100 border border-slate-200/60 sm:border-transparent"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Selling Market</span>
        </Link>
      </div>

      {/* Wizard Progress Bar */}
      <WizardProgress currentStep={4} />

      {/* COMPACT SUMMARY OF PREVIOUS STEPS (Steps 1, 2, 3) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-2xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500">
            <CheckCircle2 className="h-4 w-4 text-[#15803d]" />
            <span>Completed Wizard Steps Summary (Steps 1 – 3)</span>
          </div>
          <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
            Validated
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-1">
          {/* Crop & Location */}
          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200/70">
            {cropImage ? (
              <div className="relative h-12 w-12 rounded-lg overflow-hidden shrink-0 border border-slate-200">
                <Image
                  src={cropImage}
                  alt={selectedCropMeta?.name_en || "Crop"}
                  fill
                  className="object-cover"
                />
              </div>
            ) : (
              <div className="h-12 w-12 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                <Sprout className="h-6 w-6" />
              </div>
            )}
            <div className="min-w-0">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wide">
                Crop & Location
              </div>
              <div className="text-sm font-bold text-slate-900 truncate">
                {selectedCropMeta?.name_en || step1Data.crop_id}
              </div>
              <div className="text-xs text-slate-500 flex items-center gap-1 truncate">
                <MapPin className="h-3 w-3 text-slate-400 shrink-0" />
                <span>{selectedDistrictMeta?.name || step1Data.cultivation_district_id}</span>
              </div>
            </div>
          </div>

          {/* Harvest Date & Timing */}
          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200/70">
            <div className="h-12 w-12 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
              <Calendar className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wide">
                Expected Harvest
              </div>
              <div className="text-sm font-bold text-slate-900 truncate">
                {formatDateDisplay(step2Data.harvest_date)}
              </div>
              <div className="text-xs text-slate-500 truncate">
                Date: {step2Data.harvest_date}
              </div>
            </div>
          </div>

          {/* Land Extent & Yield */}
          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200/70">
            <div className="h-12 w-12 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
              <Scale className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wide">
                Extent & Yield
              </div>
              <div className="text-sm font-bold text-slate-900 truncate">
                {formatKg(parseFloat(step2Data.expected_yield_kg) || 0)}
              </div>
              <div className="text-xs text-slate-500 truncate">
                {step2Data.land_extent_acres} Acres
              </div>
            </div>
          </div>

          {/* Market & Price Type */}
          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200/70">
            <div className="h-12 w-12 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
              <Store className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wide">
                Target Market
              </div>
              <div className="text-sm font-bold text-slate-900 truncate">
                {selectedMarketMeta?.name || targetMarketId}
              </div>
              <div className="text-xs text-slate-600 font-semibold capitalize flex items-center gap-1 truncate">
                <Tag className="h-3 w-3 text-emerald-600 shrink-0" />
                <span>{step3Data.price_type || "Wholesale"} Price</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* QUICK CULTIVATION BUDGET FORM */}
      <form onSubmit={handleFormSubmit} className="space-y-6">
        <div className="bg-white rounded-2xl border-2 border-emerald-500/20 p-6 sm:p-8 shadow-xs space-y-6">
          {/* Section Header */}
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 rounded-2xl bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0 shadow-2xs">
              <Coins className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                Quick Cultivation Budget
              </h2>
              <p className="text-sm text-slate-600 mt-0.5 leading-relaxed">
                Provide your overall estimated cultivation expenditure to evaluate profitability and financial risk.
              </p>
            </div>
          </div>

          {/* Cultivation Cost Input Field */}
          <div className="space-y-2.5 pt-2">
            <label
              htmlFor="total_cultivation_cost_lkr"
              className="block text-sm font-bold text-slate-800"
            >
              Total Expected Cultivation Cost (LKR) <span className="text-red-500">*</span>
            </label>

            <p className="text-xs text-slate-500 leading-normal">
              Enter the total amount you expect to spend growing and selling your crop.
            </p>

            <div className="relative max-w-md">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-sm font-bold text-slate-500">
                Rs.
              </div>
              <input
                ref={costInputRef}
                id="total_cultivation_cost_lkr"
                name="total_cultivation_cost_lkr"
                type="text"
                inputMode="decimal"
                value={costInput}
                onChange={handleCostChange}
                placeholder="150000"
                aria-invalid={Boolean(costError)}
                aria-describedby="cost-helper-text cost-error cost-warning"
                className={`w-full pl-12 pr-4 py-3.5 rounded-xl border-2 font-semibold text-slate-900 text-base shadow-2xs focus:outline-hidden transition-all ${
                  costError
                    ? "border-red-400 bg-red-50/20 focus:border-red-500 focus:ring-2 focus:ring-red-200"
                    : "border-slate-300 bg-white focus:border-[#15803d] focus:ring-2 focus:ring-emerald-100"
                }`}
              />
            </div>

            {/* Error Message */}
            {costError && (
              <div
                id="cost-error"
                role="alert"
                className="flex items-center gap-2 text-xs font-semibold text-red-600 bg-red-50 p-2.5 rounded-xl border border-red-200 max-w-md animate-in fade-in duration-200"
              >
                <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
                <span>{costError}</span>
              </div>
            )}

            {/* Zero-Cost Warning Banner */}
            {costWarning && !costError && (
              <div
                id="cost-warning"
                role="alert"
                className="flex items-start gap-2.5 text-xs font-medium text-amber-800 bg-amber-50 p-3 rounded-xl border border-amber-200 max-w-md animate-in fade-in duration-200"
              >
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
                <span>{costWarning}</span>
              </div>
            )}

            {/* Live Currency Preview */}
            {isNumberValid && parsedCost > 0 && !costError && (
              <div className="text-xs font-semibold text-[#15803d] flex items-center gap-1.5 pt-1">
                <Check className="h-3.5 w-3.5" />
                <span>Amount: {formatLKR(parsedCost)}</span>
              </div>
            )}
          </div>

          {/* Farmer Advisory Note */}
          <div className="flex items-start gap-3 p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 leading-relaxed">
            <Info className="h-4 w-4 text-slate-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-800">What does cultivation cost typically include?</p>
              <p className="mt-0.5 text-slate-500">
                Common farming expenses include land preparation, seeds/nursery plants, fertilizers, pest control, irrigation fuel/electricity, labor for weeding and harvesting, and transport to the economic centre.
              </p>
            </div>
          </div>
        </div>

        {/* Confirmation Status Badge if Saved */}
        {isStep4Saved && (
          <div className="flex items-center justify-between p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-emerald-800 animate-in fade-in duration-300">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-emerald-600 text-white flex items-center justify-center shrink-0">
                <Check className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold">Cultivation Budget Saved</h4>
                <p className="text-xs text-emerald-700">
                  Total expected expenditure: {formatLKR(parseFloat(costInput) || 0)}. All 4 wizard steps are now complete!
                </p>
              </div>
            </div>
            <span className="text-xs font-extrabold uppercase tracking-wide bg-emerald-200/80 text-emerald-900 px-3 py-1 rounded-full">
              Ready
            </span>
          </div>
        )}

        {/* Navigation Action Buttons */}
        <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-200">
          <Link
            href="/market-profit/new-analysis/selling-market"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 px-6 py-3 text-sm font-bold shadow-2xs transition-all text-center"
          >
            <ArrowLeft className="h-4 w-4 text-slate-500" />
            <span>Back: Selling Market</span>
          </Link>

          <button
            type="submit"
            disabled={isSubmitting}
            aria-busy={isSubmitting}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 rounded-xl bg-[#15803d] hover:bg-[#166534] active:scale-95 text-white px-8 py-3.5 text-sm font-bold shadow-sm shadow-emerald-800/20 transition-all cursor-pointer group disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span>{isSubmitting ? "Validating Budget..." : isStep4Saved ? "Update Cultivation Budget" : "Save Cultivation Budget"}</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-100 group-hover:scale-110 transition-transform" />
          </button>
        </div>
      </form>
    </div>
  );
}
