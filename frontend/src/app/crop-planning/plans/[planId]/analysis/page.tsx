"use client";
import PlanWorkspace from "../../../components/plan-workspace";
import { AnalysisPanel } from "../../../components/analysis-panel";
export default function Page({ params }: { params: { planId: string } }) { return <PlanWorkspace planId={params.planId} section="analysis">{plan => <AnalysisPanel plan={plan} />}</PlanWorkspace>; }
