import React from "react";
import Link from "next/link";
import { MapPin, Building, Compass, ArrowRight, CheckCircle2 } from "lucide-react";
import { saveStep1ToStorage, loadStep1FromStorage, clearAnalysisSnapshot } from "../lib/wizard";

export function PilotDistrictsCard() {
  const handleSelectDistrict = (districtId: string) => {
    clearAnalysisSnapshot();
    const existing = loadStep1FromStorage();
    saveStep1ToStorage({
      crop_id: existing.crop_id || "",
      cultivation_district_id: districtId,
    });
  };

  return (
    <div className="rounded-3xl bg-gradient-to-b from-white via-white to-[#F7F5ED]/40 p-6 sm:p-8 border border-slate-200/90 shadow-xs">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#166534]">
            <Compass className="h-4 w-4" />
            <span>Regional Focus • Southern Province</span>
          </div>
          <h3 className="text-2xl font-extrabold text-slate-900 tracking-tight mt-1">
            Pilot Agricultural Districts
          </h3>
          <p className="text-[15px] sm:text-base text-[#334155] mt-1.5 max-w-2xl leading-relaxed">
            AgroDecision is currently active across Southern Sri Lanka to help local farmers evaluate market demand and prices before seasonal planting.
          </p>
        </div>
        <div className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 w-fit self-start sm:self-auto shadow-2xs">
          <CheckCircle2 className="h-3.5 w-3.5 text-[#22A06B]" />
          <span>2 Active Pilot Districts</span>
        </div>
      </div>

      {/* Pilot Districts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        {/* District 1: Matara */}
        <div className="rounded-2xl border border-[#22A06B]/25 bg-gradient-to-br from-[#F7F5ED]/90 via-white to-[#E7F5EB]/30 p-5 sm:p-6 hover:border-[#22A06B] hover:shadow-md transition-all flex flex-col justify-between group">
          <div>
            <div className="flex items-center justify-between gap-2 mb-3.5">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] group-hover:scale-105 transition-transform">
                  <MapPin className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-lg font-extrabold text-slate-900 group-hover:text-[#166534] transition-colors">
                    Matara District
                  </h4>
                  <p className="text-xs sm:text-sm text-[#166534] font-bold">
                    Southern Coastal Agricultural Belt
                  </p>
                </div>
              </div>
              <span className="text-xs font-extrabold px-3 py-1 rounded-full bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30">
                LK-32
              </span>
            </div>
            <p className="text-sm sm:text-[14.5px] text-[#334155] leading-relaxed mb-5 font-normal">
              High-rainfall coastal and mid-country belt with intensive vegetable and paddy farming. Farmers here can evaluate perishable crop timing and avoid seasonal market gluts.
            </p>
          </div>

          <Link
            href="/market-profit/new-analysis"
            onClick={() => handleSelectDistrict("LK-32")}
            className="inline-flex items-center justify-between w-full rounded-xl bg-white hover:bg-[#166534] text-[#166534] hover:text-white border border-[#22A06B]/40 hover:border-[#166534] px-4 py-3 text-xs sm:text-sm font-bold shadow-2xs transition-all group/btn cursor-pointer min-h-[46px]"
          >
            <span>Plan for Matara District</span>
            <ArrowRight className="h-4 w-4 text-[#22A06B] group-hover/btn:text-white group-hover/btn:translate-x-1 transition-all" />
          </Link>
        </div>

        {/* District 2: Hambantota */}
        <div className="rounded-2xl border border-[#22A06B]/25 bg-gradient-to-br from-[#F7F5ED]/90 via-white to-[#E7F5EB]/30 p-5 sm:p-6 hover:border-[#22A06B] hover:shadow-md transition-all flex flex-col justify-between group">
          <div>
            <div className="flex items-center justify-between gap-2 mb-3.5">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] group-hover:scale-105 transition-transform">
                  <MapPin className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-lg font-extrabold text-slate-900 group-hover:text-[#166534] transition-colors">
                    Hambantota District
                  </h4>
                  <p className="text-xs sm:text-sm text-[#166534] font-bold">
                    Southern Commercial Dry Zone
                  </p>
                </div>
              </div>
              <span className="text-xs font-extrabold px-3 py-1 rounded-full bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30">
                LK-33
              </span>
            </div>
            <p className="text-sm sm:text-[14.5px] text-[#334155] leading-relaxed mb-5 font-normal">
              Commercial dry-zone farming region specializing in field crops, condiments, and grains. Helps growers compare wholesale market prices and calculate seasonal returns.
            </p>
          </div>

          <Link
            href="/market-profit/new-analysis"
            onClick={() => handleSelectDistrict("LK-33")}
            className="inline-flex items-center justify-between w-full rounded-xl bg-white hover:bg-[#166534] text-[#166534] hover:text-white border border-[#22A06B]/40 hover:border-[#166534] px-4 py-3 text-xs sm:text-sm font-bold shadow-2xs transition-all group/btn cursor-pointer min-h-[46px]"
          >
            <span>Plan for Hambantota District</span>
            <ArrowRight className="h-4 w-4 text-[#22A06B] group-hover/btn:text-white group-hover/btn:translate-x-1 transition-all" />
          </Link>
        </div>
      </div>

      {/* Primary Trading Hub */}
      <div className="rounded-2xl border border-[#22A06B]/30 bg-gradient-to-br from-[#E7F5EB]/80 via-white to-[#F7F5ED]/80 p-5 sm:p-6 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#166534] text-white shadow-xs shrink-0">
              <Building className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="text-base sm:text-lg font-extrabold text-[#166534]">
                  Embilipitiya Dedicated Economic Centre
                </h4>
                <span className="text-[11px] font-extrabold px-3 py-1 rounded-full bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30 uppercase tracking-wider">
                  Primary Market Hub
                </span>
              </div>
              <p className="text-sm sm:text-[14.5px] text-[#334155] mt-1.5 max-w-2xl leading-relaxed font-normal">
                The central wholesale trading hub connecting southern farmers with islandwide distributors. Real-time wholesale prices at Embilipitiya DEC serve as the primary benchmark for southern market evaluations.
              </p>
            </div>
          </div>

          <Link
            href="/market-profit/new-analysis"
            onClick={() => clearAnalysisSnapshot()}
            className="inline-flex items-center gap-2 rounded-xl bg-white hover:bg-[#166534] text-[#166534] hover:text-white border border-[#22A06B]/40 hover:border-[#166534] px-5 py-3 text-xs sm:text-sm font-bold shadow-2xs transition-all shrink-0 self-start sm:self-auto cursor-pointer min-h-[44px]"
          >
            <span>Start Analysis</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
