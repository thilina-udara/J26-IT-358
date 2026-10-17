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
  Store,
  Info,
  Check,
  Building2,
  HelpCircle,
  Clock,
} from "lucide-react";

import { WizardProgress } from "../../components/WizardProgress";
import { Step4ComingSoonModal } from "../../components/Step4ComingSoonModal";
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
  validateStep1,
  loadStep1FromStorage,
  Step1FormData,
  validateStep2,
  loadStep2FromStorage,
  Step2FormData,
  validateStep3,
  isStep3Complete,
  loadStep3FromStorage,
  saveValidatedStep3ToStorage,
} from "../../lib/wizard";

// Statically import the 6 verified crop photographs for summary cards
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

export default function SellingMarketPage() {
  const router = useRouter();
  const marketSelectionSectionRef = useRef<HTMLDivElement>(null);

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

  // Step 3 state
  const [selectedMarketId, setSelectedMarketId] = useState<string>("");
  const [marketError, setMarketError] = useState<string | undefined>(undefined);
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [isStep3Saved, setIsStep3Saved] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isStep4ModalOpen, setIsStep4ModalOpen] = useState(false);

  // Validate Step 1 and Step 2 prerequisites on mount
  useEffect(() => {
    // 1. Check Step 1
    const s1 = loadStep1FromStorage();
    const v1 = validateStep1(s1);
    if (!v1.isValid) {
      setGuardStatus("invalid_step1");
      setGuardMessage("Step 1 (Crop & Location) is incomplete. Please select your crop and cultivation district first.");
      setGuardTarget("/market-profit/new-analysis");
      const timer = setTimeout(() => {
        router.replace("/market-profit/new-analysis");
      }, 2500);
      return () => clearTimeout(timer);
    }
    setStep1Data(s1);

    // 2. Check Step 2
    const s2 = loadStep2FromStorage();
    const v2 = validateStep2(s2);
    if (!v2.isValid) {
      setGuardStatus("invalid_step2");
      setGuardMessage("Step 2 (Harvest Details) is incomplete. Please provide your harvest timing, land extent, and expected yield first.");
      setGuardTarget("/market-profit/new-analysis/harvest-details");
      const timer = setTimeout(() => {
        router.replace("/market-profit/new-analysis/harvest-details");
      }, 2500);
      return () => clearTimeout(timer);
    }
    setStep2Data(s2);

    // 3. Restore Step 3 if previously selected
    const s3 = loadStep3FromStorage();
    if (s3.selling_market_id) {
      setSelectedMarketId(s3.selling_market_id);
      if (isStep3Complete(s3)) {
        setIsStep3Saved(true);
      }
    }

    setGuardStatus("ready");
  }, [router]);

  // Handle market selection
  const handleMarketSelect = (marketId: string) => {
    setSelectedMarketId(marketId);
    setMarketError(undefined);
    setIsStep3Saved(false);

    // Persist immediately if valid
    saveValidatedStep3ToStorage({ selling_market_id: marketId });
  };

  // Handle Step 3 submission
  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    setIsSubmitting(true);
    setHasAttemptedSubmit(true);

    try {
      const validation = validateStep3({ selling_market_id: selectedMarketId });

      if (!validation.isValid) {
        setMarketError(validation.errors.selling_market_id);
        setIsStep3Saved(false);
        marketSelectionSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }

      setMarketError(undefined);
      saveValidatedStep3ToStorage({ selling_market_id: selectedMarketId });
      setIsStep3Saved(true);
      setIsStep4ModalOpen(true);
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

  // Render friendly redirect notice if prerequisites are not met
  if (guardStatus === "invalid_step1" || guardStatus === "invalid_step2") {
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
        <p className="text-xs text-slate-400">Redirecting automatically...</p>
        <div>
          <Link
            href={guardTarget}
            className="inline-flex items-center gap-2 text-sm font-semibold text-[#15803d] hover:underline"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Go to previous incomplete step</span>
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

  // Recommended pilot hubs vs regional economic centres
  const recommendedMarkets = STANDARD_MARKETS.filter((m) => m.is_pilot_recommended);
  const otherMarkets = STANDARD_MARKETS.filter((m) => !m.is_pilot_recommended);

  return (
    <div className="space-y-8 pb-16">
      {/* Top Navigation & Breadcrumb */}
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/market-profit/new-analysis/harvest-details"
          className="inline-flex items-center gap-2 text-xs sm:text-sm font-semibold text-slate-600 hover:text-[#15803d] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Harvest Details</span>
        </Link>

        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-100/80 text-[#166534]">
          Step 3 of 4
        </span>
      </div>

      {/* Page Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
          Target Selling Market
        </h1>
        <p className="text-sm sm:text-base text-slate-600 mt-1.5 leading-relaxed">
          Step 3 of 4: Select the Dedicated Economic Centre (DEC) or terminal wholesale hub where you plan to market your produce.
        </p>
      </div>

      {/* Progress Stepper - Step 3 is Active */}
      <WizardProgress currentStep={3} />

      {/* Confirmed Steps 1 & 2 Summary Card */}
      <section className="rounded-2xl border border-emerald-200/90 bg-emerald-50/40 p-4 sm:p-5 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5 min-w-0">
            {cropImage && (
              <div className="relative h-14 w-14 rounded-xl overflow-hidden shrink-0 border border-emerald-300 shadow-xs bg-white">
                <Image
                  src={cropImage}
                  alt={selectedCropMeta?.name_en || "Selected crop"}
                  fill
                  className="object-cover"
                />
              </div>
            )}
            <div className="min-w-0 space-y-0.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-[#15803d] uppercase tracking-wider">
                <Sprout className="h-3.5 w-3.5" />
                <span>Confirmed Harvest Profile</span>
              </div>
              <div className="text-base font-bold text-slate-900 truncate">
                {selectedCropMeta?.name_en || "Crop"}{" "}
                <span className="text-xs font-normal text-slate-500">
                  ({selectedCropMeta?.name_si})
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-600">
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3 text-emerald-600" />
                  {selectedDistrictMeta?.name || "District"}
                  {selectedDistrictMeta?.is_pilot && (
                    <span className="text-[10px] bg-emerald-100 text-[#166534] px-1 py-0.2 rounded font-semibold ml-0.5">
                      Pilot Zone
                    </span>
                  )}
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3 text-emerald-600" />
                  {formatDateDisplay(step2Data.harvest_date)}
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Compass className="h-3 w-3 text-emerald-600" />
                  {step2Data.land_extent_acres} Acres
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Scale className="h-3 w-3 text-emerald-600" />
                  {formatKg(step2Data.expected_yield_kg)}
                </span>
              </div>
            </div>
          </div>

          <Link
            href="/market-profit/new-analysis/harvest-details"
            className="inline-flex items-center justify-center gap-1 text-xs font-bold text-[#15803d] hover:text-[#166534] hover:underline self-start sm:self-auto shrink-0 bg-white px-3 py-1.5 rounded-lg border border-emerald-200 shadow-2xs"
          >
            <span>Change Details</span>
          </Link>
        </div>
      </section>

      {/* Farmer Educational Guidance: Cultivation Location vs. Selling Market */}
      <section className="rounded-2xl border border-sky-200/90 bg-sky-50/50 p-4 sm:p-5 shadow-2xs space-y-2">
        <div className="flex items-start gap-3">
          <div className="h-8 w-8 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center shrink-0 mt-0.5">
            <HelpCircle className="h-5 w-5" />
          </div>
          <div className="text-xs sm:text-sm text-slate-700 space-y-1 leading-relaxed">
            <span className="font-bold text-slate-900 block">
              Why can your selling market differ from your cultivation district?
            </span>
            <p>
              Many commercial farmers in Sri Lanka grow crops in rural cultivation districts like{" "}
              <span className="font-semibold text-slate-800">Matara</span> or{" "}
              <span className="font-semibold text-slate-800">Hambantota</span>, but transport their harvest to major regional Dedicated Economic Centres (such as{" "}
              <span className="font-semibold text-[#166534]">Embilipitiya Dedicated Economic Centre</span> or{" "}
              <span className="font-semibold text-slate-800">Pettah Manning Market</span>) as they serve as regional wholesale collection hubs connecting local farming areas to wider commercial distribution networks.
            </p>
            <p className="text-xs text-slate-500 pt-0.5">
              Select the market where your harvest will actually be sold or auctioned.
            </p>
          </div>
        </div>
      </section>

      {/* Main Market Selection Form */}
      <form onSubmit={handleFormSubmit} className="space-y-8" noValidate>
        {/* Error Alert Banner */}
        {hasAttemptedSubmit && marketError && (
          <div
            role="alert"
            className="rounded-2xl border border-red-200 bg-red-50/80 p-4 text-red-900 shadow-2xs flex items-center gap-3 animate-in fade-in"
          >
            <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
            <div className="text-sm font-semibold">{marketError}</div>
          </div>
        )}

        {/* Market Selection Section */}
        <section
          ref={marketSelectionSectionRef}
          className="rounded-2xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs space-y-6"
        >
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#15803d]">
              <Store className="h-4 w-4" />
              <span>Step 3 — Selling Hub</span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              Select Target Selling Market <span className="text-red-500">*</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Choose ONE Dedicated Economic Centre (DEC) or commercial terminal market from the verified national catalog.
            </p>
          </div>

          {/* 1. Highlighted Pilot Hubs */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#166534]">
              <Building2 className="h-3.5 w-3.5 text-[#15803d]" />
              <span>Highlighted Pilot Study Hubs</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
              {recommendedMarkets.map((market) => {
                const isSelected = selectedMarketId === market.id;
                const isEmbilipitiya = market.id === "DEC_EMBILIPITIYA";

                return (
                  <div
                    key={market.id}
                    onClick={() => handleMarketSelect(market.id)}
                    className={`relative rounded-2xl border-2 p-4.5 cursor-pointer transition-all shadow-2xs flex flex-col justify-between gap-3 ${
                      isSelected
                        ? "border-[#15803d] bg-emerald-50/60 ring-2 ring-emerald-500/20 shadow-xs"
                        : "border-slate-200 bg-white hover:border-emerald-300 hover:bg-slate-50/60"
                    }`}
                  >
                    <div className="space-y-1.5">
                      <div className="flex items-start justify-between gap-2">
                        <span className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          isEmbilipitiya
                            ? "bg-[#15803d] text-white"
                            : "bg-emerald-100 text-[#166534]"
                        }`}>
                          {isEmbilipitiya ? "Southern Scope Pilot Hub" : "Pilot Study Hub"}
                        </span>

                        <div className={`h-5 w-5 rounded-full border flex items-center justify-center shrink-0 ${
                          isSelected
                            ? "border-[#15803d] bg-[#15803d] text-white"
                            : "border-slate-300 bg-white"
                        }`}>
                          {isSelected && <Check className="h-3.5 w-3.5 stroke-[3]" />}
                        </div>
                      </div>

                      <h3 className="text-sm font-bold text-slate-900 tracking-tight leading-snug">
                        {market.name}
                      </h3>

                      <p className="text-xs text-slate-600 leading-relaxed">
                        {market.region}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                      <span>{market.short_name}</span>
                      <span className="font-semibold text-emerald-700">
                        {isSelected ? "Selected" : "Select hub"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 2. Other Regional Economic Centres */}
          <div className="space-y-3 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-700">
              <Store className="h-3.5 w-3.5 text-slate-500" />
              <span>Other Regional Dedicated Economic Centres</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {otherMarkets.map((market) => {
                const isSelected = selectedMarketId === market.id;

                return (
                  <div
                    key={market.id}
                    onClick={() => handleMarketSelect(market.id)}
                    className={`rounded-xl border p-3.5 cursor-pointer transition-all shadow-2xs flex items-start justify-between gap-3 ${
                      isSelected
                        ? "border-[#15803d] bg-emerald-50/50 ring-1 ring-emerald-500/20"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <Store className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                        <h4 className="text-xs font-bold text-slate-900 truncate">
                          {market.name}
                        </h4>
                      </div>
                      <p className="text-[11px] text-slate-500 truncate">
                        {market.region}
                      </p>
                    </div>

                    <div className={`h-4.5 w-4.5 rounded-full border flex items-center justify-center shrink-0 mt-0.5 ${
                      isSelected
                        ? "border-[#15803d] bg-[#15803d] text-white"
                        : "border-slate-300 bg-white"
                    }`}>
                      {isSelected && <Check className="h-3 w-3 stroke-[3]" />}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Farmer-Friendly Step 3 Completion Summary */}
        {isStep3Saved && selectedMarketMeta && (
          <section className="rounded-2xl border-2 border-emerald-300 bg-linear-to-br from-emerald-50/90 via-emerald-50/50 to-white p-6 sm:p-7 shadow-xs space-y-5 animate-in fade-in">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-emerald-200/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-2xl bg-[#15803d] text-white flex items-center justify-center shrink-0 shadow-xs">
                  <CheckCircle2 className="h-6 w-6 stroke-[2.2]" />
                </div>
                <div>
                  <h3 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
                    Step 3 Complete — Selling Market Confirmed
                  </h3>
                  <p className="text-xs text-emerald-800 font-medium">
                    Your candidate crop, cultivation district, harvest timeline, and target selling hub are verified.
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setIsStep4ModalOpen(true)}
                className="inline-flex items-center gap-1.5 self-start sm:self-auto text-xs font-bold text-[#15803d] bg-white border border-emerald-200 px-3.5 py-2 rounded-lg hover:bg-emerald-50 shadow-2xs transition-colors cursor-pointer"
              >
                <Clock className="h-3.5 w-3.5" />
                <span>Next Stage Preview</span>
              </button>
            </div>

            {/* Complete 6-parameter Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {/* Crop */}
              <div className="flex items-center gap-3 p-3 rounded-xl bg-white border border-emerald-100 shadow-2xs">
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
                    Candidate Crop
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {selectedCropMeta?.name_en || "Crop"}{" "}
                    <span className="text-xs font-normal text-slate-500">
                      ({selectedCropMeta?.name_si})
                    </span>
                  </span>
                </div>
              </div>

              {/* District */}
              <div className="flex items-center gap-3 p-3 rounded-xl bg-white border border-emerald-100 shadow-2xs">
                <div className="h-11 w-11 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                  <MapPin className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Cultivation District
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {selectedDistrictMeta?.name || "District"}
                    {selectedDistrictMeta?.is_pilot && (
                      <span className="ml-1 text-[10px] bg-emerald-100 text-[#166534] px-1 py-0.2 rounded font-semibold">
                        Pilot Zone
                      </span>
                    )}
                  </span>
                </div>
              </div>

              {/* Harvest Date */}
              <div className="flex items-center gap-3 p-3 rounded-xl bg-white border border-emerald-100 shadow-2xs">
                <div className="h-11 w-11 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                  <Calendar className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Harvest Date
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {formatDateDisplay(step2Data.harvest_date)}
                  </span>
                </div>
              </div>

              {/* Land Extent */}
              <div className="flex items-center gap-3 p-3 rounded-xl bg-white border border-emerald-100 shadow-2xs">
                <div className="h-11 w-11 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                  <Compass className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Cultivation Extent
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {step2Data.land_extent_acres} Acres
                  </span>
                </div>
              </div>

              {/* Expected Yield */}
              <div className="flex items-center gap-3 p-3 rounded-xl bg-white border border-emerald-100 shadow-2xs">
                <div className="h-11 w-11 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                  <Scale className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Expected Yield
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {formatKg(step2Data.expected_yield_kg)}
                  </span>
                </div>
              </div>

              {/* Target Selling Market */}
              <div className="flex items-center gap-3 p-3 rounded-xl bg-white border border-emerald-100 shadow-2xs">
                <div className="h-11 w-11 rounded-lg bg-emerald-100 text-[#15803d] flex items-center justify-center shrink-0">
                  <Store className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Target Selling Hub
                  </span>
                  <span className="text-sm font-bold text-slate-900 truncate block">
                    {selectedMarketMeta.name}
                  </span>
                </div>
              </div>
            </div>

            {/* Next Step Guidance Notice */}
            <div className="rounded-xl border border-emerald-200 bg-white/80 p-3.5 text-xs text-slate-700 flex items-start gap-2.5">
              <Info className="h-4 w-4 text-[#15803d] shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                <span className="font-bold text-[#166534]">Next Stage: Step 4 — Cultivation Costs &amp; Financial Risk.</span>{" "}
                In the upcoming sprint task, you will enter cultivation expenditure (seed, fertilizer, labor, transport) to evaluate projected profit margins, break-even unit prices, and financial risk.
              </div>
            </div>
          </section>
        )}

        {/* Action Buttons Bar */}
        <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-200/80">
          <Link
            href="/market-profit/new-analysis/harvest-details"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs"
          >
            <ArrowLeft className="h-4 w-4 text-slate-500" />
            <span>Back to Harvest Details</span>
          </Link>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 rounded-xl bg-[#15803d] hover:bg-[#166534] active:scale-95 text-white px-8 py-3.5 text-sm font-bold shadow-sm shadow-emerald-800/20 transition-all cursor-pointer group disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span>Next: Cultivation Costs</span>
            <ArrowRight className="h-4 w-4 text-emerald-100 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </form>

      {/* Step 4 Coming Soon Modal */}
      {selectedMarketMeta && (
        <Step4ComingSoonModal
          isOpen={isStep4ModalOpen}
          onClose={() => setIsStep4ModalOpen(false)}
          cropName={selectedCropMeta?.name_en || "Selected Crop"}
          cropNameSi={selectedCropMeta?.name_si || ""}
          cropImage={cropImage}
          districtName={selectedDistrictMeta?.name || "Selected District"}
          isPilotDistrict={Boolean(selectedDistrictMeta?.is_pilot)}
          harvestDate={step2Data.harvest_date}
          landExtentAcres={step2Data.land_extent_acres}
          expectedYieldKg={step2Data.expected_yield_kg}
          marketName={selectedMarketMeta.name}
          marketRegion={selectedMarketMeta.region}
          isPilotMarket={Boolean(selectedMarketMeta.is_pilot_recommended)}
        />
      )}
    </div>
  );
}
