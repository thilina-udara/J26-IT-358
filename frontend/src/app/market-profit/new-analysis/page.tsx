"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Image, { StaticImageData } from "next/image";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  MapPin,
  Sprout,
  Check,
} from "lucide-react";

import { WizardProgress } from "../components/WizardProgress";
import {
  SUPPORTED_FRONTEND_CROPS,
  SRI_LANKA_DISTRICTS,
  SUPPORTED_PILOT_DISTRICTS,
  SUPPORTED_PILOT_DISTRICT_IDS,
  FrontendCropMetadata,
  DistrictMetadata,
} from "../lib/constants";
import {
  validateStep1,
  loadStep1FromStorage,
  saveStep1ToStorage,
  clearAnalysisSnapshot,
} from "../lib/wizard";

// Statically import the 5 verified crop photographs (Pumpkin removed from Component 1 active scope)
import okraImg from "../assets/crops/okra.jpg";
import brinjalImg from "../assets/crops/brinjal.jpg";
import maizeImg from "../assets/crops/maize.jpg";
import mungBeanImg from "../assets/crops/mung-bean.jpg";
import chilliImg from "../assets/crops/chilli.jpg";

const CROP_IMAGE_MAP: Record<string, StaticImageData> = {
  CR_OKRA: okraImg,
  CR_BRINJAL: brinjalImg,
  CR_MAIZE: maizeImg,
  CR_MUNG_BEAN: mungBeanImg,
  CR_CHILLI: chilliImg,
};

