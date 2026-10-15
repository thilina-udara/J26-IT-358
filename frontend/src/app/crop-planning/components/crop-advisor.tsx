"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, Check, ClipboardList, Leaf, RefreshCw, ShieldCheck, Sprout } from "lucide-react";
import { useSession } from "./session";
import PlanForm from "./plan-form";
import PlanSelector from "./plan-selector";
import { PlanningPanel } from "./planning-panel";
import { Button } from "./ui/button";
import { Card, ErrorNotice, Loading, Notice, ReasonList } from "./ui";
import { recommendedCrops, validatedRisk } from "../lib/advisor";
import { formatDate } from "../lib/dates";
import type { Crop, Plan, SavedPlanning, Submission, Workflow } from "../lib/contracts";

const steps = ["Farm details", "Risk assessment", "Choose your crop", "Cultivation plan"];
const riskCopy = {
  Low: "The backend has returned a validated Low classification for this assessment. Review its evidence before planning.",
  Medium: "The backend has returned a validated Medium classification. Review the assessment and your cultivation context before planning.",
  High: "The backend has returned a validated High classification. Review eligible alternatives for your location and dates below.",
};

export function AdvisorAssessment({ report, crop }: { report: Workflow; crop: Crop }) {
  const risk = validatedRisk(report);
  const notApplicable = report.analysis_status === "not_applicable";
  return <section className={`cp-advisor-risk ${risk ? `is-${risk.toLowerCase()}` : "is-pending"}`} aria-labelledby="advisor-risk-title">
    <div className="cp-advisor-risk-top"><span className="cp-advisor-kicker">YOUR CURRENT ASSESSMENT</span><span className="cp-advisor-tag">{risk ? "Backend validated" : "Evidence needed"}</span></div>
    <h2 id="advisor-risk-title">{risk ? `${risk} risk` : report.analysis_status === "failed" ? "Assessment unavailable" : notApplicable ? "Current assessment does not apply" : "Risk assessment pending"}</h2>
    <p>{risk ? riskCopy[risk] : report.analysis_status === "failed" ? "Your farm details were saved. Retry the assessment using this saved record." : notApplicable ? "This historical or already-started record cannot be assessed as upcoming cultivation. Use the private model workbench to test historical scenarios without saving them as live farmer registrations." : "The live registry and approved evidence do not support a validated Low, Medium or High classification yet. No registered peers does not establish Low risk. Use private historical model testing to check the saved models against historical data."}</p>
    {!risk && <a className="cp-subtle-link" href="http://127.0.0.1:8011" target="_blank" rel="noopener noreferrer">Open private historical model testing <ArrowRight size={15} aria-hidden="true" /></a>}
    <div className="cp-advisor-risk-scale" aria-label="Risk categories">{(["Low", "Medium", "High"] as const).map(level => <span key={level} className={`risk-${level.toLowerCase()} ${risk === level ? "is-active" : ""}`}><i aria-hidden="true" />{level}{risk === level && <Check size={14} aria-hidden="true" />}</span>)}</div>
    <p className="cp-advisor-small">Applies to your saved {crop} assessment. Historical model predictions do not establish current risk.</p>
    <details className="cp-evidence-details"><summary>Assessment evidence & limitations</summary><ReasonList evidence={report.assessment} />{report.assessment.missing_evidence?.length ? <ul className="cp-reasons">{report.assessment.missing_evidence.map((value, index) => <li key={index}>{value}</li>)}</ul> : null}</details>
  </section>;
}

