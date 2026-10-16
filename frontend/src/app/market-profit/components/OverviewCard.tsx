import React from "react";
import { TrendingUp, Coins, ShieldCheck, Info, Clock, Check } from "lucide-react";

export interface OverviewCardProps {
  id: "demand" | "price" | "risk";
  title: string;
  subtitle: string;
  description: string;
  badgeText: string;
  badgeType: "pending" | "ready";
  points: string[];
  notice: string;
}

export function OverviewCard({
  id,
  title,
  subtitle,
  description,
  badgeText,
  badgeType,
  points,
  notice,
}: OverviewCardProps) {
  const getIcon = () => {
    switch (id) {
      case "demand":
        return <TrendingUp className="h-6 w-6 text-[#15803d]" />;
      case "price":
        return <Coins className="h-6 w-6 text-[#15803d]" />;
      case "risk":
        return <ShieldCheck className="h-6 w-6 text-[#15803d]" />;
    }
  };

  return (
    <div className="flex flex-col justify-between rounded-2xl bg-white p-6 sm:p-7 border border-slate-200/90 shadow-xs hover:shadow-md transition-shadow">
      <div>
        {/* Top Icon & Status */}
        <div className="flex items-center justify-between gap-3 mb-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#dcfce7] border border-emerald-100/80">
            {getIcon()}
          </div>
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
              badgeType === "ready"
                ? "bg-emerald-50 text-[#166534] border border-emerald-200"
                : "bg-amber-50 text-amber-800 border border-amber-200/70"
            }`}
          >
            {badgeType === "ready" ? (
              <Check className="h-3.5 w-3.5 text-[#15803d]" />
            ) : (
              <Clock className="h-3.5 w-3.5 text-amber-600" />
            )}
            <span>{badgeText}</span>
          </span>
        </div>

        {/* Title & Subtitle */}
        <div className="mb-3">
          <h3 className="text-xl font-bold text-slate-900 tracking-tight">
            {title}
          </h3>
          <p className="text-sm font-medium text-[#15803d] mt-0.5">
            {subtitle}
          </p>
        </div>

        {/* Friendly Description */}
        <p className="text-sm text-slate-600 leading-relaxed mb-5">
          {description}
        </p>

        {/* Key Feature Points */}
        <ul className="space-y-2 mb-6">
          {points.map((pt, idx) => (
            <li key={idx} className="flex items-center gap-2 text-xs text-slate-600">
              <span className="h-1.5 w-1.5 rounded-full bg-[#15803d] shrink-0" />
              <span>{pt}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Helpful Transparent Note */}
      <div
        className={`rounded-xl p-3.5 text-xs border ${
          badgeType === "ready"
            ? "bg-emerald-50/60 border-emerald-200/80 text-emerald-950"
            : "bg-amber-50/60 border-amber-200/80 text-amber-950"
        }`}
      >
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 shrink-0 mt-0.5 text-slate-500" />
          <p className="leading-relaxed">{notice}</p>
        </div>
      </div>
    </div>
  );
}
