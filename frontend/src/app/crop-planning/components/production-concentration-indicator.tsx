"use client";
import React, { useEffect, useState } from "react";
import type { ConcentrationSeries, ProductionConcentrationIndicator } from "../lib/production-concentration-indicator";

const kg = (value: number | null) => value === null ? "Unavailable" : `${value.toLocaleString("en-US", { maximumFractionDigits: 0 })} kg`;
const percent = (value: number | null) => value === null ? "Unavailable" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;

export default function ProductionConcentrationIndicator({ token, baseUrl }: { token: string | null; baseUrl: string }) {
  const [series, setSeries] = useState<ConcentrationSeries[]>([]);
  const [index, setIndex] = useState(0);
  const [indicator, setIndicator] = useState<ProductionConcentrationIndicator | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    setSeries([]); setIndex(0); setIndicator(null); setError(""); setLoading(true);
    fetch(`${baseUrl}/api/admin/analytics/production-concentration-indicator/options`, { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal, cache: "no-store" })
      .then(async response => { if (!response.ok) throw new Error(response.status === 401 ? "Please log in again as an officer or administrator." : "Indicator series could not be loaded."); return response.json(); })
      .then(data => { if (!controller.signal.aborted) { setSeries(data.series); if (!data.series.length) { setError("No historical production series are available."); setLoading(false); } } })
      .catch(reason => { if (!controller.signal.aborted) { setError(reason.message); setLoading(false); } });
    return () => controller.abort();
  }, [baseUrl, token]);

  const selected = series[index];
  useEffect(() => {
    if (!token || !selected) return;
    const controller = new AbortController();
    setIndicator(null); setError(""); setLoading(true);
    const params = new URLSearchParams({ district: selected.district, crop: selected.crop, season: selected.season });
    fetch(`${baseUrl}/api/admin/analytics/production-concentration-indicator?${params}`, { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal, cache: "no-store" })
      .then(async response => { if (!response.ok) throw new Error(response.status === 401 ? "Please log in again as an officer or administrator." : "Production concentration indicator is unavailable."); return response.json(); })
      .then(data => { if (!controller.signal.aborted) setIndicator(data); })
      .catch(reason => { if (!controller.signal.aborted) setError(reason.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [baseUrl, token, selected]);

  const available = indicator?.status === "available" && indicator.forecast_2026_kg !== null;
  return <section aria-labelledby="production-concentration-indicator-title" className="bg-white border border-amber-200 rounded-2xl p-5 md:p-7 shadow-sm">
    <div className="flex flex-wrap justify-between items-start gap-4">
      <div>
        <h2 id="production-concentration-indicator-title" className="text-xl font-bold text-slate-900">2026 Forecast-Based Cultivation Concentration Indicator</h2>
        <p className="mt-1 text-sm text-slate-600">A historical production comparison independent of registered farmer participation.</p>
      </div>
      <span className="bg-amber-100 text-amber-950 rounded-full px-3 py-1.5 text-xs font-bold">Relative indicator · exploratory</span>
    </div>
    <label className="block mt-5 text-xs font-semibold text-slate-700">Crop / district / season
      <select className="block mt-1 border border-slate-300 rounded-lg p-2 text-sm bg-white" value={index} disabled={!series.length} onChange={event => { setIndicator(null); setIndex(Number(event.target.value)); }}>
        {series.map((item, itemIndex) => <option key={`${item.district}-${item.crop}-${item.season}`} value={itemIndex}>{item.crop} · {item.district} · {item.season}</option>)}
      </select>
    </label>
    {loading && <p role="status" className="mt-5 text-sm text-slate-600">Calculating historical production indicator…</p>}
    {error && <p role="alert" className="mt-5 text-sm text-red-800">{error}</p>}
    {!loading && !error && indicator && (available ? <>
      <p className="mt-4 text-sm font-semibold text-slate-800">{indicator.crop} · {indicator.district} · {indicator.season} · {indicator.forecast_year}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
        {[["2026 forecast production", kg(indicator.forecast_2026_kg)], ["Historical reference", kg(indicator.historical_reference_kg)], ["Forecast deviation", percent(indicator.deviation_percent)], ["Relative category", indicator.category || "Unavailable"]].map(([label, value]) => <div key={label} className="rounded-xl bg-slate-50 border border-slate-200 p-4"><dt className="text-xs text-slate-600">{label}</dt><dd className="text-lg font-bold text-slate-900 mt-1">{value}</dd></div>)}
      </div>
      <div className="mt-4 rounded-xl bg-emerald-50 border border-emerald-200 p-4">
        <p className="font-bold text-emerald-950">{indicator.category} relative historical production concentration</p>
        <p className="text-sm text-slate-700 mt-2">Empirical boundaries: Low below {percent(indicator.lower_threshold_percent)}; Medium from {percent(indicator.lower_threshold_percent)} through {percent(indicator.upper_threshold_percent)}; High above {percent(indicator.upper_threshold_percent)}.</p>
        <p className="text-xs text-slate-600 mt-2">Calibration sample: {indicator.calibration_sample_count} historical one-year-ahead evaluations ({indicator.calibration_years.join(", ")}).</p>
      </div>
      <details className="mt-4 text-xs text-slate-600"><summary className="cursor-pointer font-semibold">How this is calculated and limitations</summary>
        <p className="mt-2">{indicator.method_description} The reference uses recorded years {indicator.reference_years.join(", ")}. The selected 2026 method is {indicator.selected_forecast_method}.</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">{indicator.limitations.map(note => <li key={note}>{note}</li>)}</ul>
      </details>
    </> : <div role="status" className="mt-5 bg-amber-50 border border-amber-200 rounded-xl p-4"><p className="font-bold text-amber-950">Insufficient historical evidence</p><p className="text-sm mt-1">{indicator.reason || "No defensible relative category is available."}</p></div>)}
  </section>;
}
