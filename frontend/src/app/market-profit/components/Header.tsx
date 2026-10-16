import React from "react";
import { usePathname } from "next/navigation";
import { Menu, Sprout, MapPin } from "lucide-react";

interface HeaderProps {
  onToggleSidebar: () => void;
}

export function Header({ onToggleSidebar }: HeaderProps) {
  const pathname = usePathname();
  const isNewAnalysis = pathname.includes("/new-analysis");

  return (
    <header className="sticky top-0 z-30 flex h-20 w-full items-center justify-between border-b border-slate-200/80 bg-white/95 px-4 backdrop-blur-md sm:px-6 lg:px-8">
      {/* Left section: Mobile toggle + Branding / Breadcrumb */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Mobile Hamburger Button */}
        <button
          type="button"
          onClick={onToggleSidebar}
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100 lg:hidden focus:outline-hidden"
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Mobile Brand (hidden on desktop where sidebar is present) */}
        <div className="flex items-center gap-2.5 lg:hidden">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#15803d] text-white shadow-xs">
            <Sprout className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-base font-bold text-[#166534] leading-tight">
              AgroDecision
            </span>
            <span className="text-[10px] font-semibold text-[#15803d]">
              Your Farming Partner
            </span>
          </div>
        </div>

        {/* Desktop Breadcrumb */}
        <div className="hidden lg:flex items-center gap-2 text-sm text-slate-500 font-medium">
          <span className="text-slate-800 font-semibold">AgroDecision</span>
          <span>/</span>
          <span>Market & Profit</span>
          <span>/</span>
          <span className="text-[#166534] font-semibold">
            {isNewAnalysis ? "New Analysis (Step 1)" : "Overview"}
          </span>
        </div>
      </div>

      {/* Right section: Simple Pilot Zone Tag */}
      <div className="flex items-center gap-2 sm:gap-3">
        <div className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-[#166534]">
          <MapPin className="h-3.5 w-3.5 text-[#15803d] shrink-0" />
          <span>Southern Province Pilot</span>
        </div>
      </div>
    </header>
  );
}