export default function NewAnalysisPage() {
  const router = useRouter();
  const [selectedCrop, setSelectedCrop] = useState<string>("");
  const [selectedDistrict, setSelectedDistrict] = useState<string>("");
  const [errors, setErrors] = useState<{ crop_id?: string; cultivation_district_id?: string }>({});
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);

  // Restore saved state from browser session storage on mount with legacy Pumpkin & non-pilot district rejection
  useEffect(() => {
    const saved = loadStep1FromStorage();
    if (saved.crop_id) {
      if (saved.crop_id === "CR_PUMPKIN") {
        // Safe legacy handling: reject Pumpkin, clear stale snapshot, alert the farmer
        clearAnalysisSnapshot();
        saveStep1ToStorage({
          crop_id: "",
          cultivation_district_id:
            saved.cultivation_district_id === "LK-32" || saved.cultivation_district_id === "LK-33"
              ? saved.cultivation_district_id
              : "",
        });
        setSelectedCrop("");
        setErrors((prev) => ({
          ...prev,
          crop_id:
            "Pumpkin is outside the current model training scope. Please select one of the 5 supported crops.",
        }));
      } else if (SUPPORTED_FRONTEND_CROPS.some((c) => c.crop_id === saved.crop_id)) {
        setSelectedCrop(saved.crop_id);
      }
    }
    if (saved.cultivation_district_id) {
      if (
        saved.cultivation_district_id === "LK-32" ||
        saved.cultivation_district_id === "LK-33"
      ) {
        setSelectedDistrict(saved.cultivation_district_id);
      } else {
        // Safe legacy handling: non-pilot district found in saved session.
        // Do NOT silently replace it. Keep selectedDistrict empty, clear stale snapshot, alert the farmer.
        clearAnalysisSnapshot();
        saveStep1ToStorage({
          crop_id: saved.crop_id && saved.crop_id !== "CR_PUMPKIN" ? saved.crop_id : "",
          cultivation_district_id: "",
        });
        setSelectedDistrict("");
        setErrors((prev) => ({
          ...prev,
          cultivation_district_id:
            "Component 1 analysis is currently piloted in Matara (LK-32) and Hambantota (LK-33). Please select Matara or Hambantota to proceed.",
        }));
      }
    }
  }, []);

  // Update session storage whenever crop selection changes
  const handleSelectCrop = (cropId: string) => {
    if (cropId !== selectedCrop) {
      clearAnalysisSnapshot();
    }
    setSelectedCrop(cropId);
    saveStep1ToStorage({
      crop_id: cropId,
      cultivation_district_id: selectedDistrict,
    });
    setErrors((prev) => ({ ...prev, crop_id: undefined }));
  };

  // Update session storage whenever district selection changes
  const handleSelectDistrict = (districtId: string) => {
    if (districtId !== selectedDistrict) {
      clearAnalysisSnapshot();
    }
    setSelectedDistrict(districtId);
    saveStep1ToStorage({
      crop_id: selectedCrop,
      cultivation_district_id: districtId,
    });
    setErrors((prev) => ({ ...prev, cultivation_district_id: undefined }));
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
    saveStep1ToStorage({
      crop_id: selectedCrop,
      cultivation_district_id: selectedDistrict,
    });
    router.push("/market-profit/new-analysis/harvest-details");
  };

  // Active district metadata (Matara or Hambantota)
  const activeDistrictMeta = SUPPORTED_PILOT_DISTRICTS.find((d) => d.id === selectedDistrict);
  const activeCropMeta = SUPPORTED_FRONTEND_CROPS.find((c) => c.crop_id === selectedCrop);

  const isFormComplete = Boolean(
    selectedCrop && (selectedDistrict === "LK-32" || selectedDistrict === "LK-33")
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
        <span className="text-xs font-semibold text-[#166534] bg-[#E7F5EB] border border-[#22A06B]/30 px-3 py-1 rounded-full shadow-2xs">
          New Analysis Wizard · Step 1 of 4
        </span>
      </div>

      {/* Page Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
          Choose Your Crop &amp; District
        </h1>
        <p className="text-sm sm:text-base text-slate-600 mt-1.5 leading-relaxed">
          Select what you plan to grow and where you will cultivate it.
        </p>
      </div>

      {/* Progress Stepper */}
      <WizardProgress currentStep={1} />

      {/* Legacy Pumpkin Warning Banner */}
      {errors.crop_id && errors.crop_id.includes("Pumpkin") && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50/90 p-4 sm:p-5 text-amber-950 shadow-xs">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="text-sm space-y-1">
              <span className="font-bold">Catalog Notice:</span>
              <p className="text-xs text-amber-900 leading-relaxed">
                {errors.crop_id}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Non-Pilot District Warning Banner */}
      {errors.cultivation_district_id && errors.cultivation_district_id.includes("piloted in Matara") && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50/90 p-4 sm:p-5 text-amber-950 shadow-xs">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="text-sm space-y-1">
              <span className="font-bold">District Selection Notice:</span>
              <p className="text-xs text-amber-900 leading-relaxed">
                {errors.cultivation_district_id}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Standard Form Submission Error Banner */}
      {hasAttemptedSubmit &&
        Object.keys(errors).length > 0 &&
        !errors.crop_id?.includes("Pumpkin") &&
        !errors.cultivation_district_id?.includes("piloted in Matara") && (
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
        <section className="rounded-3xl bg-gradient-to-b from-white via-white to-[#F7F5ED]/40 p-6 sm:p-8 border border-slate-200/90 shadow-xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#166534]">
                <Sprout className="h-4 w-4" />
                <span>Step 1.1 · Candidate Crop</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight mt-1">
                Select Your Crop ({SUPPORTED_FRONTEND_CROPS.length} Supported Varieties)
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 mt-1">
                Choose the crop variety you plan to cultivate. High-accuracy demand and price models are calibrated for these 5 crops.
              </p>
            </div>
            {selectedCrop && activeCropMeta && (
              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 w-fit self-start sm:self-auto shadow-2xs">
                <CheckCircle2 className="h-3.5 w-3.5 text-[#22A06B]" />
                <span>Selected: {activeCropMeta.name_en}</span>
              </div>
            )}
          </div>

          {errors.crop_id && !errors.crop_id.includes("Pumpkin") && (
            <p className="text-xs font-semibold text-red-600 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errors.crop_id}</span>
            </p>
          )}

          {/* 5 Crops Grid with Real Photographs & Consistent Aspect Ratios */}
          <div
            role="radiogroup"
            aria-label="Candidate Crops"
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4"
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
                  className={`group relative flex flex-col justify-between rounded-2xl overflow-hidden cursor-pointer transition-all duration-200 text-left focus:outline-hidden ${
                    isSelected
                      ? "border-2 border-[#166534] ring-4 ring-emerald-500/15 shadow-md bg-emerald-50/25"
                      : "border border-slate-200/90 hover:border-[#22A06B] hover:shadow-md bg-white"
                  }`}
                >
                  <div>
                    {/* Crop Photograph Container */}
                    <div className="relative aspect-[16/10] w-full overflow-hidden bg-slate-100">
                      {imageAsset && (
                        <Image
                          src={imageAsset}
                          alt={crop.alt_text}
                          fill
                          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, (max-width: 1280px) 33vw, 20vw"
                          className="object-cover group-hover:scale-105 transition-transform duration-300"
                          priority={crop.crop_id === "CR_OKRA" || crop.crop_id === "CR_BRINJAL"}
                        />
                      )}

                      {/* Category Badge */}
                      <div className="absolute top-2.5 left-2.5 z-10">
                        <span
                          className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-extrabold border shadow-2xs backdrop-blur-xs ${getCategoryBadgeClass(
                            crop.category
                          )}`}
                        >
                          {crop.category}
                        </span>
                      </div>

                      {/* Selected Checkmark Badge */}
                      {isSelected && (
                        <div className="absolute top-2.5 right-2.5 z-10 flex items-center gap-1 bg-[#166534] text-white px-2 py-0.5 rounded-full text-[11px] font-bold shadow-xs">
                          <Check className="h-3 w-3 stroke-[3]" />
                          <span>Selected</span>
                        </div>
                      )}
                    </div>

                    {/* Crop Metadata Body */}
                    <div className="p-4">
                      <h3 className="text-base font-extrabold text-slate-900 tracking-tight group-hover:text-[#166534] transition-colors">
                        {crop.name_en}
                      </h3>
                      <p className="text-xs font-semibold text-[#166534] mt-0.5">
                        {crop.name_si}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-2 line-clamp-2 leading-relaxed">
                        {crop.alt_text}
                      </p>
                    </div>
                  </div>

                  {/* Bottom selection pill / radio footer */}
                  <div className="px-4 pb-3.5 pt-1 flex items-center justify-between border-t border-slate-100">
                    <span className="text-[11px] font-medium text-slate-500">
                      {isSelected ? "Active Choice" : "Click to Select"}
                    </span>
                    <div
                      className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-colors ${
                        isSelected
                          ? "border-[#166534] bg-[#166534] text-white"
                          : "border-slate-300 bg-white group-hover:border-slate-400"
                      }`}
                    >
                      {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* SECTION 2: CULTIVATION DISTRICT SELECTION */}
        <section className="rounded-3xl bg-gradient-to-b from-white via-white to-[#F7F5ED]/40 p-6 sm:p-8 border border-slate-200/90 shadow-xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#166534]">
                <MapPin className="h-4 w-4" />
                <span>Step 1.2 · Cultivation Location</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight mt-1">
                Select Your Cultivation District
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 mt-1">
                Choose where you plan to grow your crop.
              </p>
            </div>
            {selectedDistrict && activeDistrictMeta && (
              <div className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 w-fit self-start sm:self-auto shadow-2xs">
                <CheckCircle2 className="h-3.5 w-3.5 text-[#22A06B]" />
                <span>Selected: {activeDistrictMeta.name}</span>
              </div>
            )}
          </div>

          {errors.cultivation_district_id && !errors.cultivation_district_id.includes("piloted in Matara") && (
            <p className="text-xs font-semibold text-red-600 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errors.cultivation_district_id}</span>
            </p>
          )}

          {/* Two Simplified District Selection Cards: Matara & Hambantota */}
          <div
            role="radiogroup"
            aria-label="Cultivation District"
            className="grid grid-cols-1 sm:grid-cols-2 gap-5"
          >
            {SUPPORTED_PILOT_DISTRICTS.map((d: DistrictMetadata) => {
              const isSelected = selectedDistrict === d.id;

              return (
                <div
                  key={d.id}
                  role="radio"
                  aria-checked={isSelected}
                  tabIndex={0}
                  onClick={() => handleSelectDistrict(d.id)}
                  onKeyDown={(e) => {
                    if (e.key === " " || e.key === "Enter") {
                      e.preventDefault();
                      handleSelectDistrict(d.id);
                    }
                  }}
                  className={`group relative flex items-center justify-between p-6 rounded-2xl border-2 cursor-pointer transition-all duration-200 text-left focus:outline-hidden min-h-[96px] ${
                    isSelected
                      ? "border-[#166534] bg-emerald-50/40 ring-4 ring-emerald-500/15 shadow-sm"
                      : "border-slate-200/90 bg-white hover:border-[#22A06B] hover:shadow-xs"
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <div
                      className={`p-3 rounded-2xl transition-colors shrink-0 ${
                        isSelected
                          ? "bg-[#166534] text-white shadow-xs"
                          : "bg-emerald-50 text-[#166534] group-hover:bg-[#E7F5EB]"
                      }`}
                    >
                      <MapPin className="h-6 w-6" />
                    </div>
                    <div>
                      <h3 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight group-hover:text-[#166534] transition-colors">
                        {d.name}
                      </h3>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {isSelected ? (
                      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#166534] text-white text-xs font-bold shadow-2xs">
                        <Check className="h-3.5 w-3.5 stroke-[3]" />
                        <span>Selected</span>
                      </div>
                    ) : (
                      <div className="flex h-5 w-5 rounded-full border-2 border-slate-300 bg-white group-hover:border-[#22A06B] transition-colors" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Action Buttons Bar */}
        <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-200/80">
          <Link
            href="/market-profit"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs"
          >
            <ArrowLeft className="h-4 w-4 text-slate-500" />
            <span>Back to Dashboard</span>
          </Link>

          <button
            type="submit"
            disabled={!isFormComplete}
            className={`w-full sm:w-auto inline-flex items-center justify-center gap-2.5 rounded-xl px-8 py-3.5 text-sm font-bold shadow-sm transition-all ${
              isFormComplete
                ? "bg-[#15803d] hover:bg-[#166534] active:scale-95 text-white shadow-emerald-800/20 cursor-pointer group"
                : "bg-slate-200 text-slate-400 cursor-not-allowed shadow-none"
            }`}
          >
            <span>Next: Harvest Details</span>
            <ArrowRight
              className={`h-4 w-4 transition-transform ${
                isFormComplete ? "text-emerald-100 group-hover:translate-x-1" : "text-slate-400"
              }`}
            />
          </button>
        </div>
      </form>
    </div>
  );
}
