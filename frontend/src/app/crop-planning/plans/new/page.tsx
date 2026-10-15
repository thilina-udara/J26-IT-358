"use client";
import { Button } from "../../components/ui/button";
import { useState } from "react";
import Link from "next/link";
import PlanForm from "../../components/plan-form";
import { Card, Notice, PageTitle, WorkflowResult } from "../../components/ui";
import type { Submission } from "../../lib/contracts";
import { submissionOutcome } from "../../lib/evidence";

export default function NewPlanPage() {
  const [saved, setSaved] = useState<Submission | null>(null);
  return <><PageTitle eyebrow="CULTIVATION REGISTRATION" title={saved ? "Your plan has been saved." : "What are you planning to grow?"}>Record your next cultivation cycle. Analysis runs after your plan is saved.</PageTitle>{saved ? <div className="cp-stack"><Notice kind="success">Saved plan ID: <strong className="cp-id">{submissionOutcome(saved).planId}</strong> · {saved.plan.status}</Notice><WorkflowResult report={saved.workflow} /><div className="cp-actions"><Button asChild><Link href={`/crop-planning/plans/${encodeURIComponent(saved.plan.plan_id)}/analysis`}>{saved.workflow.analysis_status === "failed" ? "Retry saved-plan analysis" : "Open saved-plan analysis"}</Link></Button><Button asChild variant="outline"><Link href={`/crop-planning/plans/${encodeURIComponent(saved.plan.plan_id)}`}>View plan details</Link></Button><Link href="/crop-planning/plans">My plans →</Link></div></div> : <Card title="Cultivation details"><PlanForm onSaved={result => setSaved(result as Submission)} /></Card>}</>;
}
