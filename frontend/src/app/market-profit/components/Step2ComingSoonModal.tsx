import React from "react";
import Link from "next/link";
import { CheckCircle2, ArrowRight, Sprout, MapPin, X } from "lucide-react";

interface Step2ComingSoonModalProps {
  isOpen: boolean;
  onClose: () => void;
  cropName: string;
  cropNameSi: string;
  districtName: string;
  isPilotDistrict: boolean;
}

export function Step2ComingSoonModal({
  isOpen,
  onClose,
  cropName,
  cropNameSi,
  districtName,
  isPilotDistrict,
}: Step2ComingSoonModalProps) {
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
      <div className="relative w-full max-w-lg rounded-3xl bg-white p-6 sm:p-8 shadow-2xl border border-slate-100 z-10">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 right-5 rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-hidden"
          aria-label="Close modal"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Success Header */}
        <div className="flex items-center gap-3.5 mb-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#dcfce7] text-[#15803d]">
            <CheckCircle2 className="h-7 w-7 stroke-[2.2]" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-slate-900 tracking-tight">
              Step 1 Validated Successfully
            </h3>
            <p className="text-xs font-semibold text-[#15803d]">
              AgroDecision • Feasibility Workflow
            </p>
          </div>
        </div>

        {/* Selected Summary Card */}
        <div className="rounded-2xl border border-emerald-100 bg-emerald-50/50 p-4 mb-5 space-y-2">
          <div className="text-xs font-bold uppercase tracking-wider text-[#166534]">
            Your Confirmed Selections
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-600">Selected Crop:</span>
            <span className="font-bold text-slate-900 flex items-center gap-1.5">
              <Sprout className="h-4 w-4 text-[#15803d]" />
              <span>{cropName}</span>
              <span className="text-xs text-slate-500 font-normal">({cropNameSi})</span>
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-600">Cultivation District:</span>
            <span className="font-bold text-slate-900 flex items-center gap-1.5">
              <MapPin className="h-4 w-4 text-[#15803d]" />
              <span>{districtName}</span>
              {isPilotDistrict && (
                <span className="text-[10px] bg-emerald-100 text-[#166534] px-1.5 py-0.5 rounded font-semibold">
                  Pilot Zone
                </span>
              )}
            </span>
          </div>
        </div>

        {/* Step 2 Coming Soon Notice */}
        <div className="space-y-3 text-sm text-slate-600 mb-6 leading-relaxed">
          <p>
            Your crop and location inputs have been validated and saved to your session.
          </p>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-xs text-slate-600">
            <span className="font-semibold text-slate-800">
              Coming Soon in Next Task:
            </span>{" "}
            Step 2 will allow you to input your expected harvest yield (kg), planned harvest date, and choose wholesale auction or retail pricing.
          </div>
        </div>

        {/* Modal Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-100 border border-slate-200 transition-colors"
          >
            Review Step 1
          </button>
          <Link
            href="/market-profit"
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl text-sm font-bold bg-[#15803d] hover:bg-[#166534] text-white shadow-sm transition-colors text-center"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
