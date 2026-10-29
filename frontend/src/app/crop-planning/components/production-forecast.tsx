"use client";
import React, { useEffect, useState } from "react";
import type { ProductionForecast, ProductionSeries } from "../lib/production-forecast";

const kg = (value: number | null) => value === null ? "Unavailable" : `${value.toLocaleString("en-US", { maximumFractionDigits: 0 })} kg`;

export function ProductionChart({ forecast: f }: { forecast: ProductionForecast }) {
  if (f.status !== "available" || f.expected_production_kg === null || !f.history.length) return null;
  const history = f.history, last = history[history.length - 1], first = history[0].year;
  const reference = f.reference_range_kg;
  const maximum = Math.max(1, f.expected_production_kg, reference?.upper ?? 0, ...history.flatMap(p => [p.production_kg, p.fitted_kg ?? 0])) * 1.08;
  const x = (year: number) => 90 + (year - first) / (f.forecast_year - first) * 770;
  const y = (amount: number) => 225 - amount / maximum * 195;
  const actual = history.map(p => `${x(p.year)},${y(p.production_kg)}`).join(" ");
  const trendPoints = f.model === "linear_trend" ? [...history.map(p => `${x(p.year)},${y(p.fitted_kg ?? 0)}`), `${x(f.forecast_year)},${y(f.expected_production_kg)}`].join(" ")
    : `${x(last.year)},${y(last.production_kg)} ${x(f.forecast_year)},${y(f.expected_production_kg)}`;
  return <figure className="mt-5">
    <svg viewBox="0 0 900 275" role="img" aria-label={`Recorded production in kilograms and 2026 forecast for ${f.crop}, ${f.district}, ${f.season}`} className="w-full bg-slate-50 border border-slate-200 rounded-xl">
      {[0, 1, 2, 3].map(i => { const value = maximum * i / 3; return <g key={i}><line x1="90" x2="860" y1={y(value)} y2={y(value)} stroke="#e2e8f0" /><text x="80" y={y(value) + 4} textAnchor="end" fontSize="11" fill="#475569">{new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value)}</text></g>; })}
      <text x="20" y="17" fontSize="11" fill="#475569">Production (kg)</text>
      <polyline points={actual} fill="none" stroke="#2563eb" strokeWidth="2.5" />
      <polyline points={trendPoints} fill="none" stroke="#047857" strokeWidth="2.5" strokeDasharray="7 5" />
      <line x1={x(f.forecast_year)} x2={x(f.forecast_year)} y1="25" y2="230" stroke="#b45309" strokeDasharray="4 4" />
      {reference && <g stroke="#64748b" strokeWidth="4"><line x1={x(f.forecast_year)} x2={x(f.forecast_year)} y1={y(reference.lower)} y2={y(reference.upper)} /><line x1={x(f.forecast_year) - 8} x2={x(f.forecast_year) + 8} y1={y(reference.lower)} y2={y(reference.lower)} /><line x1={x(f.forecast_year) - 8} x2={x(f.forecast_year) + 8} y1={y(reference.upper)} y2={y(reference.upper)} /></g>}
      {history.map(p => <circle key={p.year} cx={x(p.year)} cy={y(p.production_kg)} r="3" fill="#2563eb"><title>{`${p.year}: ${kg(p.production_kg)} recorded`}</title></circle>)}
      <circle cx={x(f.forecast_year)} cy={y(f.expected_production_kg)} r="6" fill="#b45309"><title>{`2026: ${kg(f.expected_production_kg)} forecast, not observed`}</title></circle>
      {[first, Math.round((first + f.forecast_year) / 2), f.forecast_year].map(year => <text key={year} x={x(year)} y="249" textAnchor="middle" fontSize="12" fill="#475569">{year}</text>)}
    </svg>
    <figcaption className="mt-2 text-xs text-slate-600">Blue: recorded historical production. Green dashed: {f.model === "naive" ? "previous-year naive forecast" : "fitted linear trend and extrapolation"}. Amber: 2026 forecast, not an actual observation. Grey: empirical historical-error reference range in kg.</figcaption>
  </figure>;
}

