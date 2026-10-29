"use client";

import React, { useEffect } from "react";
import { X, User, MapPin, Store, Sprout, ShieldCheck } from "lucide-react";
import { SRI_LANKA_DISTRICTS, STANDARD_MARKETS, SUPPORTED_FRONTEND_CROPS } from "../lib/constants";

interface FarmerProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function FarmerProfileModal({ isOpen, onClose }: FarmerProfileModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop overlay */}
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="farmer-profile-title"
        className="relative w-full max-w-md rounded-3xl bg-white p-6 sm:p-7 shadow-2xl border border-slate-100 z-10 animate-in fade-in zoom-in-95 duration-200"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 right-5 rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-hidden transition-colors cursor-pointer"
          aria-label="Close profile modal"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Profile Header */}
        <div className="flex items-center gap-3.5 mb-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#166534] text-white text-base font-extrabold shadow-sm shadow-emerald-700/20">
            JB
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 id="farmer-profile-title" className="text-lg font-bold text-slate-900 tracking-tight">
                Janidu Bandara
              </h3>
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30">
                Farmer Profile
              </span>
            </div>
            <p className="text-xs font-semibold text-[#15803d]">
              Registered Farmer • Southern Province
            </p>
          </div>
        </div>

        {/* Farmer Information Details */}
        <div className="space-y-3 rounded-2xl border border-[#22A06B]/20 bg-[#F7F5ED]/70 p-4 text-xs mb-5">
          <div className="flex justify-between items-center py-1.5 border-b border-emerald-900/10">
            <span className="flex items-center gap-1.5 text-slate-500 font-medium">
              <MapPin className="h-3.5 w-3.5 text-[#15803d]" />
              Cultivation Districts
            </span>
            <span className="font-bold text-slate-900">
              Matara (LK-32) &amp; Hambantota (LK-33)
            </span>
          </div>

          <div className="flex justify-between items-center py-1.5 border-b border-emerald-900/10">
            <span className="flex items-center gap-1.5 text-slate-500 font-medium">
              <Store className="h-3.5 w-3.5 text-[#15803d]" />
              Primary Trading Hub
            </span>
            <span className="font-bold text-slate-900">
              Embilipitiya Dedicated Economic Centre
            </span>
          </div>

          <div className="flex justify-between items-center py-1.5 border-b border-emerald-900/10">
            <span className="flex items-center gap-1.5 text-slate-500 font-medium">
              <Sprout className="h-3.5 w-3.5 text-[#15803d]" />
              Supported Crops
            </span>
            <span className="font-bold text-[#166534]">
              {SUPPORTED_FRONTEND_CROPS.map((c) => c.name_en).join(", ")}
            </span>
          </div>

          <div className="flex justify-between items-center py-1.5">
            <span className="flex items-center gap-1.5 text-slate-500 font-medium">
              <ShieldCheck className="h-3.5 w-3.5 text-[#15803d]" />
              Current Application
            </span>
            <span className="font-bold text-slate-900">
              AgroDecision Market &amp; Profit
            </span>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Profile active</span>
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl font-bold bg-[#166534] hover:bg-[#15803d] text-white transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
