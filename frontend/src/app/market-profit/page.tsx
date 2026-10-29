"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import Image, { StaticImageData } from "next/image";
import {
  Sprout,
  ArrowRight,
  MapPin,
  Building,
  Calendar,
  BarChart3,
  RotateCcw,
} from "lucide-react";
import farmerBannerImg from "./assets/farmer-banner.png";
import { OverviewCard } from "./components/OverviewCard";
import { PilotDistrictsCard } from "./components/PilotDistrictsCard";
import { CropsCatalogCard } from "./components/CropsCatalogCard";
import {
  ValidatedAnalysisSnapshot,
  loadAnalysisSnapshot,
  clearAnalysisSnapshot,
} from "./lib/wizard";
import {
  SUPPORTED_FRONTEND_CROPS,
  SRI_LANKA_DISTRICTS,
  STANDARD_MARKETS,
} from "./lib/constants";
import { formatDateDisplay, formatKg, formatLKR } from "./lib/formatters";

// Statically import verified crop photographs
import okraImg from "./assets/crops/okra.jpg";
import brinjalImg from "./assets/crops/brinjal.jpg";
import pumpkinImg from "./assets/crops/pumpkin.jpg";
import maizeImg from "./assets/crops/maize.jpg";
import mungBeanImg from "./assets/crops/mung-bean.jpg";
import chilliImg from "./assets/crops/chilli.jpg";

const CROP_IMAGE_MAP: Record<string, StaticImageData> = {
  CR_OKRA: okraImg,
  CR_BRINJAL: brinjalImg,
  CR_PUMPKIN: pumpkinImg,
  CR_MAIZE: maizeImg,
  CR_MUNG_BEAN: mungBeanImg,
  CR_CHILLI: chilliImg,
};

