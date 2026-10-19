"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
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
  MapPin,
  Store,
  Coins,
  Wallet,
  Info,
  Check,
  Calculator,
  Receipt,
  ChevronRight,
  Package,
  ShoppingBag,
} from "lucide-react";

import { WizardProgress } from "../../components/WizardProgress";
import { AnalysisComingNextModal } from "../../components/AnalysisComingNextModal";
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
  loadStep1FromStorage,
  Step1FormData,
  loadStep2FromStorage,
  Step2FormData,
  loadStep3FromStorage,
  Step3FormData,
  BudgetMode,
  DetailedExpensesData,
  DetailedExpenseKey,
  DETAILED_EXPENSE_CATEGORIES,
  createDefaultDetailedExpenses,
  calculateDetailedCultivationTotal,
  validateDetailedExpenseField,
  validateDetailedExpenses,
  validateCultivationCost,
  validateStep4,
  loadStep4FromStorage,
  saveValidatedStep4ToStorage,
  checkPreviousStepsForStep4,
  Step4FormData,
  loadAndValidateWizardFromStorage,
  saveAnalysisSnapshot,
} from "../../lib/wizard";

// Statically import the 5 verified crop photographs for Component 1
import okraImg from "../../assets/crops/okra.jpg";
import brinjalImg from "../../assets/crops/brinjal.jpg";
import maizeImg from "../../assets/crops/maize.jpg";
import mungBeanImg from "../../assets/crops/mung-bean.jpg";
import chilliImg from "../../assets/crops/chilli.jpg";

const CROP_IMAGE_MAP: Record<string, StaticImageData> = {
  CR_OKRA: okraImg,
  CR_BRINJAL: brinjalImg,
  CR_MAIZE: maizeImg,
  CR_MUNG_BEAN: mungBeanImg,
  CR_CHILLI: chilliImg,
};