export function ProductionResult({ forecast: f }: { forecast: ProductionForecast }) {
  const available = f.status === "available" && f.expected_production_kg !== null && f.reference_range_kg !== null;
  return <div>
    <p className="mt-4 text-sm font-semibold text-slate-900">{f.crop} · {f.district} · {f.season} · forecast {f.forecast_year}</p>
    <p className="mt-1 text-xs font-semibold text-amber-900">Exploratory forecast from recorded production; measurement method and provenance unverified.</p>
    {available ? <>
      <ProductionChart forecast={f} />
      <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4"><dt className="text-xs text-slate-600">Expected production in 2026</dt><dd className="text-xl font-bold text-emerald-950 mt-1">{kg(f.expected_production_kg)}</dd></div>
        <div className="rounded-xl bg-slate-50 border border-slate-200 p-4"><dt className="text-xs text-slate-600">Empirical reference range (kg)</dt><dd className="text-lg font-bold text-slate-900 mt-1">{kg(f.reference_range_kg!.lower)} – {kg(f.reference_range_kg!.upper)}</dd></div>
        <div className="rounded-xl bg-slate-50 border border-slate-200 p-4"><dt className="text-xs text-slate-600">Historical selection-policy MAE</dt><dd className="text-lg font-bold text-slate-900 mt-1">{kg(f.evaluation?.selection_policy_mae_kg ?? null)}</dd></div>
      </dl>
      <p className="mt-4 text-sm font-semibold text-slate-800">Forecast model: {f.model_name}</p>
      <p className="mt-2 text-xs text-slate-600">Training years: {f.training_years.join(", ")}. Only recorded production through {f.training_cutoff_year} is used. Missing years are not imputed.</p>
      {f.evaluation && <div className="overflow-x-auto mt-4"><table className="w-full text-xs text-left"><caption className="text-left font-semibold text-slate-700 pb-2">Candidate rolling-origin errors (kg; lower MAE wins, ties prefer naive)</caption><thead><tr className="border-b border-slate-200"><th className="p-2">Model</th><th className="p-2">MAE (kg)</th><th className="p-2">2026 forecast (kg)</th><th className="p-2">Forecast years</th></tr></thead><tbody>{([['naive', 'Previous-year naive'], ['linear_trend', 'Linear regression trend']] as const).map(([name, label]) => <tr key={name} className="border-b border-slate-100"><td className="p-2">{label}{f.model === name ? " (selected for 2026)" : ""}</td><td className="p-2">{kg(f.evaluation!.candidate_mae_kg[name])}</td><td className="p-2">{kg(f.candidate_forecasts_kg?.[name] ?? null)}</td><td className="p-2">{f.evaluation!.candidate_years.join(", ")}</td></tr>)}</tbody></table></div>}
      <p className="mt-3 text-xs text-slate-600">The range adds the 10th/90th percentiles of {f.reference_range_kg!.calibration_count} earlier one-year errors to the 2026 forecast, with a zero lower limit. Each historical model choice uses only earlier errors. This is an empirical range for that selection procedure, not a validated 80% prediction interval or a guarantee.</p>
      {f.quality.forecast_floored_at_zero && <p className="mt-3 text-sm text-amber-900">The selected linear trend projected negative production and was constrained to zero. Treat this boundary forecast with caution.</p>}
    </> : <div role="status" className="mt-5 bg-amber-50 border border-amber-200 rounded-xl p-4"><p className="font-bold text-amber-950">Insufficient Data</p><p className="text-sm mt-1">{f.reason || "No supported production estimate is available."}</p></div>}
    <div className="mt-4 rounded-xl border border-slate-200 p-4"><p className="text-sm font-semibold">{f.planned_comparison.status}</p><p className="text-xs text-slate-600 mt-1">{f.planned_comparison.reason}</p></div>
    <details className="mt-4 text-xs text-slate-600"><summary className="cursor-pointer font-semibold">Source, method and scientific limitations</summary>
      <p className="mt-2">{f.source.designation}: {f.source.path}. Column: {f.source.quantity_column}; {f.source.input_unit} × {f.source.conversion_factor} = kilograms. {f.source.measurement_status}. {f.source.coverage}. {f.source.grain}.</p>
      <p className="mt-2">Source rows: {f.source.raw_rows}; seasonal rows: {f.source.seasonal_rows}; annual Total rows excluded: {f.source.annual_total_rows_excluded}. Duplicate rows ignored: {f.quality.duplicate_rows_ignored}. Missing years: {f.quality.missing_years.join(", ") || "None"}. Invalid years: {f.quality.invalid_years.join(", ") || "None"}.</p>
      {f.evaluation && <p className="mt-2">{f.evaluation.definition} Selection-policy evaluation years: {f.evaluation.policy_years.join(", ")}; naive MAE on those same years: {kg(f.evaluation.naive_same_period_mae_kg)}.</p>}
      {f.trend && <p className="mt-2">OLS baseline (kg) = max(0, {f.trend.level_kg.toFixed(2)} + {f.trend.slope_kg_per_year.toFixed(2)} × (year − {f.trend.center_year})).</p>}
      <ul className="list-disc pl-5 mt-2 space-y-1">{f.limitations.map(note => <li key={note}>{note}</li>)}</ul>
    </details>
  </div>;
}

