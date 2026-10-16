import React from "react";
import Image, { StaticImageData } from "next/image";
import { Layers, CheckCircle2 } from "lucide-react";
import { SUPPORTED_FRONTEND_CROPS, FrontendCropMetadata } from "../lib/constants";

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

export function CropsCatalogCard() {
  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case "Vegetable":
        return "bg-emerald-50 text-emerald-800 border-emerald-200/90";
      case "Grain":
        return "bg-amber-50 text-amber-800 border-amber-200/90";
      case "Condiment":
        return "bg-rose-50 text-rose-800 border-rose-200/90";
      case "Legume":
        return "bg-teal-50 text-teal-800 border-teal-200/90";
      default:
        return "bg-slate-50 text-slate-800 border-slate-200/90";
    }
  };

  return (
    <div className="rounded-2xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#15803d]">
            <Layers className="h-4 w-4" />
            <span>Crop Catalog</span>
          </div>
          <h3 className="text-xl font-bold text-slate-900 tracking-tight mt-0.5">
            Supported Crops ({SUPPORTED_FRONTEND_CROPS.length} Varieties)
          </h3>
          <p className="text-sm text-slate-600 mt-1">
            These crops are currently enabled for regional demand tracking, price forecasting, and profit risk analysis.
          </p>
        </div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-[#166534] border border-emerald-200 w-fit">
          <CheckCircle2 className="h-3.5 w-3.5 text-[#15803d]" />
          <span>6 Active Crops</span>
        </div>
      </div>

      {/* 6 Crops Grid with Realistic Photography */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {SUPPORTED_FRONTEND_CROPS.map((crop: FrontendCropMetadata) => {
          const imageAsset = CROP_IMAGE_MAP[crop.crop_id];

          return (
            <div
              key={crop.crop_id}
              className="group flex flex-col rounded-2xl border border-slate-200/90 bg-white overflow-hidden hover:border-emerald-300 hover:shadow-md transition-all duration-200"
            >
              {/* Crop Photograph Container */}
              <div className="relative h-44 w-full overflow-hidden bg-slate-100">
                {imageAsset && (
                  <Image
                    src={imageAsset}
                    alt={crop.alt_text}
                    fill
                    sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                    className="object-cover group-hover:scale-105 transition-transform duration-300"
                    priority={crop.crop_id === "CR_OKRA" || crop.crop_id === "CR_BRINJAL"}
                  />
                )}
                <div className="absolute top-3 right-3">
                  <span
                    className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold border shadow-xs backdrop-blur-xs ${getCategoryBadgeClass(
                      crop.category
                    )}`}
                  >
                    {crop.category}
                  </span>
                </div>
              </div>

              {/* Crop Details Body */}
              <div className="p-4.5 flex-1 flex flex-col justify-between">
                <div>
                  <h4 className="text-base font-bold text-slate-900 tracking-tight">
                    {crop.name_en}
                  </h4>
                  <p className="text-xs font-medium text-[#15803d] mt-0.5">
                    {crop.name_si}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
