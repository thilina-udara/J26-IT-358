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
  Edit,
  FileText,
  FlaskConical,
  HelpCircle,
  Info,
  Layers,
  Leaf,
  Lightbulb,
  LockKeyhole,
  MapPin,
  Plus,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sprout,
  Users,
  X,
} from "lucide-react";
import { useSession } from "../components/session";
import { useLoad } from "../components/ui";
import { formatDate } from "../lib/dates";
import type { Plan, ProductionConcentrationIndicator, Workflow } from "../lib/contracts";

export default function RiskAnalysisPage() {
  const { api, session } = useSession();
  const [selectedPlanId, setSelectedPlanId] = useState<string>("");
  const [showDetailedEvidence, setShowDetailedEvidence] = useState<boolean>(false);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [workflowReport, setWorkflowReport] = useState<Workflow | null>(null);
  const [productionIndicator, setProductionIndicator] = useState<ProductionConcentrationIndicator | null>(null);

  // Fetch farmer's saved plans from the live backend
  const plansResult = useLoad(
    (signal) => api.list(new URLSearchParams({ limit: "20", status: "active" }), signal),
    [api]
  );

  const savedPlans: Plan[] = useMemo(() => plansResult.data?.items ?? [], [plansResult.data?.items]);
  const [directPlan, setDirectPlan] = useState<Plan | null>(null);

  // Read plan_id from URL query string on client
  useEffect(() => {
    if (typeof window !== "undefined") {
      const q = new URLSearchParams(window.location.search).get("plan_id");
      if (q) {
        setSelectedPlanId(q);
      }
    }
  }, []);

  // If selectedPlanId is provided but not yet in savedPlans, fetch it directly
  useEffect(() => {
    if (!selectedPlanId) return;
    if (savedPlans.some((p) => p.plan_id === selectedPlanId)) {
      setDirectPlan(null);
      return;
    }
    let cancelled = false;
    api
      .read(selectedPlanId)
      .then((res) => {
        if (!cancelled && res?.plan) {
          setDirectPlan(res.plan);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [selectedPlanId, savedPlans, api]);

  // Combined list of plans for selection
  const allAvailablePlans: Plan[] = useMemo(() => {
    if (directPlan && !savedPlans.some((p) => p.plan_id === directPlan.plan_id)) {
      return [directPlan, ...savedPlans];
    }
    return savedPlans;
  }, [savedPlans, directPlan]);

  // Automatically select the first plan if none selected
  useEffect(() => {
    if (allAvailablePlans.length > 0 && (!selectedPlanId || !allAvailablePlans.some((p) => p.plan_id === selectedPlanId))) {
      setSelectedPlanId(allAvailablePlans[0].plan_id);
    }
  }, [allAvailablePlans, selectedPlanId]);

  // Current active plan
  const activePlan = useMemo(() => {
    return allAvailablePlans.find((p) => p.plan_id === selectedPlanId) || null;
  }, [allAvailablePlans, selectedPlanId]);

  // Fetch backend analysis for the selected active plan
  useEffect(() => {
    if (!activePlan) {
      setWorkflowReport(null);
      setProductionIndicator(null);
      return;
    }
    let cancelled = false;
    setAnalyzing(true);
    setAnalysisError(null);

    api
      .analyze(activePlan.plan_id, activePlan.farmer_declared_season || undefined)
      .then((report) => {
        if (!cancelled) {
          setWorkflowReport(report);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setAnalysisError(err?.message || "Failed to retrieve analysis report from backend");
          setWorkflowReport(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setAnalyzing(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activePlan, api]);

  useEffect(() => {
    if (!activePlan) {
      setProductionIndicator(null);
      return;
    }
    let cancelled = false;
    api.productionConcentrationIndicator(activePlan.plan_id)
      .then((result) => {
        if (!cancelled) setProductionIndicator(result);
      })
      .catch((err) => {
        if (!cancelled) {
          const status = err?.status;
          const reason = status === 404
            ? "This cultivation plan was not found or is not owned by the logged-in farmer."
            : status === 401
              ? "Your farmer session is not authorized to view this plan."
              : err?.message || "Historical production indicator could not be loaded.";
          setProductionIndicator({
            status: "Insufficient Data",
            reason,
            plan_id: activePlan.plan_id,
            plan_season: activePlan.farmer_declared_season,
            crop: activePlan.crop,
            district: activePlan.district,
            season: activePlan.farmer_declared_season,
            forecast_year: 2026,
            forecast_2026_kg: null,
            selected_forecast_method: null,
            historical_reference_kg: null,
            reference_years: [],
            deviation_percent: null,
            lower_threshold_percent: null,
            upper_threshold_percent: null,
            category: null,
            calibration_sample_count: 0,
            calibration_years: [],
            method_description: "",
            limitations: [],
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activePlan, api]);

  // Crop image selector based on crop
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

  const assessment = workflowReport?.assessment;
  const riskLevel = productionIndicator?.category ?? null;
  const isUnvalidated = productionIndicator?.status !== "available" || !riskLevel;

  // Colours / icons driven by the actual risk level returned by the backend.
  const riskStyle = {
    Low: {
      bg: "#f0fdf4", border: "#bbf7d0", titleColor: "#15803d",
      textColor: "#14532d", badgeBg: "#dcfce7", badgeText: "#15803d",
      icon: <ShieldCheck size={24} style={{ color: "#16a34a" }} />,
    },
    Medium: {
      bg: "#fffbeb", border: "#fde68a", titleColor: "#b45309",
      textColor: "#78350f", badgeBg: "#fef3c7", badgeText: "#92400e",
      icon: <AlertTriangle size={24} style={{ color: "#d97706" }} />,
    },
    High: {
      bg: "#fff1f2", border: "#fecdd3", titleColor: "#be123c",
      textColor: "#881337", badgeBg: "#ffe4e6", badgeText: "#be123c",
      icon: <ShieldAlert size={24} style={{ color: "#e11d48" }} />,
    },
  } as const;
  const currentRiskStyle = riskLevel ? riskStyle[riskLevel as keyof typeof riskStyle] : null;

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
            <BarChart3 size={28} />
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
              Crop Risk Analysis
            </h1>
            <p style={{ fontSize: "13.5px", color: "#475569", margin: 0, lineHeight: 1.5 }}>
              Live backend evaluation of cultivation concentration for your registered future plans.
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
            boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
          }}
        >
          <FlaskConical size={16} style={{ color: "#2563eb" }} />
          <span>Research Lab (2025–2026)</span>
        </Link>
      </section>

      {/* If farmer has no registered plans */}
      {allAvailablePlans.length === 0 && !plansResult.loading && (
        <div
          style={{
            background: "#ffffff",
            borderRadius: "20px",
            padding: "48px 32px",
            border: "1px dashed #cbd5e1",
            textAlign: "center",
            color: "#64748b",
            marginBottom: "24px",
          }}
        >
          <Sprout size={44} style={{ margin: "0 auto 14px", color: "#94a3b8" }} />
          <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#1e293b", margin: "0 0 8px 0" }}>
            No Active Cultivation Plans Found
          </h2>
          <p style={{ fontSize: "13.5px", maxWidth: "520px", margin: "0 auto 24px", lineHeight: 1.6 }}>
            You haven&apos;t registered any upcoming cultivation plans yet. Create an operational future-dated plan to analyze regional concentration risk, or use the Research Lab to test historical 2025 scenarios.
          </p>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "14px" }}>
            <Link
              href="/crop-planning/plans/new"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "11px 20px",
                borderRadius: "12px",
                background: "#15803d",
                color: "#ffffff",
                fontSize: "13.5px",
                fontWeight: 700,
                textDecoration: "none",
              }}
            >
              <Plus size={16} />
              <span>Create Cultivation Plan</span>
            </Link>
            <Link
              href="/crop-planning/research-demo"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "11px 20px",
                borderRadius: "12px",
                background: "#f1f5f9",
                border: "1px solid #cbd5e1",
                color: "#334155",
                fontSize: "13.5px",
                fontWeight: 700,
                textDecoration: "none",
              }}
            >
              <FlaskConical size={16} />
              <span>Open Historical Research Lab</span>
            </Link>
          </div>
        </div>
      )}

      {/* Plan Selector Card */}
      {allAvailablePlans.length > 0 && activePlan && (
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
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "12px",
            }}
          >
            <div>
              <h2 style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a", margin: "0 0 2px 0" }}>
                Select Cultivation Plan
              </h2>
              <p style={{ fontSize: "12.5px", color: "#64748b", margin: 0 }}>
                Choose which of your registered future plans to evaluate.
              </p>
            </div>

            <Link
              href="/crop-planning/plans/new"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "7px 14px",
                borderRadius: "10px",
                border: "1px solid #cbd5e1",
                background: "#ffffff",
                color: "#0f172a",
                fontSize: "12.5px",
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              <Plus size={14} />
              <span>New plan</span>
            </Link>
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
                  Active Plan
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
              {allAvailablePlans.map((p) => (
                <option key={p.plan_id} value={p.plan_id}>
                  {p.crop} · {p.district} ({p.region}) · {p.land_size_acres} Acres · {formatDate(p.planting_date)}
                </option>
              ))}
            </select>
          </div>
        </section>
      )}

      {/* Main Analysis Display Grid */}
      {activePlan && (
        <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: "24px" }}>
          {/* Left Column: Live Backend Risk Status */}
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
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "20px",
                }}
              >
                <h3 style={{ fontSize: "17px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                  Operational Risk Assessment
                </h3>

                {analyzing ? (
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "12px",
                      fontWeight: 600,
                      color: "#64748b",
                    }}
                  >
                    <RefreshCw size={13} className="animate-spin" />
                    Querying backend...
                  </span>
                ) : (
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "11.5px",
                      fontWeight: 700,
                      padding: "4px 12px",
                      borderRadius: "9999px",
                      background: "#f1f5f9",
                      color: "#475569",
                      border: "1px solid #e2e8f0",
                    }}
                  >
                    <CheckCircle2 size={13} style={{ color: "#16a34a" }} />
                    Analysis Computed
                  </span>
                )}
              </div>

              {analysisError && (
                <div
                  style={{
                    background: "#fef2f2",
                    border: "1px solid #fecaca",
                    borderRadius: "14px",
                    padding: "16px",
                    color: "#991b1b",
                    fontSize: "13px",
                    marginBottom: "20px",
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                  }}
                >
                  <AlertCircle size={18} />
                  <span>{analysisError}</span>
                </div>
              )}

              {/* Historical production-based concentration assessment */}
              {isUnvalidated ? (
                <div
                  style={{
                    background: "#fffbeb",
                    border: "1px solid #fef3c7",
                    borderRadius: "18px",
                    padding: "22px",
                    marginBottom: "24px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
                    <div
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "50%",
                        background: "#d97706",
                        color: "#ffffff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <Info size={18} />
                    </div>

                    <div>
                      <strong style={{ fontSize: "17px", fontWeight: 800, color: "#b45309", display: "block" }}>
                        Historical Production-Based Concentration Assessment
                      </strong>
                      <span style={{ fontSize: "11px", fontWeight: 700, color: "#92400e" }}>
                        Risk Level: Not Available
                      </span>
                    </div>
                  </div>

                  <p style={{ fontSize: "13px", color: "#451a03", margin: "10px 0 14px 0", lineHeight: 1.6 }}>
                    Reason: {productionIndicator?.reason || "No matching historical production data is available for this crop, district, and season."}
                  </p>

                  <div
                    style={{
                      background: "#ffffff",
                      borderRadius: "12px",
                      padding: "12px 16px",
                      border: "1px solid #fde68a",
                      fontSize: "12px",
                      color: "#78350f",
                      lineHeight: 1.5,
                    }}
                  >
                    <strong>Scientific Note:</strong> This analysis uses the plan&apos;s declared season and historical district-level production; it does not infer a season from planting month or use registered farmer counts.
                  </div>
                </div>
              ) : (
                <div
                  style={{
                    background: currentRiskStyle?.bg ?? "#f0fdf4",
                    border: `1px solid ${currentRiskStyle?.border ?? "#bbf7d0"}`,
                    borderRadius: "18px",
                    padding: "22px",
                    marginBottom: "24px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
                    {currentRiskStyle?.icon}
                    <div>
                      <strong style={{ fontSize: "18px", fontWeight: 800, color: currentRiskStyle?.titleColor ?? "#15803d", display: "block" }}>
                        Historical Production-Based Concentration Assessment:
                        <span
                          style={{
                            display: "inline-block",
                            marginLeft: "10px",
                            padding: "2px 14px",
                            borderRadius: "9999px",
                            background: currentRiskStyle?.badgeBg,
                            color: currentRiskStyle?.badgeText,
                            fontSize: "14px",
                          }}
                        >
                          {riskLevel}
                        </span>
                      </strong>
                      <span style={{ fontSize: "11px", fontWeight: 600, color: currentRiskStyle?.textColor, opacity: 0.8 }}>
                        Forecast year: {productionIndicator.forecast_year} · Historical calibration
                      </span>
                    </div>
                  </div>
                  <p style={{ fontSize: "13px", color: currentRiskStyle?.textColor ?? "#14532d", margin: "6px 0 0 0", lineHeight: 1.6 }}>
                    Your crop&apos;s predicted production is {productionIndicator.deviation_percent! >= 0 ? "+" : ""}{productionIndicator.deviation_percent!.toFixed(2)}% {productionIndicator.deviation_percent! >= 0 ? "above" : "below"} its historical reference. Based on historical thresholds, its relative cultivation concentration level is {riskLevel}.
                  </p>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(155px, 1fr))", gap: "10px", marginTop: "14px" }}>
                    {[
                      ["Crop / district / season", `${productionIndicator.crop} · ${productionIndicator.district} · ${productionIndicator.season}`],
                      ["Forecast production", `${productionIndicator.forecast_2026_kg!.toLocaleString("en-US")} kg`],
                      ["Historical reference", `${productionIndicator.historical_reference_kg!.toLocaleString("en-US")} kg`],
                      ["Historical thresholds", `${productionIndicator.lower_threshold_percent!.toFixed(2)}% to ${productionIndicator.upper_threshold_percent!.toFixed(2)}%`],
                    ].map(([label, value]) => (
                      <div key={label} style={{ background: "#ffffff", borderRadius: "10px", padding: "10px 12px", border: "1px solid #e2e8f0" }}>
                        <div style={{ fontSize: "11px", color: "#64748b" }}>{label}</div>
                        <strong style={{ fontSize: "13px", color: "#0f172a" }}>{value}</strong>
                      </div>
                    ))}
                  </div>
                  <p style={{ fontSize: "12px", color: currentRiskStyle?.textColor ?? "#14532d", margin: "14px 0 0 0", lineHeight: 1.6 }}>
                    This is a historical production concentration indicator, not a confirmed market oversupply or financial-loss prediction.
                  </p>
                </div>
              )}

              {/* Research Protocol Notice Box */}
              <div
                style={{
                  background: "#f8fafc",
                  borderRadius: "16px",
                  padding: "18px 20px",
                  border: "1px solid #e2e8f0",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                  <FlaskConical size={18} style={{ color: "#2563eb" }} />
                  <strong style={{ fontSize: "13.5px", color: "#0f172a" }}>
                    Need to Test Historical Scenarios?
                  </strong>
                </div>

                <p style={{ fontSize: "12.5px", color: "#475569", margin: "0 0 14px 0", lineHeight: 1.55 }}>
                  Because live operational data contains only recently registered future plans, use our isolated <strong>Historical Research Lab</strong> to evaluate machine learning predictions on 2020–2026 ASC cohorts with historical dates.
                </p>

                <Link
                  href="/crop-planning/research-demo"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "12.5px",
                    fontWeight: 700,
                    color: "#2563eb",
                    textDecoration: "none",
                  }}
                >
                  <span>Open Historical Research Lab (2025–2026)</span>
                  <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          </div>

          {/* Right Column: Cultivation Details & Actions */}
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
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "16px",
                }}
              >
                <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                  Cultivation Plan Details
                </h3>

                <Link
                  href="/crop-planning/plans"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "5px",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "#475569",
                    padding: "4px 10px",
                    borderRadius: "8px",
                    border: "1px solid #e2e8f0",
                    textDecoration: "none",
                  }}
                >
                  <Edit size={12} />
                  <span>Manage</span>
                </Link>
              </div>

              {/* Crop Photo */}
              <div
                style={{
                  width: "100%",
                  height: "160px",
                  borderRadius: "14px",
                  overflow: "hidden",
                  marginBottom: "16px",
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

              {/* Plan Metadata List */}
              <div style={{ display: "flex", flexDirection: "column", fontSize: "13px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f8fafc" }}>
                  <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                    <Leaf size={14} style={{ color: "#16a34a" }} /> Crop
                  </span>
                  <strong style={{ color: "#0f172a" }}>{activePlan.crop}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f8fafc" }}>
                  <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                    <MapPin size={14} style={{ color: "#94a3b8" }} /> Pilot District
                  </span>
                  <strong style={{ color: "#0f172a" }}>{activePlan.district}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f8fafc" }}>
                  <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                    <MapPin size={14} style={{ color: "#94a3b8" }} /> Region / Locality
                  </span>
                  <strong style={{ color: "#0f172a" }}>{activePlan.region}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f8fafc" }}>
                  <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                    <Layers size={14} style={{ color: "#94a3b8" }} /> Land Size
                  </span>
                  <strong style={{ color: "#0f172a" }}>{activePlan.land_size_acres} Acres</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f8fafc" }}>
                  <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                    <Calendar size={14} style={{ color: "#94a3b8" }} /> Planting Date
                  </span>
                  <strong style={{ color: "#0f172a" }}>{formatDate(activePlan.planting_date)}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f8fafc" }}>
                  <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                    <Calendar size={14} style={{ color: "#94a3b8" }} /> Expected Harvest
                  </span>
                  <strong style={{ color: "#0f172a" }}>{formatDate(activePlan.expected_harvest_date)}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0" }}>
                  <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                    <Calendar size={14} style={{ color: "#94a3b8" }} /> Declared Season
                  </span>
                  <strong style={{ color: "#0f172a" }}>{activePlan.farmer_declared_season ?? "Unspecified"}</strong>
                </div>
              </div>
            </div>

            {/* Next Steps Card */}
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
                Next Steps
              </h3>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <Link
                  href={activePlan ? `/crop-planning/plans/${encodeURIComponent(activePlan.plan_id)}` : "/crop-planning/plans"}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 14px",
                    borderRadius: "12px",
                    background: "#f0fdf4",
                    border: "1px solid #bbf7d0",
                    textDecoration: "none",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <Calendar size={18} style={{ color: "#166534" }} />
                    <div>
                      <strong style={{ fontSize: "13px", color: "#14532d", display: "block" }}>
                        View Plan Details & Activities
                      </strong>
                      <small style={{ fontSize: "11px", color: "#15803d" }}>
                        Manage timeline and seasonal activities for this plan
                      </small>
                    </div>
                  </div>
                  <ChevronRight size={16} style={{ color: "#166534" }} />
                </Link>

                <Link
                  href="/crop-planning/suggested-crops"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 14px",
                    borderRadius: "12px",
                    background: "#fefce8",
                    border: "1px solid #fef08a",
                    textDecoration: "none",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <Leaf size={18} style={{ color: "#854d0e" }} />
                    <div>
                      <strong style={{ fontSize: "13px", color: "#713f12", display: "block" }}>
                        Alternative Crops Status
                      </strong>
                      <small style={{ fontSize: "11px", color: "#a16207" }}>
                        Check evidence and approval gate requirements
                      </small>
                    </div>
                  </div>
                  <ChevronRight size={16} style={{ color: "#a16207" }} />
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