export default function CropAdvisor() {
  const { api } = useSession();
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [selected, setSelected] = useState<Crop | null>(null);
  const [mode, setMode] = useState<"new" | "saved">("new");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const request = useRef(0);
  const report = submission?.workflow;
  const risk = report ? validatedRisk(report) : null;
  const alternatives = submission ? recommendedCrops(submission.workflow, submission.plan.crop) : [];
  const currentStep = !submission ? 0 : selected ? 3 : 1;
  const stepComplete = (index: number) => index < currentStep && (index !== 1 || risk !== null);

  async function assess(plan: Plan) {
    if (busy) return;
    const attempt = ++request.current;
    setBusy(true); setError(null); setSelected(null);
    // Remove previous results before a new current-evidence request.
    setSubmission(null);
    try {
      const result = await api.analyze(plan.plan_id, plan.farmer_declared_season ?? undefined);
      if (attempt === request.current) setSubmission({ plan, workflow: result });
    } catch (reason) {
      if (attempt === request.current) {
        setError(reason);
        setSubmission({ plan, workflow: { plan_id: plan.plan_id, status: "analysis_unavailable", analysis_status: "failed",
          assessment: { status: "insufficient_evidence", risk_level: null }, historical_prediction: { status: "not_evaluated" },
          recommendations: { status: "blocked_unvalidated_risk", alternatives: [] } } });
      }
    } finally { if (attempt === request.current) setBusy(false); }
  }

  async function planningSaved(result: SavedPlanning) {
    if (!submission) return;
    const planId = submission.plan.plan_id;
    const generation = request.current;
    // Saving a crop choice changes the record: an old risk label no longer applies.
    setSubmission(value => value && { ...value, workflow: { ...value.workflow, analysis_status: "not_evaluated",
      assessment: { status: "risk_level_unvalidated", risk_level: null }, recommendations: { status: "blocked_unvalidated_risk", alternatives: [] } } });
    try {
      const latest = await api.read(result.personalized_plan.plan_id);
      if (generation === request.current) setSubmission(value => value?.plan.plan_id === planId ? { ...value, plan: latest.plan } : value);
    } catch {
      if (generation === request.current) setError(new Error("Your cultivation plan was saved. Open My Farm Plans to reload the current record before requesting another change."));
    }
  }

  function startAnother() { request.current++; setSubmission(null); setSelected(null); setError(null); setMode("new"); }

  return <div className="cp-advisor cp-stack">
    <section className="cp-advisor-hero">
      <div><span className="cp-advisor-kicker"><Sprout size={16} aria-hidden="true" /> YOUR NEXT SEASON, STEP BY STEP</span><h1>Grow with a clearer plan.</h1><p>Tell us about your farm. Review your risk assessment, choose a crop, and build a cultivation plan with approved guidance.</p><div className="cp-advisor-hero-footer"><span><ShieldCheck size={16} aria-hidden="true" /> Your farm records stay private</span><a href="http://127.0.0.1:8011" target="_blank" rel="noopener noreferrer">Test historical models <ArrowRight size={14} aria-hidden="true" /></a><Link href="/crop-planning/research-demo/history">Research disclosure <ArrowRight size={14} aria-hidden="true" /></Link></div></div>
      <div className="cp-advisor-hero-art" aria-hidden="true"><Sprout size={86} strokeWidth={1.2} /><span>Plan today.<br />Grow with care.</span></div>
    </section>
    <ol className="cp-advisor-steps" aria-label="Cultivation planning progress">{steps.map((title, index) => <li key={title} className={`${currentStep === index ? "is-current" : ""} ${stepComplete(index) ? "is-complete" : ""}`} aria-current={index === currentStep ? "step" : undefined}><span>{stepComplete(index) ? <Check size={17} aria-hidden="true" /> : index + 1}</span><div><small>STEP {index + 1}</small><strong>{title}</strong></div></li>)}</ol>
    <div className="cp-advisor-grid">
      <aside className="cp-advisor-input">
        <Card title={submission ? "Your saved farm details" : "Tell us about your cultivation"}>
          {submission ? <><span className="cp-advisor-tag"><Check size={14} aria-hidden="true" /> Details saved</span><h3 className="cp-advisor-crop-title">{submission.plan.crop}</h3><dl className="cp-advisor-details"><div><dt>Location</dt><dd>{submission.plan.district} · {submission.plan.region}</dd></div><div><dt>Your land</dt><dd>{submission.plan.land_size_acres} acres</dd></div><div><dt>Planting</dt><dd>{formatDate(submission.plan.planting_date)}</dd></div><div><dt>Expected harvest</dt><dd>{formatDate(submission.plan.expected_harvest_date)}</dd></div><div><dt>Declared season</dt><dd>{submission.plan.farmer_declared_season ?? "Not declared"}</dd></div></dl><p className="cp-advisor-small">Saved plan: <span className="cp-id">{submission.plan.plan_id}</span></p><div className="cp-stack"><Button variant="outline" disabled={busy} onClick={() => void assess(submission.plan)}><RefreshCw size={16} aria-hidden="true" />Recheck saved plan</Button><Button asChild variant="link"><Link href={`/crop-planning/plans/${encodeURIComponent(submission.plan.plan_id)}`}>View / edit saved details</Link></Button><Button variant="ghost" disabled={busy} onClick={startAnother}>Start another cultivation</Button></div></> : busy ? <Loading text="Assessing your saved cultivation…" /> : <><div className="cp-advisor-mode" aria-label="Choose cultivation details"><Button variant={mode === "new" ? "default" : "outline"} aria-pressed={mode === "new"} onClick={() => setMode("new")}>New cultivation</Button><Button variant={mode === "saved" ? "default" : "outline"} aria-pressed={mode === "saved"} onClick={() => setMode("saved")}>Use saved plan</Button></div>{mode === "new" ? <PlanForm submitLabel="Save details & check risk" onSaved={value => { if ("workflow" in value) { setSubmission(value); setSelected(null); setError(null); } }} /> : <PlanSelector>{plan => <Button disabled={busy || plan.status !== "active"} onClick={() => void assess(plan)}>Assess this saved plan <ArrowRight size={16} aria-hidden="true" /></Button>}</PlanSelector>}</>}
        </Card>
      </aside>
      <div className="cp-advisor-output" aria-live="polite" aria-busy={busy}>
        <ErrorNotice error={error} />
        {busy ? <Card><Loading text="Checking the evidence for your cultivation…" /></Card> : !submission ? <Card className="cp-advisor-welcome"><div className="cp-advisor-welcome-icon"><Leaf size={38} strokeWidth={1.4} aria-hidden="true" /></div><span className="cp-advisor-kicker">A PLAN THAT STARTS WITH YOUR FARM</span><h2>Your next steps, in one place.</h2><p>Enter your cultivation details to get started. Your assessment and available guidance will appear here.</p><div className="cp-advisor-preview"><div><ShieldCheck size={23} aria-hidden="true" /><strong>Review risk</strong><span>Low, Medium or High when validated evidence is available.</span></div><div><Sprout size={23} aria-hidden="true" /><strong>Explore alternatives</strong><span>Up to three eligible crops when validated risk is High.</span></div><div><CalendarDays size={23} aria-hidden="true" /><strong>Build your plan</strong><span>Activities and timing from approved, applicable guidance.</span></div></div></Card> : <>
          <Card><AdvisorAssessment report={submission.workflow} crop={submission.plan.crop} /></Card>
          {!selected ? <Card title={risk === "High" ? "Choose a crop for your cultivation" : "Continue to your cultivation plan"}>
            {risk === "High" && (alternatives.length ? <><p>These {alternatives.length} alternative{alternatives.length === 1 ? " is" : "s are"} eligible under the backend’s current suitability and coverage checks. Selecting one rechecks eligibility before planning.</p><div className="cp-advisor-alternatives">{alternatives.map((candidate, index) => <article key={candidate.crop} className="cp-advisor-alternative"><span className="cp-advisor-alternative-number">OPTION {index + 1}</span><Sprout size={27} strokeWidth={1.4} aria-hidden="true" /><h3>{candidate.crop}</h3><span className="cp-advisor-eligibility"><ShieldCheck size={14} aria-hidden="true" /> Eligible alternative</span><p>Approved for this comparison. Suitability does not establish a Low risk label or guaranteed returns.</p><Button data-crop={candidate.crop} onClick={() => setSelected(candidate.crop)}>Select {candidate.crop}<ArrowRight size={15} aria-hidden="true" /></Button></article>)}</div></> : <Notice kind="warning">No eligible alternatives are available for this assessment yet. Suitability and comparable coverage must be approved before crops can be suggested.</Notice>)}
            {risk !== "High" && <p>{risk ? "You can continue with your saved crop and request approved cultivation activities." : "Crop-switch recommendations are waiting for a validated High assessment and suitable alternatives. You can request approved guidance for your saved crop."}</p>}
            <div className="cp-advisor-continue"><div><strong>Keep your planned crop</strong><span>{submission.plan.crop} · {submission.plan.land_size_acres} acres</span></div><Button variant={alternatives.length ? "outline" : "default"} onClick={() => setSelected(submission.plan.crop)}>Plan with {submission.plan.crop}<ArrowRight size={16} aria-hidden="true" /></Button></div>
          </Card> : <section className="cp-stack" aria-labelledby="advisor-planning-title"><div className="cp-advisor-selection"><div><span className="cp-advisor-kicker">YOUR CROP CHOICE</span><h2 id="advisor-planning-title"><Sprout size={23} aria-hidden="true" />{selected}</h2><p>Confirm the growing context below to request your cultivation plan. Previewing leaves the saved crop unchanged; saving a revision applies your choice.</p></div><Button variant="outline" onClick={() => setSelected(null)}>Change choice</Button></div><PlanningPanel key={`${submission.plan.plan_id}-${selected}`} plan={submission.plan} saved={null} selectedCrop={selected} onSaved={planningSaved} /></section>}
          <div className="cp-advisor-footnote"><ClipboardList size={16} aria-hidden="true" /><span>Activities are shown only when approved for your context. Guidance may form a partial plan.</span></div>
        </>}
      </div>
    </div>
  </div>;
}
