"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, Plus } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, Notice, PageTitle, WorkflowResult } from "../components/ui";
import PlanForm from "../components/plan-form";
import PlanSelector from "../components/plan-selector";
import { PlanningPanel } from "../components/planning-panel";
import type { Submission } from "../lib/contracts";

export default function CultivationPlanPage() {
  const [tab, setTab] = useState<"schedule" | "register">("schedule");
  const [saved, setSaved] = useState<Submission | null>(null);
  const [newRecord, setNewRecord] = useState(0);
  return <div className="cp-stack">
    <PageTitle eyebrow="YOUR CULTIVATION WORKSPACE" title="Plan your next season with approved guidance.">
      Keep your saved intentions visible and request activities for their actual planning context.
    </PageTitle>
    <div className="cp-workspace-switch" aria-label="Choose a planning workspace">
      <Button variant={tab === "schedule" ? "default" : "outline"} aria-pressed={tab === "schedule"} onClick={() => setTab("schedule")}>
        <CalendarDays size={16} aria-hidden="true" />Personalized schedule
      </Button>
      <Button variant={tab === "register" ? "default" : "outline"} aria-pressed={tab === "register"} onClick={() => setTab("register")}>
        <Plus size={16} aria-hidden="true" />Register cultivation
      </Button>
    </div>
    {tab === "register" ? saved ? <div className="cp-stack">
      <Notice kind="success"><strong>Your {saved.plan.crop} plan is saved.</strong><p>Plan ID: <span className="cp-id">{saved.plan.plan_id}</span></p></Notice>
      <WorkflowResult report={saved.workflow} />
      <div className="cp-actions">
        <Button asChild><Link href={`/crop-planning/plans/${encodeURIComponent(saved.plan.plan_id)}/analysis`}>
          {saved.workflow.analysis_status === "failed" ? "Retry saved-plan analysis" : "Open analysis"}<ArrowRight size={16} aria-hidden="true" />
        </Link></Button>
        <Button variant="outline" onClick={() => setTab("schedule")}>Open planning workspace</Button>
        <Button variant="ghost" onClick={() => setSaved(null)}>Register a different plan</Button>
      </div>
    </div> : <Card title="Your cultivation intentions">
      <PlanForm onSaved={result => { setSaved(result as Submission); setNewRecord(value => value + 1); }} />
    </Card> : <>
      <Notice>Partial planning is available. Approved guidance may be unavailable for your location, variety, planting method or season. Current risk level not yet validated.</Notice>
      <PlanSelector refreshKey={newRecord}>{(plan, planning) => <PlanningPanel key={plan.plan_id} plan={plan} saved={planning} />}</PlanSelector>
    </>}
  </div>;
}
