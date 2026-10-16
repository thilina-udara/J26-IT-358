import React from "react";
import { AlertTriangle, CheckCircle2, MapPin, Clock, Info } from "lucide-react";

export type StatusVariant =
  | "ml-pending"
  | "heuristic-active"
  | "pilot-verified"
  | "coming-soon"
  | "neutral";

interface StatusBadgeProps {
  variant: StatusVariant;
  label?: string;
  className?: string;
}

export function StatusBadge({ variant, label, className = "" }: StatusBadgeProps) {
  switch (variant) {
    case "ml-pending":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200 shadow-xs ${className}`}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
          <span>{label || "ML Model Pending (Unavailable)"}</span>
        </span>
      );

    case "heuristic-active":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-xs ${className}`}
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-[#15803d] shrink-0" />
          <span>{label || "Rule-Based Heuristic Active"}</span>
        </span>
      );

    case "pilot-verified":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-50 text-sky-800 border border-sky-200 shadow-xs ${className}`}
        >
          <MapPin className="w-3.5 h-3.5 text-sky-600 shrink-0" />
          <span>{label || "Verified Pilot Zone"}</span>
        </span>
      );

    case "coming-soon":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200 ${className}`}
        >
          <Clock className="w-3 h-3 text-slate-500 shrink-0" />
          <span>{label || "Coming Soon"}</span>
        </span>
      );

    case "neutral":
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200 ${className}`}
        >
          <Info className="w-3.5 h-3.5 text-slate-500 shrink-0" />
          <span>{label || "Information"}</span>
        </span>
      );
  }
}
