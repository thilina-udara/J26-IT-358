"use client";

import React from "react";
import Link from "next/link";
import Image, { StaticImageData } from "next/image";
import {
  CheckCircle2,
  Calendar,
  Compass,
  Scale,
  MapPin,
  Store,
  Calculator,
  Tag,
  X,
} from "lucide-react";
import { formatDateDisplay, formatKg } from "../lib/formatters";

export interface Step4ComingSoonModalProps {
  isOpen: boolean;
  onClose: () => void;
  cropName: string;
  cropNameSi: string;
  cropImage?: StaticImageData | null;
  districtName: string;
  isPilotDistrict: boolean;
  harvestDate: string;
  landExtentAcres: string;
  expectedYieldKg: string;
  marketName: string;
  marketRegion: string;
  isPilotMarket: boolean;
  priceType?: string;
}

export function Step4ComingSoonModal({
  isOpen,
  onClose,
  cropName,
  cropNameSi,
  cropImage,
  districtName,
  isPilotDistrict,
  harvestDate,
  landExtentAcres,
  expectedYieldKg,
  marketName,
  marketRegion,
  isPilotMarket,
  priceType,
}: Step4ComingSoonModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-step4-title"
        className="relative w-full max-w-xl rounded-3xl bg-white p-6 sm:p-8 shadow-2xl border border-slate-100 z-10 max-h-[90vh] overflow-y-auto"
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 right-5 rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-hidden transition-colors cursor-pointer"
          aria-label="Close modal"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Success Header */}
        <div className="flex items-center gap-3.5 mb-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#dcfce7] text-[#15803d] shrink-0">
            <CheckCircle2 className="h-7 w-7 stroke-[2.2]" />
          </div>
          <div>
            <h3 id="modal-step4-title" className="text-xl font-bold text-slate-900 tracking-tight">
              Step 3 Completed Successfully
            </h3>
            <p className="text-xs font-semibold text-[#15803d]">
              AgroDecision • Selling Market Selection Confirmed
            </p>
          </div>
        </div>

        {/* Summary Parameters Card */}
        <div className="rounded-2xl border border-emerald-200/90 bg-emerald-50/50 p-4 sm:p-5 mb-5 space-y-3">
          <div className="text-xs font-bold uppercase tracking-wider text-[#166534]">
            Confirmed Feasibility Analysis Parameters
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            {/* Crop */}
            <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-white border border-emerald-100">
              {cropImage && (
                <div className="relative h-10 w-10 rounded-lg overflow-hidden shrink-0 border border-emerald-200">
                  <Image src={cropImage} alt={cropName} fill className="object-cover" />
                </div>
              )}
              <div className="min-w-0">
                <span className="text-[10px] font-semibold text-slate-500 block uppercase">
                  Candidate Crop
                </span>
                <span className="text-sm font-bold text-slate-900 truncate block">
                  {cropName}{" "}
                  <span className="text-xs font-normal text-slate-500">({cropNameSi})</span>
                </span>
              </div>
            </div>

            {/* District */}
            <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-white border border-emerald-100">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-[#15803d] shrink-0">
                <MapPin className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <span className="text-[10px] font-semibold text-slate-500 block uppercase">
                  Cultivation District
                </span>
                <span className="text-sm font-bold text-slate-900 truncate block">
                  {districtName}
                  {isPilotDistrict && (
                    <span className="ml-1 text-[10px] bg-emerald-100 text-[#166534] px-1 py-0.5 rounded font-semibold">
                      Pilot Zone
                    </span>
                  )}
                </span>
              </div>
            </div>

            {/* Harvest Date */}
            <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-white border border-emerald-100">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-[#15803d] shrink-0">
                <Calendar className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <span className="text-[10px] font-semibold text-slate-500 block uppercase">
                  Harvest Date
                </span>
                <span className="text-sm font-bold text-slate-900 truncate block">
                  {formatDateDisplay(harvestDate)}
                </span>
              </div>
            </div>

            {/* Land Extent */}
            <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-white border border-emerald-100">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-[#15803d] shrink-0">
                <Compass className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <span className="text-[10px] font-semibold text-slate-500 block uppercase">
                  Cultivation Extent
                </span>
                <span className="text-sm font-bold text-slate-900 truncate block">
                  {landExtentAcres} Acres
                </span>
              </div>
            </div>

            {/* Expected Yield */}
            <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-white border border-emerald-100">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-[#15803d] shrink-0">
                <Scale className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <span className="text-[10px] font-semibold text-slate-500 block uppercase">
                  Expected Yield
                </span>
                <span className="text-sm font-bold text-slate-900 truncate block">
                  {formatKg(expectedYieldKg)} ({expectedYieldKg} kg)
                </span>
              </div>
            </div>

            {/* Selling Market */}
            <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-white border border-emerald-100">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-[#15803d] shrink-0">
                <Store className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <span className="text-[10px] font-semibold text-slate-500 block uppercase">
                  Selling Market
                </span>
                <span className="text-sm font-bold text-slate-900 truncate block">
                  {marketName}
                  {isPilotMarket && (
                    <span className="ml-1 text-[10px] bg-emerald-100 text-[#166534] px-1 py-0.5 rounded font-semibold">
                      Pilot Hub
                    </span>
                  )}
                </span>
              </div>
            </div>

            {/* Price Valuation Type */}
            <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-white border border-emerald-100">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-[#15803d] shrink-0">
                <Tag className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <span className="text-[10px] font-semibold text-slate-500 block uppercase">
                  Price Valuation Type
                </span>
                <span className="text-sm font-bold text-slate-900 truncate block capitalize">
                  {priceType || "Wholesale"}
                  <span className="ml-1.5 text-[10px] bg-emerald-100 text-[#166534] px-1 py-0.5 rounded font-semibold capitalize">
                    {priceType === "retail" ? "Consumer" : "Bulk / Trade"}
                  </span>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Step 4 Coming Soon Notice */}
        <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 mb-6 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
            <Calculator className="h-4 w-4 text-[#15803d]" />
            <span>Next Stage: Step 4 — Cultivation Costs &amp; Financial Risk</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Your crop, cultivation district, harvest timing, production yield, target selling market, and price valuation type are verified and saved. Step 4 (Cultivation Costs) will be implemented in the upcoming sprint task, allowing you to enter cost parameters to evaluate projected profit margins, break-even unit prices, and financial risk.
          </p>
        </div>

        {/* Modal Action Buttons */}
        <div className="flex flex-col-reverse sm:flex-row items-center justify-end gap-3 pt-2 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
          >
            Review Selling Market
          </button>
          <Link
            href="/market-profit"
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl text-sm font-bold bg-[#15803d] hover:bg-[#166534] text-white shadow-sm transition-colors text-center"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
