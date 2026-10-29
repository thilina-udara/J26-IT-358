"use client";
import React, { useEffect, useState } from "react";
import type { TrendAnalysis, TrendSeries } from "../lib/historical-trend";

const amount = (value: number | null, unit = "ha") => value === null ? "Unavailable" : `${value.toLocaleString("en-US", { maximumFractionDigits: 2 })} ${unit}`;
const percent = (value: number | null) => value === null ? "Unavailable" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;

export function TrendChart({ analysis }: { analysis: TrendAnalysis }) {
  const points = analysis.history;
  if (points.length < 2) return null;
  const start = points[0].year, end = points[points.length - 1].year;
  const values = points.flatMap(p => [p.hectares, ...(p.fitted_hectares === null ? [] : [p.fitted_hectares])]);
  const minimum = Math.min(0, ...values), maximum = Math.max(1, ...values) * 1.08;
  const x = (year: number) => 70 + (year - start) / Math.max(1, end - start) * 790;
  const y = (value: number) => 225 - (value - minimum) / (maximum - minimum) * 195;
  const actual = points.map(p => `${x(p.year)},${y(p.hectares)}`).join(" ");
  const fitted = points.filter(p => p.fitted_hectares !== null).map(p => `${x(p.year)},${y(p.fitted_hectares!)}`).join(" ");
  return <figure className="mt-5">
    <svg viewBox="0 0 900 275" role="img" aria-label={`Historical cultivated extent and fitted trend for ${analysis.crop}, ${analysis.district}, ${analysis.season}; held-out year ${analysis.evaluation_year}`} className="w-full rounded-xl bg-slate-50 border border-slate-200">
      {[0, 1, 2, 3].map(i => { const value = minimum + (maximum - minimum) * i / 3; return <g key={i}>
        <line x1="70" x2="860" y1={y(value)} y2={y(value)} stroke="#e2e8f0" />
        <text x="62" y={y(value) + 4} textAnchor="end" fontSize="11" fill="#475569">{value.toFixed(0)}</text>
      </g>; })}
      <text x="18" y="17" fontSize="11" fill="#475569">Hectares</text>
      <polyline points={actual} stroke="#2563eb" strokeWidth="2.5" fill="none" />
      {fitted && <polyline points={fitted} stroke="#047857" strokeWidth="2.5" strokeDasharray="7 5" fill="none" />}
      <line x1={x(analysis.evaluation_year)} x2={x(analysis.evaluation_year)} y1="25" y2="230" stroke="#b45309" strokeDasharray="4 4" />
      {points.map(p => <circle key={p.year} cx={x(p.year)} cy={y(p.hectares)} r={p.year === analysis.evaluation_year ? 5 : 3} fill={p.year === analysis.evaluation_year ? "#b45309" : "#2563eb"}>
        <title>{`${p.year}: ${amount(p.hectares)}${p.year === analysis.evaluation_year ? " (held out)" : ""}`}</title>
      </circle>)}
      {[start, Math.round((start + end) / 2), end].map(year => <text key={year} x={x(year)} y="249" textAnchor="middle" fontSize="12" fill="#475569">{year}</text>)}
    </svg>
    <figcaption className="text-xs text-slate-600 mt-2">Blue: recorded seasonal cultivated extent. Green dashed: OLS trend fitted only to earlier years. Amber: held-out observation, excluded from fitting and thresholds. Missing years are not imputed.</figcaption>
  </figure>;
}

