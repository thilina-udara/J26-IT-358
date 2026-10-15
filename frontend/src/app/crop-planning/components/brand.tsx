import Link from "next/link";
import { Sprout } from "lucide-react";

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <Link href="/crop-planning" className={`cp-brand ${light ? "cp-brand-light" : ""}`} aria-label="AgroDecision AI home">
      <span
        style={{
          width: "40px",
          height: "40px",
          borderRadius: "12px",
          background: "#15803d",
          color: "#ffffff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 4px 10px rgba(21, 128, 61, 0.25)",
          flexShrink: 0,
        }}
      >
        <Sprout size={24} strokeWidth={2.2} aria-hidden="true" />
      </span>
      <span className="cp-brand-text">
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "18px",
            fontWeight: 800,
            color: light ? "#ffffff" : "#14532d",
            letterSpacing: "-0.4px",
          }}
        >
          AgroDecision
          <span
            style={{
              fontSize: "10px",
              fontWeight: 800,
              padding: "1px 5px",
              borderRadius: "4px",
              backgroundColor: "#dcfce7",
              color: "#166534",
            }}
          >
            AI
          </span>
        </span>
        <span
          style={{
            fontSize: "11px",
            color: light ? "rgba(255,255,255,0.7)" : "#64748b",
            fontWeight: 500,
            letterSpacing: "normal",
            display: "block",
            marginTop: "1px",
          }}
        >
          Your Farming Partner
        </span>
      </span>
    </Link>
  );
}
