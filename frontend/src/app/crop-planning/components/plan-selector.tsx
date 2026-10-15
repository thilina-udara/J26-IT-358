"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, MapPin, RefreshCw, Sprout } from "lucide-react";
import { useSession } from "./session";
import { Button } from "./ui/button";
import { NativeSelect } from "./ui/native-select";
import { Card, Empty, ErrorNotice, Field, Loading, Status, useLoad } from "./ui";
import { formatDate } from "../lib/dates";
import type { Plan, SavedPlanning } from "../lib/contracts";

export function PlanSummary({ plan }: { plan: Plan }) {
  return <div className="cp-selected-plan"><div className="cp-selected-title"><span className="cp-icon-tile"><Sprout size={25} aria-hidden="true" /></span><div><strong>{plan.crop}</strong><span><MapPin size={13} aria-hidden="true" />{plan.district} · {plan.region}</span></div><Status tone={plan.status === "active" ? "green" : "neutral"}>{plan.status === "active" ? "Active plan" : "Cancelled"}</Status></div><dl className="cp-plan-facts"><div><dt>Your land size</dt><dd>{plan.land_size_acres} acres</dd></div><div><dt>Planting</dt><dd>{formatDate(plan.planting_date)}</dd></div><div><dt>Expected harvest</dt><dd>{formatDate(plan.expected_harvest_date)}</dd></div><div><dt>Declared season</dt><dd>{plan.farmer_declared_season ?? "Not declared"}</dd></div></dl><Link className="cp-subtle-link" href={`/crop-planning/plans/${encodeURIComponent(plan.plan_id)}`}>View record & revisions<ArrowRight size={14} aria-hidden="true" /></Link></div>;
}
function Selected({ planId, children }: { planId: string; children: (plan: Plan, saved: SavedPlanning | null) => React.ReactNode }) {
  const { api } = useSession(); const result = useLoad(signal => api.read(planId, signal), [api, planId]);
  if (result.loading) return <Loading text="Opening your cultivation record…" />;
  if (result.error) return <><ErrorNotice error={result.error} /><Button variant="outline" onClick={result.reload}><RefreshCw size={15} aria-hidden="true" />Retry loading</Button></>;
  if (!result.data) return null;
  return <div className="cp-stack"><PlanSummary plan={result.data.plan} />{children(result.data.plan, result.data.personalized_plan)}</div>;
}
export default function PlanSelector({ children, refreshKey = 0, includeCancelled = false }: { children: (plan: Plan, saved: SavedPlanning | null) => React.ReactNode; refreshKey?: number; includeCancelled?: boolean }) {
  const { api } = useSession(); const [offset, setOffset] = useState(0); const [selected, setSelected] = useState("");
  const result = useLoad(signal => api.list(new URLSearchParams({ limit: "8", offset: String(offset), ...(includeCancelled ? {} : { status: "active" }) }), signal), [api, offset, refreshKey, includeCancelled]);
  return <div className="cp-stack"><Card title="Choose your cultivation plan"><div className="cp-picker-heading"><p className="cp-muted">Start with a record from your own farm.</p><Button variant="ghost" size="sm" aria-label="Refresh your plans" onClick={() => { setSelected(""); result.reload(); }}><RefreshCw size={15} aria-hidden="true" />Refresh</Button></div><ErrorNotice error={result.error} />{result.loading ? <Loading text="Finding your cultivation plans…" /> : result.error ? <Button variant="outline" onClick={result.reload}>Retry loading</Button> : !result.data?.items.length ? <Empty title="Your next season starts here"><p>Register a cultivation plan to explore analysis and approved planning activities.</p><Button asChild><Link href="/crop-planning/plans/new">Register a plan<ArrowRight size={16} aria-hidden="true" /></Link></Button></Empty> : <Field label="Cultivation plan" name="selected-plan"><NativeSelect id="selected-plan" value={selected} onChange={event => setSelected(event.target.value)}><option value="">Choose a saved plan…</option>{result.data.items.map(plan => <option key={plan.plan_id} value={plan.plan_id}>{plan.crop} · {plan.district} · {formatDate(plan.planting_date)}{plan.status === "cancelled" ? " · cancelled" : ""}</option>)}</NativeSelect></Field>}{result.data && result.data.total > 8 && <div className="cp-pagination"><span>{result.data.total} of your plans</span><div className="cp-actions"><Button variant="outline" size="sm" disabled={offset === 0} onClick={() => { setSelected(""); setOffset(Math.max(0, offset - 8)); }}>Previous</Button><Button variant="outline" size="sm" disabled={!result.data.has_more} onClick={() => { setSelected(""); setOffset(result.data!.next_offset!); }}>Next</Button></div></div>}</Card>{selected ? <Selected key={`${selected}-${refreshKey}`} planId={selected}>{children}</Selected> : result.data?.items.length ? <div className="cp-workspace-placeholder"><CalendarDays size={26} aria-hidden="true" /><h3>One plan. A clearer picture.</h3><p>Choose a record above to open its evidence and planning context.</p></div> : null}</div>;
}
