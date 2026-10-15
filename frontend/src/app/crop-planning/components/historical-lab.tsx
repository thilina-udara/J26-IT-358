"use client";

import React, { useState, useEffect } from "react";
import { AlertCircle, Database, FlaskConical, Lock, RefreshCw, Scale, ShieldAlert, Sparkles } from "lucide-react";
import { ResearchResult } from "./research-result";
import { useSession } from "./session";
import { useLoad } from "./ui";
import type {
  Crop,
  District,
  HistoricalScenarioRequest,
  HistoricalScenarioResponse,
  Season,
} from "../lib/contracts";

const PILOT_CROPS: Crop[] = ["Mung Beans", "Corn", "Bandakka", "Brinjal", "Pumpkin", "Chillies"];
const PILOT_DISTRICTS: District[] = ["Hambantota", "Matara"];
const PILOT_SEASONS: Season[] = ["Yala", "Maha"];
const PILOT_MODELS = ["XGBoost", "CatBoost", "Random Forest", "LinearSVC", "RBF SVC"] as const;

export default function HistoricalLab() {
  const { api } = useSession();

  // Load research demo capability status
  const statusResult = useLoad((signal) => api.researchDemoStatus(signal), [api]);

  // Form state initialized to match Screenshot 1
  const [district, setDistrict] = useState<District>("Hambantota");
  const [crop, setCrop] = useState<Crop>("Mung Beans");
  const [season, setSeason] = useState<Season>("Yala");
  const [landSize, setLandSize] = useState<number>(3.5);
  const [plantingDate, setPlantingDate] = useState<string>("2025-06-16");
  const [harvestDate, setHarvestDate] = useState<string>("2025-08-25");
  const [selectedModel, setSelectedModel] = useState<typeof PILOT_MODELS[number]>("XGBoost");

  // Evaluation execution state
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [evaluation, setEvaluation] = useState<HistoricalScenarioResponse | null>(null);
  const [previousEvaluation, setPreviousEvaluation] = useState<HistoricalScenarioResponse | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const qDistrict = params.get("district") as District | null;
    const qCrop = params.get("crop") as Crop | null;
    const qSeason = params.get("season") as Season | null;
    const qPlanting = params.get("planting_date");
    const qHarvest = params.get("harvest_date");
    const qLandSize = params.get("land_size");

    if (qDistrict && PILOT_DISTRICTS.includes(qDistrict)) setDistrict(qDistrict);
    if (qCrop && PILOT_CROPS.includes(qCrop)) setCrop(qCrop);
    if (qSeason && PILOT_SEASONS.includes(qSeason)) setSeason(qSeason);
    if (qPlanting && /^\d{4}-\d{2}-\d{2}$/.test(qPlanting)) setPlantingDate(qPlanting);
    if (qHarvest && /^\d{4}-\d{2}-\d{2}$/.test(qHarvest)) setHarvestDate(qHarvest);
    if (qLandSize && !isNaN(Number(qLandSize)) && Number(qLandSize) > 0) setLandSize(Number(qLandSize));
  }, []);

  const isEnabled = statusResult.data?.enabled ?? true;

  async function handleEvaluate(e: React.FormEvent) {
    e.preventDefault();
    setEvaluating(true);
    setError(null);
    try {
      const payload: HistoricalScenarioRequest = {
        district,
        crop,
        season,
        land_size_acres: Number(landSize),
        planting_date: plantingDate,
        expected_harvest_date: harvestDate,
        model_name: selectedModel,
      };
      const res = await api.researchDemoEvaluate(payload);
      setPreviousEvaluation(evaluation);
      setEvaluation(res);
    } catch (err: any) {
      setError(err?.message || "Failed to run historical evaluation");
      setEvaluation(null);
    } finally {
      setEvaluating(false);
    }
  }

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", paddingBottom: "60px", color: "#0f172a" }}>
      {/* Header Banner */}
      <section
        style={{
          borderRadius: "24px",
          background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
          color: "#ffffff",
          padding: "32px 36px",
          marginBottom: "24px",
          boxShadow: "0 10px 25px -5px rgba(15, 23, 42, 0.2)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "12px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "14px",
              background: "rgba(59, 130, 246, 0.2)",
              color: "#60a5fa",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <FlaskConical size={26} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h1 style={{ fontSize: "24px", fontWeight: 800, margin: 0, letterSpacing: "-0.5px" }}>
                Historical Research Testing Lab
              </h1>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  padding: "4px 10px",
                  borderRadius: "9999px",
                  background: isEnabled ? "#065f46" : "#7f1d1d",
                  color: isEnabled ? "#34d399" : "#fca5a5",
                  border: `1px solid ${isEnabled ? "#059669" : "#991b1b"}`,
                }}
              >
                {isEnabled ? "Research Mode Active" : "Authorization Disabled"}
              </span>
            </div>
            <p style={{ fontSize: "14px", color: "#94a3b8", margin: "4px 0 0 0" }}>
              Retrospective validation across 2025-01-01 to 2026-08-31 historical ASC registry records with strict provenance isolation.
            </p>
          </div>
        </div>

        {/* Isolation Guarantee Bar */}
        <div
          style={{
            marginTop: "20px",
            background: "rgba(255, 255, 255, 0.06)",
            backdropFilter: "blur(8px)",
            borderRadius: "14px",
            padding: "14px 18px",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "16px",
            fontSize: "12.5px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Database size={16} style={{ color: "#38bdf8", flexShrink: 0 }} />
            <span>
              <strong>Storage Isolation:</strong> Isolated SQLite database (storage/research_demo.sqlite3).
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Lock size={16} style={{ color: "#a78bfa", flexShrink: 0 }} />
            <span>
              <strong>Zero Leakage:</strong> Evaluation filters history strictly &lt; target date.
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Scale size={16} style={{ color: "#34d399", flexShrink: 0 }} />
            <span>
              <strong>Provenance:</strong> Model trained on 2020-2026 ASC records.
            </span>
          </div>
        </div>
      </section>

      {!isEnabled && (
        <div
          style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "16px",
            padding: "20px",
            marginBottom: "24px",
            color: "#991b1b",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <ShieldAlert size={22} />
            <strong style={{ fontSize: "15px" }}>Research Demo Workflow Disabled</strong>
          </div>
          <p style={{ fontSize: "13px", margin: 0, lineHeight: 1.5 }}>
            Historical scenario simulation is disabled by default in production. To enable it locally for research validation, set{" "}
            <code>CULTIVATION_RESEARCH_DEMO_ENABLED=true</code> in your backend environment variables and restart the server.
          </p>
        </div>
      )}

      {/* Main Grid: Form on Left, Output on Right */}
      <div style={{ display: "grid", gridTemplateColumns: "400px 1fr", gap: "24px" }}>
        {/* Left Column: Simulation Form */}
        <div
          style={{
            background: "#ffffff",
            borderRadius: "20px",
            padding: "24px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 8px rgba(0,0,0,0.02)",
            height: "fit-content",
          }}
        >
          <h2 style={{ fontSize: "17px", fontWeight: 700, margin: "0 0 16px 0", color: "#0f172a" }}>
            Simulate Historical Scenario
          </h2>

          <form onSubmit={handleEvaluate} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#475569", marginBottom: "5px" }}>
                Historical Planting Date (2025-01-01 to 2026-08-31)
              </label>
              <input
                type="date"
                min="2025-01-01"
                max="2026-08-31"
                value={plantingDate}
                onChange={(e) => setPlantingDate(e.target.value)}
                required
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  borderRadius: "10px",
                  border: "1px solid #cbd5e1",
                  fontSize: "13.5px",
                }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#475569", marginBottom: "5px" }}>
                Expected Harvest Date
              </label>
              <input
                type="date"
                min={plantingDate}
                value={harvestDate}
                onChange={(e) => setHarvestDate(e.target.value)}
                required
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  borderRadius: "10px",
                  border: "1px solid #cbd5e1",
                  fontSize: "13.5px",
                }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#475569", marginBottom: "5px" }}>
                  Pilot District
                </label>
                <select
                  value={district}
                  onChange={(e) => setDistrict(e.target.value as District)}
                  style={{
                    width: "100%",
                    padding: "9px 10px",
                    borderRadius: "10px",
                    border: "1px solid #cbd5e1",
                    fontSize: "13px",
                    background: "#ffffff",
                  }}
                >
                  {PILOT_DISTRICTS.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#475569", marginBottom: "5px" }}>
                  Pilot Season
                </label>
                <select
                  value={season}
                  onChange={(e) => setSeason(e.target.value as Season)}
                  style={{
                    width: "100%",
                    padding: "9px 10px",
                    borderRadius: "10px",
                    border: "1px solid #cbd5e1",
                    fontSize: "13px",
                    background: "#ffffff",
                  }}
                >
                  {PILOT_SEASONS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#475569", marginBottom: "5px" }}>
                Pilot Crop
              </label>
              <select
                value={crop}
                onChange={(e) => setCrop(e.target.value as Crop)}
                style={{
                  width: "100%",
                  padding: "9px 10px",
                  borderRadius: "10px",
                  border: "1px solid #cbd5e1",
                  fontSize: "13px",
                  background: "#ffffff",
                }}
              >
                {PILOT_CROPS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#475569", marginBottom: "5px" }}>
                Land Size (Acres)
              </label>
              <input
                type="number"
                step="0.25"
                min="0.25"
                max="100"
                value={landSize}
                onChange={(e) => setLandSize(parseFloat(e.target.value) || 0)}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  borderRadius: "10px",
                  border: "1px solid #cbd5e1",
                  fontSize: "13.5px",
                }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#475569", marginBottom: "5px" }}>
                Evaluated ML Model Pipeline
              </label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value as any)}
                style={{
                  width: "100%",
                  padding: "9px 10px",
                  borderRadius: "10px",
                  border: "1px solid #cbd5e1",
                  fontSize: "13px",
                  background: "#ffffff",
                }}
              >
                <option value="XGBoost">XGBoost (84.30% Accuracy / 0.7182 Macro F1)</option>
                <option value="CatBoost">CatBoost (84.41% Accuracy / 0.7088 Macro F1)</option>
                <option value="Random Forest">Random Forest (77.67% Accuracy / 0.6012 Macro F1)</option>
                <option value="LinearSVC">LinearSVC (79.04% Accuracy / 0.6064 Macro F1)</option>
                <option value="RBF SVC">RBF SVC (79.43% Accuracy / 0.6200 Macro F1)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={evaluating || !isEnabled}
              style={{
                marginTop: "10px",
                padding: "12px 18px",
                borderRadius: "12px",
                background: isEnabled ? "#15803d" : "#94a3b8",
                color: "#ffffff",
                fontSize: "14px",
                fontWeight: 700,
                border: "none",
                cursor: isEnabled && !evaluating ? "pointer" : "not-allowed",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                transition: "background 0.2s",
              }}
            >
              {evaluating ? (
                <>
                  <RefreshCw size={16} className="animate-spin" />
                  <span>Evaluating Scenario...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Run Historical Evaluation</span>
                </>
              )}
            </button>
          </form>

          {/* Preset Buttons for Quick 2025 Verification */}
          <div style={{ marginTop: "20px", borderTop: "1px solid #f1f5f9", paddingTop: "16px" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "#64748b", display: "block", marginBottom: "8px" }}>
              Quick Test Presets
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <button
                type="button"
                onClick={() => {
                  setDistrict("Hambantota");
                  setCrop("Mung Beans");
                  setSeason("Yala");
                  setLandSize(3.5);
                  setPlantingDate("2025-06-16");
                  setHarvestDate("2025-08-25");
                  setSelectedModel("XGBoost");
                }}
                style={{
                  textAlign: "left",
                  fontSize: "12px",
                  padding: "8px 10px",
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  background: "#f8fafc",
                  cursor: "pointer",
                  color: "#334155",
                }}
              >
                🌾 <strong>2025 Scenario 1 (Mung Beans):</strong> Hambantota 3.5 ac (June 2025)
              </button>
              <button
                type="button"
                onClick={() => {
                  setDistrict("Hambantota");
                  setCrop("Corn");
                  setSeason("Yala");
                  setLandSize(49);
                  setPlantingDate("2025-05-15");
                  setHarvestDate("2025-08-15");
                  setSelectedModel("XGBoost");
                }}
                style={{
                  textAlign: "left",
                  fontSize: "12px",
                  padding: "8px 10px",
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  background: "#f8fafc",
                  cursor: "pointer",
                  color: "#334155",
                }}
              >
                🌽 <strong>2025 Scenario 2 (Corn):</strong> Hambantota 49 ac (May 2025)
              </button>
              <button
                type="button"
                onClick={() => {
                  setDistrict("Matara");
                  setCrop("Pumpkin");
                  setSeason("Maha");
                  setLandSize(1.5);
                  setPlantingDate("2025-01-10");
                  setHarvestDate("2025-04-20");
                  setSelectedModel("XGBoost");
                }}
                style={{
                  textAlign: "left",
                  fontSize: "12px",
                  padding: "8px 10px",
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  background: "#f8fafc",
                  cursor: "pointer",
                  color: "#334155",
                }}
              >
                🎃 <strong>2025 Maha Season:</strong> Matara Pumpkin 1.5 ac (Jan 2025)
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Results & Audit Diagnostic Display */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {error && (
            <div
              style={{
                background: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: "16px",
                padding: "16px 20px",
                color: "#991b1b",
                display: "flex",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <AlertCircle size={20} />
              <span style={{ fontSize: "13.5px" }}>{error}</span>
            </div>
          )}

          {!evaluation && !error && (
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
              <FlaskConical size={40} style={{ margin: "0 auto 12px", color: "#94a3b8" }} />
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#334155", margin: "0 0 6px 0" }}>
                Ready to Run Historical Scenario
              </h3>
              <p style={{ fontSize: "13px", maxWidth: "460px", margin: "0 auto", lineHeight: 1.5 }}>
                Configure historical dates (January 2025 through August 2026) and click &quot;Run Historical Evaluation&quot; to test the trained model against historical ASC data.
              </p>
            </div>
          )}

          {evaluation && <ResearchResult result={evaluation} previous={previousEvaluation} />}
        </div>
      </div>
    </div>
  );
}