export default function MarketProfitHomePage() {
  const [activeSnapshot, setActiveSnapshot] = useState<ValidatedAnalysisSnapshot | null>(null);

  useEffect(() => {
    try {
      const snap = loadAnalysisSnapshot();
      setActiveSnapshot(snap);
    } catch {
      setActiveSnapshot(null);
    }
  }, []);

  const handleStartFresh = () => {
    clearAnalysisSnapshot();
    setActiveSnapshot(null);
  };

  // Resolve metadata for active analysis banner if present
  const cropMeta = activeSnapshot
    ? SUPPORTED_FRONTEND_CROPS.find((c) => c.crop_id === activeSnapshot.crop_id)
    : undefined;
  const districtMeta = activeSnapshot
    ? SRI_LANKA_DISTRICTS.find((d) => d.id === activeSnapshot.cultivation_district_id)
    : undefined;
  const marketMeta = activeSnapshot
    ? STANDARD_MARKETS.find((m) => m.id === activeSnapshot.target_market_id)
    : undefined;
  const cropImage = activeSnapshot ? CROP_IMAGE_MAP[activeSnapshot.crop_id] : null;

  return (
    <div className="space-y-8 sm:space-y-10 pb-16 animate-in fade-in duration-300">
      {/* ===================================================================== */}
      {/* 1. Welcome Section (No Supported Area or location badge)               */}
      {/* ===================================================================== */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 bg-white border border-[#22A06B]/25 rounded-2xl px-5 py-4 shadow-2xs">
        <div className="flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] font-extrabold text-base shrink-0 shadow-2xs">
            JB
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-extrabold text-slate-900 tracking-tight">
              Welcome back, Janidu
            </h2>
            <p className="text-xs sm:text-sm text-[#334155] font-medium mt-0.5">
              Ready to plan your next crop? Check market demand, selling prices, and profit before planting.
            </p>
          </div>
        </div>
      </section>

      {/* ===================================================================== */}
      {/* 2. Main Farmer Banner                                                 */}
      {/* ===================================================================== */}
      <section className="relative overflow-hidden rounded-3xl min-h-[360px] sm:min-h-[420px] flex items-center shadow-md border border-[#22A06B]/25">
        <Image
          src={farmerBannerImg}
          alt="Sri Lankan farmer in cultivation field"
          fill
          priority
          sizes="(max-width: 1280px) 100vw, 1920px"
          className="object-cover object-[right_center]"
        />

        <div className="absolute inset-0 bg-gradient-to-r from-white/95 via-white/70 to-transparent sm:from-white/90 sm:via-white/40 sm:to-transparent" />

        <div className="relative z-10 p-6 sm:p-10 lg:p-12 max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/90 px-3.5 py-1 text-xs font-bold text-[#166534] border border-[#22A06B]/30 mb-3 shadow-2xs">
            <Sprout className="h-4 w-4 text-[#166534]" />
            <span>AgroDecision • Market &amp; Profit</span>
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-900 mb-3 leading-tight sm:leading-tight">
            Plan Your Harvest with Confidence
          </h1>

          <p className="text-base sm:text-lg text-slate-700 leading-relaxed mb-6 max-w-xl font-medium">
            Understand market demand, expected selling prices, and profit before you spend money on planting.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/market-profit/new-analysis"
              onClick={() => clearAnalysisSnapshot()}
              className="inline-flex items-center gap-2.5 rounded-2xl bg-[#166534] hover:bg-[#15803d] active:scale-95 text-white font-extrabold text-base px-8 py-4 shadow-md transition-all cursor-pointer min-h-[48px] group"
            >
              <Sprout className="h-5 w-5 text-emerald-200 group-hover:scale-110 transition-transform" />
              <span>Start Analysis</span>
              <ArrowRight className="h-4 w-4 text-emerald-200 group-hover:translate-x-1 transition-transform" />
            </Link>

            {activeSnapshot && (
              <Link
                href="/market-profit/results"
                className="inline-flex items-center gap-2 rounded-2xl bg-white hover:bg-[#F7F5ED] border border-[#22A06B]/40 text-[#166534] font-extrabold text-base px-6 py-4 shadow-sm transition-all cursor-pointer min-h-[48px]"
              >
                <BarChart3 className="h-5 w-5 text-[#166534]" />
                <span>View Results</span>
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* ===================================================================== */}
      {/* 3. "Your Current Analysis is Ready" (When a saved analysis exists)    */}
      {/* ===================================================================== */}
      {activeSnapshot && (
        <section className="rounded-3xl border-2 border-[#166534]/30 bg-gradient-to-br from-white via-white to-[#E7F5EB]/40 p-5 sm:p-6 shadow-xs space-y-4 animate-in fade-in duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-emerald-900/10">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#166534] text-white shadow-2xs">
                <BarChart3 className="h-4.5 w-4.5" />
              </div>
              <div>
                <h3 className="text-sm sm:text-base font-extrabold text-slate-900">
                  Your Current Analysis is Ready
                </h3>
                <p className="text-xs text-[#334155] font-medium">
                  You have a saved cultivation plan. View your results or start a new analysis anytime.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 self-start sm:self-auto">
              <Link
                href="/market-profit/results"
                className="inline-flex items-center gap-2 rounded-xl bg-[#166534] hover:bg-[#15803d] text-white px-5 py-2.5 text-xs sm:text-sm font-bold shadow-sm transition-all"
              >
                <span>View Results</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/market-profit/new-analysis"
                onClick={handleStartFresh}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 px-3.5 py-2.5 text-xs sm:text-sm font-bold transition-all"
              >
                <RotateCcw className="h-3.5 w-3.5 text-slate-500" />
                <span>Start New Analysis</span>
              </Link>
            </div>
          </div>

          {/* Quick Snapshot Details Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="flex items-center gap-3 p-3 rounded-2xl bg-white border border-[#22A06B]/25">
              {cropImage && (
                <div className="relative h-12 w-12 rounded-xl overflow-hidden shrink-0 border border-emerald-200">
                  <Image
                    src={cropImage}
                    alt={cropMeta?.name_en || activeSnapshot.crop_id}
                    fill
                    className="object-cover"
                  />
                </div>
              )}
              <div className="min-w-0">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Crop</span>
                <span className="text-xs font-bold text-slate-900 block truncate">
                  {cropMeta?.name_en || activeSnapshot.crop_id}
                </span>
                <span className="text-[11px] text-[#166534] font-medium block truncate">
                  {cropMeta?.name_si}
                </span>
              </div>
            </div>

            <div className="p-3 rounded-2xl bg-white border border-[#22A06B]/25">
              <div className="flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase">
                <MapPin className="h-3 w-3 text-[#15803d]" />
                <span>Location</span>
              </div>
              <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                {districtMeta?.name || activeSnapshot.cultivation_district_id}
              </span>
              <span className="text-[11px] text-slate-500 block truncate">
                {marketMeta?.short_name || marketMeta?.name || activeSnapshot.target_market_id}
              </span>
            </div>

            <div className="p-3 rounded-2xl bg-white border border-[#22A06B]/25">
              <div className="flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase">
                <Calendar className="h-3 w-3 text-[#15803d]" />
                <span>Harvest Date</span>
              </div>
              <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                {formatDateDisplay(activeSnapshot.harvest_date)}
              </span>
              <span className="text-[11px] text-slate-500 block truncate">
                Yield: {formatKg(activeSnapshot.expected_yield_kg)}
              </span>
            </div>

            <div className="p-3 rounded-2xl bg-white border border-[#22A06B]/25">
              <div className="flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase">
                <Building className="h-3 w-3 text-[#15803d]" />
                <span>Farming Cost</span>
              </div>
              <span className="text-xs font-bold text-slate-900 block truncate mt-0.5">
                {formatLKR(activeSnapshot.total_cultivation_cost)}
              </span>
              <span className="text-[11px] text-slate-500 block truncate capitalize">
                {activeSnapshot.metadata.budget_mode} mode
              </span>
            </div>
          </div>
        </section>
      )}

      {/* ===================================================================== */}
      {/* 4. Supported Crops Section with Photographs                           */}
      {/* ===================================================================== */}
      <section id="supported-crops">
        <CropsCatalogCard />
      </section>

      {/* ===================================================================== */}
      {/* 5. Other Useful Existing Content: Three Essential Checks              */}
      {/* ===================================================================== */}
      <section className="space-y-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Three Essential Checks Before Planting
          </h2>
          <p className="text-sm text-[#334155] mt-1">
            Simple decision support designed for every farmer.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <OverviewCard
            id="demand"
            title="Market Demand"
            description="Check buyer demand before harvest to help avoid selling during oversupplied weeks."
          />

          <OverviewCard
            id="price"
            title="Price Forecast"
            description="See expected wholesale and retail prices at your destination economic centre."
          />

          <OverviewCard
            id="risk"
            title="Profit & Risk"
            description="Estimate your farming income, total costs, net profit, and financial risk."
          />
        </div>
      </section>

      {/* ===================================================================== */}
      {/* 6. Supported Districts Section                                        */}
      {/* ===================================================================== */}
      <section>
        <PilotDistrictsCard />
      </section>

      {/* ===================================================================== */}
      {/* 7. Quick Summary Bar                                                  */}
      {/* ===================================================================== */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-gradient-to-br from-white via-white to-[#F7F5ED]/80 border border-[#22A06B]/25 shadow-2xs flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] shrink-0">
            <Sprout className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm sm:text-base font-extrabold text-slate-900">
              {SUPPORTED_FRONTEND_CROPS.length} Supported Crops
            </div>
            <div className="text-xs text-[#334155]">Vegetables, grains &amp; condiments</div>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-gradient-to-br from-white via-white to-[#F7F5ED]/80 border border-[#22A06B]/25 shadow-2xs flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] shrink-0">
            <MapPin className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm sm:text-base font-extrabold text-slate-900">
              2 Districts
            </div>
            <div className="text-xs text-[#334155]">Matara &amp; Hambantota</div>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-gradient-to-br from-white via-white to-[#F7F5ED]/80 border border-[#22A06B]/25 shadow-2xs flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] shrink-0">
            <Building className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm sm:text-base font-extrabold text-slate-900">
              Embilipitiya DEC
            </div>
            <div className="text-xs text-[#334155]">Dedicated trading hub</div>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-gradient-to-br from-white via-white to-[#F7F5ED]/80 border border-[#22A06B]/25 shadow-2xs flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] shrink-0">
            <Calendar className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm sm:text-base font-extrabold text-slate-900">
              1–16 Weeks
            </div>
            <div className="text-xs text-[#334155]">Weekly harvest forecasting</div>
          </div>
        </div>
      </section>
    </div>
  );
}
