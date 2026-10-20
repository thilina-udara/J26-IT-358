"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  Flame,
  Leaf,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Thermometer,
  Truck,
  X,
} from "lucide-react";
import { TransportLotItem } from "./product-lot-popup-form";

interface RiskPredictionModalProps {
  isOpen: boolean;
  onClose: () => void;
  predictionData: {
    total_lots: number;
    total_kg: number;
    total_predicted_waste_kg: number;
    overall_waste_pct: number;
    overall_risk_level: string;
    items: TransportLotItem[];
  } | null;
  onConfirmTransport: () => Promise<void>;
  farmerId?: string;
}

export function RiskPredictionModal({
  isOpen,
  onClose,
  predictionData,
  onConfirmTransport,
  farmerId = "farmer_kamal",
}: RiskPredictionModalProps) {
  const [confirming, setConfirming] = useState(false);
  const [confirmedSuccess, setConfirmedSuccess] = useState(false);

  if (!isOpen || !predictionData) return null;

  const {
    total_lots,
    total_kg,
    total_predicted_waste_kg,
    overall_waste_pct,
    overall_risk_level,
    items,
  } = predictionData;

  const isHigh = overall_risk_level.toUpperCase() === "HIGH";
  const isMedium = overall_risk_level.toUpperCase() === "MEDIUM";

  const tierBg = isHigh ? "#fef2f2" : isMedium ? "#fffbeb" : "#f0fdf4";
  const tierColor = isHigh ? "#b91c1c" : isMedium ? "#b45309" : "#15803d";
  const tierBorder = isHigh ? "#fca5a5" : isMedium ? "#fde68a" : "#86efac";

  async function handleConfirm() {
    setConfirming(true);
    try {
      await onConfirmTransport();
      setConfirmedSuccess(true);
      setTimeout(() => {
        setConfirmedSuccess(false);
        onClose();
      }, 2500);
    } finally {
      setConfirming(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(15, 23, 42, 0.75)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !confirming) onClose();
      }}
    >
      <div
        style={{
          background: "#ffffff",
          borderRadius: "24px",
          width: "100%",
          maxWidth: "880px",
          maxHeight: "92vh",
          boxShadow: "0 25px 50px -12px rgba(0,0,0,0.3)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          border: "1px solid #e2e8f0",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 28px",
            borderBottom: "1px solid #e2e8f0",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "14px",
                background: "linear-gradient(135deg, #16a34a 0%, #15803d 100%)",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 12px rgba(22, 163, 74, 0.25)",
              }}
            >
              <Cpu size={22} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h3 style={{ fontSize: "18px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                  XGBoost Spoilage Risk Assessment
                </h3>
                <span
                  style={{
                    background: tierBg,
                    color: tierColor,
                    border: `1px solid ${tierBorder}`,
                    fontSize: "11px",
                    fontWeight: 800,
                    padding: "2px 8px",
                    borderRadius: "9999px",
                  }}
                >
                  {overall_risk_level.toUpperCase()} RISK TIER
                </span>
              </div>
              <p style={{ fontSize: "12.5px", color: "#64748b", margin: "2px 0 0 0" }}>
                Dual-Stream Fresh Mass vs Bioeconomy Cull Partitioning (Port 8003 ML Engine)
              </p>
            </div>
          </div>
          <button
            type="button"
            disabled={confirming}
            onClick={onClose}
            style={{
              background: "#f1f5f9",
              border: "none",
              borderRadius: "10px",
              width: "36px",
              height: "36px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              color: "#64748b",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Scrollable Content */}
        <div style={{ padding: "24px 28px", overflowY: "auto", flex: 1 }}>
          {confirmedSuccess ? (
            <div
              style={{
                textAlign: "center",
                padding: "48px 24px",
                background: "#f0fdf4",
                borderRadius: "20px",
                border: "1px solid #86efac",
              }}
            >
              <div
                style={{
                  width: "64px",
                  height: "64px",
                  borderRadius: "20px",
                  background: "#16a34a",
                  color: "#ffffff",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "16px",
                }}
              >
                <CheckCircle2 size={36} />
              </div>
              <h4 style={{ fontSize: "20px", fontWeight: 800, color: "#166534", margin: "0 0 8px 0" }}>
                Transport Batch Confirmed & Locked!
              </h4>
              <p style={{ fontSize: "14px", color: "#475569", maxWidth: "480px", margin: "0 auto" }}>
                Your produce consignment has been saved with status <strong style={{ color: "#15803d" }}>Ready for Transport</strong>.
                Crate barcodes are permanently assigned and telemetry risk indices recorded in the bioeconomy database.
              </p>
            </div>
          ) : (
            <div>
              {/* Top Metrics Row */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: "14px",
                  marginBottom: "24px",
                }}
              >
                <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "16px", border: "1px solid #e2e8f0" }}>
                  <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600, display: "block" }}>
                    Total Gross Payload
                  </span>
                  <strong style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a" }}>
                    {total_kg.toLocaleString()} kg
                  </strong>
                  <small style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginTop: "2px" }}>
                    Across {total_lots} crate lot{total_lots > 1 ? "s" : ""}
                  </small>
                </div>

                <div style={{ background: tierBg, padding: "16px", borderRadius: "16px", border: `1px solid ${tierBorder}` }}>
                  <span style={{ fontSize: "12px", color: tierColor, fontWeight: 700, display: "block" }}>
                    Projected Spoilage Loss (ŷ)
                  </span>
                  <strong style={{ fontSize: "22px", fontWeight: 800, color: tierColor }}>
                    {overall_waste_pct.toFixed(2)}%
                  </strong>
                  <small style={{ fontSize: "11px", color: tierColor, display: "block", marginTop: "2px" }}>
                    XGBoost v3.4.1 Inference
                  </small>
                </div>

                <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "16px", border: "1px solid #e2e8f0" }}>
                  <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600, display: "block" }}>
                    Estimated Cull Waste Mass
                  </span>
                  <strong style={{ fontSize: "22px", fontWeight: 800, color: "#dc2626" }}>
                    {total_predicted_waste_kg.toLocaleString()} kg
                  </strong>
                  <small style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginTop: "2px" }}>
                    Diverted to circular bioeconomy
                  </small>
                </div>

                <div style={{ background: "#f0fdf4", padding: "16px", borderRadius: "16px", border: "1px solid #bbf7d0" }}>
                  <span style={{ fontSize: "12px", color: "#166534", fontWeight: 700, display: "block" }}>
                    Commercial Fresh Produce
                  </span>
                  <strong style={{ fontSize: "22px", fontWeight: 800, color: "#15803d" }}>
                    {(total_kg - total_predicted_waste_kg).toLocaleString()} kg
                  </strong>
                  <small style={{ fontSize: "11px", color: "#166534", display: "block", marginTop: "2px" }}>
                    Viable wholesale yield
                  </small>
                </div>
              </div>

              {/* Per-Lot Breakdown Cards */}
              <h4 style={{ fontSize: "15px", fontWeight: 800, color: "#0f172a", margin: "0 0 12px 0" }}>
                Produce Lots Risk Partitioning & Safety Instructions
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "20px" }}>
                {items.map((item, idx) => {
                  const itemHigh = item.risk_level?.toUpperCase() === "HIGH";
                  const itemColor = itemHigh ? "#b91c1c" : item.risk_level === "MEDIUM" ? "#b45309" : "#15803d";
                  const itemBg = itemHigh ? "#fef2f2" : item.risk_level === "MEDIUM" ? "#fffbeb" : "#f0fdf4";

                  return (
                    <div
                      key={item.id || idx}
                      style={{
                        background: "#ffffff",
                        borderRadius: "18px",
                        border: "1px solid #e2e8f0",
                        padding: "18px 20px",
                        boxShadow: "0 2px 6px rgba(0,0,0,0.02)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          flexWrap: "wrap",
                          gap: "10px",
                          marginBottom: "12px",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <span style={{ fontSize: "20px" }}>
                            {item.crop_category === "Fruit" ? "🍌" : "🍅"}
                          </span>
                          <div>
                            <strong style={{ fontSize: "14px", color: "#0f172a" }}>
                              {item.food_name} — {item.kg} kg
                            </strong>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "2px" }}>
                              <span style={{ fontFamily: "monospace", fontSize: "11px", color: "#64748b", fontWeight: 700 }}>
                                Barcode: {item.barcode_no}
                              </span>
                              <span style={{ fontSize: "11px", color: "#94a3b8" }}>•</span>
                              <span style={{ fontSize: "11.5px", color: "#475569" }}>
                                {item.origin_district} ➔ {item.destination_center.split(" ")[0]} DEC
                              </span>
                            </div>
                          </div>
                        </div>

                        <div style={{ textAlign: "right" }}>
                          <span
                            style={{
                              background: itemBg,
                              color: itemColor,
                              fontSize: "11px",
                              fontWeight: 800,
                              padding: "3px 10px",
                              borderRadius: "9999px",
                              display: "inline-block",
                            }}
                          >
                            {item.risk_level || "EVALUATED"} • {item.predicted_waste_pct?.toFixed(2)}% LOSS
                          </span>
                          <span style={{ fontSize: "12px", color: "#64748b", display: "block", marginTop: "2px" }}>
                            Cull Mass: <strong style={{ color: "#dc2626" }}>{item.predicted_waste_kg} kg</strong>
                          </span>
                        </div>
                      </div>

                      {/* Bioeconomy Dual Stream Details */}
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: "10px",
                          background: "#f8fafc",
                          padding: "12px 14px",
                          borderRadius: "12px",
                          fontSize: "12px",
                          marginBottom: "12px",
                        }}
                      >
                        <div>
                          <span style={{ color: "#166534", fontWeight: 700, display: "block" }}>
                            🟢 Stream 1 (Commercial Human Food)
                          </span>
                          <span style={{ color: "#334155" }}>
                            <strong>{item.stream_1_fresh_kg ?? (item.kg - (item.predicted_waste_kg || 0)).toFixed(1)} kg</strong> (Grade A/B Wholesale Allocation)
                          </span>
                        </div>
                        <div>
                          <span style={{ color: "#b45309", fontWeight: 700, display: "block" }}>
                            🟡 Stream 2 (Circular Bioeconomy Feedstock)
                          </span>
                          <span style={{ color: "#334155" }}>
                            <strong>{item.stream_2_waste_kg ?? item.predicted_waste_kg} kg</strong> ➔ {item.bioeconomy_destination?.replace(/_/g, " ") || "AEROBIC COMPOSTING"}
                          </span>
                        </div>
                      </div>

                      {/* Tailored Advice Checklist */}
                      {item.advice && item.advice.length > 0 && (
                        <div>
                          <span style={{ fontSize: "11.5px", fontWeight: 700, color: "#334155", display: "block", marginBottom: "6px" }}>
                            Recommended Agronomic & Transport Mitigations:
                          </span>
                          <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "#475569", lineHeight: 1.5 }}>
                            {item.advice.map((adv, aIdx) => (
                              <li key={aIdx} style={{ marginBottom: "4px" }}>
                                {adv}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div
          style={{
            padding: "16px 28px",
            borderTop: "1px solid #e2e8f0",
            background: "#f8fafc",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <button
            type="button"
            disabled={confirming}
            onClick={onClose}
            style={{
              background: "#ffffff",
              border: "1px solid #cbd5e1",
              borderRadius: "12px",
              padding: "10px 18px",
              fontSize: "13.5px",
              fontWeight: 600,
              color: "#475569",
              cursor: "pointer",
            }}
          >
            Back to Transport List
          </button>

          {!confirmedSuccess && (
            <button
              type="button"
              disabled={confirming}
              onClick={handleConfirm}
              style={{
                background: "linear-gradient(135deg, #16a34a 0%, #15803d 100%)",
                border: "none",
                borderRadius: "12px",
                padding: "11px 26px",
                fontSize: "14px",
                fontWeight: 800,
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                cursor: confirming ? "wait" : "pointer",
                boxShadow: "0 4px 14px rgba(22, 163, 74, 0.3)",
              }}
            >
              {confirming ? <RefreshCw size={18} className="animate-spin" /> : <ShieldCheck size={18} />}
              <span>{confirming ? "Confirming Dispatch..." : "Confirm & Save Transport (Ready)"}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