export function TrendResult({ analysis }: { analysis: TrendAnalysis }) {
  const a = analysis;
  const available = a.status === "available" && a.category !== null && a.thresholds !== null;
  return <div>
    <p className="text-sm font-semibold text-slate-800 mt-4">{a.crop} · {a.district} · {a.season} · held-out {a.evaluation_year}</p>
    <p className="text-xs font-semibold text-amber-900 mt-1">{a.mode} — recorded-year split; publication availability unverified</p>
    <TrendChart analysis={a} />
    <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
      {[["Forecast baseline", amount(a.baseline_hectares)], ["Observed full-season cumulative extent", amount(a.observed_hectares)], ["Deviation from trend", percent(a.deviation_percent)]].map(([label, value]) => <div key={label} className="rounded-xl border border-slate-200 p-4 bg-slate-50"><dt className="text-xs text-slate-600">{label}</dt><dd className="text-lg font-bold text-slate-900 mt-1">{value}</dd></div>)}
    </dl>
    {available && a.thresholds ? <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
      <p className="font-bold text-emerald-950">{a.category} relative historical concentration</p>
      <p className="text-sm text-slate-700 mt-2">Low: below {percent(a.thresholds.lower_percent)} ({amount(a.thresholds.lower_hectares)}). Medium: {percent(a.thresholds.lower_percent)} to {percent(a.thresholds.upper_percent)}. High: above {percent(a.thresholds.upper_percent)} ({amount(a.thresholds.upper_hectares)}).</p>
      <p className="text-xs text-slate-600 mt-2">Boundaries are the 1/3 and 2/3 empirical quantiles of {a.calibration.length} earlier one-year-ahead percentage errors (linear interpolation). Equal boundary values belong to Medium. These relative bands are not validated risk cutoffs or prediction intervals.</p>
    </div> : <div role="status" className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-xl"><p className="font-bold text-amber-950">Insufficient Data</p><p className="text-sm mt-1">{a.reason || "No defensible classification is available."}</p></div>}
    <p className="mt-4 text-xs text-slate-600">Training years: {a.training_years.join(", ") || "None"}. Calibration years: {a.calibration.map(p => p.year).join(", ") || "None"}. Minimum initial fit: 5 observations; minimum calibration: 8 errors.</p>
    {a.trend && <p className="mt-2 text-xs text-slate-600">Trend (ha) = {a.trend.intercept_hectares.toFixed(4)} + {a.trend.slope_hectares_per_year.toFixed(4)} × (year − {a.trend.center_year.toFixed(2)}). Deviation = (observed / baseline − 1) × 100.</p>}
    <details className="mt-4 text-xs text-slate-600"><summary className="cursor-pointer font-semibold">Data source, coverage and limitations</summary>
      <p className="mt-2">{a.source.designation}: {a.source.path}. Unit: hectares. Grain: {a.source.grain}. {a.source.period}. {a.source.coverage}.</p>
      <p className="mt-2">Source rows: {a.source.raw_rows}; seasonal rows: {a.source.seasonal_rows}; annual Total rows excluded: {a.source.annual_total_rows_excluded}. Duplicate rows ignored: {a.quality.duplicate_rows_ignored}. Missing years: {a.quality.missing_years.join(", ") || "None"}. Invalid years: {a.quality.invalid_years.join(", ") || "None"}. Extreme residual years retained: {a.quality.extreme_residual_years?.join(", ") || "None"}.</p>
      <ul className="list-disc pl-5 mt-2 space-y-1">{a.limitations.map(note => <li key={note}>{note}</li>)}</ul>
    </details>
  </div>;
}

export default function HistoricalTrendAnalysis({ token, baseUrl }: { token: string | null; baseUrl: string }) {
  const [series, setSeries] = useState<TrendSeries[]>([]);
  const [selected, setSelected] = useState(0);
  const [year, setYear] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<TrendAnalysis | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    setAnalysis(null); setSeries([]); setYear(null); setSelected(0); setError(""); setLoading(true);
    fetch(`${baseUrl}/api/admin/analytics/historical-trend/options`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store", signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error(response.status === 401 ? "Please log in again as an officer or administrator." : "Historical series could not be loaded."); return response.json(); })
      .then(data => { if (!controller.signal.aborted) { setSeries(data.series); setYear(data.series[0]?.years.at(-1) ?? null); if (!data.series.length) { setError("No seasonal historical series are available."); setLoading(false); } } })
      .catch(e => { if (!controller.signal.aborted) { setError(e.message); setLoading(false); } });
    return () => controller.abort();
  }, [baseUrl, token]);
  const group = series[selected];
  useEffect(() => {
    if (!token || !group || year === null) return;
    const controller = new AbortController();
    setAnalysis(null); setError(""); setLoading(true);
    const params = new URLSearchParams({ district: group.district, crop: group.crop, season: group.season, evaluation_year: String(year) });
    fetch(`${baseUrl}/api/admin/analytics/historical-trend?${params}`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store", signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error(response.status === 401 ? "Please log in again as an officer or administrator." : "Historical analysis is unavailable. Retry after checking backend configuration."); return response.json(); })
      .then(data => { if (!controller.signal.aborted) setAnalysis(data); })
      .catch(e => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [baseUrl, token, group, year]);
  return <section aria-labelledby="historical-trend-title" className="bg-white border border-emerald-200 rounded-2xl p-5 md:p-7 shadow-sm">
    <div className="flex flex-wrap justify-between items-start gap-4"><div><h2 id="historical-trend-title" className="text-xl font-bold text-slate-900">Historical Trend-Based Concentration Analysis</h2><p className="mt-1 text-sm text-slate-600">Compare an observed historical district season with a trend and thresholds estimated from earlier years.</p></div><span className="text-xs font-bold bg-amber-100 text-amber-950 px-3 py-1.5 rounded-full">Historical backtest · exploratory</span></div>
    <div className="flex flex-wrap gap-4 mt-5">
      <label className="text-xs font-semibold text-slate-700">Crop / district / season<select className="block mt-1 border border-slate-300 rounded-lg p-2 text-sm bg-white" value={selected} disabled={!series.length} onChange={e => { const index = Number(e.target.value); setAnalysis(null); setSelected(index); setYear(series[index].years.at(-1)!); }}>
        {series.map((s, index) => <option key={`${s.district}-${s.crop}-${s.season}`} value={index}>{s.crop} · {s.district} · {s.season}</option>)}
      </select></label>
      <label className="text-xs font-semibold text-slate-700">Held-out year<select className="block mt-1 border border-slate-300 rounded-lg p-2 text-sm bg-white" disabled={!group} value={year ?? ""} onChange={e => { setAnalysis(null); setYear(Number(e.target.value)); }}>{group?.years.map(value => <option key={value} value={value}>{value}</option>)}</select></label>
    </div>
    {loading && <p role="status" className="text-sm text-slate-600 mt-5">Loading historical trend…</p>}
    {error && <p role="alert" className="text-sm text-red-800 mt-5">{error}</p>}
    {!loading && !error && analysis && <TrendResult analysis={analysis} />}
    <p className="text-xs text-slate-600 border-t border-slate-200 mt-5 pt-4">XGBoost is a separate offline historical research classifier. This section uses a separate linear trend analysis. K-Means and DBSCAN describe clusters; they do not validate risk. Existing live farmer risk remains rule-based and subject to its evidence and privacy checks. Historical deviation does not prove market oversupply or economic loss.</p>
  </section>;
}
