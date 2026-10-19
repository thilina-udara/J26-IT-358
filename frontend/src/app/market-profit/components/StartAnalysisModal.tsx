import React from "react";
import { X, Sprout, ArrowRight, CheckCircle2 } from "lucide-react";

interface StartAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function StartAnalysisModal({ isOpen, onClose }: StartAnalysisModalProps) {
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

        {/* Header */}
        <div className="flex items-center gap-3.5 mb-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#15803d] text-white shadow-sm shadow-emerald-700/20">
            <Sprout className="h-6 w-6 stroke-[2.2]" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-slate-900 tracking-tight">
              Start New Crop Analysis
            </h3>
            <p className="text-xs font-semibold text-[#15803d]">
              AgroDecision • Farmer Planning Assistant
            </p>
          </div>
        </div>

        {/* How it Works / Steps */}
        <div className="space-y-4 text-sm text-slate-600 mb-6">
          <p className="leading-relaxed">
            The full crop planning form is opening in the next step. Here is how your upcoming analysis works:
          </p>

          <div className="rounded-2xl border border-emerald-100 bg-emerald-50/50 p-4 space-y-2.5 text-xs">
            <div className="flex items-start gap-2.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#15803d] text-white text-[10px] font-bold shrink-0">
                1
              </span>
              <div>
                <span className="font-bold text-slate-900">Select Crop:</span> Choose from the 5 supported varieties (Okra, Brinjal, Maize, Mung Bean, Chilli).
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#15803d] text-white text-[10px] font-bold shrink-0">
                2
              </span>
              <div>
                <span className="font-bold text-slate-900">Choose Location:</span> Pick your district and target market (e.g., Embilipitiya Economic Centre).
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#15803d] text-white text-[10px] font-bold shrink-0">
                3
              </span>
              <div>
                <span className="font-bold text-slate-900">Enter Farm Details:</span> Input expected harvest weight (kg) and cultivation budget (LKR).
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#15803d] text-white text-[10px] font-bold shrink-0">
                4
              </span>
              <div>
                <span className="font-bold text-slate-900">View Evaluation:</span> Receive clear profit margin estimates and risk guidance.
              </div>
            </div>
          </div>

          <p className="text-xs text-slate-500">
            For now, feel free to explore the feature cards, pilot regions, and supported crop catalog on this overview screen.
          </p>
        </div>

        {/* Action Button */}
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl font-semibold text-sm bg-[#15803d] text-white hover:bg-[#166534] transition-colors shadow-sm cursor-pointer"
          >
            Explore Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
