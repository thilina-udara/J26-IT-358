"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Sprout,
  ArrowRight,
  Sparkles,
  MapPin,
  Building,
  ShieldCheck,
} from "lucide-react";
import farmerBannerImg from "./assets/farmer-banner.png";
import { OverviewCard } from "./components/OverviewCard";
import { PilotDistrictsCard } from "./components/PilotDistrictsCard";
import { CropsCatalogCard } from "./components/CropsCatalogCard";
import { clearAnalysisSnapshot } from "./lib/wizard";

export default function MarketProfitHomePage() {
  return (
    <div className="space-y-8 sm:space-y-10 pb-16 animate-in fade-in duration-300">
      {/* ===================================================================== */}
      {/* 1. Logged-In Farmer Welcome & Workspace Header Bar                   */}
      {/* ===================================================================== */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 bg-white border border-[#22A06B]/25 rounded-2xl px-5 py-3.5 shadow-2xs">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] font-extrabold text-sm shrink-0">
            JB
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm sm:text-base font-extrabold text-slate-900">
                Welcome back, Janidu
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100/70 px-2 py-0.5 text-[11px] font-bold text-[#166534] border border-emerald-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse" />
                Southern Pilot Workspace
              </span>
            </div>
            <p className="text-xs text-[#334155] font-medium">
              Ready for your next crop analysis? Let&apos;s plan your next harvest wisely.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-semibold text-[#166534] self-start sm:self-auto">
          <span className="text-slate-400 font-normal">Active Pilot Zone:</span>
          <span className="rounded-xl bg-[#E7F5EB] px-3 py-1 border border-[#22A06B]/25 font-bold">
            Matara &amp; Hambantota (Embilipitiya DEC)
          </span>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* 2. Agricultural Hero Banner with Farmer & Analytics Visuals           */}
      {/* ===================================================================== */}
      <section className="relative overflow-hidden rounded-3xl min-h-[380px] sm:min-h-[440px] flex items-center shadow-lg border border-[#22A06B]/25">
        {/* Supplied Farmer Banner (Farmer visible on right, brighter on left) */}
        <Image
          src={farmerBannerImg}
          alt="Sri Lankan farmer in cultivation field with agricultural analytics"
          fill
          priority
          sizes="(max-width: 1280px) 100vw, 1920px"
          className="object-cover object-[right_center]"
        />

        {/* Subtle Legibility Gradient Overlay (Preserving bright left side, no excessive dark overlays) */}
        <div className="absolute inset-0 bg-gradient-to-r from-white/90 via-white/60 to-transparent sm:from-white/85 sm:via-white/35 sm:to-transparent" />

        {/* Hero Content Left */}
        <div className="relative z-10 p-6 sm:p-10 lg:p-12 max-w-2xl">
          {/* Eyebrow Pill */}
          <div className="inline-flex items-center gap-2 rounded-full bg-white/85 backdrop-blur-xs px-3.5 py-1 text-xs font-bold text-[#166534] border border-[#22A06B]/30 mb-4 shadow-2xs">
            <Sprout className="h-4 w-4 text-[#166534]" />
            <span className="tracking-wide">AgroDecision • Market &amp; Profit Analysis</span>
          </div>

          {/* Main Heading */}
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-900 mb-3.5 leading-tight sm:leading-tight">
            Plan Your Harvest with Confidence
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-slate-700 leading-relaxed mb-6 max-w-xl font-medium">
            Understand future market demand, expected selling prices and profit risks before you plant.
          </p>

          {/* Action Button & Pre-Planting Checks */}
          <div className="space-y-4">
            <div>
              <Link
                href="/market-profit/new-analysis"
                onClick={() => clearAnalysisSnapshot()}
                className="inline-flex items-center gap-3 rounded-2xl bg-[#166534] hover:bg-[#15803d] active:scale-95 text-white font-extrabold text-base px-8 py-4 shadow-lg hover:shadow-xl transition-all cursor-pointer min-h-[48px] group"
              >
                <Sprout className="h-5 w-5 text-emerald-200 group-hover:scale-110 transition-transform" />
                <span>Start New Analysis</span>
                <ArrowRight className="h-4 w-4 text-emerald-200 group-hover:translate-x-1.5 transition-transform" />
              </Link>
            </div>

            {/* Pre-Planting Checks Indicator Chips (Positioned on left to leave farmer visuals open) */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/85 backdrop-blur-xs border border-[#22A06B]/25 px-3 py-1 text-xs font-bold text-slate-800 shadow-2xs">
                <span className="h-2 w-2 rounded-full bg-emerald-600" />
                Buyer Market Demand
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/85 backdrop-blur-xs border border-[#22A06B]/25 px-3 py-1 text-xs font-bold text-slate-800 shadow-2xs">
                <span className="h-2 w-2 rounded-full bg-emerald-600" />
                DEC Price Trends
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/85 backdrop-blur-xs border border-[#22A06B]/25 px-3 py-1 text-xs font-bold text-slate-800 shadow-2xs">
                <span className="h-2 w-2 rounded-full bg-emerald-600" />
                Profit &amp; Risk Safety
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ===================================================================== */}
      {/* 2. Three Compact Feature Highlights                                  */}
      {/* ===================================================================== */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1 pb-1">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-[#166534]">
              Decision Support Tools
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mt-0.5">
              Three Essential Checks Before Planting
            </h2>
          </div>
          <p className="text-sm text-[#334155] font-normal">
            Transparent insights designed for smallholder and commercial farmers
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* Feature 1: Market Demand */}
          <OverviewCard
            id="demand"
            title="Market Demand"
            subtitle="Buyer Demand Tracking"
            description="Evaluate regional wholesale buyer demand before harvest to avoid crop gluts and selling during oversupplied weeks."
            badgeText="In Development"
            badgeType="pending"
            points={[
              "Anticipates seasonal buyer demand patterns across pilot zones",
              "Helps avoid harvesting during heavy regional market gluts",
            ]}
            notice="Upcoming: Machine learning demand level indicators will activate when models are connected."
          />

          {/* Feature 2: Price Forecast */}
          <OverviewCard
            id="price"
            title="Price Forecast"
            subtitle="Wholesale & Retail Trends"
            description="Compare wholesale auction prices at Dedicated Economic Centres against local retail rates to choose the most profitable selling market."
            badgeText="In Development"
            badgeType="pending"
            points={[
              "Tracks benchmark prices at Dedicated Economic Centres (DECs)",
              "Compares wholesale auction rates with local retail pricing",
            ]}
            notice="Upcoming: Forecasted selling prices (LKR/kg) will display when trained models are connected."
          />

          {/* Feature 3: Profit Risk */}
          <OverviewCard
            id="risk"
            title="Profit Risk"
            subtitle="Cost & Net Margin Analysis"
            description="Calculate your expected harvest income, total cultivation expenses, net profit, and break-even selling price before spending money."
            badgeText="Available Now"
            badgeType="ready"
            points={[
              "Calculates estimated earnings from your expected yield and budget",
              "Evaluates returns against a healthy 25% profit safety margin",
            ]}
            notice="Available now: Calculated using transparent farm financial rules based on your inputs."
          />
        </div>
      </section>

      {/* ===================================================================== */}
      {/* 3. Supported Crops Catalog Section                                    */}
      {/* ===================================================================== */}
      <section id="supported-crops">
        <CropsCatalogCard />
      </section>

      {/* ===================================================================== */}
      {/* 4. Pilot Agricultural Districts Section                               */}
      {/* ===================================================================== */}
      <section>
        <PilotDistrictsCard />
      </section>

      {/* ===================================================================== */}
      {/* 5. Quick Value Overview Bar (Warm Cream Cards & Farmer Scope)         */}
      {/* ===================================================================== */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 sm:p-4.5 rounded-2xl bg-gradient-to-br from-white via-white to-[#F7F5ED]/80 border border-[#22A06B]/25 shadow-2xs flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] shrink-0">
            <Sprout className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm sm:text-base font-extrabold text-slate-900">5 Supported Crops</div>
            <div className="text-xs sm:text-sm text-[#334155] font-medium mt-0.5">Vegetables, Grains & Legumes</div>
          </div>
        </div>

        <div className="p-4 sm:p-4.5 rounded-2xl bg-gradient-to-br from-white via-white to-[#F7F5ED]/80 border border-[#22A06B]/25 shadow-2xs flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] shrink-0">
            <MapPin className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm sm:text-base font-extrabold text-slate-900">2 Pilot Districts</div>
            <div className="text-xs sm:text-sm text-[#334155] font-medium mt-0.5">Matara & Hambantota</div>
          </div>
        </div>

        <div className="p-4 sm:p-4.5 rounded-2xl bg-gradient-to-br from-white via-white to-[#F7F5ED]/80 border border-[#22A06B]/25 shadow-2xs flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] shrink-0">
            <Building className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm sm:text-base font-extrabold text-slate-900">Wholesale Centre</div>
            <div className="text-xs sm:text-sm text-[#334155] font-medium mt-0.5">Embilipitiya DEC Hub</div>
          </div>
        </div>

        <div className="p-4 sm:p-4.5 rounded-2xl bg-gradient-to-br from-white via-white to-[#F7F5ED]/80 border border-[#22A06B]/25 shadow-2xs flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] shrink-0">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm sm:text-base font-extrabold text-slate-900">100% Free Tool</div>
            <div className="text-xs sm:text-sm text-[#334155] font-medium mt-0.5">Transparent Decision Support</div>
          </div>
        </div>
      </section>

      {/* ===================================================================== */}
      {/* 6. Bottom Prominent Call to Action Banner                             */}
      {/* ===================================================================== */}
      <section className="rounded-3xl bg-gradient-to-r from-[#166534] via-[#15803d] to-[#14532d] p-8 sm:p-10 text-white shadow-md flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2 text-center md:text-left">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3.5 py-1 text-xs font-bold text-white border border-white/20">
            <Sparkles className="h-3.5 w-3.5 text-emerald-200" />
            <span>Ready for Seasonal Cultivation</span>
          </div>
          <h3 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Start Planning Your Harvest Today
          </h3>
          <p className="text-sm sm:text-base text-emerald-50/90 max-w-xl leading-relaxed">
            Evaluate your crop demand, price forecasts, and cultivation profit margin before planting.
          </p>
        </div>

        <Link
          href="/market-profit/new-analysis"
          onClick={() => clearAnalysisSnapshot()}
          className="inline-flex items-center gap-3 rounded-2xl bg-white hover:bg-[#F7F5ED] active:scale-95 text-[#166534] font-extrabold text-base px-8 py-4 shadow-lg transition-all shrink-0 cursor-pointer min-h-[48px] group"
        >
          <Sprout className="h-5 w-5 text-[#166534] group-hover:scale-110 transition-transform" />
          <span>Start New Analysis</span>
          <ArrowRight className="h-4 w-4 text-[#166534] group-hover:translate-x-1.5 transition-transform" />
        </Link>
      </section>
    </div>
  );
}
