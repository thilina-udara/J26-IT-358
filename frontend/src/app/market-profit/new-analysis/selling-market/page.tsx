"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Image, { StaticImageData } from "next/image";
import {
  ArrowLeft,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Calendar,
  Compass,
  Scale,
  MapPin,
  Store,
  Check,
  ChevronRight,
  Package,
  ShoppingBag,
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
import { formatDateDisplay, formatKg } from "../../lib/formatters";
import {
  loadStep1FromStorage,
  Step1FormData,
  loadStep2FromStorage,
  Step2FormData,
  validateStep3,
  isStep3Complete,
  loadStep3FromStorage,
  saveStep3ToStorage,
  saveValidatedStep3ToStorage,
  checkPreviousStepsForStep3,
  clearAnalysisSnapshot,
  PriceType,
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

export default function SellingMarketPage() {
  const router = useRouter();
  const marketSelectionSectionRef = useRef<HTMLDivElement>(null);
  const priceTypeSectionRef = useRef<HTMLDivElement>(null);
  const firstMarketCardRef = useRef<HTMLDivElement>(null);
  const firstPriceTypeRadioRef = useRef<HTMLDivElement>(null);

  // Wizard state from Step 1 and Step 2
  const [step1Data, setStep1Data] = useState<Step1FormData>({
    crop_id: "",
    cultivation_district_id: "",
  });
  const [step2Data, setStep2Data] = useState<Step2FormData>({
    harvest_date: "",
    land_extent_acres: "",
    expected_yield_kg: "",
  });

  // Guard state
  const [guardStatus, setGuardStatus] = useState<"checking" | "invalid_step1" | "invalid_step2" | "ready">("checking");
  const [guardMessage, setGuardMessage] = useState<string>("");
  const [guardTarget, setGuardTarget] = useState<string>("");

  // Step 3 state: market and price type
  const [selectedMarketId, setSelectedMarketId] = useState<string>("");
  const [selectedPriceType, setSelectedPriceType] = useState<PriceType | "">("");
  const [marketError, setMarketError] = useState<string | undefined>(undefined);
  const [priceTypeError, setPriceTypeError] = useState<string | undefined>(undefined);
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [isStep3Saved, setIsStep3Saved] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validate Step 1 and Step 2 prerequisites on mount
  useEffect(() => {
    const s1 = loadStep1FromStorage();
    const s2 = loadStep2FromStorage();
    const integrity = checkPreviousStepsForStep3(s1, s2);

    if (!integrity.isValid) {
      if (integrity.earliestIncompleteStep === 1) {
        setGuardStatus("invalid_step1");
      } else {
        setGuardStatus("invalid_step2");
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

    // Restore Step 3 if previously selected
    const s3 = loadStep3FromStorage();
    const market = s3.target_market_id || s3.selling_market_id || "";
    if (market) {
      setSelectedMarketId(market);
    }
    if (s3.price_type) {
      setSelectedPriceType(s3.price_type);
    }
    if (isStep3Complete(s3)) {
      setIsStep3Saved(true);
    }

    setGuardStatus("ready");
  }, [router]);

  // Handle market selection
  const handleMarketSelect = (marketId: string) => {
    clearAnalysisSnapshot();
    setSelectedMarketId(marketId);
    setMarketError(undefined);
    setIsStep3Saved(false);

    // Persist draft immediately so page refresh preserves choices
    saveStep3ToStorage({
      target_market_id: marketId,
      selling_market_id: marketId,
      price_type: selectedPriceType,
    });
  };

  // Handle price type selection
  const handlePriceTypeSelect = (priceType: PriceType) => {
    clearAnalysisSnapshot();
    setSelectedPriceType(priceType);
    setPriceTypeError(undefined);
    setIsStep3Saved(false);

    // Persist draft immediately so page refresh preserves choices
    saveStep3ToStorage({
      target_market_id: selectedMarketId,
      selling_market_id: selectedMarketId,
      price_type: priceType,
    });
  };

  // Handle Step 3 submission with validation
  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    setIsSubmitting(true);
    setHasAttemptedSubmit(true);

    try {
      // 1. Re-verify earlier steps integrity before submission
      const s1 = loadStep1FromStorage();
      const s2 = loadStep2FromStorage();
      const integrity = checkPreviousStepsForStep3(s1, s2);
      if (!integrity.isValid) {
        router.replace(integrity.redirectTarget || "/market-profit/new-analysis");
        return;
      }

      // 2. Validate Step 3 inputs together
      const validation = validateStep3({
        target_market_id: selectedMarketId,
        selling_market_id: selectedMarketId,
        price_type: selectedPriceType,
      });

      const mError = validation.errors.target_market_id || validation.errors.selling_market_id;
      const pError = validation.errors.price_type;

      setMarketError(mError);
      setPriceTypeError(pError);

      if (!validation.isValid) {
        setIsStep3Saved(false);
        if (mError) {
          firstMarketCardRef.current?.focus();
          marketSelectionSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        } else if (pError) {
          firstPriceTypeRadioRef.current?.focus();
          priceTypeSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        return;
      }

      // 3. Persist valid selections
      setMarketError(undefined);
      setPriceTypeError(undefined);
      saveValidatedStep3ToStorage({
        target_market_id: selectedMarketId,
        selling_market_id: selectedMarketId,
        price_type: selectedPriceType,
      });
      setIsStep3Saved(true);
      router.push("/market-profit/new-analysis/cultivation-costs");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Find metadata for summary cards
  const selectedCropMeta: FrontendCropMetadata | undefined =
    SUPPORTED_FRONTEND_CROPS.find((c) => c.crop_id === step1Data.crop_id);
  const selectedDistrictMeta: DistrictMetadata | undefined =
    SRI_LANKA_DISTRICTS.find((d) => d.id === step1Data.cultivation_district_id);
  const selectedMarketMeta: MarketMetadata | undefined =
    STANDARD_MARKETS.find((m) => m.id === selectedMarketId);
  const cropImage = step1Data.crop_id ? CROP_IMAGE_MAP[step1Data.crop_id] : null;

  const isFormValid = Boolean(
    selectedMarketId && (selectedPriceType === "wholesale" || selectedPriceType === "retail")
  );

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
  if (guardStatus === "invalid_step1" || guardStatus === "invalid_step2") {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-4">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-700 shadow-2xs">
          <AlertCircle className="h-7 w-7" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Previous Steps Required
        </h2>
        <p className="text-sm text-slate-600 max-w-md mx-auto leading-relaxed">
          {guardMessage}
        </p>
        <div className="pt-2">
          <Link
            href={guardTarget}
            className="inline-flex items-center gap-2 text-sm font-semibold text-[#15803d] hover:text-[#166534] hover:underline"
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
        Loading analysis wizard parameters...
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-16">
      {/* Top Navigation & Breadcrumb */}
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/market-profit/new-analysis/harvest-details"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs sm:text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs group"
        >
          <ArrowLeft className="h-4 w-4 text-slate-500 group-hover:-translate-x-0.5 transition-transform" />
          <span>Back to Harvest Details</span>
        </Link>

        <span className="text-xs font-semibold text-[#166534] bg-[#E7F5EB] border border-[#22A06B]/30 px-3 py-1 rounded-full shadow-2xs">
          New Analysis Wizard · Step 3 of 4
        </span>
      </div>

      {/* Page Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
          Where Will You Sell Your Harvest?
        </h1>
        <p className="text-sm sm:text-base text-slate-600 mt-1.5 leading-relaxed">
          Choose your selling market and price type.
        </p>
      </div>

      {/* Progress Stepper - Step 3 is Active */}
      <WizardProgress currentStep={3} />

      {/* Selected Harvest Summary */}
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
                  Harvest Summary
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
              </div>
            </div>
          </div>

          <Link
            href="/market-profit/new-analysis/harvest-details"
            className="inline-flex items-center justify-center gap-1.5 text-xs font-bold text-[#15803d] hover:text-[#166534] bg-white hover:bg-emerald-50 px-3.5 py-2 rounded-xl border border-emerald-200/90 shadow-2xs transition-colors self-start sm:self-auto shrink-0 group"
          >
            <span>Edit Harvest Details</span>
            <ChevronRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>
      </section>

      {/* Main Market & Price Type Form */}
      <form onSubmit={handleFormSubmit} className="space-y-8" noValidate>
        {/* Error Alert Banner */}
        {hasAttemptedSubmit && (marketError || priceTypeError) && (
          <div
            role="alert"
            className="rounded-2xl border border-red-200 bg-red-50/90 p-4 sm:p-5 text-red-900 shadow-xs flex items-center gap-3 animate-in fade-in"
          >
            <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
            <div className="text-sm font-semibold">
              {marketError && priceTypeError
                ? "Please select a target selling market and a price type."
                : marketError || priceTypeError}
            </div>
          </div>
        )}

        {/* 1. Market Selection Section */}
        <section
          ref={marketSelectionSectionRef}
          className="rounded-2xl sm:rounded-3xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs space-y-5"
        >
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#15803d]">
              <Store className="h-4 w-4" />
              <span>Step 3.1 — Selling Market</span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              Select Selling Market <span className="text-red-500">*</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Select the Dedicated Economic Centre or terminal wholesale market where your harvest will be sold.
            </p>
          </div>

          {/* Market-level Error */}
          {hasAttemptedSubmit && marketError && (
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50/80 p-3.5 text-red-900 text-xs font-semibold flex items-center gap-2.5 animate-in fade-in"
            >
              <AlertCircle className="h-4 w-4 text-red-600 shrink-0" />
              <span>{marketError}</span>
            </div>
          )}

          {/* Markets Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {STANDARD_MARKETS.map((market, idx) => {
              const isSelected = selectedMarketId === market.id;

              return (
                <div
                  key={market.id}
                  ref={idx === 0 ? firstMarketCardRef : undefined}
                  tabIndex={0}
                  role="button"
                  aria-pressed={isSelected}
                  onClick={() => handleMarketSelect(market.id)}
                  onKeyDown={(e) => {
                    if (e.key === " " || e.key === "Enter") {
                      e.preventDefault();
                      handleMarketSelect(market.id);
                    }
                  }}
                  className={`relative rounded-2xl border-2 p-4 cursor-pointer transition-all shadow-2xs flex items-center justify-between gap-3 focus:outline-hidden focus:ring-4 focus:ring-emerald-500/20 ${
                    isSelected
                      ? "border-[#15803d] bg-emerald-50/60 shadow-xs"
                      : "border-slate-200/90 bg-white hover:border-emerald-300 hover:bg-slate-50/70"
                  }`}
                >
                  <div className="space-y-1 min-w-0 pr-2">
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                          isSelected
                            ? "bg-[#15803d] text-white"
                            : "bg-[#E7F5EB] text-[#15803d]"
                        }`}
                      >
                        <Store className="h-4 w-4" />
                      </div>
                      <h3 className="text-sm font-bold text-slate-900 tracking-tight leading-snug truncate">
                        {market.name}
                      </h3>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-slate-500 pl-10.5">
                      <MapPin className="h-3 w-3 text-emerald-600 shrink-0" />
                      <span className="truncate">{market.region}</span>
                    </div>
                  </div>

                  <div
                    className={`h-5 w-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${
                      isSelected
                        ? "border-[#15803d] bg-[#15803d] text-white"
                        : "border-slate-300 bg-white"
                    }`}
                  >
                    {isSelected && <Check className="h-3 w-3 stroke-[3]" />}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* 2. Price Type Selection Section */}
        <section
          ref={priceTypeSectionRef}
          className="rounded-2xl sm:rounded-3xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs space-y-5"
        >
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#15803d]">
              <Package className="h-4 w-4" />
              <span>Step 3.2 — Price Type</span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              Select Price Type <span className="text-red-500">*</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Choose whether your financial analysis should use wholesale or retail market prices.
            </p>
          </div>

          {/* Field-level Error */}
          {hasAttemptedSubmit && priceTypeError && (
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50/80 p-3.5 text-red-900 text-xs font-semibold flex items-center gap-2.5 animate-in fade-in"
            >
              <AlertCircle className="h-4 w-4 text-red-600 shrink-0" />
              <span>{priceTypeError}</span>
            </div>
          )}

          {/* Two Accessible Cards: Wholesale and Retail */}
          <div
            role="radiogroup"
            aria-label="Choose your price type"
            aria-required="true"
            className="grid grid-cols-1 sm:grid-cols-2 gap-4"
          >
            {/* WHOLESALE */}
            <div
              ref={firstPriceTypeRadioRef}
              role="radio"
              aria-checked={selectedPriceType === "wholesale"}
              tabIndex={0}
              onClick={() => handlePriceTypeSelect("wholesale")}
              onKeyDown={(e) => {
                if (e.key === " " || e.key === "Enter") {
                  e.preventDefault();
                  handlePriceTypeSelect("wholesale");
                }
              }}
              className={`relative rounded-2xl border-2 p-5 cursor-pointer transition-all shadow-2xs flex flex-col justify-between gap-3 focus:outline-hidden focus:ring-4 focus:ring-emerald-500/20 ${
                selectedPriceType === "wholesale"
                  ? "border-[#15803d] bg-emerald-50/60 shadow-xs"
                  : "border-slate-200/90 bg-white hover:border-emerald-300 hover:bg-slate-50/70"
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div
                    className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
                      selectedPriceType === "wholesale"
                        ? "bg-[#15803d] text-white"
                        : "bg-[#E7F5EB] text-[#15803d]"
                    }`}
                  >
                    <Package className="h-5 w-5" />
                  </div>

                  <div
                    className={`h-5 w-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${
                      selectedPriceType === "wholesale"
                        ? "border-[#15803d] bg-[#15803d] text-white"
                        : "border-slate-300 bg-white"
                    }`}
                  >
                    {selectedPriceType === "wholesale" && (
                      <Check className="h-3 w-3 stroke-[3]" />
                    )}
                  </div>
                </div>

                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Wholesale
                </h3>

                <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                  Prices for bulk market trading.
                </p>
              </div>

              <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span className="font-medium text-slate-600">Bulk trading at Economic Centres</span>
                <span className="font-semibold text-emerald-700">
                  {selectedPriceType === "wholesale" ? "Selected" : "Select Wholesale"}
                </span>
              </div>
            </div>

            {/* RETAIL */}
            <div
              role="radio"
              aria-checked={selectedPriceType === "retail"}
              tabIndex={0}
              onClick={() => handlePriceTypeSelect("retail")}
              onKeyDown={(e) => {
                if (e.key === " " || e.key === "Enter") {
                  e.preventDefault();
                  handlePriceTypeSelect("retail");
                }
              }}
              className={`relative rounded-2xl border-2 p-5 cursor-pointer transition-all shadow-2xs flex flex-col justify-between gap-3 focus:outline-hidden focus:ring-4 focus:ring-emerald-500/20 ${
                selectedPriceType === "retail"
                  ? "border-[#15803d] bg-emerald-50/60 shadow-xs"
                  : "border-slate-200/90 bg-white hover:border-emerald-300 hover:bg-slate-50/70"
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div
                    className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
                      selectedPriceType === "retail"
                        ? "bg-[#15803d] text-white"
                        : "bg-[#E7F5EB] text-[#15803d]"
                    }`}
                  >
                    <ShoppingBag className="h-5 w-5" />
                  </div>

                  <div
                    className={`h-5 w-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${
                      selectedPriceType === "retail"
                        ? "border-[#15803d] bg-[#15803d] text-white"
                        : "border-slate-300 bg-white"
                    }`}
                  >
                    {selectedPriceType === "retail" && (
                      <Check className="h-3 w-3 stroke-[3]" />
                    )}
                  </div>
                </div>

                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Retail
                </h3>

                <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                  Prices paid by consumers.
                </p>
              </div>

              <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span className="font-medium text-slate-600">Consumer market pricing</span>
                <span className="font-semibold text-emerald-700">
                  {selectedPriceType === "retail" ? "Selected" : "Select Retail"}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Farmer-Friendly Step 3 Completion Summary */}
        {isStep3Saved && selectedMarketMeta && selectedPriceType && (
          <section className="rounded-2xl sm:rounded-3xl border-2 border-emerald-300 bg-linear-to-br from-emerald-50/90 via-emerald-50/40 to-white p-6 sm:p-7 shadow-xs space-y-4 animate-in fade-in">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-emerald-200/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-2xl bg-[#15803d] text-white flex items-center justify-center shrink-0 shadow-xs">
                  <CheckCircle2 className="h-6 w-6 stroke-[2.2]" />
                </div>
                <div>
                  <h3 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
                    Selling Market &amp; Price Type Confirmed
                  </h3>
                  <p className="text-xs text-emerald-800 font-medium">
                    Your market preferences are verified and stored for price trend forecasting.
                  </p>
                </div>
              </div>

              <Link
                href="/market-profit/new-analysis/cultivation-costs"
                className="inline-flex items-center gap-1.5 self-start sm:self-auto text-xs font-bold text-[#15803d] bg-white border border-emerald-200 px-3.5 py-2 rounded-xl hover:bg-emerald-50 shadow-2xs transition-colors cursor-pointer group"
              >
                <span>Proceed to Step 4</span>
                <ArrowRight className="h-3.5 w-3.5 text-emerald-600 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="flex items-center gap-3 p-3.5 rounded-xl bg-white border border-emerald-100 shadow-2xs">
                <div className="h-10 w-10 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                  <Store className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Selected Market
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {selectedMarketMeta.name}
                  </span>
                  <span className="text-xs text-slate-500 truncate block">
                    {selectedMarketMeta.region}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3.5 rounded-xl bg-white border border-emerald-100 shadow-2xs">
                <div className="h-10 w-10 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                  {selectedPriceType === "wholesale" ? (
                    <Package className="h-5 w-5" />
                  ) : (
                    <ShoppingBag className="h-5 w-5" />
                  )}
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Selected Price Type
                  </span>
                  <span className="text-sm font-bold text-slate-900 capitalize block">
                    {selectedPriceType} Market Price
                  </span>
                  <span className="text-xs text-slate-500 block">
                    {selectedPriceType === "wholesale"
                      ? "Prices for bulk market trading"
                      : "Prices paid by consumers"}
                  </span>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Action Buttons Bar */}
        <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-200/80">
          <Link
            href="/market-profit/new-analysis/harvest-details"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors shadow-2xs group"
          >
            <ArrowLeft className="h-4 w-4 text-slate-500 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back to Harvest Details</span>
          </Link>

          <button
            type="submit"
            disabled={isSubmitting || !isFormValid}
            aria-busy={isSubmitting}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 rounded-xl bg-[#15803d] hover:bg-[#166534] active:scale-95 text-white px-8 py-3.5 text-sm font-bold shadow-sm shadow-emerald-800/20 transition-all cursor-pointer group disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span>Next: Cultivation Costs</span>
            <ArrowRight className="h-4 w-4 text-emerald-100 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </form>
    </div>
  );
}
