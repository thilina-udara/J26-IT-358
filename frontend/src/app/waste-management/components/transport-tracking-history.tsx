"use client";

import React, { useEffect, useState } from "react";
import {
  Truck,
  CheckCircle2,
  Clock,
  MapPin,
  Sparkles,
  Package,
  Box,
  Scale,
  Receipt,
  History,
  Eye,
  RefreshCw,
  FileText,
  AlertCircle,
  Calendar,
  ChevronRight,
  ShieldCheck,
  Leaf,
  Flame,
  ArrowRight,
  X,
  User,
  Barcode,
} from "lucide-react";
import { TransportLotItem } from "./product-lot-popup-form";

export interface TimelineEvent {
  step: number;
  title: string;
  status: "completed" | "current" | "pending";
  timestamp?: string | null;
  description: string;
}

export interface TransportTrackingDetail {
  id: string;
  farmer_id: string;
  status: "Ready" | "In Transit" | "Delivered" | "Cancelled";
  destination_center: string;
  total_kg: number;
  created_at: string;
  updated_at: string;
  dispatched_at?: string | null;
  received_at?: string | null;
  actual_received_kg?: number | null;
  accepted_fresh_kg?: number | null;
  cull_waste_kg?: number | null;
  inspector_name?: string | null;
  receiving_notes?: string | null;
  quality_grade?: string | null;
  bioeconomy_action?: string | null;
  items: TransportLotItem[];
  timeline: TimelineEvent[];
}

export interface FarmerHistoryData {
  farmer_id: string;
  total_shipments: number;
  active_shipments_count: number;
  delivered_shipments_count: number;
  total_produce_kg: number;
  total_fresh_delivered_kg: number;
  total_cull_recovered_kg: number;
  active_transports: TransportTrackingDetail[];
  completed_transports: TransportTrackingDetail[];
}

interface TransportTrackingHistoryProps {
  farmerId: string;
  refreshTrigger: number;
  activeTab: "register" | "tracking" | "history";
  setActiveTab: (tab: "register" | "tracking" | "history") => void;
  onNotification: (msg: string) => void;
}

