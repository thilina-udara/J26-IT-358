"use client";
import { Button } from "./ui/button";
import Link from "next/link";
import { useSession } from "./session";
import { ErrorNotice, Loading, PageTitle, Status, useLoad } from "./ui";
import type { Plan, SavedPlanning } from "../lib/contracts";

export default function PlanWorkspace({ planId, section, children }: { planId: string; section: "details" | "analysis" | "alternatives" | "planning"; children: (plan: Plan, saved: SavedPlanning | null, reload: () => void) => React.ReactNode }) {
  const { api } = useSession(); const result = useLoad(signal => api.read(planId, signal), [api, planId]);
  const root = `/crop-planning/plans/${encodeURIComponent(planId)}`;
  return <><Link href="/crop-planning/plans" className="cp-back">← My cultivation plans</Link><PageTitle eyebrow="SAVED CULTIVATION PLAN" title={result.data ? `${result.data.plan.crop} · ${result.data.plan.district}` : "Your cultivation plan"}>{result.data ? `${result.data.plan.region} · ${result.data.plan.land_size_acres} acres of your declared land` : "Loading your private record."}</PageTitle><nav className="cp-tabs" aria-label="Plan sections">{[{ key: "details", label: "Plan details", suffix: "" }, { key: "analysis", label: "Analysis", suffix: "/analysis" }, { key: "alternatives", label: "Crop comparison", suffix: "/alternatives" }, { key: "planning", label: "Cultivation schedule", suffix: "/planning" }].map(item => <Link href={root + item.suffix} key={item.key} aria-current={section === item.key ? "page" : undefined}>{item.label}</Link>)}</nav>{result.loading ? <Loading /> : result.error ? <div className="cp-stack"><ErrorNotice error={result.error} /><Button variant="outline" onClick={result.reload}>Retry loading</Button></div> : result.data && <><div className="cp-record-meta"><span className="cp-id">Plan ID: {result.data.plan.plan_id}</span><Status tone={result.data.plan.status === "active" ? "green" : "neutral"}>{result.data.plan.status}</Status></div>{children(result.data.plan, result.data.personalized_plan, result.reload)}</>}</>;
}
