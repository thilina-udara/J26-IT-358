"use client";

import React from "react";
import {
  Sprout,
  ArrowRight,
  TrendingUp,
  Coins,
  ShieldCheck,
  MapPin,
  Sparkles,
} from "lucide-react";
import { useShell } from "./components/Shell";
import { OverviewCard } from "./components/OverviewCard";
import { PilotDistrictsCard } from "./components/PilotDistrictsCard";
import { CropsCatalogCard } from "./components/CropsCatalogCard";
import { MASTER_CROPS, SRI_LANKA_DISTRICTS, STANDARD_MARKETS } from "./lib/constants";

export default function MarketProfitHomePage() {
  const { openStartAnalysisModal } = useShell();

  return (
    <div className="space-y-8 pb-12">
      {/* 1. Welcoming Hero Banner (High Contrast & Farmer-Friendly) */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-emerald-50 via-white to-green-50/80 border border-emerald-200/90 p-8 sm:p-10 shadow-xs">
        {/* Subtle decorative background circles */}
        <div className="absolute -top-16 -right-16 h-64 w-64 rounded-full bg-emerald-100/50 blur-2xl pointer-events-none" />
        <div className="absolute -bottom-16 -left-16 h-64 w-64 rounded-full bg-green-100/40 blur-2xl pointer-events-none" />

        <div className="relative z-10 max-w-3xl">
          {/* Brand Tag Pill */}
          <div className="inline-flex items-center gap-2 rounded-full bg-emerald-100/80 px-3.5 py-1 text-xs font-semibold text-[#166534] border border-emerald-200/80 mb-4">
            <Sprout className="h-4 w-4 text-[#15803d]" />
            <span className="tracking-wide">AgroDecision • Your Farming Partner</span>
          </div>

          {/* Main Farmer Heading */}
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#166534] mb-3 leading-tight sm:leading-tight">
            Plan Smarter, Grow Better
          </h1>

          {/* Subheading */}
          <p className="text-base sm:text-lg text-slate-700 leading-relaxed mb-7 max-w-2xl font-normal">
            Explore market opportunities, plan your harvest, and understand your potential profit before planting.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={openStartAnalysisModal}
              className="inline-flex items-center gap-2.5 rounded-xl bg-[#15803d] hover:bg-[#166534] active:scale-95 text-white font-bold text-sm px-6 py-3.5 shadow-sm shadow-emerald-800/20 transition-all cursor-pointer group"
            >
              <Sprout className="h-5 w-5 text-emerald-100 group-hover:scale-110 transition-transform" />
              <span>Start New Analysis</span>
              <ArrowRight className="h-4 w-4 text-emerald-100 group-hover:translate-x-1 transition-transform" />
            </button>

            <a
              href="#supported-crops"
              className="inline-flex items-center gap-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-semibold text-sm px-5 py-3.5 transition-colors cursor-pointer"
            >
              <span>View Supported Crops</span>
            </a>
          </div>
        </div>
      </section>

      {/* 2. Three Clean Feature Cards */}
      <section className="space-y-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-[#15803d]">
            How AgroDecision Helps You
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight mt-0.5">
            Key Planning Tools
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Feature 1: Market Demand */}
          <OverviewCard
            id="demand"
            title="Market Demand"
            subtitle="Understand future market opportunities"
            description="Discover which crops have strong buyer demand across districts so you can harvest at the most profitable time."
            badgeText="In Development"
            badgeType="pending"
            points={[
              "Designed to identify buyer demand trends across districts",
              "Aims to help avoid harvesting during seasonal oversupply",
              "Pilot focus on Matara and Hambantota growing zones",
            ]}
            notice="Demand forecasting model is currently in development. Market demand indicators will activate once connected."
          />

          {/* Feature 2: Price Trends */}
          <OverviewCard
            id="price"
            title="Price Trends"
            subtitle="Explore potential market prices"
            description="Compare wholesale auction prices at major economic centres with local retail prices to find the best selling channel."
            badgeText="In Development"
            badgeType="pending"
            points={[
              "Designed to track wholesale prices at Dedicated Economic Centres",
              "Compares wholesale auction rates with local retail pricing",
              "Focuses on Embilipitiya Economic Centre as primary southern hub",
            ]}
            notice="Price forecasting model is currently in development. Market price feeds will activate once connected."
          />

          {/* Feature 3: Profit Risk */}
          <OverviewCard
            id="risk"
            title="Profit Risk"
            subtitle="Check possible earnings and financial risks"
            description="Estimate your gross earnings, net profit, and break-even harvest price before planting to protect against losses."
            badgeText="Rule-Based"
            badgeType="ready"
            points={[
              "Calculates estimated earnings from your expected yield and budget",
              "Evaluates returns against a healthy 25% profit margin benchmark",
              "Identifies high-risk crops before spending on seeds and fertilizer",
            ]}
            notice="Preliminary rule-based assessment — Estimates are calculated using basic profit rules and benchmark margins, not machine learning."
          />
        </div>
      </section>

      {/* 3. Pilot Agricultural Districts Section */}
      <section>
        <PilotDistrictsCard />
      </section>

      {/* 4. Supported Crops Catalog Section */}
      <section id="supported-crops">
        <CropsCatalogCard />
      </section>
    </div>
  );
}
