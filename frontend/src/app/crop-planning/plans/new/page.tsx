"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { Button } from "../../components/ui/button";
import PlanForm from "../../components/plan-form";
import { Card, Notice, PageTitle, WorkflowResult } from "../../components/ui";
import type { Plan, Submission } from "../../lib/contracts";
import { submissionOutcome } from "../../lib/evidence";

export default function NewPlanPage() {
  const router = useRouter();
  const [saved, setSaved] = useState<Submission | null>(null);

  function handleSaved(result: Submission | { plan: Plan }) {
    const sub = result as Submission;
    setSaved(sub);
    const planId = sub.plan?.plan_id;
    if (planId && sub.workflow?.analysis_status !== "failed") {
      router.push(`/crop-planning/risk-analysis?plan_id=${encodeURIComponent(planId)}`);
    }
  }

  useEffect(() => {
    if (saved?.plan?.plan_id && saved.workflow?.analysis_status !== "failed") {
      router.push(`/crop-planning/risk-analysis?plan_id=${encodeURIComponent(saved.plan.plan_id)}`);
    }
  }, [saved, router]);

  return (
    <>
      <PageTitle
        eyebrow="CULTIVATION REGISTRATION"
        title={saved ? "Your plan has been saved." : "What are you planning to grow?"}
      >
        Record your next cultivation cycle. Analysis runs after your plan is saved.
      </PageTitle>

      {saved ? (
        saved.workflow?.analysis_status === "failed" ? (
          <div className="cp-stack">
            <Notice kind="success">
              Saved plan ID: <strong className="cp-id">{submissionOutcome(saved).planId}</strong> ·{" "}
              {saved.plan.status}
            </Notice>
            <WorkflowResult report={saved.workflow} />
            <div className="cp-actions">
              <Button asChild>
                <Link
                  href={`/crop-planning/plans/${encodeURIComponent(saved.plan.plan_id)}/analysis`}
                >
                  Retry saved-plan analysis
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href={`/crop-planning/plans/${encodeURIComponent(saved.plan.plan_id)}`}>
                  View plan details
                </Link>
              </Button>
              <Link href="/crop-planning/plans">My plans →</Link>
            </div>
          </div>
        ) : (
          <div
            style={{
              background: "#ffffff",
              borderRadius: "20px",
              padding: "44px 32px",
              border: "1px solid #e2e8f0",
              textAlign: "center",
              boxShadow: "0 4px 16px rgba(0,0,0,0.03)",
              maxWidth: "580px",
              margin: "32px auto",
            }}
          >
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "18px",
                background: "#dcfce7",
                color: "#166534",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 16px auto",
              }}
            >
              <CheckCircle2 size={30} />
            </div>

            <h2
              style={{
                fontSize: "20px",
                fontWeight: 800,
                color: "#0f172a",
                margin: "0 0 6px 0",
              }}
            >
              Plan Saved! Calculating Risk Level...
            </h2>
            <p
              style={{
                color: "#64748b",
                fontSize: "13.5px",
                margin: "0 0 20px 0",
                lineHeight: 1.5,
              }}
            >
              Redirecting you to the calculated Risk Analysis for your{" "}
              <strong style={{ color: "#0f172a" }}>{saved.plan.crop}</strong> plan...
            </p>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "12px",
              }}
            >
              <Button
                asChild
                style={{
                  background: "#166534",
                  color: "#ffffff",
                  borderRadius: "10px",
                  padding: "10px 22px",
                  fontSize: "13.5px",
                  fontWeight: 700,
                }}
              >
                <Link
                  href={`/crop-planning/risk-analysis?plan_id=${encodeURIComponent(
                    saved.plan.plan_id
                  )}`}
                >
                  View Calculated Risk Level →
                </Link>
              </Button>
            </div>
          </div>
        )
      ) : (
        <Card title="Cultivation details">
          <PlanForm onSaved={handleSaved} />
        </Card>
      )}
    </>
  );
}
