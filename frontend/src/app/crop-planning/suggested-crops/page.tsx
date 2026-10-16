"use client";

import React, { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Database,
  FileCheck,
  FileText,
  FlaskConical,
  HelpCircle,
  Info,
  Layers,
  Leaf,
  Lock,
  MapPin,
  Plus,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sprout,
  X,
} from "lucide-react";
import { useSession } from "../components/session";
import { useLoad } from "../components/ui";
import { formatDate } from "../lib/dates";
import type { Plan, Workflow } from "../lib/contracts";

export default function SuggestedCropsPage() {
  const { api } = useSession();
  const [selectedPlanId, setSelectedPlanId] = useState<string>("");
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [workflowReport, setWorkflowReport] = useState<Workflow | null>(null);

  // Fetch farmer's saved plans from the backend
  const plansResult = useLoad(
    (signal) => api.list(new URLSearchParams({ limit: "20", status: "active" }), signal),
    [api]
  );

  const savedPlans: Plan[] = useMemo(() => plansResult.data?.items ?? [], [plansResult.data?.items]);

  useEffect(() => {
    if (savedPlans.length > 0 && (!selectedPlanId || !savedPlans.some((p) => p.plan_id === selectedPlanId))) {
      setSelectedPlanId(savedPlans[0].plan_id);
    }
  }, [savedPlans, selectedPlanId]);

  const activePlan = useMemo(() => {
    return savedPlans.find((p) => p.plan_id === selectedPlanId) || null;
  }, [savedPlans, selectedPlanId]);

  useEffect(() => {
    if (!activePlan) {
      setWorkflowReport(null);
      return;
    }
    let cancelled = false;
    setAnalyzing(true);
    setAnalysisError(null);

    api
      .analyze(activePlan.plan_id, activePlan.farmer_declared_season || undefined)
      .then((report) => {
        if (!cancelled) setWorkflowReport(report);
      })
      .catch((err) => {
        if (!cancelled) {
          setAnalysisError(err?.message || "Failed to retrieve workflow report from backend");
          setWorkflowReport(null);
        }
      })
      .finally(() => {
        if (!cancelled) setAnalyzing(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activePlan, api]);

  const cropImage = useMemo(() => {
    if (!activePlan) return "/images/component2_planning.jpg";
    const c = (activePlan.crop || "").toLowerCase();
    if (c.includes("bandakka") || c.includes("okra")) return "/images/crop_okra_detail.jpg";
    if (c.includes("brinjal") || c.includes("eggplant")) return "/images/crop_brinjal_detail.jpg";
    if (c.includes("pumpkin")) return "/images/crop_pumpkin_detail.jpg";
    if (c.includes("corn") || c.includes("maize")) return "/images/crop_corn_detail.jpg";
    if (c.includes("mung")) return "/images/crop_mungbean_detail.jpg";
    if (c.includes("chilli") || c.includes("chili")) return "/images/crop_chili_detail.jpg";
    return "/images/component2_planning.jpg";
  }, [activePlan]);

  const recommendations = workflowReport?.recommendations;
  const alternatives = (recommendations as any)?.alternatives || [];
  const hasAlternatives = alternatives.length > 0;

  return (
    <div style={{ maxWidth: "1320px", margin: "0 auto", color: "#0f172a" }}>
      {/* 1. Header Banner */}
      <section
        style={{
          borderRadius: "24px",
          overflow: "hidden",
          position: "relative",
          marginBottom: "24px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.03)",
          background: "linear-gradient(90deg, #f7faf5 0%, #edf5e8 50%, #e1efd8 100%)",
          display: "flex",
          alignItems: "center",
          minHeight: "130px",
          padding: "24px 32px",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0.3,
            zIndex: 0,
            pointerEvents: "none",
          }}
        >
          <img
            src="/images/dashboard_banner_landscape.jpg"
            alt="Agricultural landscape"
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>

        <div
          style={{
            position: "relative",
            zIndex: 1,
            display: "flex",
            alignItems: "center",
            gap: "20px",
            flex: 1,
          }}
        >
          <div
            style={{
              width: "52px",
              height: "52px",
              borderRadius: "16px",
              background: "#eaf5ea",
              color: "#15803d",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              boxShadow: "0 2px 8px rgba(21, 128, 61, 0.12)",
            }}
          >
            <Sprout size={28} />
          </div>

          <div>
            <h1
              style={{
                fontSize: "26px",
                fontWeight: 800,
                color: "#0f172a",
                margin: "0 0 4px 0",
                letterSpacing: "-0.5px",
              }}
            >
              Suggested Crop Alternatives
            </h1>
            <p style={{ fontSize: "13.5px", color: "#475569", margin: 0, lineHeight: 1.5 }}>
              Evidence-based alternative crop recommendations protected by scientific and agronomic approval gates.
            </p>
          </div>
        </div>

        <Link
          href="/crop-planning/research-demo"
          style={{
            position: "relative",
            zIndex: 1,
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            background: "rgba(255, 255, 255, 0.95)",
            backdropFilter: "blur(6px)",
            padding: "10px 16px",
            borderRadius: "14px",
            border: "1px solid #cbd5e1",
            color: "#0f172a",
            fontSize: "12.5px",
            fontWeight: 700,
            textDecoration: "none",
          }}
        >
          <FlaskConical size={16} style={{ color: "#2563eb" }} />
          <span>Research Lab</span>
        </Link>
      </section>

      {/* Plan Selection Card */}
      {savedPlans.length > 0 && activePlan && (
        <section
          style={{
            background: "#ffffff",
            borderRadius: "20px",
            padding: "20px 24px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
            marginBottom: "24px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <div>
              <h2 style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a", margin: "0 0 2px 0" }}>
                Current Cultivation Plan
              </h2>
              <p style={{ fontSize: "12.5px", color: "#64748b", margin: 0 }}>
                Select which registered plan to inspect for alternative recommendation eligibility.
              </p>
            </div>
          </div>

          <div style={{ position: "relative" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 16px",
                borderRadius: "12px",
                border: "1px solid #cbd5e1",
                background: "#f8fafc",
                cursor: "pointer",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontSize: "16px" }}>🌱</span>
                <strong style={{ fontSize: "13.5px", color: "#0f172a" }}>
                  {activePlan.crop} · {activePlan.district} ({activePlan.region}) · {activePlan.land_size_acres} Acres · Planting {formatDate(activePlan.planting_date)}
                </strong>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    padding: "3px 10px",
                    borderRadius: "9999px",
                    background: "#dcfce7",
                    color: "#15803d",
                  }}
                >
                  Selected Plan
                </span>
                <ChevronDown size={16} style={{ color: "#64748b" }} />
              </div>
            </div>

            <select
              value={selectedPlanId}
              onChange={(e) => setSelectedPlanId(e.target.value)}
              style={{
                position: "absolute",
                inset: 0,
                opacity: 0,
                cursor: "pointer",
                width: "100%",
                height: "100%",
              }}
              aria-label="Select saved cultivation plan"
            >
              {savedPlans.map((p) => (
                <option key={p.plan_id} value={p.plan_id}>
                  {p.crop} · {p.district} ({p.region}) · {p.land_size_acres} Acres · {formatDate(p.planting_date)}
                </option>
              ))}
            </select>
          </div>
        </section>
      )}

      {/* Main Content Layout */}
      {savedPlans.length === 0 && !plansResult.loading && (
        <div
          style={{
            background: "#ffffff",
            borderRadius: "20px",
            padding: "48px 32px",
            border: "1px dashed #cbd5e1",
            textAlign: "center",
            color: "#64748b",
          }}
        >
          <Leaf size={44} style={{ margin: "0 auto 14px", color: "#94a3b8" }} />
          <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#1e293b", margin: "0 0 8px 0" }}>
            No Registered Plans to Evaluate
          </h2>
          <p style={{ fontSize: "13.5px", maxWidth: "500px", margin: "0 auto 20px", lineHeight: 1.6 }}>
            Alternative crop recommendations are evaluated only in response to a registered future cultivation plan. Register a plan first or inspect historical distributions in the Research Lab.
          </p>
          <Link
            href="/crop-planning/plans/new"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 18px",
              borderRadius: "12px",
              background: "#15803d",
              color: "#ffffff",
              fontSize: "13.5px",
              fontWeight: 700,
              textDecoration: "none",
            }}
          >
            <Plus size={16} />
            <span>Create Plan</span>
          </Link>
        </div>
      )}

      {activePlan && (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "24px" }}>
          {/* Left Column: Recommendations Status & Gate Verification */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div
              style={{
                background: "#ffffff",
                borderRadius: "22px",
                padding: "26px",
                border: "1px solid #e2e8f0",
                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "18px" }}>
                <h3 style={{ fontSize: "17px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                  Recommendation Status
                </h3>

                {analyzing ? (
                  <span style={{ fontSize: "12px", color: "#64748b", display: "inline-flex", alignItems: "center", gap: "6px" }}>
                    <RefreshCw size={13} className="animate-spin" /> Verifying approval gates...
                  </span>
                ) : (
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      padding: "4px 10px",
                      borderRadius: "9999px",
                      background: hasAlternatives ? "#dcfce7" : "#f1f5f9",
                      color: hasAlternatives ? "#15803d" : "#475569",
                      border: "1px solid #e2e8f0",
                    }}
                  >
                    {hasAlternatives ? "Recommendations Eligible" : "Approval Gates Enforced"}
                  </span>
                )}
              </div>

              {/* Status Message */}
              {!hasAlternatives && (
                <div
                  style={{
                    background: "#f8fafc",
                    border: "1px solid #e2e8f0",
                    borderRadius: "16px",
                    padding: "20px",
                    marginBottom: "20px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                    <ShieldAlert size={20} style={{ color: "#d97706" }} />
                    <strong style={{ fontSize: "15px", color: "#0f172a" }}>
                      Alternative crop recommendations unavailable
                    </strong>
                  </div>

                  <p style={{ fontSize: "13px", color: "#475569", margin: "0 0 12px 0", lineHeight: 1.6 }}>
                    {(recommendations as any)?.explanation ||
                      "No defensible High-risk classification is available for this plan. The system does not fabricate or automatically suggest alternative crops when primary concentration risk is unvalidated."}
                  </p>

                  <div
                    style={{
                      background: "#ffffff",
                      borderRadius: "12px",
                      padding: "12px 16px",
                      border: "1px solid #e2e8f0",
                      fontSize: "12px",
                      color: "#334155",
                      lineHeight: 1.5,
                    }}
                  >
                    <strong>Governance Rule:</strong> Recommending crop switches without verified regional oversupply evidence risks causing secondary crop gluts and misleading farmers.
                  </div>
                </div>
              )}

              {hasAlternatives && (
                <div
                  style={{
                    background: "#f0fdf4",
                    border: "1px solid #bbf7d0",
                    borderRadius: "16px",
                    padding: "20px",
                    marginBottom: "20px",
                  }}
                >
                  <div style={{ marginBottom: "14px" }}>
                    <strong style={{ fontSize: "15px", color: "#166534", display: "block" }}>
                      3 low-risk alternative crops
                    </strong>
                    <p style={{ fontSize: "13px", color: "#365314", margin: "6px 0 0", lineHeight: 1.5 }}>
                      These options passed the available lower-supply proxy and suitability checks for this High-risk
                      assessment. Review the evidence before changing your plan.
                    </p>
                  </div>
                  <div style={{ display: "grid", gap: "10px" }}>
                    {alternatives.slice(0, 3).map((alternative: any, index: number) => (
                      <div
                        key={`${alternative.crop}-${index}`}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "12px",
                          background: "#ffffff",
                          border: "1px solid #dcfce7",
                          borderRadius: "12px",
                          padding: "12px 14px",
                        }}
                      >
                        <div>
                          <strong style={{ color: "#14532d", fontSize: "14px" }}>{alternative.crop}</strong>
                          <small style={{ display: "block", color: "#64748b", fontSize: "11.5px", marginTop: "3px" }}>
                            Evidence-gated experimental alternative
                          </small>
                        </div>
                        <span
                          style={{
                            color: "#15803d",
                            background: "#dcfce7",
                            borderRadius: "9999px",
                            padding: "4px 9px",
                            fontSize: "11px",
                            fontWeight: 700,
                          }}
                        >
                          Low proxy
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Four Mandatory Approval Gates Checklist */}
              <div>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a", margin: "0 0 12px 0" }}>
                  Required Scientific & Agricultural Approval Gates:
                </h4>

                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "12px",
                      padding: "12px 14px",
                      borderRadius: "12px",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0",
                    }}
                  >
                    <div
                      style={{
                        width: "22px",
                        height: "22px",
                        borderRadius: "50%",
                        background: "#fee2e2",
                        color: "#dc2626",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        fontSize: "11px",
                        fontWeight: 700,
                      }}
                    >
                      ✕
                    </div>
                    <div>
                      <strong style={{ fontSize: "13px", color: "#0f172a", display: "block" }}>
                        1. Defensible High-Risk Concentration Gate
                      </strong>
                      <small style={{ fontSize: "11.5px", color: "#64748b", lineHeight: 1.4, display: "block" }}>
                        Requires independently verified current classification evidence. Protected peer statistics do not establish zero peers or validate risk.
                      </small>
                    </div>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "12px",
                      padding: "12px 14px",
                      borderRadius: "12px",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0",
                    }}
                  >
                    <div
                      style={{
                        width: "22px",
                        height: "22px",
                        borderRadius: "50%",
                        background: "#fef3c7",
                        color: "#d97706",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        fontSize: "11px",
                        fontWeight: 700,
                      }}
                    >
                      !
                    </div>
                    <div>
                      <strong style={{ fontSize: "13px", color: "#0f172a", display: "block" }}>
                        2. Agro-Ecological Suitability Clearance
                      </strong>
                      <small style={{ fontSize: "11.5px", color: "#64748b", lineHeight: 1.4, display: "block" }}>
                        Requires Department of Agriculture soil and climate compatibility clearance for {activePlan.district}.
                      </small>
                    </div>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "12px",
                      padding: "12px 14px",
                      borderRadius: "12px",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0",
                    }}
                  >
                    <div
                      style={{
                        width: "22px",
                        height: "22px",
                        borderRadius: "50%",
                        background: "#fef3c7",
                        color: "#d97706",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        fontSize: "11px",
                        fontWeight: 700,
                      }}
                    >
                      !
                    </div>
                    <div>
                      <strong style={{ fontSize: "13px", color: "#0f172a", display: "block" }}>
                        3. Comparable Seasonal Window Coverage
                      </strong>
                      <small style={{ fontSize: "11.5px", color: "#64748b", lineHeight: 1.4, display: "block" }}>
                        Candidate must match harvest timeline ({formatDate(activePlan.expected_harvest_date)}) without generating new local spikes.
                      </small>
                    </div>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "12px",
                      padding: "12px 14px",
                      borderRadius: "12px",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0",
                    }}
                  >
                    <div
                      style={{
                        width: "22px",
                        height: "22px",
                        borderRadius: "50%",
                        background: "#dcfce7",
                        color: "#15803d",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        fontSize: "11px",
                        fontWeight: 700,
                      }}
                    >
                      ✔
                    </div>
                    <div>
                      <strong style={{ fontSize: "13px", color: "#0f172a", display: "block" }}>
                        4. Agricultural Practice Guidelines
                      </strong>
                      <small style={{ fontSize: "11.5px", color: "#64748b", lineHeight: 1.4, display: "block" }}>
                        Only applicable backend-approved activities can be shown. A complete approved schedule is not established.
                      </small>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Selected Plan Card & Research Lab Redirection */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div
              style={{
                background: "#ffffff",
                borderRadius: "22px",
                padding: "24px",
                border: "1px solid #e2e8f0",
                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
              }}
            >
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a", margin: "0 0 14px 0" }}>
                Selected Plan Details
              </h3>

              <div
                style={{
                  width: "100%",
                  height: "150px",
                  borderRadius: "14px",
                  overflow: "hidden",
                  marginBottom: "14px",
                  border: "1px solid #f1f5f9",
                }}
              >
                <img
                  src={cropImage}
                  alt={`${activePlan.crop} crop detail`}
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = "/images/component2_planning.jpg";
                  }}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              </div>

              <div style={{ display: "flex", flexDirection: "column", fontSize: "13px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f8fafc" }}>
                  <span style={{ color: "#64748b" }}>Crop:</span>
                  <strong style={{ color: "#0f172a" }}>{activePlan.crop}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f8fafc" }}>
                  <span style={{ color: "#64748b" }}>District:</span>
                  <strong style={{ color: "#0f172a" }}>{activePlan.district}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f8fafc" }}>
                  <span style={{ color: "#64748b" }}>Land Size:</span>
                  <strong style={{ color: "#0f172a" }}>{activePlan.land_size_acres} Acres</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0" }}>
                  <span style={{ color: "#64748b" }}>Expected Harvest:</span>
                  <strong style={{ color: "#0f172a" }}>{formatDate(activePlan.expected_harvest_date)}</strong>
                </div>
              </div>
            </div>

            {/* Research Lab Card */}
            <div
              style={{
                background: "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)",
                borderRadius: "22px",
                padding: "24px",
                border: "1px solid #cbd5e1",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                <FlaskConical size={20} style={{ color: "#2563eb" }} />
                <h4 style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a", margin: 0 }}>
                  Historical Cohort Diagnostics
                </h4>
              </div>

              <p style={{ fontSize: "12.5px", color: "#475569", margin: "0 0 16px 0", lineHeight: 1.55 }}>
                Want to observe how alternative crops were distributed during historical 2025 and 2026 windows? Use the isolated Research Lab to inspect diagnostic crop cohorts without bypassing farmer safety gates.
              </p>

              <Link
                href="/crop-planning/research-demo"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "10px 16px",
                  borderRadius: "10px",
                  background: "#2563eb",
                  color: "#ffffff",
                  fontSize: "12.5px",
                  fontWeight: 700,
                  textDecoration: "none",
                }}
              >
                <span>Open Research Diagnostics</span>
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
