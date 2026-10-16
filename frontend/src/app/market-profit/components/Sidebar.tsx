import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sprout,
  Home,
  PlusCircle,
  TrendingUp,
  Coins,
  ShieldCheck,
  MapPin,
  X,
} from "lucide-react";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onStartAnalysisClick?: () => void;
}

export function Sidebar({ isOpen, onClose, onStartAnalysisClick }: SidebarProps) {
  const pathname = usePathname();
  const isOverviewActive = pathname === "/market-profit";
  const isNewAnalysisActive = pathname === "/market-profit/new-analysis";

  return (
    <>
      {/* Mobile Backdrop overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-xs transition-opacity lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex w-72 flex-col bg-white border-r border-slate-200/80 transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand Header */}
        <div className="flex h-20 items-center justify-between px-6 border-b border-slate-100 bg-emerald-50/30">
          <Link
            href="/market-profit"
            className="flex items-center gap-3 group focus:outline-hidden"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#15803d] text-white shadow-sm shadow-emerald-700/20 group-hover:bg-[#166534] transition-colors">
              <Sprout className="h-6 w-6 stroke-[2.2]" />
            </div>
            <div className="flex flex-col">
              <span className="text-xl font-bold tracking-tight text-[#166534]">
                AgroDecision
              </span>
              <span className="text-xs font-semibold text-[#15803d] tracking-wide">
                Your Farming Partner
              </span>
            </div>
          </Link>

          {/* Close button for mobile screens */}
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 lg:hidden focus:outline-hidden"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation list */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
          <nav className="space-y-1.5">
            {/* 1. Overview */}
            <Link
              href="/market-profit"
              onClick={onClose}
              className={`flex items-center justify-between rounded-xl px-4 py-3 text-sm font-semibold transition-colors ${
                isOverviewActive
                  ? "bg-[#dcfce7] text-[#166534] border border-[#bbf7d0]/60 shadow-2xs"
                  : "text-slate-700 hover:bg-slate-50 border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <Home className={`h-5 w-5 ${isOverviewActive ? "text-[#15803d]" : "text-slate-400"}`} />
                <span>Overview</span>
              </div>
              {isOverviewActive && <span className="h-2 w-2 rounded-full bg-[#15803d]" />}
            </Link>

            {/* 2. New Analysis */}
            <Link
              href="/market-profit/new-analysis"
              onClick={onClose}
              className={`flex items-center justify-between rounded-xl px-4 py-3 text-sm font-semibold transition-colors group ${
                isNewAnalysisActive
                  ? "bg-[#dcfce7] text-[#166534] border border-[#bbf7d0]/60 shadow-2xs"
                  : "text-slate-700 hover:bg-slate-50 border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <PlusCircle className="h-5 w-5 text-[#15803d] group-hover:scale-105 transition-transform" />
                <span>New Analysis</span>
              </div>
              {isNewAnalysisActive && <span className="h-2 w-2 rounded-full bg-[#15803d]" />}
            </Link>

            {/* 3. Market Demand (Coming Soon) */}
            <div
              className="flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-slate-400 select-none"
              title="Coming Soon in next update"
            >
              <div className="flex items-center gap-3">
                <TrendingUp className="h-5 w-5 text-slate-400" />
                <span>Market Demand</span>
              </div>
              <span className="text-[11px] font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                Coming Soon
              </span>
            </div>

            {/* 4. Price Forecast (Coming Soon) */}
            <div
              className="flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-slate-400 select-none"
              title="Coming Soon in next update"
            >
              <div className="flex items-center gap-3">
                <Coins className="h-5 w-5 text-slate-400" />
                <span>Price Forecast</span>
              </div>
              <span className="text-[11px] font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                Coming Soon
              </span>
            </div>

            {/* 5. Profit Risk (Coming Soon) */}
            <div
              className="flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-slate-400 select-none"
              title="Coming Soon in next update"
            >
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-5 w-5 text-slate-400" />
                <span>Profit Risk</span>
              </div>
              <span className="text-[11px] font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                Coming Soon
              </span>
            </div>
          </nav>
        </div>

        {/* Sidebar Footer with Pilot Information */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50">
          <div className="rounded-xl border border-emerald-100 bg-white p-3.5 text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-[#166534] mb-1.5">
              <MapPin className="h-3.5 w-3.5 text-[#15803d]" />
              <span>Pilot Areas</span>
            </div>
            <p className="text-slate-600 text-[11px] leading-relaxed">
              Matara & Hambantota districts, served by Embilipitiya Economic Centre.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