export function TransportTrackingHistory({
  farmerId,
  refreshTrigger,
  activeTab,
  setActiveTab,
  onNotification,
}: TransportTrackingHistoryProps) {
  const [historyData, setHistoryData] = useState<FarmerHistoryData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [selectedTransport, setSelectedTransport] = useState<TransportTrackingDetail | null>(null);

  // Collection Centre Intake Modal State
  const [intakeModalTransport, setIntakeModalTransport] = useState<TransportTrackingDetail | null>(null);
  const [inspectorName, setInspectorName] = useState<string>("S. Jayawardena (Quality Division)");
  const [qualityGrade, setQualityGrade] = useState<string>("Grade A - Superior Quality");
  const [intakeGrossKg, setIntakeGrossKg] = useState<number>(0);
  const [intakeFreshKg, setIntakeFreshKg] = useState<number>(0);
  const [intakeCullKg, setIntakeCullKg] = useState<number>(0);
  const [intakeNotes, setIntakeNotes] = useState<string>("Produce inspected at receiving dock. Firmness and sorting verified.");
  const [intakeBioAction, setIntakeBioAction] = useState<string>("SLSI 1246:2003 Aerobic Composting");
  const [isIntakeSubmitting, setIsIntakeSubmitting] = useState<boolean>(false);

  // Digital Receipt Modal State
  const [receiptTransport, setReceiptTransport] = useState<TransportTrackingDetail | null>(null);

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`http://localhost:8003/api/transport/farmer/${farmerId}/history`);
      if (res.ok) {
        const data: FarmerHistoryData = await res.json();
        setHistoryData(data);
      }
    } catch {
      // Backend offline or unreachable
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [farmerId, refreshTrigger]);

  // Dispatch Action (Farm Gate Departure)
  const handleDispatchTransport = async (transportId: string) => {
    try {
      const res = await fetch(`http://localhost:8003/api/transport/${transportId}/dispatch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error("Dispatch failed");
      onNotification(`Produce batch [${transportId}] marked as Dispatched & In Transit! Barcode stickers locked in transit.`);
      await fetchHistory();
    } catch (e: any) {
      alert("Error dispatching: " + e.message);
    }
  };

  // Open Collection Centre Intake Simulation Modal
  const openIntakeModal = (transport: TransportTrackingDetail) => {
    setIntakeModalTransport(transport);
    const gross = transport.total_kg;
    setIntakeGrossKg(gross);
    // Estimate fresh vs cull based on average predicted waste
    const avgLoss = transport.items.length > 0 && transport.items[0].predicted_waste_pct
      ? transport.items[0].predicted_waste_pct
      : 20.0;
    const fresh = Number((gross * (1.0 - avgLoss / 100.0)).toFixed(1));
    const cull = Number((gross - fresh).toFixed(1));
    setIntakeFreshKg(fresh);
    setIntakeCullKg(cull);
    setIntakeBioAction(
      avgLoss > 25.0
        ? "Anaerobic Biogas Diversion (High Moisture / Acidic Cull)"
        : "SLSI 1246:2003 Aerobic Composting (Dambulla Bio-Hub)"
    );
  };

  // Submit Collection Centre Intake
  const handleSubmitIntake = async () => {
    if (!intakeModalTransport) return;
    setIsIntakeSubmitting(true);
    try {
      const res = await fetch(`http://localhost:8003/api/transport/${intakeModalTransport.id}/receive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inspector_name: inspectorName,
          quality_grade: qualityGrade,
          actual_received_kg: intakeGrossKg,
          accepted_fresh_kg: intakeFreshKg,
          cull_waste_kg: intakeCullKg,
          receiving_notes: intakeNotes,
          bioeconomy_action: intakeBioAction,
        }),
      });

      if (!res.ok) throw new Error("Receiving intake failed");
      const result = await res.json();
      setIntakeModalTransport(null);
      onNotification(`Collection Centre Intake Recorded! Certified fresh: ${intakeFreshKg} kg | Cull diverted to bioeconomy: ${intakeCullKg} kg.`);
      await fetchHistory();
      // Automatically switch to history tab so the farmer sees the updated completed log
      setActiveTab("history");
    } catch (e: any) {
      alert("Error recording intake: " + e.message);
    } finally {
      setIsIntakeSubmitting(false);
    }
  };

  const activeTransports = historyData?.active_transports || [];
  const completedTransports = historyData?.completed_transports || [];

  return (
    <div style={{ marginTop: "12px", marginBottom: "36px" }}>
      {/* ----------------------------------------------------------------------
          1. NAVIGATION TABS (DISPATCH vs LIVE TRACKING vs PRODUCT HISTORY)
          ---------------------------------------------------------------------- */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
          background: "#ffffff",
          borderRadius: "18px",
          padding: "8px 12px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 2px 10px rgba(0,0,0,0.02)",
          marginBottom: "24px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <button
            type="button"
            id="tab-btn-register"
            onClick={() => setActiveTab("register")}
            style={{
              padding: "10px 18px",
              borderRadius: "12px",
              border: "none",
              fontSize: "13.5px",
              fontWeight: 700,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: activeTab === "register" ? "#15803d" : "transparent",
              color: activeTab === "register" ? "#ffffff" : "#475569",
              transition: "all 0.2s ease",
            }}
          >
            <Box size={16} />
            <span>1. Dispatch New Produce Lot</span>
          </button>

          <button
            type="button"
            id="tab-btn-tracking"
            onClick={() => setActiveTab("tracking")}
            style={{
              padding: "10px 18px",
              borderRadius: "12px",
              border: "none",
              fontSize: "13.5px",
              fontWeight: 700,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: activeTab === "tracking" ? "#15803d" : "transparent",
              color: activeTab === "tracking" ? "#ffffff" : "#475569",
              position: "relative",
              transition: "all 0.2s ease",
            }}
          >
            <Truck size={16} />
            <span>2. Current Process & Live Tracking</span>
            {activeTransports.length > 0 && (
              <span
                style={{
                  background: activeTab === "tracking" ? "#ffffff" : "#22c55e",
                  color: activeTab === "tracking" ? "#15803d" : "#ffffff",
                  fontSize: "11px",
                  fontWeight: 900,
                  padding: "1px 7px",
                  borderRadius: "9999px",
                }}
              >
                {activeTransports.length}
              </span>
            )}
          </button>

          <button
            type="button"
            id="tab-btn-history"
            onClick={() => setActiveTab("history")}
            style={{
              padding: "10px 18px",
              borderRadius: "12px",
              border: "none",
              fontSize: "13.5px",
              fontWeight: 700,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: activeTab === "history" ? "#15803d" : "transparent",
              color: activeTab === "history" ? "#ffffff" : "#475569",
              transition: "all 0.2s ease",
            }}
          >
            <History size={16} />
            <span>3. Product History & Bioeconomy Log</span>
            {completedTransports.length > 0 && (
              <span
                style={{
                  background: activeTab === "history" ? "#ffffff" : "#94a3b8",
                  color: activeTab === "history" ? "#15803d" : "#ffffff",
                  fontSize: "11px",
                  fontWeight: 900,
                  padding: "1px 7px",
                  borderRadius: "9999px",
                }}
              >
                {completedTransports.length}
              </span>
            )}
          </button>
        </div>

        <button
          type="button"
          onClick={fetchHistory}
          style={{
            background: "#f8fafc",
            border: "1px solid #cbd5e1",
            borderRadius: "10px",
            padding: "8px 14px",
            fontSize: "12.5px",
            fontWeight: 600,
            color: "#475569",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
          <span>Refresh Tracking</span>
        </button>
      </div>

      {/* ----------------------------------------------------------------------
          2. TAB CONTENT: CURRENT PROCESS & LIVE TRACKING
          ---------------------------------------------------------------------- */}
      {activeTab === "tracking" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {activeTransports.length === 0 ? (
            <div
              style={{
                background: "#ffffff",
                borderRadius: "22px",
                padding: "48px 24px",
                textAlign: "center",
                border: "1px dashed #cbd5e1",
              }}
            >
              <div
                style={{
                  width: "60px",
                  height: "60px",
                  borderRadius: "50%",
                  background: "#f0fdf4",
                  color: "#16a34a",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 16px auto",
                }}
              >
                <Truck size={30} />
              </div>
              <h3 style={{ fontSize: "18px", fontWeight: 800, margin: "0 0 8px 0", color: "#0f172a" }}>
                No Active Shipments in Transit
              </h3>
              <p style={{ fontSize: "13.5px", color: "#64748b", maxWidth: "480px", margin: "0 auto 20px auto" }}>
                All previous produce transports have been received and processed. Go to "Dispatch New Produce Lot" to register your next harvest delivery with crate barcodes.
              </p>
              <button
                type="button"
                onClick={() => setActiveTab("register")}
                style={{
                  background: "#15803d",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "10px",
                  padding: "10px 20px",
                  fontSize: "13.5px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                + Register New Produce Lot
              </button>
            </div>
          ) : (
            activeTransports.map((trans) => {
              const primaryItem = trans.items[0];
              const isInTransit = trans.status === "In Transit";

              return (
                <div
                  key={trans.id}
                  style={{
                    background: "#ffffff",
                    borderRadius: "24px",
                    border: "1px solid #e2e8f0",
                    boxShadow: "0 8px 24px rgba(0,0,0,0.03)",
                    overflow: "hidden",
                  }}
                >
                  {/* Transport Card Header */}
                  <div
                    style={{
                      padding: "20px 26px",
                      background: "linear-gradient(90deg, #f8fafc 0%, #ffffff 100%)",
                      borderBottom: "1px solid #e2e8f0",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      flexWrap: "wrap",
                      gap: "14px",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                        <span
                          style={{
                            background: isInTransit ? "#eff6ff" : "#fefce8",
                            color: isInTransit ? "#1d4ed8" : "#854d0e",
                            border: `1px solid ${isInTransit ? "#bfdbfe" : "#fef08a"}`,
                            fontSize: "12px",
                            fontWeight: 800,
                            padding: "3px 10px",
                            borderRadius: "9999px",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                          }}
                        >
                          <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: isInTransit ? "#2563eb" : "#ca8a04" }} />
                          {trans.status.toUpperCase()}
                        </span>
                        <h3 style={{ fontSize: "17px", fontWeight: 800, margin: 0, color: "#0f172a" }}>
                          Transport Manifest: <code>{trans.id}</code>
                        </h3>
                      </div>
                      <div style={{ fontSize: "13px", color: "#64748b", display: "flex", alignItems: "center", gap: "12px" }}>
                        <span>
                          Destination: <strong style={{ color: "#0f172a" }}>{trans.destination_center}</strong>
                        </span>
                        <span>•</span>
                        <span>
                          Total Load: <strong style={{ color: "#0f172a" }}>{trans.total_kg} kg</strong> ({trans.items.length} crate lots)
                        </span>
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      {!isInTransit && (
                        <button
                          type="button"
                          id={`btn-dispatch-${trans.id}`}
                          onClick={() => handleDispatchTransport(trans.id)}
                          style={{
                            background: "#15803d",
                            color: "#ffffff",
                            border: "none",
                            borderRadius: "10px",
                            padding: "9px 18px",
                            fontSize: "13px",
                            fontWeight: 700,
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "7px",
                            boxShadow: "0 2px 8px rgba(21, 128, 61, 0.2)",
                          }}
                        >
                          <Truck size={15} />
                          <span>Mark Dispatched (In Transit)</span>
                        </button>
                      )}

                      <button
                        type="button"
                        id={`btn-intake-${trans.id}`}
                        onClick={() => openIntakeModal(trans)}
                        style={{
                          background: "#ffffff",
                          color: "#1d4ed8",
                          border: "1px solid #bfdbfe",
                          borderRadius: "10px",
                          padding: "9px 16px",
                          fontSize: "13px",
                          fontWeight: 700,
                          cursor: "pointer",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "7px",
                        }}
                      >
                        <ShieldCheck size={15} />
                        <span>Simulate Collection Centre Intake</span>
                      </button>
                    </div>
                  </div>

                  {/* 5-Step Visual Milestone Stepper */}
                  <div style={{ padding: "26px 26px 20px 26px" }}>
                    <h4 style={{ fontSize: "13px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.5px", color: "#64748b", margin: "0 0 18px 0" }}>
                      Current Process & Milestone Progression
                    </h4>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "12px", position: "relative" }}>
                      {trans.timeline.map((event) => {
                        const isDone = event.status === "completed";
                        const isCurrent = event.status === "current";

                        return (
                          <div
                            key={event.step}
                            style={{
                              background: isDone ? "#f0fdf4" : isCurrent ? "#eff6ff" : "#f8fafc",
                              border: `1px solid ${isDone ? "#86efac" : isCurrent ? "#93c5fd" : "#e2e8f0"}`,
                              borderRadius: "14px",
                              padding: "14px 16px",
                              display: "flex",
                              flexDirection: "column",
                              justifyContent: "space-between",
                            }}
                          >
                            <div>
                              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                                <span
                                  style={{
                                    width: "24px",
                                    height: "24px",
                                    borderRadius: "50%",
                                    background: isDone ? "#16a34a" : isCurrent ? "#2563eb" : "#cbd5e1",
                                    color: "#ffffff",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontSize: "12px",
                                    fontWeight: 900,
                                  }}
                                >
                                  {isDone ? "✓" : event.step}
                                </span>
                                <span style={{ fontSize: "11px", fontWeight: 700, color: isDone ? "#16a34a" : isCurrent ? "#2563eb" : "#94a3b8" }}>
                                  {isDone ? "COMPLETED" : isCurrent ? "IN PROGRESS" : "UPCOMING"}
                                </span>
                              </div>
                              <h5 style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a", margin: "0 0 4px 0" }}>
                                {event.title}
                              </h5>
                              <p style={{ fontSize: "11.5px", color: "#64748b", margin: 0, lineHeight: 1.4 }}>
                                {event.description}
                              </p>
                            </div>
                            {event.timestamp && (
                              <div style={{ marginTop: "10px", fontSize: "10.5px", color: "#94a3b8", display: "flex", alignItems: "center", gap: "4px" }}>
                                <Clock size={11} />
                                <span>{new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Produce Lots Table inside this transport */}
                  <div style={{ padding: "0 26px 24px 26px" }}>
                    <div style={{ background: "#f8fafc", borderRadius: "14px", border: "1px solid #e2e8f0", overflow: "hidden" }}>
                      <div style={{ padding: "12px 18px", borderBottom: "1px solid #e2e8f0", fontSize: "12px", fontWeight: 700, color: "#475569" }}>
                        Registered Produce Crate Lots ({trans.items.length})
                      </div>
                      <div style={{ overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12.5px" }}>
                          <thead>
                            <tr style={{ background: "#ffffff", borderBottom: "1px solid #e2e8f0", textAlign: "left", color: "#64748b" }}>
                              <th style={{ padding: "10px 16px" }}>Crate Barcode</th>
                              <th style={{ padding: "10px 16px" }}>Produce Item</th>
                              <th style={{ padding: "10px 16px", textAlign: "right" }}>Gross Weight</th>
                              <th style={{ padding: "10px 16px" }}>Vehicle & Packaging</th>
                              <th style={{ padding: "10px 16px" }}>Predicted Loss</th>
                              <th style={{ padding: "10px 16px" }}>Risk Tier</th>
                            </tr>
                          </thead>
                          <tbody>
                            {trans.items.map((it) => (
                              <tr key={it.barcode_no} style={{ borderBottom: "1px solid #f1f5f9" }}>
                                <td style={{ padding: "10px 16px" }}>
                                  <span style={{ fontFamily: "monospace", fontWeight: 800, background: "#e2e8f0", padding: "2px 6px", borderRadius: "4px" }}>
                                    {it.barcode_no}
                                  </span>
                                </td>
                                <td style={{ padding: "10px 16px", fontWeight: 700, color: "#0f172a" }}>
                                  {it.food_name} ({it.crop_category})
                                </td>
                                <td style={{ padding: "10px 16px", textAlign: "right", fontWeight: 800 }}>
                                  {it.kg} kg
                                </td>
                                <td style={{ padding: "10px 16px", color: "#475569" }}>
                                  {it.transport_type.replace(/_/g, " ")} • {it.packing_type.replace(/_/g, " ")}
                                </td>
                                <td style={{ padding: "10px 16px", fontWeight: 700, color: (it.predicted_waste_pct || 0) > 20 ? "#dc2626" : "#16a34a" }}>
                                  {it.predicted_waste_pct || 20.0}% ({it.predicted_waste_kg || ((it.kg * 0.2).toFixed(1))} kg)
                                </td>
                                <td style={{ padding: "10px 16px" }}>
                                  <span
                                    style={{
                                      fontSize: "11px",
                                      fontWeight: 800,
                                      padding: "2px 8px",
                                      borderRadius: "9999px",
                                      background: it.risk_level === "LOW" ? "#dcfce7" : it.risk_level === "MEDIUM" ? "#fef3c7" : "#fee2e2",
                                      color: it.risk_level === "LOW" ? "#166534" : it.risk_level === "MEDIUM" ? "#92400e" : "#991b1b",
                                    }}
                                  >
                                    {it.risk_level || "MEDIUM"}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* ----------------------------------------------------------------------
          3. TAB CONTENT: PRODUCT HISTORY & BIOECONOMY LOG
          ---------------------------------------------------------------------- */}
      {activeTab === "history" && (
        <div>
          {/* Summary Metric Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px", marginBottom: "22px" }}>
            <div style={{ background: "#ffffff", padding: "18px 20px", borderRadius: "18px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 600, marginBottom: "4px" }}>Total Shipments Completed</div>
              <div style={{ fontSize: "24px", fontWeight: 900, color: "#0f172a" }}>
                {historyData?.delivered_shipments_count || completedTransports.length}
              </div>
              <div style={{ fontSize: "11px", color: "#16a34a", marginTop: "4px", fontWeight: 700 }}>
                Traceability verified
              </div>
            </div>

            <div style={{ background: "#ffffff", padding: "18px 20px", borderRadius: "18px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 600, marginBottom: "4px" }}>Total Produce Delivered</div>
              <div style={{ fontSize: "24px", fontWeight: 900, color: "#0f172a" }}>
                {historyData?.total_produce_kg || 0} kg
              </div>
              <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>Gross farm dispatch</div>
            </div>

            <div style={{ background: "#ffffff", padding: "18px 20px", borderRadius: "18px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "12px", color: "#15803d", fontWeight: 600, marginBottom: "4px" }}>Certified Fresh Retail</div>
              <div style={{ fontSize: "24px", fontWeight: 900, color: "#15803d" }}>
                {historyData?.total_fresh_delivered_kg || 0} kg
              </div>
              <div style={{ fontSize: "11px", color: "#15803d", marginTop: "4px", fontWeight: 700 }}>
                Routed to wholesale market
              </div>
            </div>

            <div style={{ background: "#ffffff", padding: "18px 20px", borderRadius: "18px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "12px", color: "#b45309", fontWeight: 600, marginBottom: "4px" }}>Bioeconomy Cull Recovered</div>
              <div style={{ fontSize: "24px", fontWeight: 900, color: "#b45309" }}>
                {historyData?.total_cull_recovered_kg || 0} kg
              </div>
              <div style={{ fontSize: "11px", color: "#b45309", marginTop: "4px", fontWeight: 700 }}>
                Saved from landfill
              </div>
            </div>
          </div>

          {/* Completed Transports Table */}
          {completedTransports.length === 0 ? (
            <div style={{ background: "#ffffff", borderRadius: "20px", padding: "40px 20px", textAlign: "center", border: "1px dashed #cbd5e1" }}>
              <History size={32} style={{ color: "#94a3b8", margin: "0 auto 12px auto" }} />
              <h4 style={{ fontSize: "16px", fontWeight: 800, margin: "0 0 6px 0", color: "#334155" }}>
                No Past Delivered Shipments Yet
              </h4>
              <p style={{ fontSize: "13px", color: "#64748b", margin: 0 }}>
                When an active transport is received and inspected at a Collection Centre, its verified grading and bioeconomy recovery log will appear here.
              </p>
            </div>
          ) : (
            <div style={{ background: "#ffffff", borderRadius: "22px", border: "1px solid #e2e8f0", overflow: "hidden", boxShadow: "0 4px 16px rgba(0,0,0,0.02)" }}>
              <div style={{ padding: "16px 22px", background: "#f8fafc", borderBottom: "1px solid #e2e8f0", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: "13.5px", fontWeight: 800, color: "#0f172a" }}>
                  Completed Delivery History & Quality Certification
                </span>
                <span style={{ fontSize: "12px", color: "#64748b" }}>
                  {completedTransports.length} completed batch{completedTransports.length > 1 ? "es" : ""}
                </span>
              </div>

              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                  <thead>
                    <tr style={{ background: "#ffffff", borderBottom: "1px solid #e2e8f0", textAlign: "left", color: "#64748b", fontSize: "12px" }}>
                      <th style={{ padding: "14px 18px" }}>Manifest ID & Date</th>
                      <th style={{ padding: "14px 18px" }}>Collection Centre</th>
                      <th style={{ padding: "14px 18px", textAlign: "right" }}>Gross Weighed</th>
                      <th style={{ padding: "14px 18px", textAlign: "right" }}>Fresh Retail</th>
                      <th style={{ padding: "14px 18px", textAlign: "right" }}>Bioeconomy Cull</th>
                      <th style={{ padding: "14px 18px" }}>Quality Grade</th>
                      <th style={{ padding: "14px 18px" }}>Bioeconomy Action</th>
                      <th style={{ padding: "14px 18px", textAlign: "right" }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {completedTransports.map((trans) => (
                      <tr key={trans.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "14px 18px" }}>
                          <div style={{ fontWeight: 800, color: "#0f172a" }}>{trans.id}</div>
                          <div style={{ fontSize: "11px", color: "#64748b" }}>
                            {new Date(trans.created_at).toLocaleDateString()} {trans.items[0]?.food_name ? `• ${trans.items[0].food_name}` : ""}
                          </div>
                        </td>
                        <td style={{ padding: "14px 18px" }}>
                          <span style={{ fontWeight: 600, color: "#334155" }}>
                            {trans.destination_center.split(" ")[0]} DEC
                          </span>
                        </td>
                        <td style={{ padding: "14px 18px", textAlign: "right", fontWeight: 800, color: "#0f172a" }}>
                          {trans.actual_received_kg || trans.total_kg} kg
                        </td>
                        <td style={{ padding: "14px 18px", textAlign: "right", fontWeight: 800, color: "#16a34a" }}>
                          {trans.accepted_fresh_kg || (trans.total_kg * 0.8).toFixed(1)} kg
                        </td>
                        <td style={{ padding: "14px 18px", textAlign: "right", fontWeight: 800, color: "#d97706" }}>
                          {trans.cull_waste_kg || (trans.total_kg * 0.2).toFixed(1)} kg
                        </td>
                        <td style={{ padding: "14px 18px" }}>
                          <span
                            style={{
                              fontSize: "11px",
                              fontWeight: 800,
                              padding: "2px 8px",
                              borderRadius: "9999px",
                              background: "#dcfce7",
                              color: "#166534",
                            }}
                          >
                            {trans.quality_grade || "Grade A"}
                          </span>
                        </td>
                        <td style={{ padding: "14px 18px", fontSize: "12px", color: "#475569" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                            {trans.bioeconomy_action?.includes("Biogas") ? (
                              <Flame size={13} style={{ color: "#d97706" }} />
                            ) : (
                              <Leaf size={13} style={{ color: "#16a34a" }} />
                            )}
                            <span>{trans.bioeconomy_action || "SLSI 1246 Composting"}</span>
                          </div>
                        </td>
                        <td style={{ padding: "14px 18px", textAlign: "right" }}>
                          <button
                            type="button"
                            onClick={() => setReceiptTransport(trans)}
                            style={{
                              background: "#f8fafc",
                              border: "1px solid #cbd5e1",
                              borderRadius: "8px",
                              padding: "6px 12px",
                              fontSize: "12px",
                              fontWeight: 700,
                              color: "#1e293b",
                              cursor: "pointer",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                            }}
                          >
                            <FileText size={13} />
                            <span>Receipt</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ----------------------------------------------------------------------
          4. COLLECTION CENTRE INTAKE SIMULATION MODAL
          ---------------------------------------------------------------------- */}
      {intakeModalTransport && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.75)",
            backdropFilter: "blur(4px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            style={{
              background: "#ffffff",
              borderRadius: "24px",
              width: "100%",
              maxWidth: "640px",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
              overflow: "hidden",
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                background: "linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%)",
                padding: "20px 24px",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div>
                <span style={{ fontSize: "11px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.5px", opacity: 0.85 }}>
                  Dedicated Economic Centre Receiving Terminal
                </span>
                <h3 style={{ fontSize: "18px", fontWeight: 800, margin: "2px 0 0 0" }}>
                  Record Intake & Quality Inspection ({intakeModalTransport.destination_center.split(" ")[0]} DEC)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIntakeModalTransport(null)}
                style={{ background: "transparent", border: "none", color: "#ffffff", cursor: "pointer" }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px", maxHeight: "75vh", overflowY: "auto" }}>
              <div style={{ background: "#f8fafc", padding: "12px 16px", borderRadius: "12px", border: "1px solid #e2e8f0", fontSize: "12.5px" }}>
                <div>
                  <strong>Transport ID:</strong> <code>{intakeModalTransport.id}</code>
                </div>
                <div>
                  <strong>Farmer:</strong> {intakeModalTransport.farmer_id} • <strong>Items:</strong> {intakeModalTransport.items.map((it) => it.food_name).join(", ")}
                </div>
              </div>

              {/* Inspector Name */}
              <div>
                <label style={{ display: "block", fontSize: "12.5px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                  Quality Control Officer
                </label>
                <input
                  type="text"
                  value={inspectorName}
                  onChange={(e) => setInspectorName(e.target.value)}
                  style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", border: "1px solid #cbd5e1", fontSize: "13.5px", fontWeight: 600 }}
                />
              </div>

              {/* Scale Readings: Gross, Fresh, Cull */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                    Actual Scale (kg)
                  </label>
                  <input
                    type="number"
                    value={intakeGrossKg}
                    onChange={(e) => {
                      const v = Number(e.target.value);
                      setIntakeGrossKg(v);
                      setIntakeFreshKg(Number((v * 0.8).toFixed(1)));
                      setIntakeCullKg(Number((v * 0.2).toFixed(1)));
                    }}
                    style={{ width: "100%", padding: "10px", borderRadius: "10px", border: "1px solid #cbd5e1", fontSize: "14px", fontWeight: 800 }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#16a34a", marginBottom: "4px" }}>
                    Accepted Fresh (kg)
                  </label>
                  <input
                    type="number"
                    value={intakeFreshKg}
                    onChange={(e) => {
                      const v = Number(e.target.value);
                      setIntakeFreshKg(v);
                      setIntakeCullKg(Math.max(0, Number((intakeGrossKg - v).toFixed(1))));
                    }}
                    style={{ width: "100%", padding: "10px", borderRadius: "10px", border: "1px solid #86efac", background: "#f0fdf4", fontSize: "14px", fontWeight: 800, color: "#166534" }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#b45309", marginBottom: "4px" }}>
                    Bioeconomy Cull (kg)
                  </label>
                  <input
                    type="number"
                    value={intakeCullKg}
                    onChange={(e) => setIntakeCullKg(Number(e.target.value))}
                    style={{ width: "100%", padding: "10px", borderRadius: "10px", border: "1px solid #fde68a", background: "#fffbeb", fontSize: "14px", fontWeight: 800, color: "#92400e" }}
                  />
                </div>
              </div>

              {/* Quality Grade */}
              <div>
                <label style={{ display: "block", fontSize: "12.5px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                  Certified SLSI Quality Grade
                </label>
                <select
                  value={qualityGrade}
                  onChange={(e) => setQualityGrade(e.target.value)}
                  style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", border: "1px solid #cbd5e1", fontSize: "13.5px" }}
                >
                  <option value="Grade A - Superior Quality">Grade A - Superior Quality (Wholesale Premium)</option>
                  <option value="Grade B - Standard Commercial">Grade B - Standard Commercial (Standard Supermarket)</option>
                  <option value="Grade C - Salvage Wholesaling">Grade C - Salvage Wholesaling (Local Market)</option>
                </select>
              </div>

              {/* Bioeconomy Cull Action */}
              <div>
                <label style={{ display: "block", fontSize: "12.5px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                  Bioeconomy Cull Stream Diversion
                </label>
                <select
                  value={intakeBioAction}
                  onChange={(e) => setIntakeBioAction(e.target.value)}
                  style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", border: "1px solid #cbd5e1", fontSize: "13.5px" }}
                >
                  <option value="SLSI 1246:2003 Aerobic Composting (Dambulla Bio-Hub)">SLSI 1246:2003 Aerobic Composting (Dambulla Bio-Hub)</option>
                  <option value="Anaerobic Biogas Diversion (High Moisture / Acidic Cull)">Anaerobic Biogas Diversion (Methane & Electricity Recovery)</option>
                </select>
              </div>

              {/* Inspector Notes */}
              <div>
                <label style={{ display: "block", fontSize: "12.5px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                  Dock Inspection Notes
                </label>
                <textarea
                  rows={2}
                  value={intakeNotes}
                  onChange={(e) => setIntakeNotes(e.target.value)}
                  style={{ width: "100%", padding: "10px", borderRadius: "10px", border: "1px solid #cbd5e1", fontSize: "13px" }}
                />
              </div>
            </div>

            {/* Modal Footer */}
            <div style={{ padding: "16px 24px", background: "#f8fafc", borderTop: "1px solid #e2e8f0", display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button
                type="button"
                onClick={() => setIntakeModalTransport(null)}
                style={{ background: "#ffffff", border: "1px solid #cbd5e1", padding: "10px 18px", borderRadius: "10px", fontSize: "13px", fontWeight: 700, cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isIntakeSubmitting}
                onClick={handleSubmitIntake}
                style={{
                  background: "#1e40af",
                  color: "#ffffff",
                  border: "none",
                  padding: "10px 22px",
                  borderRadius: "10px",
                  fontSize: "13px",
                  fontWeight: 800,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <CheckCircle2 size={16} />
                <span>{isIntakeSubmitting ? "Recording..." : "Confirm Intake & Partition Produce"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------------
          5. DIGITAL RECEIPT / TRACEABILITY SLIP MODAL
          ---------------------------------------------------------------------- */}
      {receiptTransport && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.75)",
            backdropFilter: "blur(4px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            style={{
              background: "#ffffff",
              borderRadius: "24px",
              width: "100%",
              maxWidth: "520px",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
              overflow: "hidden",
            }}
          >
            {/* Receipt Header */}
            <div style={{ background: "#064e3b", color: "#ffffff", padding: "24px", textAlign: "center" }}>
              <div style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px", opacity: 0.85 }}>
                National Agricultural Produce Traceability System
              </div>
              <h3 style={{ fontSize: "20px", fontWeight: 900, margin: "6px 0 2px 0" }}>
                Delivery Intake Certification
              </h3>
              <p style={{ fontSize: "12px", opacity: 0.8, margin: 0 }}>
                {receiptTransport.destination_center}
              </p>
            </div>

            {/* Receipt Content */}
            <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "14px", fontSize: "13px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px dashed #cbd5e1", paddingBottom: "10px" }}>
                <span style={{ color: "#64748b" }}>Manifest Number:</span>
                <strong style={{ fontFamily: "monospace" }}>{receiptTransport.id}</strong>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px dashed #cbd5e1", paddingBottom: "10px" }}>
                <span style={{ color: "#64748b" }}>Farmer Account:</span>
                <strong>{receiptTransport.farmer_id}</strong>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px dashed #cbd5e1", paddingBottom: "10px" }}>
                <span style={{ color: "#64748b" }}>Delivered Date & Time:</span>
                <strong>{new Date(receiptTransport.received_at || receiptTransport.created_at).toLocaleString()}</strong>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px dashed #cbd5e1", paddingBottom: "10px" }}>
                <span style={{ color: "#64748b" }}>Quality Inspection Grade:</span>
                <strong style={{ color: "#166534" }}>{receiptTransport.quality_grade || "Grade A"}</strong>
              </div>

              {/* Mass Partitioning Summary */}
              <div style={{ background: "#f8fafc", borderRadius: "12px", padding: "14px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "11.5px", fontWeight: 800, textTransform: "uppercase", color: "#475569", marginBottom: "8px" }}>
                  Dual-Stream Mass Partitioning
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span>Gross Intake Weight:</span>
                  <strong>{receiptTransport.actual_received_kg || receiptTransport.total_kg} kg</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", color: "#16a34a", marginBottom: "6px" }}>
                  <span>✓ Accepted Fresh Commercial:</span>
                  <strong>{receiptTransport.accepted_fresh_kg || (receiptTransport.total_kg * 0.8).toFixed(1)} kg</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", color: "#b45309" }}>
                  <span>♻ Diverted Bioeconomy Cull:</span>
                  <strong>{receiptTransport.cull_waste_kg || (receiptTransport.total_kg * 0.2).toFixed(1)} kg</strong>
                </div>
              </div>

              <div style={{ fontSize: "11.5px", color: "#64748b", lineHeight: 1.4 }}>
                <strong>Bioeconomy Outcome:</strong> {receiptTransport.bioeconomy_action || "SLSI 1246:2003 Aerobic Composting"}
                <br />
                <strong>Inspector:</strong> {receiptTransport.inspector_name || "Quality Division Officer"}
              </div>
            </div>

            {/* Receipt Footer */}
            <div style={{ padding: "16px 24px", background: "#f8fafc", borderTop: "1px solid #e2e8f0", display: "flex", justifyContent: "flex-end" }}>
              <button
                type="button"
                onClick={() => setReceiptTransport(null)}
                style={{ background: "#15803d", color: "#ffffff", border: "none", borderRadius: "10px", padding: "8px 20px", fontSize: "13px", fontWeight: 700, cursor: "pointer" }}
              >
                Close Slip
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
