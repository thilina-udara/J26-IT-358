import React from "react";
import Link from "next/link";
import Image, { StaticImageData } from "next/image";
import { Layers, ArrowRight, Sprout } from "lucide-react";
import { SUPPORTED_FRONTEND_CROPS, FrontendCropMetadata } from "../lib/constants";
import { saveStep1ToStorage, loadStep1FromStorage, clearAnalysisSnapshot } from "../lib/wizard";

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

export function CropsCatalogCard() {
  const handleSelectCrop = (cropId: string) => {
    clearAnalysisSnapshot();
    const existing = loadStep1FromStorage();
    saveStep1ToStorage({
      crop_id: cropId,
      cultivation_district_id: existing.cultivation_district_id || "",
    });
  };

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
    <div className="rounded-3xl bg-gradient-to-b from-white via-white to-[#F7F5ED]/40 p-6 sm:p-8 border border-slate-200/90 shadow-xs">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#166534]">
            <Layers className="h-4 w-4" />
            <span>Supported Crops</span>
          </div>
          <h3 className="text-2xl font-extrabold text-slate-900 tracking-tight mt-1">
            Supported Crops ({SUPPORTED_FRONTEND_CROPS.length} Varieties)
          </h3>
          <p className="text-[15px] sm:text-base text-[#334155] mt-1.5 max-w-2xl leading-relaxed">
            Select any crop below to begin planning your harvest, expected selling price, and farming budget.
          </p>
        </div>
      </div>

      {/* Crops Grid with High-Quality Photography */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {SUPPORTED_FRONTEND_CROPS.map((crop: FrontendCropMetadata) => {
          const imageAsset = CROP_IMAGE_MAP[crop.crop_id];

          return (
            <div
              key={crop.crop_id}
              className="group flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white overflow-hidden hover:border-[#22A06B] hover:shadow-lg transition-all duration-200"
            >
              <div>
                {/* Crop Photograph Container - Explicit Height for Fill Image */}
                <div className="relative h-48 sm:h-52 w-full overflow-hidden bg-slate-100">
                  {imageAsset ? (
                    <Image
                      src={imageAsset}
                      alt={crop.alt_text}
                      fill
                      sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                      className="object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center bg-slate-100 text-slate-400">
                      <Sprout className="h-10 w-10 text-emerald-600" />
                    </div>
                  )}
                  <div className="absolute top-3 right-3 z-10">
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-xs font-extrabold border shadow-xs backdrop-blur-xs ${getCategoryBadgeClass(
                        crop.category
                      )}`}
                    >
                      {crop.category}
                    </span>
                  </div>
                </div>

                {/* Content */}
                <div className="p-5">
                  <div className="flex items-baseline justify-between gap-2">
                    <h4 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight group-hover:text-[#166534] transition-colors">
                      {crop.name_en}
                    </h4>
                    <span className="text-sm sm:text-base font-bold text-[#166534] shrink-0">
                      {crop.name_si}
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm text-[#334155] mt-1.5 line-clamp-2 leading-relaxed">
                    {crop.alt_text}
                  </p>
                </div>
              </div>

              {/* "Plan with..." Action Button */}
              <div className="px-5 pb-5 pt-1">
                <Link
                  href="/market-profit/new-analysis"
                  onClick={() => handleSelectCrop(crop.crop_id)}
                  className="inline-flex items-center justify-between w-full rounded-xl bg-white hover:bg-[#166534] text-[#166534] hover:text-white border border-[#22A06B]/40 hover:border-[#166534] px-4 py-3 text-xs sm:text-sm font-bold shadow-2xs transition-all group/btn cursor-pointer min-h-[44px]"
                >
                  <span className="flex items-center gap-2">
                    <Sprout className="h-4 w-4 text-[#166534] group-hover/btn:text-white transition-colors" />
                    <span>Plan with {crop.name_en}</span>
                  </span>
                  <ArrowRight className="h-4 w-4 text-[#22A06B] group-hover/btn:text-white group-hover/btn:translate-x-1 transition-all" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
