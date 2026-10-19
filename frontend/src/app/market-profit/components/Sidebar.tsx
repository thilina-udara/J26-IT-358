import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sprout,
  LayoutDashboard,
  PlusCircle,
  TrendingUp,
  Coins,
  ShieldCheck,
  BarChart3,
  UserCheck,
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
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const isDashboardActive = pathname === "/market-profit";
  const isNewAnalysisActive = pathname.startsWith("/market-profit/new-analysis");
  const isResultsActive = pathname.startsWith("/market-profit/results");

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
        <div className="flex h-20 items-center justify-between px-6 border-b border-slate-100 bg-[#E7F5EB]/40">
          <Link
            href="/market-profit"
            onClick={onClose}
            className="flex items-center gap-3 group focus:outline-hidden"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#166534] text-white shadow-sm shadow-emerald-700/20 group-hover:bg-[#15803d] transition-colors">
              <Sprout className="h-6 w-6 stroke-[2.2]" />
            </div>
            <div className="flex flex-col">
              <span className="text-xl font-extrabold tracking-tight text-[#166534]">
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

        {/* Navigation list tailored to Component 1 (7 items) */}
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5">
          <nav className="space-y-1">
            {/* 1. Dashboard */}
            <Link
              href="/market-profit"
              onClick={onClose}
              className={`flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-bold transition-all ${
                isDashboardActive
                  ? "bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 shadow-2xs"
                  : "text-slate-700 hover:bg-[#F7F5ED] hover:text-[#166534] border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <LayoutDashboard className={`h-4.5 w-4.5 ${isDashboardActive ? "text-[#166534]" : "text-slate-400"}`} />
                <span>Dashboard</span>
              </div>
              {isDashboardActive && <span className="h-2 w-2 rounded-full bg-[#166534]" />}
            </Link>

            {/* 2. Start Analysis */}
            <Link
              href="/market-profit/new-analysis"
              onClick={onClose}
              className={`flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-bold transition-all group ${
                isNewAnalysisActive
                  ? "bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 shadow-2xs"
                  : "text-slate-700 hover:bg-[#F7F5ED] hover:text-[#166534] border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <PlusCircle className="h-4.5 w-4.5 text-[#22A06B] group-hover:scale-110 transition-transform" />
                <span>Start Analysis</span>
              </div>
              {isNewAnalysisActive && <span className="h-2 w-2 rounded-full bg-[#166534]" />}
            </Link>

            {/* 3. Market Demand */}
            <Link
              href="/market-profit#demand"
              onClick={onClose}
              className="flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-[#F7F5ED] hover:text-[#166534] transition-all group"
            >
              <div className="flex items-center gap-3">
                <TrendingUp className="h-4.5 w-4.5 text-slate-400 group-hover:text-[#22A06B] transition-colors" />
                <span>Market Demand</span>
              </div>
              <span className="text-[10px] font-bold text-[#166534] bg-[#E7F5EB] px-2 py-0.5 rounded-full border border-[#22A06B]/25">
                Pilot
              </span>
            </Link>

            {/* 4. Price Forecast */}
            <Link
              href="/market-profit#price"
              onClick={onClose}
              className="flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-[#F7F5ED] hover:text-[#166534] transition-all group"
            >
              <div className="flex items-center gap-3">
                <Coins className="h-4.5 w-4.5 text-slate-400 group-hover:text-[#22A06B] transition-colors" />
                <span>Price Forecast</span>
              </div>
              <span className="text-[10px] font-bold text-[#166534] bg-[#E7F5EB] px-2 py-0.5 rounded-full border border-[#22A06B]/25">
                Trends
              </span>
            </Link>

            {/* 5. Profit & Risk */}
            <Link
              href="/market-profit#risk"
              onClick={onClose}
              className="flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-[#F7F5ED] hover:text-[#166534] transition-all group"
            >
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-4.5 w-4.5 text-slate-400 group-hover:text-[#22A06B] transition-colors" />
                <span>Profit &amp; Risk</span>
              </div>
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full border border-emerald-300">
                Ready
              </span>
            </Link>

            {/* 6. Analysis Results */}
            <Link
              href="/market-profit/results"
              onClick={onClose}
              className={`flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-bold transition-all ${
                isResultsActive
                  ? "bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 shadow-2xs"
                  : "text-slate-700 hover:bg-[#F7F5ED] hover:text-[#166534] border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <BarChart3 className={`h-4.5 w-4.5 ${isResultsActive ? "text-[#166534]" : "text-slate-400"}`} />
                <span>Analysis Results</span>
              </div>
              {isResultsActive && <span className="h-2 w-2 rounded-full bg-[#166534]" />}
            </Link>

            {/* 7. Farmer Profile */}
            <button
              type="button"
              onClick={() => {
                onClose();
                setIsProfileOpen(true);
              }}
              className="w-full flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-[#F7F5ED] hover:text-[#166534] transition-all text-left cursor-pointer group"
            >
              <div className="flex items-center gap-3">
                <UserCheck className="h-4.5 w-4.5 text-slate-400 group-hover:text-[#22A06B] transition-colors" />
                <span>Farmer Profile</span>
              </div>
              <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                Active
              </span>
            </button>
          </nav>
        </div>

        {/* Sidebar Footer with Pilot Information */}
        <div className="p-4 border-t border-slate-100 bg-[#F7F5ED]/60">
          <div className="rounded-2xl border border-[#22A06B]/25 bg-white p-3.5 text-xs shadow-2xs">
            <div className="flex items-center gap-1.5 font-extrabold text-[#166534] mb-1">
              <MapPin className="h-4 w-4 text-[#22A06B] shrink-0" />
              <span>Pilot Agriculture Zone</span>
            </div>
            <p className="text-[#334155] text-[11.5px] leading-relaxed font-normal">
              Matara &amp; Hambantota districts, served by Embilipitiya Economic Centre.
            </p>
          </div>
        </div>
      </aside>

      {/* Interactive Farmer Profile Modal */}
      {isProfileOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity"
            onClick={() => setIsProfileOpen(false)}
            aria-hidden="true"
          />
          <div className="relative w-full max-w-md rounded-3xl bg-white p-6 sm:p-7 shadow-2xl border border-slate-100 z-10 animate-in fade-in zoom-in-95 duration-200">
            <button
              type="button"
              onClick={() => setIsProfileOpen(false)}
              className="absolute top-5 right-5 rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-hidden"
              aria-label="Close profile modal"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Header */}
            <div className="flex items-center gap-3.5 mb-5">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#166534] text-white text-base font-extrabold shadow-sm shadow-emerald-700/20">
                JB
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                    Janidu Bandara
                  </h3>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-[#166534] border border-emerald-300">
                    Pilot Profile
                  </span>
                </div>
                <p className="text-xs font-semibold text-[#15803d]">
                  Southern Province Pilot Demonstration
                </p>
              </div>
            </div>

            {/* Details List */}
            <div className="space-y-3 rounded-2xl border border-[#22A06B]/20 bg-[#F7F5ED]/70 p-4 text-xs mb-5">
              <div className="flex justify-between items-center py-1 border-b border-emerald-900/10">
                <span className="text-slate-500 font-medium">Cultivation Districts</span>
                <span className="font-bold text-slate-900">Matara (LK-32) &amp; Hambantota (LK-33)</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-emerald-900/10">
                <span className="text-slate-500 font-medium">Primary Trading Hub</span>
                <span className="font-bold text-slate-900">Embilipitiya Dedicated Economic Centre</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-emerald-900/10">
                <span className="text-slate-500 font-medium">Active Crop Types</span>
                <span className="font-bold text-[#166534]">Okra, Brinjal, Pumpkin, Maize, G.Gram, Chilli</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-emerald-900/10">
                <span className="text-slate-500 font-medium">Research Scope</span>
                <span className="font-bold text-slate-900">Component 1 (Market, Price &amp; Risk)</span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-slate-500 font-medium">Access Mode</span>
                <span className="font-bold text-emerald-800">Pilot Demo (No Login Required)</span>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>Southern Province Pilot Phase 1</span>
              <button
                type="button"
                onClick={() => setIsProfileOpen(false)}
                className="px-4 py-2 rounded-xl font-bold bg-[#166534] text-white hover:bg-[#15803d] transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
