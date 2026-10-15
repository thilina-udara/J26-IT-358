"use client";
import { useState } from "react";
import { ArrowRight, BarChart3, RefreshCw } from "lucide-react";
import { NativeSelect } from "./ui/native-select";
import { Button } from "./ui/button";
import { useSession } from "./session";
import { Card, ErrorNotice, Field, Loading, Notice, WorkflowResult } from "./ui";
import type { Plan, Workflow } from "../lib/contracts";

export function AnalysisPanel({ plan }: { plan: Plan }) {
  const { api } = useSession(); const [season, setSeason] = useState(""); const [report, setReport] = useState<Workflow | null>(null); const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false);
  const researchAsOf = process.env.NEXT_PUBLIC_CULTIVATION_RESEARCH_AS_OF;
  async function analyze() { if (busy) return; setBusy(true); setError(null); setReport(null); try { setReport(await api.analyze(plan.plan_id, season || undefined, researchAsOf)); } catch (reason) { setError(reason); } finally { setBusy(false); } }
  return <div className="cp-stack"><Card title="Explore this plan’s evidence"><div className="cp-analysis-controls"><div><span className="cp-tool-icon"><BarChart3 size={22} aria-hidden="true" /></span><p>Run descriptive analysis for your saved crop and harvest window.</p>{researchAsOf && <Notice kind="warning">Research test cutoff: {researchAsOf}. This mode is enabled by the frontend environment and is not a live farmer assessment.</Notice>}</div><Field label="Season context" name="analysis-season" hint="An override changes analysis context, not your saved declaration."><NativeSelect id="analysis-season" aria-describedby="analysis-season-hint" value={season} onChange={event => { setSeason(event.target.value); setReport(null); }} disabled={busy}><option value="">Use saved declaration ({plan.farmer_declared_season ?? "unknown"})</option><option>Maha</option><option>Yala</option></NativeSelect></Field><Button disabled={busy || plan.status !== "active"} onClick={() => void analyze()}>{report ? <RefreshCw size={16} aria-hidden="true" /> : <ArrowRight size={16} aria-hidden="true" />}{busy ? "Evaluating evidence…" : report ? "Run analysis again" : "Run / retry analysis"}</Button></div>{plan.status === "cancelled" && <Notice kind="warning">Cancelled plans remain available as records, but cannot be analyzed as active plans.</Notice>}</Card><ErrorNotice error={error} />{busy && <Loading text="Evaluating the evidence for your plan…" />}{report && <WorkflowResult report={report} />}</div>;
}
