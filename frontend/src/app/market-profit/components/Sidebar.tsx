import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sprout,
  LayoutDashboard,
  PlusCircle,
  BarChart3,
  UserCheck,
  X,
} from "lucide-react";
import { FarmerProfileModal } from "./FarmerProfileModal";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenProfile?: () => void;
}

export function Sidebar({ isOpen, onClose, onOpenProfile }: SidebarProps) {
  const pathname = usePathname();
  const [internalProfileOpen, setInternalProfileOpen] = useState(false);

  const isDashboardActive = pathname === "/market-profit";
  const isNewAnalysisActive = pathname.startsWith("/market-profit/new-analysis");
  const isResultsActive = pathname.startsWith("/market-profit/results");

  const handleOpenProfile = () => {
    onClose(); // close mobile sidebar drawer
    if (onOpenProfile) {
      onOpenProfile();
    } else {
      setInternalProfileOpen(true);
    }
  };

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

        {/* Navigation list: Exactly 4 main items */}
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-2">
          <nav className="space-y-1.5">
            {/* 1. Dashboard */}
            <Link
              href="/market-profit"
              onClick={onClose}
              className={`flex items-center justify-between rounded-xl px-3.5 py-3 text-sm font-bold transition-all ${
                isDashboardActive
                  ? "bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 shadow-2xs"
                  : "text-slate-700 hover:bg-[#F7F5ED] hover:text-[#166534] border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <LayoutDashboard className={`h-5 w-5 ${isDashboardActive ? "text-[#166534]" : "text-slate-400"}`} />
                <span>Dashboard</span>
              </div>
              {isDashboardActive && <span className="h-2 w-2 rounded-full bg-[#166534]" />}
            </Link>

            {/* 2. Start Analysis (Active across all 4 input steps) */}
            <Link
              href="/market-profit/new-analysis"
              onClick={onClose}
              className={`flex items-center justify-between rounded-xl px-3.5 py-3 text-sm font-bold transition-all group ${
                isNewAnalysisActive
                  ? "bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 shadow-2xs"
                  : "text-slate-700 hover:bg-[#F7F5ED] hover:text-[#166534] border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <PlusCircle className={`h-5 w-5 ${isNewAnalysisActive ? "text-[#166534]" : "text-[#22A06B]"} group-hover:scale-110 transition-transform`} />
                <span>Start Analysis</span>
              </div>
              {isNewAnalysisActive && <span className="h-2 w-2 rounded-full bg-[#166534]" />}
            </Link>

            {/* 3. Analysis Results */}
            <Link
              href="/market-profit/results"
              onClick={onClose}
              className={`flex items-center justify-between rounded-xl px-3.5 py-3 text-sm font-bold transition-all ${
                isResultsActive
                  ? "bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 shadow-2xs"
                  : "text-slate-700 hover:bg-[#F7F5ED] hover:text-[#166534] border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <BarChart3 className={`h-5 w-5 ${isResultsActive ? "text-[#166534]" : "text-slate-400"}`} />
                <span>Analysis Results</span>
              </div>
              {isResultsActive && <span className="h-2 w-2 rounded-full bg-[#166534]" />}
            </Link>

            {/* 4. Farmer Profile */}
            <button
              type="button"
              onClick={handleOpenProfile}
              className="flex items-center justify-between w-full rounded-xl px-3.5 py-3 text-sm font-bold text-slate-700 hover:bg-[#F7F5ED] hover:text-[#166534] border border-transparent transition-all cursor-pointer group"
            >
              <div className="flex items-center gap-3">
                <UserCheck className="h-5 w-5 text-slate-400 group-hover:text-[#166534] transition-colors" />
                <span>Farmer Profile</span>
              </div>
            </button>
          </nav>
        </div>
      </aside>

      {/* Internal profile modal fallback if not handled by Shell */}
      {!onOpenProfile && (
        <FarmerProfileModal
          isOpen={internalProfileOpen}
          onClose={() => setInternalProfileOpen(false)}
        />
      )}
    </>
  );
}
