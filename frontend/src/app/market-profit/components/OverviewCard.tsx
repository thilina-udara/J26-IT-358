import React from "react";
import { TrendingUp, Coins, ShieldCheck, Clock, CheckCircle2 } from "lucide-react";

export interface OverviewCardProps {
  id: "demand" | "price" | "risk";
  title: string;
  subtitle: string;
  description: string;
  badgeText: string;
  badgeType: "pending" | "ready";
  points?: string[];
  notice?: string;
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
        return <TrendingUp className="h-6 w-6 text-[#166534]" />;
      case "price":
        return <Coins className="h-6 w-6 text-[#166534]" />;
      case "risk":
        return <ShieldCheck className="h-6 w-6 text-[#166534]" />;
    }
  };

  const isReady = badgeType === "ready";

  return (
    <div className="flex flex-col justify-between rounded-2xl bg-gradient-to-b from-white via-white to-[#F7F5ED]/70 p-6 border border-slate-200/90 shadow-2xs hover:border-[#22A06B]/60 hover:shadow-md transition-all duration-200 group">
      <div>
        {/* Top Icon & Readiness Badge */}
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] group-hover:scale-105 transition-transform shadow-2xs">
            {getIcon()}
          </div>
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold tracking-wide shadow-2xs ${
              isReady
                ? "bg-[#E7F5EB] text-[#166534] border border-[#22A06B]/30"
                : "bg-amber-50 text-amber-900 border border-amber-200"
            }`}
          >
            {isReady ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-[#166534]" />
            ) : (
              <Clock className="h-3.5 w-3.5 text-amber-700" />
            )}
            <span>{badgeText}</span>
          </span>
        </div>

        {/* Title & Subtitle */}
        <div className="mb-2.5">
          <h3 className="text-xl font-extrabold text-slate-900 tracking-tight group-hover:text-[#166534] transition-colors">
            {title}
          </h3>
          <p className="text-xs sm:text-sm font-bold text-[#166534] mt-0.5">
            {subtitle}
          </p>
        </div>

        {/* Friendly Farmer Description */}
        <p className="text-sm sm:text-[14.5px] text-[#334155] leading-relaxed mb-4 font-normal">
          {description}
        </p>

        {/* Optional Compact Highlights */}
        {points && points.length > 0 && (
          <ul className="space-y-2 mb-4">
            {points.map((pt, idx) => (
              <li key={idx} className="flex items-start gap-2 text-xs sm:text-sm text-[#334155]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#22A06B] shrink-0 mt-2" />
                <span className="leading-snug font-medium">{pt}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Compact Status Note */}
      {notice && (
        <div
          className={`rounded-xl px-3.5 py-2.5 text-xs border ${
            isReady
              ? "bg-[#E7F5EB]/70 border-[#22A06B]/30 text-[#166534]"
              : "bg-amber-50/70 border-amber-200/80 text-amber-900"
          }`}
        >
          <p className="leading-relaxed font-medium">{notice}</p>
        </div>
      )}
    </div>
  );
}
