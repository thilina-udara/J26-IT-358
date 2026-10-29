import React from "react";
import { TrendingUp, Coins, ShieldCheck } from "lucide-react";

export interface OverviewCardProps {
  id: "demand" | "price" | "risk";
  title: string;
  subtitle?: string;
  description: string;
  badgeText?: string;
  badgeType?: "pending" | "ready";
  points?: string[];
  notice?: string;
  actionText?: string;
  actionHref?: string;
  onActionClick?: () => void;
}

export function OverviewCard({ id, title, description }: OverviewCardProps) {
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

  return (
    <div className="flex flex-col justify-start rounded-2xl bg-gradient-to-b from-white via-white to-[#F7F5ED]/70 p-6 border border-slate-200/90 shadow-2xs hover:border-[#22A06B]/50 hover:shadow-xs transition-all duration-200 group">
      <div className="flex items-center gap-3.5 mb-3.5">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#E7F5EB] border border-[#22A06B]/30 text-[#166534] group-hover:scale-105 transition-transform shadow-2xs shrink-0">
          {getIcon()}
        </div>
        <h3 className="text-xl font-extrabold text-slate-900 tracking-tight group-hover:text-[#166534] transition-colors">
          {title}
        </h3>
      </div>
      <p className="text-sm text-[#334155] leading-relaxed font-normal">
        {description}
      </p>
    </div>
  );
}
