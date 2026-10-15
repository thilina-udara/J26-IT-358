"use client";
import PlanWorkspace from "../../../components/plan-workspace";
import { ComparisonPanel } from "../../../components/comparison-panel";
export default function Page({ params }: { params: { planId: string } }) { return <PlanWorkspace planId={params.planId} section="alternatives">{plan => <ComparisonPanel plan={plan} />}</PlanWorkspace>; }