export default function CultivationCostsPage() {
  const router = useRouter();

  // Input element refs for accessibility and focus management
  const costInputRef = useRef<HTMLInputElement>(null);
  const detailedInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

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
  const [guardStatus, setGuardStatus] = useState<
    "checking" | "invalid_step1" | "invalid_step2" | "invalid_step3" | "ready"
  >("checking");
  const [guardMessage, setGuardMessage] = useState<string>("");
  const [guardTarget, setGuardTarget] = useState<string>("");

  // Step 4 state: Mode selection
  const [budgetMode, setBudgetMode] = useState<BudgetMode>("quick");

  // Quick Budget state
  const [quickCostInput, setQuickCostInput] = useState<string>("");
  const [quickCostError, setQuickCostError] = useState<string | undefined>(undefined);
  const [quickCostWarning, setQuickCostWarning] = useState<string | undefined>(undefined);

  // Detailed Budget state
  const [detailedExpenses, setDetailedExpenses] = useState<DetailedExpensesData>(
    createDefaultDetailedExpenses()
  );
  const [detailedErrors, setDetailedErrors] = useState<Partial<Record<DetailedExpenseKey, string>>>({});
  const [detailedWarning, setDetailedWarning] = useState<string | undefined>(undefined);

  // Submission & Confirmation state
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [isStep4Saved, setIsStep4Saved] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isComingNextModalOpen, setIsComingNextModalOpen] = useState(false);

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
    setBudgetMode(s4.budget_mode);

    if (s4.quick_total_cultivation_cost_lkr) {
      setQuickCostInput(s4.quick_total_cultivation_cost_lkr);
    } else if (s4.total_cultivation_cost_lkr && s4.budget_mode === "quick") {
      setQuickCostInput(s4.total_cultivation_cost_lkr);
    }

    if (s4.detailed_expenses) {
      setDetailedExpenses(s4.detailed_expenses);
    }

    // Verify validity of restored data
    const validation = validateStep4(s4);
    if (validation.isValid) {
      setIsStep4Saved(true);
      if (s4.budget_mode === "detailed") {
        setDetailedWarning(validation.warnings?.total_cultivation_cost_lkr);
      } else {
        setQuickCostWarning(validation.warnings?.total_cultivation_cost_lkr);
      }
    }
  }, [router]);

  // Running total calculation for Detailed Budget
  const detailedCalculation = useMemo(() => {
    return calculateDetailedCultivationTotal(detailedExpenses);
  }, [detailedExpenses]);

  // Handle mode switch between Quick and Detailed Budget
  const handleModeChange = (newMode: BudgetMode) => {
    if (newMode === budgetMode) return;
    setBudgetMode(newMode);
    setIsStep4Saved(false);

    // Re-evaluate validation for the newly selected mode
    if (newMode === "detailed") {
      const val = validateDetailedExpenses(detailedExpenses);
      setDetailedWarning(val.warning);
      if (hasAttemptedSubmit) {
        setDetailedErrors(val.errors);
      }
    } else {
      const val = validateCultivationCost(quickCostInput);
      setQuickCostWarning(val.warning);
      if (hasAttemptedSubmit) {
        setQuickCostError(val.error);
      }
    }
  };

  // Handle Quick Budget input change
  const handleQuickCostChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuickCostInput(value);
    setIsStep4Saved(false);

    const validation = validateCultivationCost(value);
    setQuickCostWarning(validation.warning);

    if (hasAttemptedSubmit) {
      setQuickCostError(validation.error);
    } else if (validation.isValid) {
      setQuickCostError(undefined);
    }
  };

  // Handle Detailed Budget expense field change
  const handleDetailedFieldChange = (key: DetailedExpenseKey, value: string) => {
    const updated = {
      ...detailedExpenses,
      [key]: value,
    };
    setDetailedExpenses(updated);
    setIsStep4Saved(false);

    // Clear error for this field if it becomes valid or empty
    const fieldVal = validateDetailedExpenseField(key, value);
    if (fieldVal.isValid) {
      setDetailedErrors((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    } else if (hasAttemptedSubmit) {
      setDetailedErrors((prev) => ({
        ...prev,
        [key]: fieldVal.error,
      }));
    }

    // Update zero-cost warning on running sum
    const calc = calculateDetailedCultivationTotal(updated);
    if (calc.isZeroCost) {
      setDetailedWarning(
        "Cultivation cost is set to Rs. 0. Profit percentage and risk evaluation may be unavailable when cost is zero."
      );
    } else {
      setDetailedWarning(undefined);
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

      // 2. Validate Step 4 budget
      const step4Payload: Partial<Step4FormData> = {
        budget_mode: budgetMode,
        quick_total_cultivation_cost_lkr: quickCostInput,
        detailed_expenses: detailedExpenses,
      };

      const validation = validateStep4(step4Payload);

      // Check budget errors
      if (budgetMode === "detailed") {
        setDetailedErrors(validation.errors.detailed_expenses || {});
        setDetailedWarning(validation.warnings?.total_cultivation_cost_lkr);

        const hasDetailedErrors = Object.keys(validation.errors.detailed_expenses || {}).length > 0;
        if (hasDetailedErrors) {
          setIsStep4Saved(false);
          // Find first invalid detailed field and focus it accessibly
          const firstErrKey = DETAILED_EXPENSE_CATEGORIES.find(
            (c) => validation.errors.detailed_expenses?.[c.key]
          )?.key;
          if (firstErrKey && detailedInputRefs.current[firstErrKey]) {
            detailedInputRefs.current[firstErrKey]?.focus();
            detailedInputRefs.current[firstErrKey]?.scrollIntoView({ behavior: "smooth", block: "center" });
          }
          return;
        }
      } else {
        setQuickCostError(validation.errors.quick_total_cultivation_cost_lkr);
        setQuickCostWarning(validation.warnings?.total_cultivation_cost_lkr);

        if (validation.errors.quick_total_cultivation_cost_lkr) {
          setIsStep4Saved(false);
          costInputRef.current?.focus();
          costInputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
          return;
        }
      }

      if (!validation.isValid) {
        setIsStep4Saved(false);
        return;
      }

      // 3. Persist valid selections preserving mode isolation and decimal precision
      saveValidatedStep4ToStorage(step4Payload);
      setIsStep4Saved(true);

      // Pre-save validated analysis snapshot so results page is immediately ready
      const fullVal = loadAndValidateWizardFromStorage();
      if (fullVal.isValid && fullVal.snapshot) {
        saveAnalysisSnapshot(fullVal.snapshot);
      }

      setIsComingNextModalOpen(true);
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

  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case "Vegetable":
        return "bg-[#E7F5EB] text-[#166534] border-[#22A06B]/40";
      case "Grain":
        return "bg-amber-50 text-amber-900 border-amber-300";
      case "Condiment":
        return "bg-rose-50 text-rose-900 border-rose-300";
      case "Legume":
        return "bg-teal-50 text-teal-900 border-teal-300";
      default:
        return "bg-slate-50 text-slate-800 border-slate-200";
    }
  };

  // Render friendly redirect notice if prerequisites are not met
  if (
    guardStatus === "invalid_step1" ||
    guardStatus === "invalid_step2" ||
    guardStatus === "invalid_step3"
  ) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-4">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-700 shadow-2xs">
          <AlertCircle className="h-7 w-7" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">Previous Steps Required</h2>
        <p className="text-sm text-slate-600 max-w-md mx-auto leading-relaxed">
          {guardMessage}
        </p>
        <div className="pt-2">
          <Link
            href={guardTarget || "/market-profit/new-analysis"}
            className="inline-flex items-center gap-2 rounded-xl bg-[#15803d] px-5 py-2.5 text-xs font-bold text-white hover:bg-[#166534] transition-colors shadow-2xs"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Go to incomplete step</span>
          </Link>
        </div>
      </div>
    );
  }

  // Loading state while checking guards
  if (guardStatus === "checking") {
    return (
      <div className="max-w-xl mx-auto py-16 text-center text-sm text-slate-500">
        Loading cultivation budget parameters...
      </div>
    );
  }

  // Active effective total for display and status
  const effectiveTotalNumber =
    budgetMode === "detailed"
      ? detailedCalculation.totalCultivationCost
      : parseFloat(quickCostInput) || 0;

  const isQuickNumberValid =
    !Number.isNaN(parseFloat(quickCostInput)) && parseFloat(quickCostInput) >= 0;

  const isFormValid =
    budgetMode === "detailed"
      ? Object.keys(detailedErrors).length === 0
      : isQuickNumberValid && !quickCostError;

  return (
    <div className="space-y-8 pb-16">
      {/* Top Navigation & Breadcrumb */}
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/market-profit/new-analysis/selling-market"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs sm:text-sm font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors shadow-2xs group"
        >
          <ArrowLeft className="h-4 w-4 text-slate-500 group-hover:-translate-x-0.5 transition-transform" />
          <span>Back to Selling Market</span>
        </Link>

        <span className="text-xs font-semibold text-[#166534] bg-[#E7F5EB] border border-[#22A06B]/30 px-3 py-1 rounded-full shadow-2xs">
          New Analysis Wizard · Step 4 of 4
        </span>
      </div>

      {/* Page Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
          Plan Your Cultivation Budget
        </h1>
        <p className="text-sm sm:text-base text-slate-600 mt-1.5 leading-relaxed">
          Enter your estimated cultivation expenses using either a quick lump-sum or detailed itemized categories.
        </p>
      </div>

      {/* Progress Stepper - Step 4 is Active */}
      <WizardProgress currentStep={4} />

      {/* Compact Farmer Summary of Steps 1, 2, and 3 */}
      <section className="rounded-2xl sm:rounded-3xl border border-emerald-200/80 bg-linear-to-r from-emerald-50/70 via-emerald-50/30 to-white p-4 sm:p-5 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4 min-w-0">
            {cropImage && (
              <div className="relative h-16 w-24 sm:h-18 sm:w-28 rounded-2xl overflow-hidden shrink-0 border border-emerald-200 shadow-xs bg-white">
                <Image
                  src={cropImage}
                  alt={selectedCropMeta?.name_en || "Selected crop"}
                  fill
                  className="object-cover"
                  sizes="(max-width: 640px) 96px, 112px"
                />
              </div>
            )}
            <div className="min-w-0 space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#15803d] bg-white border border-[#22A06B]/30 px-2 py-0.5 rounded-full shadow-2xs">
                  Harvest &amp; Selling Summary
                </span>
                {selectedCropMeta && (
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getCategoryBadgeClass(
                      selectedCropMeta.category
                    )}`}
                  >
                    {selectedCropMeta.category}
                  </span>
                )}
              </div>
              <div className="text-base sm:text-lg font-bold text-slate-900 truncate flex items-baseline gap-2">
                <span>{selectedCropMeta?.name_en || "Crop"}</span>
                <span className="text-xs sm:text-sm font-medium text-slate-500">
                  ({selectedCropMeta?.name_si})
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-600">
                <span className="flex items-center gap-1 font-medium text-slate-700">
                  <MapPin className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  {selectedDistrictMeta?.name || "District"} District
                </span>
                <span className="text-slate-300">•</span>
                <span className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  {formatDateDisplay(step2Data.harvest_date)}
                </span>
                <span className="text-slate-300">•</span>
                <span className="flex items-center gap-1">
                  <Compass className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  {step2Data.land_extent_acres} Acres
                </span>
                <span className="text-slate-300">•</span>
                <span className="flex items-center gap-1">
                  <Scale className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  {formatKg(step2Data.expected_yield_kg)}
                </span>
                <span className="text-slate-300">•</span>
                <span className="flex items-center gap-1 font-medium text-slate-700">
                  <Store className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  {selectedMarketMeta?.name || "Market"}
                </span>
                <span className="text-slate-300">•</span>
                <span className="flex items-center gap-1 font-semibold text-[#166534]">
                  {step3Data.price_type === "retail" ? (
                    <ShoppingBag className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  ) : (
                    <Package className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  )}
                  <span className="capitalize">{step3Data.price_type || "Wholesale"} Price</span>
                </span>
              </div>
            </div>
          </div>

          <Link
            href="/market-profit/new-analysis/selling-market"
            className="inline-flex items-center justify-center gap-1.5 text-xs font-bold text-[#15803d] hover:text-[#166534] bg-white hover:bg-emerald-50 px-3.5 py-2 rounded-xl border border-emerald-200/90 shadow-2xs transition-colors self-start sm:self-auto shrink-0 group"
          >
            <span>Edit Selections</span>
            <ChevronRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>
      </section>

      {/* Budget Mode Switcher: Quick vs Detailed */}
      <section className="space-y-3">
        <label className="block text-sm font-bold text-slate-900 tracking-tight">
          Select Budget Entry Method
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Quick Budget Mode Option */}
          <div
            role="radio"
            aria-checked={budgetMode === "quick"}
            tabIndex={0}
            onClick={() => handleModeChange("quick")}
            onKeyDown={(e) => {
              if (e.key === " " || e.key === "Enter") {
                e.preventDefault();
                handleModeChange("quick");
              }
            }}
            className={`relative rounded-2xl border-2 p-5 cursor-pointer transition-all shadow-2xs flex flex-col justify-between gap-3 focus:outline-hidden focus:ring-4 focus:ring-emerald-500/20 ${
              budgetMode === "quick"
                ? "border-[#15803d] bg-emerald-50/60 shadow-xs"
                : "border-slate-200/90 bg-white hover:border-emerald-300 hover:bg-slate-50/70"
            }`}
          >
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div
                  className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
                    budgetMode === "quick"
                      ? "bg-[#15803d] text-white"
                      : "bg-[#E7F5EB] text-[#15803d]"
                  }`}
                >
                  <Coins className="h-5 w-5" />
                </div>

                <div
                  className={`h-5 w-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${
                    budgetMode === "quick"
                      ? "border-[#15803d] bg-[#15803d] text-white"
                      : "border-slate-300 bg-white"
                  }`}
                >
                  {budgetMode === "quick" && <Check className="h-3 w-3 stroke-[3]" />}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900 tracking-tight">Quick Budget</h3>
                {budgetMode === "quick" && (
                  <span className="text-[10px] font-extrabold uppercase tracking-wide bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 px-2 py-0.5 rounded-full">
                    Active
                  </span>
                )}
              </div>

              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Enter one total cultivation expenditure for fast evaluation.
              </p>
            </div>

            <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
              <span className="font-medium text-slate-600">Single lump-sum input</span>
              <span className="font-semibold text-emerald-700">
                {budgetMode === "quick" ? "Selected" : "Select Quick"}
              </span>
            </div>
          </div>

          {/* Detailed Budget Mode Option */}
          <div
            role="radio"
            aria-checked={budgetMode === "detailed"}
            tabIndex={0}
            onClick={() => handleModeChange("detailed")}
            onKeyDown={(e) => {
              if (e.key === " " || e.key === "Enter") {
                e.preventDefault();
                handleModeChange("detailed");
              }
            }}
            className={`relative rounded-2xl border-2 p-5 cursor-pointer transition-all shadow-2xs flex flex-col justify-between gap-3 focus:outline-hidden focus:ring-4 focus:ring-emerald-500/20 ${
              budgetMode === "detailed"
                ? "border-[#15803d] bg-emerald-50/60 shadow-xs"
                : "border-slate-200/90 bg-white hover:border-emerald-300 hover:bg-slate-50/70"
            }`}
          >
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div
                  className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
                    budgetMode === "detailed"
                      ? "bg-[#15803d] text-white"
                      : "bg-[#E7F5EB] text-[#15803d]"
                  }`}
                >
                  <Receipt className="h-5 w-5" />
                </div>

                <div
                  className={`h-5 w-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${
                    budgetMode === "detailed"
                      ? "border-[#15803d] bg-[#15803d] text-white"
                      : "border-slate-300 bg-white"
                  }`}
                >
                  {budgetMode === "detailed" && <Check className="h-3 w-3 stroke-[3]" />}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900 tracking-tight">Detailed Budget</h3>
                {budgetMode === "detailed" && (
                  <span className="text-[10px] font-extrabold uppercase tracking-wide bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 px-2 py-0.5 rounded-full">
                    Active
                  </span>
                )}
              </div>

              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Itemize costs across 10 farming categories with automatic live summing.
              </p>
            </div>

            <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
              <span className="font-medium text-slate-600">10 Itemized farming categories</span>
              <span className="font-semibold text-emerald-700">
                {budgetMode === "detailed" ? "Selected" : "Select Detailed"}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Main Budget Form */}
      <form onSubmit={handleFormSubmit} className="space-y-8" noValidate>
        {/* ================================================================= */}
        {/* OPTION A: QUICK BUDGET SECTION */}
        {/* ================================================================= */}
        {budgetMode === "quick" && (
          <section className="rounded-2xl sm:rounded-3xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs space-y-6 animate-in fade-in">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#15803d]">
                <Coins className="h-4 w-4" />
                <span>Step 4.1 — Quick Budget</span>
              </div>
              <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight mt-0.5">
                Total Cultivation Cost (LKR) <span className="text-red-500">*</span>
              </h2>
              <p className="text-xs sm:text-sm text-slate-500 mt-1">
                Enter your total estimated expenditure to grow and transport your crop.
              </p>
            </div>

            {/* Quick Cost Input */}
            <div className="space-y-2">
              <label
                htmlFor="total_cultivation_cost_lkr"
                className="block text-xs font-bold uppercase tracking-wider text-slate-700"
              >
                Expected Cultivation Cost (LKR)
              </label>

              <div className="relative max-w-lg">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-sm font-bold text-slate-500">
                  Rs.
                </div>
                <input
                  ref={costInputRef}
                  id="total_cultivation_cost_lkr"
                  name="total_cultivation_cost_lkr"
                  type="text"
                  inputMode="decimal"
                  value={quickCostInput}
                  onChange={handleQuickCostChange}
                  placeholder="150000"
                  aria-invalid={Boolean(quickCostError)}
                  aria-describedby="cost-helper-text cost-error cost-warning"
                  className={`w-full pl-12 pr-4 py-3.5 rounded-xl border-2 font-semibold text-slate-900 text-base shadow-2xs focus:outline-hidden transition-all ${
                    quickCostError
                      ? "border-red-400 bg-red-50/20 focus:border-red-500 focus:ring-4 focus:ring-red-500/20"
                      : "border-slate-300 bg-white focus:border-[#15803d] focus:ring-4 focus:ring-emerald-500/20"
                  }`}
                />
              </div>

              {/* Error Message */}
              {quickCostError && (
                <div
                  id="cost-error"
                  role="alert"
                  className="rounded-xl border border-red-200 bg-red-50/80 p-3 text-red-900 text-xs font-semibold flex items-center gap-2.5 max-w-lg animate-in fade-in"
                >
                  <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                  <span>{quickCostError}</span>
                </div>
              )}

              {/* Zero-Cost Warning Banner */}
              {quickCostWarning && !quickCostError && (
                <div
                  id="cost-warning"
                  role="alert"
                  className="rounded-xl border border-amber-200 bg-amber-50/80 p-3.5 text-amber-900 text-xs font-medium flex items-start gap-2.5 max-w-lg animate-in fade-in"
                >
                  <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
                  <span>{quickCostWarning}</span>
                </div>
              )}

              {/* Live Formatted Amount Preview */}
              {isQuickNumberValid && parseFloat(quickCostInput) > 0 && !quickCostError && (
                <div className="text-xs font-semibold text-[#15803d] flex items-center gap-1.5 pt-1">
                  <Check className="h-3.5 w-3.5 stroke-[2.5]" />
                  <span>Formatted: {formatLKR(parseFloat(quickCostInput))}</span>
                </div>
              )}
            </div>

            {/* Helper Advisory Note */}
            <div className="flex items-start gap-3 p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 leading-relaxed max-w-2xl">
              <Info className="h-4 w-4 text-slate-500 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-800">What does cultivation cost typically include?</p>
                <p className="mt-0.5 text-slate-500">
                  Common farming expenses include land preparation, seeds/nursery plants, fertilizers, pest control, irrigation fuel/electricity, labor for planting and harvesting, and transport to the economic centre.
                </p>
              </div>
            </div>
          </section>
        )}

        {/* ================================================================= */}
        {/* OPTION B: DETAILED BUDGET SECTION */}
        {/* ================================================================= */}
        {budgetMode === "detailed" && (
          <section className="rounded-2xl sm:rounded-3xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs space-y-6 animate-in fade-in">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#15803d]">
                  <Receipt className="h-4 w-4" />
                  <span>Step 4.1 — Detailed Budget (10 Categories)</span>
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight mt-0.5">
                  Itemized Cultivation Expenses
                </h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  Enter your estimated cost for each category. Empty fields are treated as Rs. 0.
                </p>
              </div>

              {/* Live Running Total Badge in Section Header */}
              <div className="bg-[#E7F5EB] border border-[#22A06B]/30 rounded-2xl px-5 py-3 text-left sm:text-right shrink-0">
                <div className="text-[10px] font-bold uppercase tracking-wider text-[#166534]">
                  Calculated Total
                </div>
                <div className="text-xl sm:text-2xl font-black text-[#15803d]">
                  {formatLKR(detailedCalculation.totalCultivationCost)}
                </div>
                <div className="text-[10px] text-emerald-800 font-medium">
                  {detailedCalculation.nonZeroCount} of 10 categories filled
                </div>
              </div>
            </div>

            {/* 10 Expense Categories Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              {DETAILED_EXPENSE_CATEGORIES.map((cat) => {
                const val = detailedExpenses[cat.key];
                const err = detailedErrors[cat.key];
                const hasValue =
                  val !== "" && !Number.isNaN(parseFloat(val)) && parseFloat(val) > 0;

                return (
                  <div
                    key={cat.key}
                    className={`p-4 rounded-2xl border-2 transition-all shadow-2xs ${
                      err
                        ? "border-red-300 bg-red-50/20"
                        : hasValue
                        ? "border-emerald-300 bg-emerald-50/30"
                        : "border-slate-200/90 bg-white hover:border-emerald-200"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <label
                        htmlFor={`detailed_expense_${cat.key}`}
                        className="text-xs sm:text-sm font-bold text-slate-900"
                      >
                        {cat.label}
                      </label>
                      <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
                        LKR
                      </span>
                    </div>

                    <p className="text-xs text-slate-500 mb-2.5 leading-snug">
                      {cat.helperText}
                    </p>

                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-xs font-bold text-slate-500">
                        Rs.
                      </div>
                      <input
                        ref={(el) => {
                          detailedInputRefs.current[cat.key] = el;
                        }}
                        id={`detailed_expense_${cat.key}`}
                        name={`detailed_expense_${cat.key}`}
                        type="text"
                        inputMode="decimal"
                        value={val}
                        onChange={(e) => handleDetailedFieldChange(cat.key, e.target.value)}
                        placeholder={cat.placeholder}
                        aria-invalid={Boolean(err)}
                        className={`w-full pl-11 pr-3.5 py-2.5 rounded-xl border text-sm font-semibold text-slate-900 shadow-2xs focus:outline-hidden transition-all ${
                          err
                            ? "border-red-400 bg-white focus:border-red-500 focus:ring-4 focus:ring-red-500/20"
                            : "border-slate-300 bg-white focus:border-[#15803d] focus:ring-4 focus:ring-emerald-500/20"
                        }`}
                      />
                    </div>

                    {/* Field Error Message */}
                    {err && (
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-red-600 mt-2">
                        <AlertCircle className="h-3.5 w-3.5 shrink-0 text-red-500" />
                        <span>{err}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Zero-Cost Warning Banner for Detailed Budget */}
            {detailedWarning && Object.keys(detailedErrors).length === 0 && (
              <div
                role="alert"
                className="rounded-xl border border-amber-200 bg-amber-50/80 p-3.5 text-amber-900 text-xs font-medium flex items-start gap-2.5 animate-in fade-in"
              >
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
                <span>{detailedWarning}</span>
              </div>
            )}

            {/* Calculation Provenance Banner */}
            <div className="flex items-start gap-3 p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 leading-relaxed">
              <Calculator className="h-4 w-4 text-[#15803d] shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-800">
                  Transparent, Farmer-Driven Budget Calculation
                </p>
                <p className="mt-0.5 text-slate-500">
                  The total above is calculated automatically as the exact sum of your entered categories. Unfilled categories are treated as Rs. 0.
                </p>
              </div>
            </div>
          </section>
        )}

        {/* ================================================================= */}
        {/* PROMINENT LIVE TOTAL CULTIVATION COST SUMMARY */}
        {/* ================================================================= */}
        <section className="rounded-2xl sm:rounded-3xl border-2 border-emerald-300 bg-linear-to-br from-emerald-50/90 via-emerald-50/40 to-white p-6 sm:p-7 shadow-xs space-y-4 animate-in fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="h-12 w-12 rounded-2xl bg-[#15803d] text-white flex items-center justify-center shrink-0 shadow-xs">
                <Wallet className="h-6 w-6 stroke-[2.2]" />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#166534] block">
                  Total Cultivation Cost
                </span>
                <div className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                  {formatLKR(effectiveTotalNumber)}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
              <span className="text-xs font-bold text-[#166534] bg-white border border-[#22A06B]/30 px-3 py-1.5 rounded-xl shadow-2xs">
                {budgetMode === "detailed"
                  ? `Detailed Budget (${detailedCalculation.nonZeroCount} Itemized)`
                  : "Quick Budget (Single Total)"}
              </span>

              {isStep4Saved && (
                <span className="text-xs font-bold text-white bg-[#15803d] px-3 py-1.5 rounded-xl shadow-2xs flex items-center gap-1.5">
                  <Check className="h-3.5 w-3.5 stroke-[2.5]" />
                  <span>Saved</span>
                </span>
              )}
            </div>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed border-t border-emerald-200/70 pt-3">
            {effectiveTotalNumber === 0 ? (
              <span className="text-amber-800 font-medium">
                Note: Total cultivation cost is currently Rs. 0. Projected net profit and ROI require non-zero expenditure for full financial evaluation.
              </span>
            ) : (
              <span>
                This verified cultivation budget will be used alongside the AI market price forecast to evaluate breakeven unit costs, net returns, and financial risk.
              </span>
            )}
          </p>
        </section>

        {/* Confirmation Status if Saved */}
        {isStep4Saved && (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-emerald-800 animate-in fade-in">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-[#15803d] text-white flex items-center justify-center shrink-0">
                <Check className="h-4 w-4 stroke-[3]" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">
                  Step 4 Confirmed &amp; Ready for Analysis
                </h4>
                <p className="text-xs text-emerald-800">
                  Effective cost: {formatLKR(effectiveTotalNumber)} ({budgetMode === "detailed" ? "Detailed Budget" : "Quick Budget"}) • Ready for Price Forecasting &amp; Profit Risk Analysis
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 self-end sm:self-auto">
              <button
                type="button"
                onClick={() => setIsComingNextModalOpen(true)}
                className="px-3.5 py-1.5 rounded-xl bg-white hover:bg-emerald-100/70 text-[#166534] border border-emerald-300 text-xs font-bold transition-colors cursor-pointer shadow-2xs"
              >
                View Analysis Summary
              </button>
            </div>
          </div>
        )}

        {/* Action Buttons Bar */}
        <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-200/80">
          <Link
            href="/market-profit/new-analysis/selling-market"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors shadow-2xs group"
          >
            <ArrowLeft className="h-4 w-4 text-slate-500 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back to Selling Market</span>
          </Link>

          <button
            type="submit"
            disabled={isSubmitting || !isFormValid}
            aria-busy={isSubmitting}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 rounded-xl bg-[#15803d] hover:bg-[#166534] active:scale-95 text-white px-8 py-3.5 text-sm font-bold shadow-sm shadow-emerald-800/20 transition-all cursor-pointer group disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span>{isSubmitting ? "Validating Budget..." : "View Analysis Results"}</span>
            <ArrowRight className="h-4 w-4 text-emerald-100 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </form>

      {/* Analysis Coming Next Modal */}
      <AnalysisComingNextModal
        isOpen={isComingNextModalOpen}
        onClose={() => setIsComingNextModalOpen(false)}
        cropName={selectedCropMeta?.name_en || "Selected Crop"}
        cropNameSi={selectedCropMeta?.name_si || ""}
        cropImage={cropImage}
        districtName={selectedDistrictMeta?.name || step1Data.cultivation_district_id}
        isPilotDistrict={Boolean(selectedDistrictMeta?.is_pilot)}
        harvestDate={step2Data.harvest_date}
        landExtentAcres={step2Data.land_extent_acres}
        expectedYieldKg={step2Data.expected_yield_kg}
        marketName={selectedMarketMeta?.name || targetMarketId || "Economic Centre"}
        marketRegion={selectedMarketMeta?.region || ""}
        isPilotMarket={Boolean(selectedMarketMeta?.is_pilot_recommended)}
        priceType={step3Data.price_type}
        budgetMode={budgetMode}
        effectiveCultivationCost={effectiveTotalNumber}
      />
    </div>
  );
}