export default function CropProductionForecast({ token, baseUrl }: { token: string | null; baseUrl: string }) {
  const [series, setSeries] = useState<ProductionSeries[]>([]);
  const [index, setIndex] = useState(0);
  const [forecast, setForecast] = useState<ProductionForecast | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    setSeries([]); setIndex(0); setForecast(null); setError(""); setLoading(true);
    fetch(`${baseUrl}/api/admin/analytics/production-forecast/options`, { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal, cache: "no-store" })
      .then(async r => { if (!r.ok) throw new Error(r.status === 401 ? "Please log in again as an officer or administrator." : "Production history could not be loaded."); return r.json(); })
      .then(data => { if (!controller.signal.aborted) { setSeries(data.series); if (!data.series.length) { setError("No recorded production series are available."); setLoading(false); } } })
      .catch(e => { if (!controller.signal.aborted) { setError(e.message); setLoading(false); } });
    return () => controller.abort();
  }, [baseUrl, token]);
  const group = series[index];
  useEffect(() => {
    if (!token || !group) return;
    const controller = new AbortController();
    setForecast(null); setError(""); setLoading(true);
    const params = new URLSearchParams({ crop: group.crop, district: group.district, season: group.season });
    fetch(`${baseUrl}/api/admin/analytics/production-forecast?${params}`, { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal, cache: "no-store" })
      .then(async r => { if (!r.ok) throw new Error(r.status === 401 ? "Please log in again as an officer or administrator." : "Production forecast is unavailable. Check the backend configuration."); return r.json(); })
      .then(data => { if (!controller.signal.aborted) setForecast(data); })
      .catch(e => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [baseUrl, token, group]);
  return <section aria-labelledby="production-forecast-title" className="bg-white border border-emerald-200 rounded-2xl p-5 md:p-7 shadow-sm">
    <div className="flex flex-wrap justify-between items-start gap-4"><div><h2 id="production-forecast-title" className="text-xl font-bold text-slate-900">2026 Crop Production Forecast (kg)</h2><p className="mt-1 text-sm text-slate-600">A seasonal production estimate from recorded historical quantities, separate from the hectares-based concentration analysis.</p></div><span className="bg-amber-100 text-amber-950 rounded-full px-3 py-1.5 text-xs font-bold">Exploratory forecast · 2026</span></div>
    <label className="block mt-5 text-xs font-semibold text-slate-700">Crop / district / season<select className="block mt-1 border border-slate-300 rounded-lg p-2 text-sm bg-white" value={index} disabled={!series.length} onChange={event => { setForecast(null); setIndex(Number(event.target.value)); }}>{series.map((s, i) => <option key={`${s.district}-${s.crop}-${s.season}`} value={i}>{s.crop} · {s.district} · {s.season}</option>)}</select></label>
    {loading && <p role="status" className="mt-5 text-sm text-slate-600">Loading production forecast…</p>}
    {error && <p role="alert" className="mt-5 text-sm text-red-800">{error}</p>}
    {!loading && !error && forecast && <ProductionResult forecast={forecast} />}
    <p className="mt-5 pt-4 border-t border-slate-200 text-xs text-slate-600">This forecast is a historical production reference, not a validated economic optimum or recommended production target. Market demand is unavailable. Above-reference production does not prove oversupply or market loss.</p>
  </section>;
}
