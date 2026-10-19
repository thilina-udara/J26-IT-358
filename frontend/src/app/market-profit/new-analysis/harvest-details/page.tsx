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
  Sprout,
  MapPin,
  Clock,
  Info,
  Store,
  ChevronRight,
  Sparkles,
} from "lucide-react";

import { WizardProgress } from "../../components/WizardProgress";
import {
  SUPPORTED_FRONTEND_CROPS,
  SRI_LANKA_DISTRICTS,
  FrontendCropMetadata,
  DistrictMetadata,
} from "../../lib/constants";
import { formatDateDisplay, formatKg } from "../../lib/formatters";
import {
  validateStep1,
  loadStep1FromStorage,
  Step1FormData,
  validateHarvestDate,
  validateLandExtent,
  validateExpectedYield,
  validateStep2,
  isStep2Complete,
  loadStep2FromStorage,
  saveValidatedStep2ToStorage,
  getTodayDateString,
  clearAnalysisSnapshot,
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

export default function HarvestDetailsPage() {
  const router = useRouter();

  // Input element refs for accessibility and first-invalid-field focus
  const harvestDateInputRef = useRef<HTMLInputElement>(null);
  const landExtentInputRef = useRef<HTMLInputElement>(null);
  const expectedYieldInputRef = useRef<HTMLInputElement>(null);

  // Step 1 summary state
  const [step1Data, setStep1Data] = useState<Step1FormData>({
    crop_id: "",
    cultivation_district_id: "",
  });
  const [isStep1Valid, setIsStep1Valid] = useState<boolean | null>(null);

  // Step 2 form state
  const [harvestDate, setHarvestDate] = useState<string>("");
  const [landExtent, setLandExtent] = useState<string>("");
  const [expectedYield, setExpectedYield] = useState<string>("");
  const [dateError, setDateError] = useState<string | undefined>(undefined);
  const [extentError, setExtentError] = useState<string | undefined>(undefined);
  const [yieldError, setYieldError] = useState<string | undefined>(undefined);
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [isStep2Saved, setIsStep2Saved] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Minimum allowed date is today's local date
  const todayString = getTodayDateString();

  // Load Step 1 and Step 2 state on mount
  useEffect(() => {
    // 1. Verify Step 1 selections
    const savedStep1 = loadStep1FromStorage();
    const validation = validateStep1(savedStep1);

    if (!validation.isValid) {
      setIsStep1Valid(false);
      // Brief redirect delay to allow explanation to show
      const timer = setTimeout(() => {
        router.replace("/market-profit/new-analysis");
      }, 2000);
      return () => clearTimeout(timer);
    } else {
      setIsStep1Valid(true);
      setStep1Data(savedStep1);
    }

    // 2. Restore Step 2 saved values if available
    const savedStep2 = loadStep2FromStorage();
    if (savedStep2.harvest_date) {
      setHarvestDate(savedStep2.harvest_date);
    }
    if (savedStep2.land_extent_acres) {
      setLandExtent(savedStep2.land_extent_acres);
    }
    if (savedStep2.expected_yield_kg) {
      setExpectedYield(savedStep2.expected_yield_kg);
    }

    // If previously completed in full, restore confirmed status
    if (isStep2Complete(savedStep2)) {
      setIsStep2Saved(true);
    }
  }, [router]);

  // Handle date input change
  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newDate = e.target.value;
    clearAnalysisSnapshot();
    setHarvestDate(newDate);
    setIsStep2Saved(false);

    // Safely sync to session storage ONLY if full Step 2 remains valid
    saveValidatedStep2ToStorage({
      harvest_date: newDate,
      land_extent_acres: landExtent,
      expected_yield_kg: expectedYield,
    });

    // Clear inline error if user fixes input
    if (hasAttemptedSubmit) {
      const validation = validateHarvestDate(newDate);
      setDateError(validation.error);
    }
  };

  // Handle land extent input change
  const handleLandExtentChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    clearAnalysisSnapshot();
    setLandExtent(val);
    setIsStep2Saved(false);

    // Safely sync to session storage ONLY if full Step 2 remains valid
    saveValidatedStep2ToStorage({
      harvest_date: harvestDate,
      land_extent_acres: val,
      expected_yield_kg: expectedYield,
    });

    // Clear inline error if user fixes input
    if (hasAttemptedSubmit) {
      const validation = validateLandExtent(val);
      setExtentError(validation.error);
    }
  };

  // Handle expected yield input change
  const handleYieldChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    clearAnalysisSnapshot();
    setExpectedYield(val);
    setIsStep2Saved(false);

    // Safely sync to session storage ONLY if full Step 2 remains valid
    saveValidatedStep2ToStorage({
      harvest_date: harvestDate,
      land_extent_acres: landExtent,
      expected_yield_kg: val,
    });

    // Clear inline error if user fixes input
    if (hasAttemptedSubmit) {
      const validation = validateExpectedYield(val);
      setYieldError(validation.error);
    }
  };

  // Handle form submission with composite validation and first-field focus
  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    setIsSubmitting(true);
    setHasAttemptedSubmit(true);

    try {
      const validation = validateStep2({
        harvest_date: harvestDate,
        land_extent_acres: landExtent,
        expected_yield_kg: expectedYield,
      });

      setDateError(validation.errors.harvest_date);
      setExtentError(validation.errors.land_extent_acres);
      setYieldError(validation.errors.expected_yield_kg);

      if (!validation.isValid) {
        setIsStep2Saved(false);

        // Focus first invalid field
        if (validation.errors.harvest_date) {
          harvestDateInputRef.current?.focus();
        } else if (validation.errors.land_extent_acres) {
          landExtentInputRef.current?.focus();
        } else if (validation.errors.expected_yield_kg) {
          expectedYieldInputRef.current?.focus();
        }
        return;
      }

      // Valid: safely persist to session storage
      saveValidatedStep2ToStorage({
        harvest_date: harvestDate,
        land_extent_acres: landExtent,
        expected_yield_kg: expectedYield,
      });

      setIsStep2Saved(true);
      router.push("/market-profit/new-analysis/selling-market");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Find metadata for summary card
  const selectedCropMeta: FrontendCropMetadata | undefined =
    SUPPORTED_FRONTEND_CROPS.find((c) => c.crop_id === step1Data.crop_id);
  const selectedDistrictMeta: DistrictMetadata | undefined =
    SRI_LANKA_DISTRICTS.find((d) => d.id === step1Data.cultivation_district_id);
  const cropImage = step1Data.crop_id ? CROP_IMAGE_MAP[step1Data.crop_id] : null;

  // Compute calculated yield rate if both extent and yield are positive numbers
  const parsedExtent = parseFloat(landExtent);
  const parsedYield = parseFloat(expectedYield);
  const hasValidYieldRate =
    !isNaN(parsedExtent) &&
    parsedExtent > 0 &&
    !isNaN(parsedYield) &&
    parsedYield > 0;
  const calculatedYieldPerAcre = hasValidYieldRate
    ? Math.round(parsedYield / parsedExtent)
    : null;

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

  // If Step 1 is invalid, show friendly redirect notice
  if (isStep1Valid === false) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-4">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-700 shadow-2xs">
          <AlertCircle className="h-7 w-7" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Step 1 Information Missing
        </h2>
        <p className="text-sm text-slate-600 max-w-md mx-auto leading-relaxed">
          Please select your crop and cultivation district first. Redirecting you to Step 1...
        </p>
        <div className="pt-2">
          <Link
            href="/market-profit/new-analysis"
            className="inline-flex items-center gap-2 text-sm font-semibold text-[#15803d] hover:text-[#166534] hover:underline"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Go to Step 1: Crop &amp; District</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-16">
      {/* Top Navigation & Breadcrumb */}
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/market-profit/new-analysis"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs sm:text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs group"
        >
          <ArrowLeft className="h-4 w-4 text-slate-500 group-hover:-translate-x-0.5 transition-transform" />
          <span>Back to Crop &amp; District</span>
        </Link>

        <span className="text-xs font-semibold text-[#166534] bg-[#E7F5EB] border border-[#22A06B]/30 px-3 py-1 rounded-full shadow-2xs">
          New Analysis Wizard · Step 2 of 4
        </span>
      </div>

      {/* Page Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
          Plan Your Expected Harvest
        </h1>
        <p className="text-sm sm:text-base text-slate-600 mt-1.5 leading-relaxed">
          Enter when you expect to harvest and how much you plan to produce.
        </p>
      </div>

      {/* Progress Stepper - Step 2 is Active */}
      <WizardProgress currentStep={2} />

      {/* Step 1 Selections Summary Banner */}
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
                  Selected Crop &amp; District
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
              <div className="flex items-center gap-1.5 text-xs text-slate-600">
                <MapPin className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                <span className="font-medium text-slate-700">
                  {selectedDistrictMeta?.name || "District"} District, Sri Lanka
                </span>
              </div>
            </div>
          </div>

          <Link
            href="/market-profit/new-analysis"
            className="inline-flex items-center justify-center gap-1.5 text-xs font-bold text-[#15803d] hover:text-[#166534] bg-white hover:bg-emerald-50 px-3.5 py-2 rounded-xl border border-emerald-200/90 shadow-2xs transition-colors self-start sm:self-auto shrink-0 group"
          >
            <span>Change Selection</span>
            <ChevronRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>
      </section>

      {/* Main Step 2 Form */}
      <form onSubmit={handleFormSubmit} className="space-y-6" noValidate>
        {/* Top Form Validation Alert Banner */}
        {hasAttemptedSubmit && (dateError || extentError || yieldError) && (
          <div
            role="alert"
            className="rounded-2xl border border-red-200 bg-red-50/90 p-4 sm:p-5 text-red-900 shadow-xs space-y-1.5 animate-in fade-in"
          >
            <div className="flex items-center gap-2 text-sm font-bold text-red-800">
              <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
              <span>Please correct the highlighted fields before proceeding:</span>
            </div>
            <ul className="list-disc list-inside text-xs text-red-700 space-y-0.5 pl-2">
              {dateError && <li>{dateError}</li>}
              {extentError && <li>{extentError}</li>}
              {yieldError && <li>{yieldError}</li>}
            </ul>
          </div>
        )}

        {/* The Three Farmer Inputs as Clean, Distinctive Cards */}
        <div className="space-y-6">
          {/* Card 1: Expected Harvest Date */}
          <section className="rounded-2xl sm:rounded-3xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs hover:border-slate-300 transition-all space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-[#E7F5EB] text-[#15803d] flex items-center justify-center shrink-0 border border-[#22A06B]/20">
                  <Calendar className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-[#15803d]">
                      Field 1 of 3
                    </span>
                    <span className="text-xs text-slate-400 font-medium">· Timeline</span>
                  </div>
                  <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight mt-0.5">
                    Expected Harvest Date
                  </h2>
                </div>
              </div>
              {harvestDate && !dateError && (
                <div className="hidden sm:inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-emerald-50 text-[#166534] border border-emerald-200 shadow-2xs">
                  <CheckCircle2 className="h-3.5 w-3.5 text-[#15803d]" />
                  <span>{formatDateDisplay(harvestDate)}</span>
                </div>
              )}
            </div>

            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed max-w-2xl">
              Select the calendar date you expect to complete your harvest. This identifies the monthly wholesale demand cycles and seasonal price forecast period.
            </p>

            <div className="max-w-md space-y-2 pt-1">
              <label
                htmlFor="harvest_date"
                className="block text-xs font-bold uppercase tracking-wider text-slate-700"
              >
                Expected Harvest Date <span className="text-red-500">*</span>
              </label>

              <div className="relative">
                <input
                  ref={harvestDateInputRef}
                  type="date"
                  id="harvest_date"
                  name="harvest_date"
                  min={todayString}
                  value={harvestDate}
                  onChange={handleDateChange}
                  aria-describedby="harvest_date_help harvest_date_error"
                  className={`w-full rounded-xl border px-4 py-3 text-sm font-medium text-slate-900 shadow-2xs transition-colors focus:outline-hidden ${
                    dateError
                      ? "border-red-400 focus:border-red-500 focus:ring-4 focus:ring-red-400/20 bg-red-50/20"
                      : "border-slate-300 focus:border-[#15803d] focus:ring-4 focus:ring-emerald-500/15 bg-white"
                  }`}
                />
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500 pt-0.5">
                <span id="harvest_date_help">
                  Today or any future calendar date is accepted.
                </span>
                {harvestDate && !dateError && (
                  <span className="sm:hidden font-semibold text-[#15803d]">
                    {formatDateDisplay(harvestDate)}
                  </span>
                )}
              </div>

              {dateError && (
                <p
                  id="harvest_date_error"
                  role="alert"
                  className="text-xs font-semibold text-red-600 flex items-center gap-1.5 pt-1"
                >
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{dateError}</span>
                </p>
              )}
            </div>
          </section>

          {/* Card 2: Cultivation Land Extent */}
          <section className="rounded-2xl sm:rounded-3xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs hover:border-slate-300 transition-all space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-[#E7F5EB] text-[#15803d] flex items-center justify-center shrink-0 border border-[#22A06B]/20">
                  <Compass className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-[#15803d]">
                      Field 2 of 3
                    </span>
                    <span className="text-xs text-slate-400 font-medium">· Farm Area</span>
                  </div>
                  <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight mt-0.5">
                    Cultivation Land Extent (Acres)
                  </h2>
                </div>
              </div>
              {landExtent && !extentError && (
                <div className="hidden sm:inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-emerald-50 text-[#166534] border border-emerald-200 shadow-2xs">
                  <CheckCircle2 className="h-3.5 w-3.5 text-[#15803d]" />
                  <span>{landExtent} Acres</span>
                </div>
              )}
            </div>

            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed max-w-2xl">
              Enter the total land area dedicated to this crop cultivation in acres. Decimal values are fully supported.
            </p>

            <div className="max-w-md space-y-2 pt-1">
              <label
                htmlFor="land_extent"
                className="block text-xs font-bold uppercase tracking-wider text-slate-700"
              >
                Cultivation Land Extent <span className="text-red-500">*</span>
              </label>

              <div className="relative">
                <input
                  ref={landExtentInputRef}
                  type="number"
                  id="land_extent"
                  name="land_extent"
                  step="any"
                  min="0.01"
                  max="1000"
                  placeholder="e.g. 1.5"
                  value={landExtent}
                  onChange={handleLandExtentChange}
                  aria-describedby="land_extent_help land_extent_error"
                  className={`w-full rounded-xl border pl-4 pr-24 py-3 text-sm font-semibold text-slate-900 shadow-2xs transition-colors focus:outline-hidden ${
                    extentError
                      ? "border-red-400 focus:border-red-500 focus:ring-4 focus:ring-red-400/20 bg-red-50/20"
                      : "border-slate-300 focus:border-[#15803d] focus:ring-4 focus:ring-emerald-500/15 bg-white"
                  }`}
                />
                <div className="absolute inset-y-0 right-0 flex items-center pr-3.5 pointer-events-none text-xs font-bold text-slate-600 bg-slate-100 border-l border-slate-300 px-3.5 rounded-r-xl">
                  Acres
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500 pt-0.5">
                <span id="land_extent_help">
                  Allowed range: 0.01 to 1,000 Acres.
                </span>
                {landExtent && !extentError && (
                  <span className="sm:hidden font-semibold text-[#15803d]">
                    {landExtent} Acres
                  </span>
                )}
              </div>

              {extentError && (
                <p
                  id="land_extent_error"
                  role="alert"
                  className="text-xs font-semibold text-red-600 flex items-center gap-1.5 pt-1"
                >
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{extentError}</span>
                </p>
              )}
            </div>
          </section>

          {/* Card 3: Expected Harvest Yield */}
          <section className="rounded-2xl sm:rounded-3xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs hover:border-slate-300 transition-all space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-[#E7F5EB] text-[#15803d] flex items-center justify-center shrink-0 border border-[#22A06B]/20">
                  <Scale className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-[#15803d]">
                      Field 3 of 3
                    </span>
                    <span className="text-xs text-slate-400 font-medium">· Expected Production</span>
                  </div>
                  <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight mt-0.5">
                    Expected Harvest Yield (kg)
                  </h2>
                </div>
              </div>
              {expectedYield && !yieldError && (
                <div className="hidden sm:inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-emerald-50 text-[#166534] border border-emerald-200 shadow-2xs">
                  <CheckCircle2 className="h-3.5 w-3.5 text-[#15803d]" />
                  <span>{formatKg(expectedYield)}</span>
                </div>
              )}
            </div>

            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed max-w-2xl">
              Enter the total marketable harvest weight you expect to produce across your cultivated area in kilograms.
            </p>

            <div className="max-w-md space-y-2 pt-1">
              <label
                htmlFor="expected_yield"
                className="block text-xs font-bold uppercase tracking-wider text-slate-700"
              >
                Expected Harvest Yield <span className="text-red-500">*</span>
              </label>

              <div className="relative">
                <input
                  ref={expectedYieldInputRef}
                  type="number"
                  id="expected_yield"
                  name="expected_yield"
                  step="any"
                  min="0.01"
                  max="1000000"
                  placeholder="e.g. 1500"
                  value={expectedYield}
                  onChange={handleYieldChange}
                  aria-describedby="expected_yield_help expected_yield_error"
                  className={`w-full rounded-xl border pl-4 pr-20 py-3 text-sm font-semibold text-slate-900 shadow-2xs transition-colors focus:outline-hidden ${
                    yieldError
                      ? "border-red-400 focus:border-red-500 focus:ring-4 focus:ring-red-400/20 bg-red-50/20"
                      : "border-slate-300 focus:border-[#15803d] focus:ring-4 focus:ring-emerald-500/15 bg-white"
                  }`}
                />
                <div className="absolute inset-y-0 right-0 flex items-center pr-3.5 pointer-events-none text-xs font-bold text-slate-600 bg-slate-100 border-l border-slate-300 px-3.5 rounded-r-xl">
                  kg
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500 pt-0.5">
                <span id="expected_yield_help">
                  Allowed range: 0.01 to 1,000,000 kg.
                </span>
                {expectedYield && !yieldError && (
                  <span className="sm:hidden font-semibold text-[#15803d]">
                    {formatKg(expectedYield)}
                  </span>
                )}
              </div>

              {yieldError && (
                <p
                  id="expected_yield_error"
                  role="alert"
                  className="text-xs font-semibold text-red-600 flex items-center gap-1.5 pt-1"
                >
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{yieldError}</span>
                </p>
              )}
            </div>
          </section>

          {/* Dynamic Harvest Intensity Callout (Calculated helper insight) */}
          {hasValidYieldRate && calculatedYieldPerAcre !== null && (
            <div className="rounded-2xl sm:rounded-3xl border border-emerald-200/90 bg-[#E7F5EB]/60 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs animate-in fade-in">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-white border border-[#22A06B]/30 flex items-center justify-center text-[#15803d] shadow-2xs shrink-0">
                  <Sprout className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold text-[#166534] uppercase tracking-wider block">
                    Expected Yield per Acre
                  </span>
                  <span className="text-sm font-semibold text-slate-800">
                    Expected Yield per Acre:{" "}
                    <span className="font-extrabold text-[#15803d]">
                      ~{calculatedYieldPerAcre.toLocaleString("en-LK")} kg / acre
                    </span>
                  </span>
                </div>
              </div>
              <div className="text-left sm:text-right pl-13 sm:pl-0">
                <span className="text-[11px] text-slate-500 block">
                  Derived from your entered land extent and expected yield
                </span>
                <span className="text-xs font-medium text-emerald-800">
                  {formatKg(expectedYield)} total across {landExtent} {parsedExtent === 1 ? "acre" : "acres"}
                </span>
              </div>
            </div>
          )}

          {/* Contextual Guidance Box */}
          <div className="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-emerald-700 shrink-0 mt-0.5" />
              <div className="space-y-1 text-xs text-slate-600 leading-relaxed">
                <span className="font-bold text-slate-800 block text-sm">
                  How your harvest details are used
                </span>
                <p>
                  <strong className="text-slate-700">Expected Harvest Date:</strong> Aligns with seasonal wholesale price forecasts and terminal market demand cycles.
                </p>
                <p>
                  <strong className="text-slate-700">Land Extent &amp; Expected Yield:</strong> Determine your planned harvest volume to project cultivation costs, revenue, and profit risk.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Farmer-Friendly Step 2 Completion Summary */}
        {isStep2Saved && (
          <section className="rounded-2xl sm:rounded-3xl border-2 border-emerald-300 bg-linear-to-br from-emerald-50/90 via-emerald-50/40 to-white p-6 sm:p-7 shadow-xs space-y-5 animate-in fade-in">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-emerald-200/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-2xl bg-[#15803d] text-white flex items-center justify-center shrink-0 shadow-xs">
                  <CheckCircle2 className="h-6 w-6 stroke-[2.2]" />
                </div>
                <div>
                  <h3 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
                    Harvest Details Confirmed
                  </h3>
                  <p className="text-xs text-emerald-800 font-medium">
                    Your harvest timing and production scale are verified and stored for market analysis.
                  </p>
                </div>
              </div>
              <Link
                href="/market-profit/new-analysis/selling-market"
                className="inline-flex items-center gap-1.5 self-start sm:self-auto text-xs font-bold text-[#15803d] bg-white border border-emerald-200 px-3.5 py-2 rounded-xl hover:bg-emerald-50 shadow-2xs transition-colors cursor-pointer group"
              >
                <Store className="h-3.5 w-3.5" />
                <span>Proceed to Selling Market</span>
                <ArrowRight className="h-3.5 w-3.5 text-emerald-600 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>

            {/* Summary Parameters Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {/* 1. Crop */}
              <div className="flex items-center gap-3 p-3.5 rounded-xl bg-white border border-emerald-100 shadow-2xs">
                {cropImage && (
                  <div className="relative h-11 w-11 rounded-lg overflow-hidden shrink-0 border border-emerald-200">
                    <Image
                      src={cropImage}
                      alt={selectedCropMeta?.name_en || "Selected crop"}
                      fill
                      className="object-cover"
                    />
                  </div>
                )}
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Selected Crop
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {selectedCropMeta?.name_en || "Crop"}{" "}
                    <span className="text-xs font-normal text-slate-500">
                      ({selectedCropMeta?.name_si})
                    </span>
                  </span>
                </div>
              </div>

              {/* 2. District */}
              <div className="flex items-center gap-3 p-3.5 rounded-xl bg-white border border-emerald-100 shadow-2xs">
                <div className="h-11 w-11 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                  <MapPin className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Cultivation District
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {selectedDistrictMeta?.name || "District"}
                  </span>
                </div>
              </div>

              {/* 3. Expected Harvest Date */}
              <div className="flex items-center gap-3 p-3.5 rounded-xl bg-white border border-emerald-100 shadow-2xs">
                <div className="h-11 w-11 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                  <Calendar className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Expected Harvest Date
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {formatDateDisplay(harvestDate)}
                  </span>
                </div>
              </div>

              {/* 4. Cultivation Land Extent */}
              <div className="flex items-center gap-3 p-3.5 rounded-xl bg-white border border-emerald-100 shadow-2xs">
                <div className="h-11 w-11 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                  <Compass className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Cultivation Land Extent
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {landExtent} Acres
                  </span>
                </div>
              </div>

              {/* 5. Expected Harvest Yield */}
              <div className="flex items-center gap-3 p-3.5 rounded-xl bg-white border border-emerald-100 shadow-2xs sm:col-span-2 lg:col-span-2">
                <div className="h-11 w-11 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                  <Scale className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Expected Harvest Yield
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {formatKg(expectedYield)} ({expectedYield} kg)
                  </span>
                </div>
              </div>
            </div>

            {/* Stage Indicator */}
            <div className="rounded-xl border border-emerald-200 bg-white/80 p-3.5 text-xs text-slate-700 flex items-start gap-2.5">
              <Info className="h-4 w-4 text-[#15803d] shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                <span className="font-bold text-[#166534]">Next Stage: Step 3 — Selling Market Selection.</span>{" "}
                Select your intended wholesale terminal market (e.g. Meegoda, Embilipitiya, Colombo Manning Market) to evaluate local demand and seasonal price trends.
              </div>
            </div>
          </section>
        )}

        {/* Action Buttons Bar */}
        <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-200/80">
          <Link
            href="/market-profit/new-analysis"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors shadow-2xs group"
          >
            <ArrowLeft className="h-4 w-4 text-slate-500 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back to Crop &amp; District</span>
          </Link>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 rounded-xl bg-[#15803d] hover:bg-[#166534] active:scale-95 text-white px-8 py-3.5 text-sm font-bold shadow-sm shadow-emerald-800/20 transition-all cursor-pointer group disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span>Next: Selling Market</span>
            <ArrowRight className="h-4 w-4 text-emerald-100 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </form>
    </div>
  );
}
