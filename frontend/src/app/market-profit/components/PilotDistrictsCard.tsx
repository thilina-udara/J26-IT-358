import React from "react";
import { MapPin, Building, Compass } from "lucide-react";

export function PilotDistrictsCard() {
  return (
    <div className="rounded-2xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs">
      {/* Section Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#15803d]">
          <Compass className="h-4 w-4" />
          <span>Regional Focus</span>
        </div>
        <h3 className="text-xl font-bold text-slate-900 tracking-tight mt-0.5">
          Pilot Agricultural Districts
        </h3>
        <p className="text-sm text-slate-600 mt-1">
          AgroDecision is currently piloted across Southern Sri Lanka to help local farmers make informed planting and marketing decisions.
        </p>
      </div>

      {/* Pilot Districts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        {/* District 1: Matara */}
        <div className="rounded-xl border border-slate-200/80 bg-slate-50/50 p-5 hover:border-emerald-200 transition-colors">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-[#166534]">
              <MapPin className="h-4 w-4" />
            </div>
            <div>
              <h4 className="text-base font-bold text-slate-900">
                Matara District
              </h4>
              <p className="text-xs text-slate-500 font-medium">
                Southern Coastal Agricultural Belt
              </p>
            </div>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            High-rainfall region with intensive vegetable and paddy cultivation. Helps farmers evaluate perishable crop timing and local consumer market opportunities.
          </p>
        </div>

        {/* District 2: Hambantota */}
        <div className="rounded-xl border border-slate-200/80 bg-slate-50/50 p-5 hover:border-emerald-200 transition-colors">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-[#166534]">
              <MapPin className="h-4 w-4" />
            </div>
            <div>
              <h4 className="text-base font-bold text-slate-900">
                Hambantota District
              </h4>
              <p className="text-xs text-slate-500 font-medium">
                Southern Commercial Dry Zone
              </p>
            </div>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Major commercial farming region specializing in field crops, condiments, and grains. Helps growers plan bulk production and track wholesale pricing.
          </p>
        </div>
      </div>

      {/* Primary Trading Hub */}
      <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#15803d] text-white shrink-0">
            <Building className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-[#166534]">
              Embilipitiya Dedicated Economic Centre
            </h4>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              The primary wholesale trading hub serving southern farmers. Connects harvests from Matara and Hambantota directly with distribution networks across Sri Lanka.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
