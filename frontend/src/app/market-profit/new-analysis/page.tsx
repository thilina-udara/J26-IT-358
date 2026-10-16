"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import Image, { StaticImageData } from "next/image";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  MapPin,
  Sprout,
  Compass,
  Check,
} from "lucide-react";

import { WizardProgress } from "../components/WizardProgress";
import { Step2ComingSoonModal } from "../components/Step2ComingSoonModal";
import {
  SUPPORTED_FRONTEND_CROPS,
  SRI_LANKA_DISTRICTS,
  FrontendCropMetadata,
  DistrictMetadata,
} from "../lib/constants";
import {
  validateStep1,
  loadStep1FromStorage,
  saveStep1ToStorage,
  Step1FormData,
} from "../lib/wizard";

// Statically import the 6 verified crop photographs
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

export default function NewAnalysisPage() {
  const [selectedCrop, setSelectedCrop] = useState<string>("");
  const [selectedDistrict, setSelectedDistrict] = useState<string>("");
  const [errors, setErrors] = useState<{ crop_id?: string; cultivation_district_id?: string }>({});
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [isSuccessModalOpen, setIsSuccessModalOpen] = useState(false);

  // Restore saved state from browser session storage on mount
  useEffect(() => {
    const saved = loadStep1FromStorage();
    if (saved.crop_id) {
      setSelectedCrop(saved.crop_id);
    }
    if (saved.cultivation_district_id) {
      setSelectedDistrict(saved.cultivation_district_id);
    }
  }, []);

  // Update session storage whenever selections change
  const handleSelectCrop = (cropId: string) => {
    setSelectedCrop(cropId);
    saveStep1ToStorage({
      crop_id: cropId,
      cultivation_district_id: selectedDistrict,
    });
    if (hasAttemptedSubmit) {
      setErrors((prev) => ({ ...prev, crop_id: undefined }));
    }
  };

  const handleSelectDistrict = (districtId: string) => {
    setSelectedDistrict(districtId);
    saveStep1ToStorage({
      crop_id: selectedCrop,
      cultivation_district_id: districtId,
    });
    if (hasAttemptedSubmit) {
      setErrors((prev) => ({ ...prev, cultivation_district_id: undefined }));
    }
  };

  const handleNextClick = (e: React.FormEvent) => {
    e.preventDefault();
    setHasAttemptedSubmit(true);

    const validation = validateStep1({
      crop_id: selectedCrop,
      cultivation_district_id: selectedDistrict,
    });

    if (!validation.isValid) {
      setErrors(validation.errors);
      return;
    }

    setErrors({});
    setIsSuccessModalOpen(true);
  };

  // Pilot districts vs other districts
  const pilotDistricts = SRI_LANKA_DISTRICTS.filter((d) => d.is_pilot);
  const otherDistricts = SRI_LANKA_DISTRICTS.filter((d) => !d.is_pilot);

  // Get active crop metadata for display
  const activeCropMeta = SUPPORTED_FRONTEND_CROPS.find((c) => c.crop_id === selectedCrop);
  const activeDistrictMeta = SRI_LANKA_DISTRICTS.find((d) => d.id === selectedDistrict);

  return (
    <div className="space-y-8 pb-16">
      {/* Top Navigation & Breadcrumb */}
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/market-profit"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs sm:text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs group"
        >
          <ArrowLeft className="h-4 w-4 text-slate-500 group-hover:-translate-x-0.5 transition-transform" />
          <span>Back to Dashboard</span>
        </Link>
        <span className="text-xs font-semibold text-[#15803d] bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full">
          New Analysis Wizard
        </span>
      </div>

      {/* Page Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
          New Crop Feasibility Analysis
        </h1>
        <p className="text-sm sm:text-base text-slate-600 mt-1.5 leading-relaxed">
          Step 1 of 4: Select the crop variety you plan to cultivate and your farm location in Sri Lanka.
        </p>
      </div>

      {/* Progress Stepper */}
      <WizardProgress currentStep={1} />

      {/* Validation Error Banner (if submission failed) */}
      {hasAttemptedSubmit && Object.keys(errors).length > 0 && (
        <div className="rounded-2xl border border-red-200 bg-red-50/80 p-4 sm:p-5 text-red-900 shadow-xs animate-shake">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
            <div className="text-sm space-y-1">
              <span className="font-bold">Please complete the required selections:</span>
              <ul className="list-disc list-inside text-xs text-red-700 pl-1 space-y-0.5">
                {errors.crop_id && <li>{errors.crop_id}</li>}
                {errors.cultivation_district_id && <li>{errors.cultivation_district_id}</li>}
              </ul>
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleNextClick} className="space-y-8">
        {/* SECTION 1: CROP SELECTION */}
        <section className="rounded-2xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs space-y-5">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#15803d]">
              <Sprout className="h-4 w-4" />
              <span>Step 1.1</span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              1. Select Candidate Crop
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Choose the single crop variety you plan to cultivate. Only one crop can be selected at a time.
            </p>
          </div>

          {errors.crop_id && (
            <p className="text-xs font-semibold text-red-600 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{errors.crop_id}</span>
            </p>
          )}

          {/* 6 Crops Radio-Card Grid */}
          <div
            role="radiogroup"
            aria-label="Candidate Crops"
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
          >
            {SUPPORTED_FRONTEND_CROPS.map((crop: FrontendCropMetadata) => {
              const isSelected = selectedCrop === crop.crop_id;
              const imageAsset = CROP_IMAGE_MAP[crop.crop_id];

              return (
                <div
                  key={crop.crop_id}
                  role="radio"
                  aria-checked={isSelected}
                  tabIndex={0}
                  onClick={() => handleSelectCrop(crop.crop_id)}
                  onKeyDown={(e) => {
                    if (e.key === " " || e.key === "Enter") {
                      e.preventDefault();
                      handleSelectCrop(crop.crop_id);
                    }
                  }}
                  className={`group relative flex flex-col rounded-2xl overflow-hidden cursor-pointer transition-all duration-200 text-left focus:outline-hidden ${
                    isSelected
                      ? "border-2 border-[#15803d] ring-4 ring-emerald-500/15 shadow-md bg-emerald-50/20"
                      : "border border-slate-200/90 hover:border-emerald-300 hover:shadow-xs bg-white"
                  }`}
                >
                  {/* Crop Photograph */}
                  <div className="relative h-40 w-full overflow-hidden bg-slate-100">
                    {imageAsset && (
                      <Image
                        src={imageAsset}
                        alt={crop.alt_text}
                        fill
                        sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                        className="object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    )}

                    {/* Category Pill */}
                    <div className="absolute top-3 left-3">
                      <span className="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-white/95 text-slate-800 border border-slate-200 shadow-2xs backdrop-blur-xs">
                        {crop.category}
                      </span>
                    </div>

                    {/* Selection Checkmark Badge */}
                    {isSelected && (
                      <div className="absolute top-3 right-3 flex items-center gap-1 bg-[#15803d] text-white px-2.5 py-0.5 rounded-full text-xs font-bold shadow-xs">
                        <Check className="h-3.5 w-3.5 stroke-[3]" />
                        <span>Selected</span>
                      </div>
                    )}
                  </div>

                  {/* Crop Body */}
                  <div className="p-4 flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-bold text-slate-900 tracking-tight">
                        {crop.name_en}
                      </h3>
                      <p className="text-xs font-medium text-[#15803d]">
                        {crop.name_si}
                      </p>
                    </div>

                    {/* Radio visual indicator */}
                    <div
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                        isSelected
                          ? "border-[#15803d] bg-[#15803d] text-white"
                          : "border-slate-300 bg-white"
                      }`}
                    >
                      {isSelected && <span className="h-2 w-2 rounded-full bg-white" />}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* SECTION 2: CULTIVATION DISTRICT */}
        <section className="rounded-2xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs space-y-5">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#15803d]">
              <MapPin className="h-4 w-4" />
              <span>Step 1.2</span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              2. Select Cultivation District
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Choose the administrative district where your cultivation land is located.
            </p>
          </div>

          {errors.cultivation_district_id && (
            <p className="text-xs font-semibold text-red-600 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{errors.cultivation_district_id}</span>
            </p>
          )}

          {/* District Dropdown Selector */}
          <div className="max-w-xl">
            <label
              htmlFor="cultivation-district"
              className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2"
            >
              Cultivation District <span className="text-red-500">*</span>
            </label>
            <select
              id="cultivation-district"
              value={selectedDistrict}
              onChange={(e) => handleSelectDistrict(e.target.value)}
              className={`w-full rounded-xl border bg-white px-4 py-3 text-sm font-medium transition-colors focus:outline-hidden focus:ring-2 ${
                errors.cultivation_district_id
                  ? "border-red-300 text-red-900 focus:ring-red-400"
                  : "border-slate-300 text-slate-900 focus:border-[#15803d] focus:ring-emerald-500/20"
              }`}
            >
              <option value="">-- Choose Cultivation District --</option>
              <optgroup label="★ Pilot Districts (Southern Province)">
                {pilotDistricts.map((d: DistrictMetadata) => (
                  <option key={d.id} value={d.id}>
                    ★ {d.name} ({d.zone}) — Pilot Focus
                  </option>
                ))}
              </optgroup>
              <optgroup label="Other Sri Lankan Districts">
                {otherDistricts.map((d: DistrictMetadata) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.zone})
                  </option>
                ))}
              </optgroup>
            </select>
          </div>

          {/* Pilot District Highlight Callout */}
          {activeDistrictMeta && (
            <div
              className={`rounded-xl p-4 text-xs border max-w-xl ${
                activeDistrictMeta.is_pilot
                  ? "bg-emerald-50 border-emerald-200 text-[#166534]"
                  : "bg-slate-50 border-slate-200 text-slate-700"
              }`}
            >
              <div className="flex items-start gap-2.5">
                <MapPin
                  className={`h-4 w-4 shrink-0 mt-0.5 ${
                    activeDistrictMeta.is_pilot ? "text-[#15803d]" : "text-slate-500"
                  }`}
                />
                <div>
                  <div className="font-bold text-sm">
                    {activeDistrictMeta.name} District{" "}
                    {activeDistrictMeta.is_pilot && (
                      <span className="ml-1.5 text-[11px] bg-[#15803d] text-white px-2 py-0.5 rounded-full font-bold">
                        Southern Pilot Zone
                      </span>
                    )}
                  </div>
                  <p className="mt-1 leading-relaxed text-slate-600">
                    Agro-ecological Zone:{" "}
                    <span className="font-semibold text-slate-800">
                      {activeDistrictMeta.zone}
                    </span>
                    {activeDistrictMeta.id === "LK-32" && (
                      <span>
                        {" "}
                        — High-rainfall coastal agriculture belt with intensive vegetable and lowland production.
                      </span>
                    )}
                    {activeDistrictMeta.id === "LK-33" && (
                      <span>
                        {" "}
                        — Commercial dry-zone farming belt connected directly to Embilipitiya Economic Centre.
                      </span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          )}

          {!activeDistrictMeta && (
            <p className="text-xs text-slate-500 max-w-xl">
              Tip: Selecting <span className="font-semibold text-[#166534]">Matara</span> or{" "}
              <span className="font-semibold text-[#166534]">Hambantota</span> accesses localized agricultural data verified under Component 1.
            </p>
          )}
        </section>

        {/* Action Buttons Bar */}
        <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-200/80">
          <Link
            href="/market-profit"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs"
          >
            <ArrowLeft className="h-4 w-4 text-slate-500" />
            <span>Back to Dashboard</span>
          </Link>

          <button
            type="submit"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 rounded-xl bg-[#15803d] hover:bg-[#166534] active:scale-95 text-white px-8 py-3.5 text-sm font-bold shadow-sm shadow-emerald-800/20 transition-all cursor-pointer group"
          >
            <span>Next: Harvest Details</span>
            <ArrowRight className="h-4 w-4 text-emerald-100 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </form>

      {/* Step 2 Coming Soon Confirmation Modal */}
      <Step2ComingSoonModal
        isOpen={isSuccessModalOpen}
        onClose={() => setIsSuccessModalOpen(false)}
        cropName={activeCropMeta?.name_en || ""}
        cropNameSi={activeCropMeta?.name_si || ""}
        districtName={activeDistrictMeta?.name || ""}
        isPilotDistrict={Boolean(activeDistrictMeta?.is_pilot)}
      />
    </div>
  );
}
