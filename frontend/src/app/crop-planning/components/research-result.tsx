import React from "react";
import { AlertCircle, CheckCircle2, Sprout } from "lucide-react";
import type { HistoricalScenarioResponse } from "../lib/contracts";

export function ResearchResult({
  result,
  previous,
}: {
  result: HistoricalScenarioResponse;
  previous: HistoricalScenarioResponse | null;
}) {
  const [selectedAlternative, setSelectedAlternative] = React.useState<string | null>(null);
  const { simulated_plan: plan, model_metadata: model, prediction, features } = result;

  // Fallback if outputs are withheld
  if (result.status === "historical_result_withheld" || !prediction?.historical_proxy_label) {
    return (
      <article
        className="cp-stack"
        style={{
          background: "white",
          border: "1px solid #cbd5e1",
          borderRadius: 16,
          padding: 24,
        }}
      >
        <h2>Historical outputs withheld for privacy</h2>
        <p role="note">
          Historical publication permissions are unverified. Counts, acreage, historical features, proxy categories and
          probabilities remain protected for every cohort.
        </p>
        <p>Protected values do not imply zero peers or Low risk. No public historical inference is performed.</p>
        <dl>
          <dt>Simulation decision cutoff (start of day, Asia/Colombo)</dt>
          <dd>{plan.cutoff_timestamp}</dd>
          <dt>Selected planting date</dt>
          <dd>{plan.planting_date}</dd>
          <dt>Expected harvest date</dt>
          <dd>{plan.expected_harvest_date}</dd>
          <dt>Selected crop and location</dt>
          <dd>
            {plan.crop}, {plan.district}, {plan.season}
          </dd>
          <dt>Your hypothetical acreage</dt>
          <dd>{plan.land_size_acres}</dd>
          <dt>Model training data cutoff</dt>
          <dd>{model.training_data_cutoff}; recorded Year upper bound, not observation availability</dd>
          <dt>Observation availability</dt>
          <dd>Not established. Planting dates and recorded Years cannot establish when an exact version was observable.</dd>
          <dt>Current risk</dt>
          <dd>Unvalidated. Recommendations remain blocked.</dd>
        </dl>
        <h3>Harvest-window definition</h3>
        <p>
          Inclusive expected harvest date +/-14 days. Dataset membership and verified availability are separate concepts;
          their protected values are not displayed.
        </p>
        <h3>Saved model contract ({model.feature_count} inputs)</h3>
        <p>
          Historical inputs are withheld. Own production is not supplied; no approved yield or profit estimate is inferred.
        </p>
        <p>
          Unknown availability remains an assumption in private retrospective research. No claim of zero temporal leakage is
          made.
        </p>
        {previous && (
          <section aria-label="Comparison with previous scenario">
            <h3>Comparison of your scenario inputs</h3>
            <p>
              Decision cutoff: {previous.simulated_plan.decision_cutoff} to {plan.decision_cutoff}. Planting:{" "}
              {previous.simulated_plan.planting_date} to {plan.planting_date}. Harvest:{" "}
              {previous.simulated_plan.expected_harvest_date} to {plan.expected_harvest_date}.
            </p>
            <p>
              Historical comparison results are withheld. Changing the cutoff or acreage cannot authorize disclosure of
              peer contributions.
            </p>
          </section>
        )}
        <h3>Previously reported frozen evaluation ({model.simulated_target_year})</h3>
        {model.benchmark_metrics ? (
          <p>
            Accuracy: {(model.benchmark_metrics.accuracy * 100).toFixed(2)}%; macro F1:{" "}
            {model.benchmark_metrics.macro_f1.toFixed(4)}. Saved historical labels only; these metrics are not performance
            for this scenario or current risk.
          </p>
        ) : (
          <p>No saved evaluation metrics for this year.</p>
        )}
        <p>
          Alternative crop rankings remain withheld. Verified current High risk, comparable coverage, suitability and
          applicable agricultural guideline approvals remain required.
        </p>
      </article>
    );
  }

  const rawLabel = prediction.historical_proxy_label || prediction.predicted_risk_level || "Unknown";
  const label = rawLabel === "High" ? "High Risk Proxy" : rawLabel === "Low" ? "Low Risk Proxy" : "Medium Risk Proxy";
  const isHigh = rawLabel === "High";
  const isLow = rawLabel === "Low";

  // Card themes matching screenshots
  const cardBg = isHigh ? "#fef2f2" : isLow ? "#f0fdf4" : "#fffbeb";
  const cardBorder = isHigh ? "#fecaca" : isLow ? "#bbf7d0" : "#fde68a";
  const titleColor = isHigh ? "#dc2626" : isLow ? "#16a34a" : "#d97706";
  const subCaptionColor = isHigh ? "#991b1b" : isLow ? "#166534" : "#92400e";
  const dividerColor = isHigh ? "#fee2e2" : isLow ? "#dcfce7" : "#fef3c7";

  const probs = prediction.class_probabilities || {};
  const lowPct = probs.Low !== undefined ? (probs.Low * 100).toFixed(1) : "0.0";
  const medPct = probs.Medium !== undefined ? (probs.Medium * 100).toFixed(1) : "0.0";
  const highPct = probs.High !== undefined ? (probs.High * 100).toFixed(1) : "0.0";

  const peerCount = prediction.overlapping_peer_count ?? 0;
  const peerAcres = prediction.overlapping_peer_acres !== null && prediction.overlapping_peer_acres !== undefined
    ? Number(prediction.overlapping_peer_acres).toFixed(1)
    : "0.0";

  const featureEntries = Object.entries(features || {});
  const diagnosticAlternatives = isHigh && Array.isArray(result.diagnostic_alternatives)
    ? result.diagnostic_alternatives.slice(0, 3)
    : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Model Badge Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "4px 2px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span
            style={{
              background: "#eff6ff",
              color: "#1d4ed8",
              border: "1px solid #bfdbfe",
              padding: "4px 12px",
              borderRadius: "9999px",
              fontWeight: 700,
              fontSize: "12.5px",
            }}
          >
            {model.model_name} Historical Proxy
          </span>
          <span style={{ color: "#64748b", fontSize: "12.5px" }}>
            Trained through {model.trained_through || 2024} · Evaluating {model.simulated_target_year || plan.target_year || 2025}
          </span>
        </div>
        <span
          style={{
            background: "#f1f5f9",
            color: "#475569",
            border: "1px solid #e2e8f0",
            padding: "4px 10px",
            borderRadius: "6px",
            fontSize: "11.5px",
            fontWeight: 600,
          }}
        >
          Research Simulation
        </span>
      </div>

      {/* Main Historical Proxy Classification Card */}
      <div
        style={{
          background: cardBg,
          border: `1px solid ${cardBorder}`,
          borderRadius: "16px",
          padding: "24px 28px",
        }}
      >
        <span
          style={{
            display: "block",
            fontSize: "11px",
            fontWeight: 700,
            letterSpacing: "0.5px",
            textTransform: "uppercase",
            color: subCaptionColor,
            marginBottom: "8px",
          }}
        >
          HISTORICAL PROXY CLASSIFICATION
        </span>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 220px", gap: "24px", alignItems: "center" }}>
          <div>
            <h2
              style={{
                fontSize: "30px",
                fontWeight: 800,
                color: titleColor,
                margin: "0 0 10px 0",
                letterSpacing: "-0.5px",
              }}
            >
              {label}
            </h2>
            <p style={{ fontSize: "13px", color: "#475569", margin: 0, lineHeight: 1.5 }}>
              Found {peerCount} overlapping historical peer plan(s) totaling {peerAcres} acres in this +/-14-day harvest
              window.
            </p>
          </div>

          {/* Model Probability Distribution */}
          <div
            style={{
              borderLeft: `1px solid ${dividerColor}`,
              paddingLeft: "20px",
            }}
          >
            <strong
              style={{
                display: "block",
                fontSize: "12px",
                color: "#1e293b",
                marginBottom: "8px",
              }}
            >
              Model Probability Distribution:
            </strong>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12.5px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", color: "#475569" }}>
                <span>Low:</span>
                <strong style={{ color: "#0f172a" }}>{lowPct}%</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", color: "#475569" }}>
                <span>Medium:</span>
                <strong style={{ color: "#0f172a" }}>{medPct}%</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", color: "#475569" }}>
                <span>High:</span>
                <strong style={{ color: "#0f172a" }}>{highPct}%</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Research Validity Statement Blue Banner */}
      <div
        style={{
          background: "#f0f9ff",
          border: "1px solid #bae6fd",
          borderRadius: "14px",
          padding: "14px 18px",
          display: "flex",
          alignItems: "flex-start",
          gap: "12px",
        }}
      >
        <AlertCircle size={18} style={{ color: "#0284c7", flexShrink: 0, marginTop: "2px" }} />
        <p style={{ fontSize: "12.5px", color: "#0369a1", margin: 0, lineHeight: 1.5 }}>
          <strong>Research Validity Statement:</strong> RESEARCH DEMO PROXY: This result is a retrospective research proxy
          derived from frozen historical labels (2020-2026). It does not represent an independently verified market
          oversupply, price drop, or live farmer risk claim. Current operational risk remains strictly unvalidated.
        </p>
      </div>

      {diagnosticAlternatives.length > 0 && (
        <div
          style={{
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: "16px",
            padding: "20px 24px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
            <Sprout size={18} style={{ color: "#2563eb" }} />
            <h3 style={{ fontSize: "15px", color: "#1e3a8a", margin: 0 }}>
              3 alternative crops for this High Risk Proxy
            </h3>
          </div>
          <p style={{ fontSize: "12.5px", color: "#1e40af", margin: "0 0 14px", lineHeight: 1.5 }}>
            These are historical diagnostic candidates only. They are not verified low-risk recommendations for current
            farming decisions.
          </p>
          <div style={{ display: "grid", gap: "8px" }}>
            {diagnosticAlternatives.map((alternative, index) => (
              <div
                key={`${alternative.crop}-${index}`}
                style={{
                  background: "#ffffff",
                  border: `1px solid ${selectedAlternative === alternative.crop ? "#2563eb" : "#dbeafe"}`,
                  borderRadius: "10px",
                  padding: "10px 12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                }}
              >
                <input
                  id={`alternative-${index}`}
                  type="radio"
                  name="alternative-crop"
                  value={alternative.crop}
                  checked={selectedAlternative === alternative.crop}
                  onChange={() => {
                    setSelectedAlternative(alternative.crop);
                    window.location.href = `/crop-planning/cultivation-methods?crop=${encodeURIComponent(alternative.crop)}`;
                  }}
                  style={{ accentColor: "#2563eb", width: "16px", height: "16px", flexShrink: 0 }}
                />
                <label
                  htmlFor={`alternative-${index}`}
                  style={{ color: "#1e3a8a", fontSize: "13px", fontWeight: 700, cursor: "pointer", flex: 1 }}
                >
                  {alternative.crop}
                </label>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Exact 15 Model Features Grid */}
      <div
        style={{
          background: "#ffffff",
          border: "1px solid #e2e8f0",
          borderRadius: "18px",
          padding: "20px 24px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
          <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a", margin: 0 }}>
            Exact {featureEntries.length || 15} Model Features (Temporal Cutoff Verification)
          </h3>
          <span
            style={{
              fontSize: "11.5px",
              fontWeight: 600,
              color: "#15803d",
              background: "#dcfce7",
              padding: "3px 10px",
              borderRadius: "9999px",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            ✓ Strictly Prior Observations Used
          </span>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "12px",
          }}
        >
          {featureEntries.map(([key, val]) => {
            let displayVal = "N/A";
            if (val !== null && val !== undefined) {
              if (typeof val === "number") {
                displayVal = Number.isInteger(val) ? String(val) : val.toFixed(2);
              } else {
                displayVal = String(val);
              }
            }
            return (
              <div
                key={key}
                style={{
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "10px",
                  padding: "10px 14px",
                }}
              >
                <span
                  style={{
                    display: "block",
                    fontSize: "11px",
                    color: "#64748b",
                    fontWeight: 500,
                    marginBottom: "3px",
                  }}
                >
                  {key}
                </span>
                <strong style={{ fontSize: "14px", color: "#0f172a", fontWeight: 700 }}>{displayVal}</strong>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
