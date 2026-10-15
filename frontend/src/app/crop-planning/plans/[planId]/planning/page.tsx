"use client";
import PlanWorkspace from "../../../components/plan-workspace";
import { PlanningPanel } from "../../../components/planning-panel";
export default function Page({ params }: { params: { planId: string } }) { return <PlanWorkspace planId={params.planId} section="planning">{(plan, saved) => <PlanningPanel plan={plan} saved={saved} />}</PlanWorkspace>; }
