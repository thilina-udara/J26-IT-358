// All responses here are explicitly fictional test fixtures, never application data.
import { test } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { act, create, type ReactTestRenderer } from "react-test-renderer";
import { AppRouterContext } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { createApi, ApiError } from "../lib/api";
import { approvedActivities, eligibleCandidates, evidenceMessages, safeSource, submissionOutcome } from "../lib/evidence";
import { validateCredentials, validatePlan } from "../lib/validation";
import { AccessGate, Protected, SessionProvider, useSession } from "../components/session";
import { PlanningResult, WorkflowResult } from "../components/ui";
import AuthForm from "../components/auth-form";
import NewPlanPage from "../plans/new/page";
import type { Personalized, Plan, Session, Workflow } from "../lib/contracts";
import { PathnameContext } from "next/dist/shared/lib/hooks-client-context.shared-runtime";
import { CropShell } from "../components/shell";
import HomePage from "../page";
import CultivationPlanPage from "../cultivation-plan/page";
import PlanSelector from "../components/plan-selector";
import { AnalysisPanel } from "../components/analysis-panel";
import CropAdvisor, { AdvisorAssessment } from "../components/crop-advisor";
import { PlanningPanel } from "../components/planning-panel";
import { validatedRisk, recommendedCrops } from "../lib/advisor";
import type { Candidate } from "../lib/contracts";

function advisorReport(level: "Low" | "Medium" | "High", candidates: Candidate[] = []): Workflow {
  return { ...workflow, analysis_status: "completed", status: "risk_level_validated",
    assessment: { status: "risk_level_validated", risk_level: level },
    recommendations: { status: "alternatives_available", alternatives: candidates } };
}

function advisorCandidate(crop: Candidate["crop"]): Candidate {
  return { crop, status: "eligible_alternative", approval_status: "applicable_suitability_approved", risk_level: "unknown_unvalidated" };
}
import { formatDate, nextUtcDate, utcToday } from "../lib/dates";
import { activeWorkspace, isPublicRoute, WORKSPACE_NAV } from "../lib/navigation";
import { ResearchResult } from "../components/research-result";
import type { HistoricalScenarioResponse } from "../lib/contracts";

// Next Link's idle-callback fallback needs the browser's self alias in Node.
Object.defineProperty(globalThis, "self", { value: globalThis, configurable: true });

const farmer = { farmer_id: "fictional-owner", login_identifier: "fictional-owner", authentication_method: "account_session", created_at: null };
const session: Session = { access_token: "fictional-test-token", token_type: "bearer", expires_at: "2099-01-01T00:00:00Z", expires_in: 3600, farmer };
const plan: Plan = { plan_id: "fictional-plan", farmer_id: farmer.farmer_id, district: "Matara", region: "fictional-region", crop: "Corn", land_size_acres: 2, planting_date: "2090-01-01", expected_harvest_date: "2090-04-01", farmer_declared_season: "Maha", status: "active", submitted_at: "2089-12-01T00:00:00Z", updated_at: "2089-12-01T00:00:00Z" };
const workflow: Workflow = { plan_id: plan.plan_id, status: "analysis_unavailable", analysis_status: "failed", reason_codes: ["analysis_unavailable"], assessment: { status: "insufficient_evidence", risk_level: null, disclosure_status: "collective_values_withheld", reason_codes: ["analysis_not_evaluated", "collective_values_protected"] }, historical_prediction: { status: "insufficient_evidence", reason_codes: ["historical_prediction_unavailable"] }, recommendations: { status: "blocked_unvalidated_risk" }, recovery: { plan_saved: true, retryable: true } };
const partial: Personalized = { status: "partial_plan", plan_id: plan.plan_id, final_crop: "Corn", expected_harvest_date: plan.expected_harvest_date, based_on_updated_at: plan.updated_at, approval_status: "no_approved_applicable_activities", reason_codes: ["schedule_incomplete", "applicable_guidance_unavailable"], activities: [], warnings: [], missing_categories: ["harvest"] };
const response = (body: unknown, status = 200) => new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

for (const level of ["Low", "Medium", "High"] as const) {
  test(`advisor displays the validated backend ${level} classification`, () => {
    const report = advisorReport(level);
    assert.equal(validatedRisk(report), level);
    const html = renderToStaticMarkup(<AdvisorAssessment report={report} crop="Corn" />);
    assert.ok(html.includes(`${level} risk`));
    assert.ok(html.includes("Backend validated"));
  });
}

test("advisor never promotes historical or unvalidated High into a current classification", () => {
  const report = { ...advisorReport("High", [advisorCandidate("Brinjal")]),
    assessment: { status: "risk_level_unvalidated", risk_level: "High" },
    historical_prediction: { status: "historical_proxy_prediction", risk_level: "High" } };
  assert.equal(validatedRisk(report), null);
  assert.deepEqual(recommendedCrops(report, "Corn"), []);
  const html = renderToStaticMarkup(<AdvisorAssessment report={report} crop="Corn" />);
  assert.ok(html.includes("Risk assessment pending")); assert.ok(!html.includes("High risk"));
  assert.equal(validatedRisk({ ...advisorReport("High"), analysis_status: "failed" }), null);
});

test("advisor selects at most three distinct approved backend alternatives only for validated High", () => {
  const candidates = [advisorCandidate("Corn"), advisorCandidate("Mung Beans"), advisorCandidate("Mung Beans"),
    { ...advisorCandidate("Chillies"), approval_status: "applicable_suitability_unavailable" },
    advisorCandidate("Brinjal"), advisorCandidate("Pumpkin"), advisorCandidate("Bandakka")];
  assert.deepEqual(recommendedCrops(advisorReport("High", candidates), "Corn").map(value => value.crop), ["Mung Beans", "Brinjal", "Pumpkin"]);
  for (const level of ["Low", "Medium"] as const) assert.deepEqual(recommendedCrops(advisorReport(level, candidates), "Corn"), []);
  assert.deepEqual(recommendedCrops({ ...advisorReport("High", candidates), recommendations: { status: "blocked_unvalidated_risk", alternatives: candidates } }, "Corn"), []);
});

test("advisor preserves a saved plan after failed analysis and retries using the same owned ID", async () => {
  const original = global.fetch; let creates = 0; const analyses: Record<string, unknown>[] = [];
  global.fetch = async (url, init) => {
    const path = String(url);
    if (path.endsWith("/auth/login")) return response(session);
    if (path.endsWith("/auth/me")) return response(farmer);
    if (path.endsWith("/api/farmer-workflow/plans")) { creates++; return response({ plan, workflow }, 201); }
    if (path.endsWith("/api/farmer-workflow/analyze")) { analyses.push(JSON.parse(String(init!.body))); return response({ ...workflow, analysis_status: "completed" }); }
    throw new Error("Unexpected fictional advisor request");
  };
  const rendered = await renderSession(<Protected><CropAdvisor /></Protected>, true);
  try {
    act(() => { for (const [id, value] of [["region", "fictional-region"], ["land_size_acres", "2"], ["planting_date", "2090-01-01"], ["expected_harvest_date", "2090-04-01"]]) rendered.tree.root.findByProps({ id }).props.onChange({ target: { value } }); });
    await act(async () => { await rendered.tree.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
    assert.equal(creates, 1); assert.equal(rendered.tree.root.findAllByType("form").length, 0);
    assert.ok(JSON.stringify(rendered.tree.toJSON()).includes("Assessment unavailable"));
    const retry = rendered.tree.root.findAllByType("button").find(button => button.children.includes("Recheck saved plan"))!;
    await act(async () => { await retry.props.onClick(); });
    assert.deepEqual(analyses, [{ plan_id: plan.plan_id, season: "Maha" }]); assert.equal(creates, 1);
    assert.ok(JSON.stringify(rendered.tree.toJSON()).includes("Risk assessment pending"));
    assert.equal(rendered.tree.root.findAllByProps({ "data-crop": "Brinjal" }).length, 0);
  } finally { act(() => rendered.tree.unmount()); global.fetch = original; }
});

for (const rejected of [false, true]) {
  test(`advisor sends the selected alternative through guarded backend planning: ${rejected ? "approval expired" : "preview and save"}`, async () => {
    const original = global.fetch; const requests: Record<string, unknown>[] = [];
    const high = advisorReport("High", [advisorCandidate("Mung Beans"), advisorCandidate("Brinjal"), advisorCandidate("Pumpkin")]);
    const activity = { activity_name: "FICTIONAL approved alternative activity", category: "management", verification_status: "explicitly_verified_for_planning", approval_evidence: "FICTIONAL exact-context approval", date_windows: [{ earliest: "2090-01-03", latest: "2090-01-05" }] };
    const personalized: Personalized = { ...partial, final_crop: "Mung Beans", approval_status: "approved_activities_only", activities: [activity] };
    global.fetch = async (url, init) => {
      const path = String(url);
      if (path.endsWith("/auth/login")) return response(session);
      if (path.endsWith("/auth/me")) return response(farmer);
      if (path.endsWith("/api/farmer-workflow/plans")) return response({ plan, workflow: high }, 201);
      if (path.endsWith("/api/farmer-workflow/select")) {
        const body = JSON.parse(String(init!.body)); requests.push(body);
        if (rejected) return response({ detail: "No defensible High-risk eligible alternative is available" }, 409);
        return response(body.save ? { personalized_plan: personalized, revision_id: 1, revisions: [], stale: false } : personalized);
      }
      if (path.endsWith(`/api/farmer-workflow/plans/${plan.plan_id}`)) return response({ plan: { ...plan, crop: "Mung Beans", updated_at: "2089-12-02T00:00:00Z" }, personalized_plan: null });
      throw new Error("Unexpected fictional advisor request");
    };
    const rendered = await renderSession(<Protected><CropAdvisor /></Protected>, true);
    try {
      act(() => { for (const [id, value] of [["region", "fictional-region"], ["land_size_acres", "2"], ["planting_date", "2090-01-01"], ["expected_harvest_date", "2090-04-01"]]) rendered.tree.root.findByProps({ id }).props.onChange({ target: { value } }); });
      await act(async () => { await rendered.tree.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
      assert.ok(JSON.stringify(rendered.tree.toJSON()).includes("High risk"));
      assert.equal(rendered.tree.root.findAll(node => node.type === "button" && Boolean(node.props["data-crop"])).length, 3);
      act(() => rendered.tree.root.findByProps({ "data-crop": "Mung Beans" }).props.onClick());
      await act(async () => { await rendered.tree.root.findByType("form").props.onSubmit({ preventDefault() {}, nativeEvent: { submitter: { getAttribute: () => "preview" } } }); });
      assert.equal(requests[0].final_crop, "Mung Beans"); assert.equal(requests[0].plan_id, plan.plan_id);
      assert.equal(requests[0].district, plan.district); assert.equal(requests[0].region, plan.region);
      assert.equal(requests[0].planting_date, plan.planting_date); assert.equal(requests[0].save, false);
      let json = JSON.stringify(rendered.tree.toJSON());
      if (rejected) { assert.ok(json.includes("No defensible High-risk eligible alternative")); assert.ok(!json.includes(activity.activity_name)); }
      else {
        assert.ok(json.includes(activity.activity_name)); assert.ok(json.includes("3 Jan 2090"));
        await act(async () => { await rendered.tree.root.findByType("form").props.onSubmit({ preventDefault() {}, nativeEvent: { submitter: { getAttribute: () => "save" } } }); });
        assert.equal(requests[1].final_crop, "Mung Beans"); assert.equal(requests[1].save, true);
        json = JSON.stringify(rendered.tree.toJSON()); assert.ok(json.includes("Risk assessment pending")); assert.ok(!json.includes("High risk"));
        assert.ok(json.includes("Partial plan saved as revision 1"));
      }
    } finally { act(() => rendered.tree.unmount()); global.fetch = original; }
  });
}

test("alternative planning does not display an original-crop saved timeline", async () => {
  const original = global.fetch;
  const activity = { activity_name: "FICTIONAL original-only activity", category: "management", verification_status: "explicitly_verified_for_planning", approval_evidence: "FICTIONAL original-crop approval", date_windows: [] };
  global.fetch = async url => {
    const path = String(url);
    if (path.endsWith("/auth/login")) return response(session);
    if (path.endsWith("/auth/me")) return response(farmer);
    if (path.endsWith(`/api/personalized-cultivation-plans/${plan.plan_id}`)) return response({ personalized_plan: { ...partial, approval_status: "approved_activities_only", activities: [activity] }, revision_id: 1, revisions: [], stale: false });
    throw new Error("Unexpected fictional planning request");
  };
  const rendered = await renderSession(<PlanningPanel plan={plan} saved={null} selectedCrop="Mung Beans" />, true);
  try {
    const retrieve = rendered.tree.root.findAllByType("button").find(button => button.children.includes("Retrieve saved result"))!;
    await act(async () => { await retrieve.props.onClick(); });
    const json = JSON.stringify(rendered.tree.toJSON());
    assert.ok(!json.includes(activity.activity_name)); assert.ok(json.includes("The saved revision is for Corn"));
    assert.ok(json.includes("Request a new preview for Mung Beans"));
  } finally { act(() => rendered.tree.unmount()); global.fetch = original; }
});

test("historical or started farmer records point to private model testing instead of pending current risk", () => {
  const html = renderToStaticMarkup(<AdvisorAssessment report={{ ...workflow, analysis_status: "not_applicable" }} crop="Corn" />);
  assert.ok(html.includes("Current assessment does not apply"));
  assert.ok(!html.includes("Risk assessment pending"));
  assert.ok(html.includes("http://127.0.0.1:8011"));
  const empty = renderToStaticMarkup(<AdvisorAssessment report={{ ...workflow, analysis_status: "completed" }} crop="Corn" />);
  assert.ok(empty.includes("No registered peers does not establish Low risk"));
});

function researchFixture(): HistoricalScenarioResponse {
  return {
    status: "historical_result_withheld", mode: "research_demo_simulation", operational_status: "risk_level_not_yet_validated",
    disclosure_status: "collective_values_withheld", reason_codes: ["collective_values_protected"],
    simulated_plan: { district: "Hambantota", crop: "Mung Beans", season: "Yala", land_size_acres: 3.5,
      planting_date: "2025-06-16", expected_harvest_date: "2025-08-25", target_year: 2025,
      decision_cutoff: "2025-06-16", cutoff_timestamp: "2025-06-16T00:00:00+05:30", cutoff_source: "explicit_decision_cutoff" },
    model_metadata: { model_name: "XGBoost", trained_through: 2024, simulated_target_year: 2025, is_out_of_time_holdout: true,
      training_data_cutoff: "2024-12-31", training_cutoff_basis: "recorded Year upper bound", model_available_at_cutoff: "not verified",
      holdout_caveat: "Previously examined", benchmark_scope: "Saved historical labels only", feature_count: 1,
      feature_names: ["Overlap_Plan_Count"], own_production_status: "Missing; frozen pipeline handling", probability_status: "Uncalibrated historical class probabilities",
      benchmark_metrics: null },
    features: { Overlap_Plan_Count: 11 }, prediction: { historical_proxy_label: "High", predicted_risk_level: "High",
      class_probabilities: { Low: .05, Medium: .05, High: .9 }, overlapping_peer_count: 10, overlapping_peer_acres: 20,
      total_window_acres: 23.5, is_isolated_plan: false, coverage_status: "replay_coverage_available", peer_explanation: "Retrospective assumption" },
    observation_availability: { status: "unverified", replay_unknown_peer_records: 10, replay_unknown_prior_records: 5,
      source_provenance: "Fictional test fixture", required_evidence: "Exact version timestamps required" },
    concentration_indicators: { harvest_window_start: "2025-08-11", harvest_window_end: "2025-09-08", matching_scope: "same district/crop/season",
      historical_dataset_window: { record_count: 15, acres: 30, disclosure_status: "aggregate" },
      provably_available_window: { record_count: 0, acres: null, disclosure_status: "sparse_or_zero_coverage" },
      availability_status: "not_fully_verified", unknown_availability_count: 15, observed_after_cutoff_count: 0,
      interpretation: "Dataset presence is not availability" },
    scenario_explanation: "Planting dates cannot prove availability", recommendation_status: "blocked_unvalidated_risk",
    diagnostic_alternatives: [], governance_notice: "Research proxy only; no current validated risk" };
}

test("research rendering protects classes, singleton means, sparse counts and derived totals even if injected", () => {
  const fixture = researchFixture();
  fixture.prediction.overlapping_peer_acres = 9876543;
  fixture.features.Previous_Year_Mean_Plan_Acres = 7.25;
  fixture.observation_availability.replay_unknown_peer_records = 1;
  const html = renderToStaticMarkup(<ResearchResult result={fixture} previous={fixture} />);
  for (const text of ["Historical outputs withheld for privacy", "Simulation decision cutoff", "Selected planting date", "Expected harvest date", "Model training data cutoff", "No public historical inference", "Unvalidated. Recommendations remain blocked."])
    assert.ok(html.includes(text), text);
  for (const text of ["9876543", "7.25", "90.00%", "Historical proxy: High", "10 peer", "Strictly Prior Observations Used"])
    assert.ok(!html.includes(text), text);
  assert.ok(html.includes("No saved evaluation metrics for this year"));
});

test("research comparison displays caller date changes without exposing changed private inputs", () => {
  const current = researchFixture(); const previous = researchFixture();
  previous.simulated_plan.decision_cutoff = "2025-06-10";
  previous.features.Overlap_Plan_Count = 6;
  previous.prediction.historical_proxy_label = "Low";
  const html = renderToStaticMarkup(<ResearchResult result={current} previous={previous} />);
  assert.ok(html.includes("2025-06-10 to 2025-06-16"));
  assert.ok(html.includes("Historical comparison results are withheld"));
  assert.ok(!html.includes("Overlap_Plan_Count"));
});

test("research API sends independent cutoff without persisting a farmer plan", async () => {
  let body: unknown; let calledUrl = "";
  const api = createApi("", () => session.access_token, () => {}, async (url, init) => {
    calledUrl = String(url); body = JSON.parse(String(init?.body)); return response(researchFixture());
  });
  const request = { district: "Hambantota" as const, crop: "Mung Beans" as const, season: "Yala" as const,
    land_size_acres: 3.5, planting_date: "2025-06-16", expected_harvest_date: "2025-08-25", decision_cutoff: "2025-06-10" };
  await api.researchDemoEvaluate(request);
  assert.equal(calledUrl, "/api/research-demo/evaluate"); assert.deepEqual(body, request);
});

test("registration and login validation match username and password contracts", () => {
  assert.deepEqual(validateCredentials({ login_identifier: " fictional-owner ", password: "fictional long passphrase" }, true), {});
  assert.ok(validateCredentials({ login_identifier: "bad username", password: "short" }, true).password);
  assert.ok(validateCredentials({ login_identifier: "bad username", password: "long fictional passphrase" }, true).login_identifier);
  assert.deepEqual(validateCredentials({ login_identifier: "fictional-owner", password: "short" }, false), {});
});
test("plan validation enforces acreage, chronology and future creation without rejecting historical edits", () => {
  assert.deepEqual(validatePlan(plan, true, "2089-01-01"), {});
  assert.ok(validatePlan({ ...plan, land_size_acres: Infinity }, false).land_size_acres);
  assert.ok(validatePlan({ ...plan, expected_harvest_date: "2080-01-01" }, false).expected_harvest_date);
  assert.ok(validatePlan(plan, true, "2090-01-01").planting_date);
  assert.deepEqual(validatePlan(plan, false, "2091-01-01"), {});
});
test("protected content is absent until authentication", () => {
  const denied = renderToStaticMarkup(<AccessGate authenticated={false}><p>fictional-private-plan</p></AccessGate>);
  assert.ok(!denied.includes("fictional-private-plan")); assert.ok(denied.includes("/crop-planning/login"));
  assert.ok(renderToStaticMarkup(<AccessGate authenticated><p>fictional-private-plan</p></AccessGate>).includes("fictional-private-plan"));
});
test("API uses configured base URL, bearer header, no cookies and no store", async () => {
  let init: RequestInit | undefined; let url = "";
  const api = createApi("https://fictional.example/", () => session.access_token, () => {}, async (input, options) => { url = String(input); init = options; return response({ items: [] }); });
  await api.list(new URLSearchParams({ limit: "10", offset: "20", crop: "Corn" }));
  assert.equal(url, "https://fictional.example/api/cultivation-plans?limit=10&offset=20&crop=Corn");
  assert.equal((init!.headers as Record<string, string>).Authorization, "Bearer fictional-test-token"); assert.equal(init!.credentials, "omit"); assert.equal(init!.cache, "no-store");
});
test("registration and login send only exact credentials without bearer headers", async () => {
  const calls: { url: string; options: RequestInit }[] = [];
  const api = createApi("", () => session.access_token, () => {}, async (url, options) => { calls.push({ url: String(url), options: options! }); return response(farmer); });
  const credentials = { login_identifier: "fictional-owner", password: "fictional passphrase" }; await api.register(credentials); await api.login(credentials);
  assert.deepEqual(calls.map(call => call.url), ["/auth/register", "/auth/login"]);
  for (const call of calls) { assert.deepEqual(JSON.parse(String(call.options.body)), credentials); assert.ok(!("Authorization" in (call.options.headers as object))); }
});
test("missing sessions never request private endpoints", async () => {
  let called = false; const api = createApi("", () => null, () => {}, async () => { called = true; return response({}); });
  await assert.rejects(api.read(plan.plan_id), (error: ApiError) => error.status === 401); assert.equal(called, false);
});
test("401 clears a matching session, login 401 does not revoke an existing one", async () => {
  let cleared = 0; const api = createApi("", () => session.access_token, () => { cleared++; }, async () => response({ detail: "Login required" }, 401));
  await assert.rejects(api.me()); assert.equal(cleared, 1); await assert.rejects(api.login({ login_identifier: "fictional", password: "wrong" })); assert.equal(cleared, 1);
});
test("late unauthorized response cannot revoke a newer login", async () => {
  let token = "fictional-old"; let cleared = false;
  const api = createApi("", () => token, () => { cleared = true; }, async () => { token = "fictional-new"; return response({ detail: "Expired" }, 401); });
  await assert.rejects(api.me()); assert.equal(cleared, false);
});
test("validation messages omit echoed inputs and preserve field names", async () => {
  const api = createApi("", () => session.access_token, () => {}, async () => response({ detail: [{ loc: ["body", "password"], msg: "Too short", input: "fictional-sensitive-input" }] }, 422));
  await assert.rejects(api.me(), (error: ApiError) => { assert.equal(error.fields.password, "Too short"); assert.ok(!JSON.stringify(error).includes("fictional-sensitive-input")); return true; });
});
test("network failure never retries a write and advises checking saved plans", async () => {
  let calls = 0; const api = createApi("", () => session.access_token, () => {}, async () => { calls++; throw new Error("fictional diagnostic"); });
  await assert.rejects(api.create(plan), (error: ApiError) => error.status === 0 && error.message.includes("Check your saved plans")); assert.equal(calls, 1);
});
test("201 partial success preserves the saved ID and retries only analysis", async () => {
  const calls: { path: string; body: unknown }[] = [];
  const api = createApi("", () => session.access_token, () => {}, async (path, options) => { calls.push({ path: String(path), body: JSON.parse(String(options!.body)) }); return calls.length === 1 ? response({ plan, workflow }, 201) : response(workflow); });
  const { farmer_id, plan_id, status, submitted_at, updated_at, ...fields } = plan;
  const saved = await api.create(fields); assert.deepEqual(submissionOutcome(saved), { planId: "fictional-plan", analysisFailed: true, retryAnalysis: true });
  assert.equal((calls[0].body as Record<string, unknown>).season, "Maha"); assert.ok(!("farmer_id" in (calls[0].body as object))); assert.ok(!("farmer_declared_season" in (calls[0].body as object)));
  await api.analyze(saved.plan.plan_id); assert.equal(calls[1].path, "/api/farmer-workflow/analyze"); assert.deepEqual(calls[1].body, { plan_id: "fictional-plan" }); assert.equal(calls.filter(call => call.path === "/api/farmer-workflow/plans").length, 1);
});
test("update, cancellation, comparison and planning preserve actual endpoint/body contracts", async () => {
  const calls: { path: string; method: string; body: Record<string, unknown> | null }[] = [];
  const api = createApi("", () => session.access_token, () => {}, async (url, init) => { calls.push({ path: String(url), method: init!.method!, body: init!.body ? JSON.parse(String(init!.body)) : null }); return response({}); });
  const { farmer_id, plan_id, status, submitted_at, updated_at, ...fields } = plan;
  await api.update(plan.plan_id, fields); await api.cancel(plan.plan_id); await api.compare(plan);
  const body = { plan_id: plan.plan_id, final_crop: plan.crop, district: plan.district, region: plan.region, land_size_acres: plan.land_size_acres, planting_date: plan.planting_date, expected_harvest_date: plan.expected_harvest_date, season: "Maha" as const, variety: null, planting_method: null, corn_product: null, nursery_sowing_date: null, emergence_date: null, flowering_date: null };
  await api.generate(body); await api.save(body); await api.saved(plan.plan_id);
  assert.equal(calls[0].method, "PUT"); assert.equal(calls[0].body!.farmer_declared_season, "Maha"); assert.equal(calls[1].method, "DELETE");
  assert.equal(calls[2].body!.replacing_plan_id, plan.plan_id); assert.equal(calls[2].body!.selected_crop, "Corn");
  assert.equal(calls[3].path, "/api/farmer-workflow/select"); assert.equal(calls[3].body!.save, false); assert.equal(calls[4].body!.save, true);
  assert.equal(calls[5].path, "/api/personalized-cultivation-plans/fictional-plan");
});
test("logout accepts 204 and throttling preserves Retry-After", async () => {
  await createApi("", () => session.access_token, () => {}, async () => response(null, 204)).logout();
  const api = createApi("", () => session.access_token, () => {}, async () => new Response(JSON.stringify({ detail: "Wait" }), { status: 429, headers: { "Retry-After": "60" } }));
  await assert.rejects(api.me(), (error: ApiError) => error.retryAfter === "60");
});
test("privacy rendering ignores injected collective numbers, shares and clusters", () => {
  const injected = { ...workflow, assessment: { ...workflow.assessment, risk_level: "High", indicators: { status: "available", total_planned_acreage: 912345, farmer_count: 987654, crop_share_of_regional_window_acreage: .987654, cluster_context: "fictional-private-cluster" } } };
  const html = renderToStaticMarkup(<WorkflowResult report={injected} />);
  for (const forbidden of ["912345", "987654", "fictional-private-cluster", "High"]) assert.ok(!html.includes(forbidden));
  assert.ok(html.includes("Validated current risk unavailable")); assert.ok(html.includes("Collective farmer counts")); assert.ok(html.includes("do not create the plan again"));
});
test("only explicitly approved candidates and activities are presented as approved", () => {
  assert.equal(eligibleCandidates([{ crop: "Corn", status: "eligible_alternative", risk_level: "unknown_unvalidated" }]).length, 0);
  const activity = { activity_name: "fictional approved activity", category: "management", verification_status: "explicitly_verified_for_planning", approval_evidence: "fictional approval", date_windows: [] };
  assert.equal(approvedActivities({ ...partial, activities: [activity] }).length, 0);
  assert.equal(approvedActivities({ ...partial, approval_status: "approved_activities_only", activities: [activity] }).length, 1);
  const html = renderToStaticMarkup(<PlanningResult result={{ ...partial, approval_status: "approval_not_recorded", activities: [activity] }} stale />);
  assert.ok(html.includes("stale")); assert.ok(html.includes("Partial plan")); assert.ok(!html.includes(activity.activity_name));
  const approved = renderToStaticMarkup(<PlanningResult result={{ ...partial, approval_status: "approved_activities_only", activities: [activity] }} />);
  assert.ok(approved.includes(activity.activity_name)); assert.ok(approved.includes("Partial plan"));
});
test("unknown reason codes remain neutral and source links reject executable protocols", () => {
  assert.match(evidenceMessages({ status: "unknown", reason_codes: ["future_reason"] })[0], /evidence is unavailable/);
  assert.equal(safeSource("javascript:alert(1)"), undefined); assert.equal(safeSource("https://fictional.example/guidance"), "https://fictional.example/guidance");
});

const redirects: string[] = [];
const router = { back() {}, forward() {}, refresh() {}, push() {}, replace(href: string) { redirects.push(href); }, async prefetch() {} };
async function renderSession(child: React.ReactNode, login = false) {
  let context: ReturnType<typeof useSession> | undefined;
  function Capture() { context = useSession(); return <>{child}</>; }
  let tree!: ReactTestRenderer;
  await act(async () => { tree = create(<AppRouterContext.Provider value={router}><SessionProvider><Capture /></SessionProvider></AppRouterContext.Provider>); });
  if (login) await act(async () => { await context!.signIn({ login_identifier: "fictional-owner", password: "fictional long passphrase" }); });
  return { tree, context: () => context! };
}
test("registration form shows success without creating a session", async () => {
  const original = global.fetch; let requests = 0;
  global.fetch = async () => { requests++; return response(farmer, 201); };
  const rendered = await renderSession(<AuthForm registration />);
  try {
    act(() => { rendered.tree.root.findByProps({ id: "login_identifier" }).props.onChange({ target: { value: "fictional-owner" } }); rendered.tree.root.findByProps({ id: "password" }).props.onChange({ target: { value: "fictional long passphrase" } }); rendered.tree.root.findByProps({ id: "confirmation" }).props.onChange({ target: { value: "fictional long passphrase" } }); });
    await act(async () => { await rendered.tree.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
    assert.equal(requests, 1); assert.equal(rendered.context().session, null); assert.ok(JSON.stringify(rendered.tree.toJSON()).includes("Your account was created"));
  } finally { act(() => rendered.tree.unmount()); global.fetch = original; }
});
test("login form verifies the account then logout removes the private session", async () => {
  const original = global.fetch; const paths: string[] = [];
  global.fetch = async url => { const path = String(url); paths.push(path); return path.endsWith("/auth/login") ? response(session) : path.endsWith("/auth/logout") ? response(null, 204) : response(farmer); };
  const rendered = await renderSession(<AuthForm />);
  try {
    act(() => { rendered.tree.root.findByProps({ id: "login_identifier" }).props.onChange({ target: { value: "fictional-owner" } }); rendered.tree.root.findByProps({ id: "password" }).props.onChange({ target: { value: "fictional long passphrase" } }); });
    await act(async () => { await rendered.tree.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
    assert.equal(rendered.context().session?.farmer.farmer_id, "fictional-owner"); assert.ok(paths.some(path => path.endsWith("/auth/me")));
    assert.equal(redirects.at(-1), "/crop-planning/dashboard");
    await act(async () => { await rendered.context().signOut(); }); assert.equal(rendered.context().session, null);
  } finally { act(() => rendered.tree.unmount()); global.fetch = original; }
});

test("public home introduces the research without requiring a farmer session", () => {
  const html = renderToStaticMarkup(<HomePage />);
  assert.ok(html.includes("Cultivate with")); assert.ok(html.includes("/crop-planning/register"));
  assert.ok(html.includes("retrospectively evaluated concentration proxy"));
  assert.ok(!html.includes("fictional-plan")); assert.ok(!html.includes("risk score"));
  assert.equal(isPublicRoute("/crop-planning"), true);
  for (const item of WORKSPACE_NAV) assert.equal(isPublicRoute(item.href), false);
  assert.equal(activeWorkspace("/crop-planning/plans/fictional-plan/analysis", "/crop-planning/risk-analysis"), true);
  assert.equal(activeWorkspace("/crop-planning/plans/fictional-plan/planning", "/crop-planning/cultivation-plan"), true);
});
test("public navigation opens accessible mobile links and leaves the home content public", async () => {
  const rendered = await renderSession(<PathnameContext.Provider value="/crop-planning"><CropShell><HomePage /></CropShell></PathnameContext.Provider>);
  try {
    assert.ok(JSON.stringify(rendered.tree.toJSON()).includes("Cultivate with"));
    act(() => rendered.tree.root.findByProps({ "aria-label": "Open navigation" }).props.onClick());
    assert.equal(rendered.tree.root.findByProps({ "aria-label": "Close navigation" }).props["aria-expanded"], true);
    const menu = rendered.tree.root.findByProps({ id: "cp-public-mobile" });
    assert.ok(menu.findAllByProps({ href: "/crop-planning/login" }).length > 0);
    assert.ok(menu.findAllByProps({ href: "/crop-planning/register" }).length > 0);
  } finally { act(() => rendered.tree.unmount()); }
});
test("workspace navigation cannot mount private child content while logged out", async () => {
  const rendered = await renderSession(<PathnameContext.Provider value="/crop-planning/dashboard"><CropShell><p>fictional-private-record</p></CropShell></PathnameContext.Provider>);
  try { const html = JSON.stringify(rendered.tree.toJSON()); assert.ok(!html.includes("fictional-private-record")); for (const item of WORKSPACE_NAV) assert.ok(html.includes(item.href)); }
  finally { act(() => rendered.tree.unmount()); }
});
test("account form validates live and show-password control keeps credentials unchanged", async () => {
  const rendered = await renderSession(<AuthForm registration />);
  try {
    act(() => rendered.tree.root.findByProps({ id: "password" }).props.onChange({ target: { value: "short" } }));
    assert.ok(JSON.stringify(rendered.tree.toJSON()).includes("8–128"));
    act(() => rendered.tree.root.findByProps({ "aria-label": "Show password" }).props.onClick());
    assert.equal(rendered.tree.root.findByProps({ id: "password" }).props.type, "text");
    assert.equal(rendered.tree.root.findByProps({ id: "password" }).props.value, "short");
  } finally { act(() => rendered.tree.unmount()); }
});
test("friendly date validation preserves exact UTC cutoff and same-day harvest semantics", () => {
  const now = new Date("2030-01-01T00:30:00+05:30");
  assert.equal(utcToday(now), "2029-12-31"); assert.equal(nextUtcDate(now), "2030-01-01");
  assert.equal(validatePlan({ ...plan, planting_date: "2029-12-31" }, true, utcToday(now)).planting_date, "Please choose a future planting date.");
  assert.deepEqual(validatePlan({ ...plan, planting_date: "2030-01-01", expected_harvest_date: "2030-01-01" }, true, utcToday(now)), {});
  assert.equal(formatDate("2030-01-01"), "1 Jan 2030");
  assert.ok(validatePlan({ ...plan, crop: "fictional-unsupported-crop" } as unknown as Plan, true).crop);
  assert.ok(validatePlan({ ...plan, district: "fictional-unsupported-district" } as unknown as Plan, true).district);
  assert.deepEqual(validateCredentials({ login_identifier: "fictional-owner", password: "🌱".repeat(8) }, true), {});
  assert.ok(validateCredentials({ login_identifier: "fictional-owner", password: "🌱".repeat(129) }, true).password);
});
test("timeline renders only returned approved activities and their recorded dates", () => {
  const activity = { activity_name: "fictional-approved-event", category: "management", verification_status: "explicitly_verified_for_planning", approval_evidence: "fictional-officer-record", date_windows: [{ earliest: "2090-01-01", latest: "2090-01-03" }] };
  const html = renderToStaticMarkup(<PlanningResult result={{ ...partial, approval_status: "approved_activities_only", activities: [activity, { ...activity, activity_name: "fictional-unapproved-event", approval_evidence: "" }] }} />);
  assert.ok(html.includes("fictional-approved-event")); assert.ok(!html.includes("fictional-unapproved-event"));
  assert.ok(html.includes("1 Jan 2090")); assert.ok(html.includes("3 Jan 2090")); assert.ok(html.includes("Partial plan"));
});
test("selected owned record supplies the exact plan ID to analysis", async () => {
  const original = global.fetch; const writes: Record<string, unknown>[] = [];
  global.fetch = async (url, init) => { const path = String(url); if (path.endsWith("/auth/login")) return response(session); if (path.endsWith("/auth/me")) return response(farmer); if (path.includes("/api/cultivation-plans?")) return response({ items: [plan], total: 1, has_more: false }); if (path.endsWith("/api/farmer-workflow/plans/fictional-plan")) return response({ plan, personalized_plan: null }); if (path.endsWith("/api/farmer-workflow/analyze")) { writes.push(JSON.parse(String(init!.body))); return response(workflow); } throw new Error("Unexpected fictional request"); };
  const rendered = await renderSession(<Protected><PlanSelector>{record => <AnalysisPanel plan={record} />}</PlanSelector></Protected>, true);
  try {
    await act(async () => { rendered.tree.root.findByProps({ id: "selected-plan" }).props.onChange({ target: { value: plan.plan_id } }); });
    const run = rendered.tree.root.findAllByType("button").find(button => button.children.some(child => child === "Run / retry analysis"))!;
    assert.ok(run); await act(async () => { run.props.onClick(); });
    assert.deepEqual(writes, [{ plan_id: "fictional-plan" }]);
    assert.ok(JSON.stringify(rendered.tree.toJSON()).includes("Analysis unavailable"));
  } finally { act(() => rendered.tree.unmount()); global.fetch = original; }
});
test("cultivation workspace preserves partial-success state when changing workspace modes", async () => {
  const original = global.fetch; let writes = 0;
  global.fetch = async (url, init) => { const path = String(url); if (path.endsWith("/auth/login")) return response(session); if (path.endsWith("/auth/me")) return response(farmer); if (path.includes("/api/cultivation-plans?")) return response({ items: [], total: 0, has_more: false }); if (path.endsWith("/api/farmer-workflow/plans")) { writes++; assert.equal(init!.method, "POST"); return response({ plan, workflow }, 201); } throw new Error("Unexpected fictional request"); };
  const rendered = await renderSession(<Protected><CultivationPlanPage /></Protected>, true);
  try {
    act(() => rendered.tree.root.findAllByType("button").find(button => button.children.some(child => child === "Register cultivation"))!.props.onClick());
    act(() => { for (const [id, value] of [["region", "fictional-region"], ["land_size_acres", "2"], ["planting_date", "2090-01-01"], ["expected_harvest_date", "2090-04-01"]]) rendered.tree.root.findByProps({ id }).props.onChange({ target: { value } }); });
    await act(async () => { await rendered.tree.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
    assert.equal(writes, 1); assert.equal(rendered.tree.root.findAllByType("form").length, 0);
    await act(async () => rendered.tree.root.findAllByType("button").find(button => button.children.some(child => child === "Personalized schedule"))!.props.onClick());
    act(() => rendered.tree.root.findAllByType("button").find(button => button.children.some(child => child === "Register cultivation"))!.props.onClick());
    assert.equal(rendered.tree.root.findAllByType("form").length, 0); assert.equal(writes, 1);
    assert.ok(JSON.stringify(rendered.tree.toJSON()).includes("Retry saved-plan analysis"));
  } finally { act(() => rendered.tree.unmount()); global.fetch = original; }
});
test("existing creation route removes the submit form after a 201 analysis failure", async () => {
  const original = global.fetch; let writes = 0;
  global.fetch = async (url, init) => { const path = String(url); if (path.endsWith("/auth/login")) return response(session); if (path.endsWith("/auth/me")) return response(farmer); if (path.endsWith("/api/farmer-workflow/plans")) { writes++; assert.equal(init!.method, "POST"); return response({ plan, workflow }, 201); } throw new Error("Unexpected fictional request"); };
  const rendered = await renderSession(<NewPlanPage />, true);
  try {
    act(() => { for (const [id, value] of [["region", "fictional-region"], ["land_size_acres", "2"], ["planting_date", "2090-01-01"], ["expected_harvest_date", "2090-04-01"]]) rendered.tree.root.findByProps({ id }).props.onChange({ target: { value } }); });
    await act(async () => { await rendered.tree.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
    assert.equal(writes, 1); assert.equal(rendered.tree.root.findAllByType("form").length, 0);
    const html = JSON.stringify(rendered.tree.toJSON()); assert.ok(html.includes("fictional-plan")); assert.ok(html.includes("Retry saved-plan analysis"));
  } finally { act(() => rendered.tree.unmount()); global.fetch = original; }
});
test("workspace navigation includes Research Lab pointing to /crop-planning/research-demo", () => {
  const researchItem = WORKSPACE_NAV.find((item) => item.href.endsWith("/research-demo"));
  assert.ok(researchItem, "Research Lab navigation item must be present");
  assert.equal(researchItem.label, "Research Lab (2025-2026)");
  assert.equal(activeWorkspace("/crop-planning/research-demo", researchItem.href), true);
});
test("operational cultivation-plan page renders unvalidated risk without hardcoded scores", async () => {
  const original = global.fetch;
  global.fetch = async (url) => {
    const path = String(url);
    if (path.endsWith("/auth/login")) return response(session);
    if (path.endsWith("/auth/me")) return response(farmer);
    if (path.includes("/api/cultivation-plans?")) return response({ items: [plan], total: 1, has_more: false });
    return response({});
  };
  const rendered = await renderSession(<Protected><CultivationPlanPage /></Protected>, true);
  try {
    const json = JSON.stringify(rendered.tree.toJSON());
    assert.ok(json.includes("Current risk level not yet validated"));
    assert.ok(!json.includes("78/100"));
    assert.ok(!json.includes("65/100"));
    assert.ok(!json.includes("28/100"));
    assert.ok(!json.includes("20/100"));
    assert.ok(!json.includes("25/100"));
  } finally {
    act(() => rendered.tree.unmount());
    global.fetch = original;
  }
});

for (const approval of ["none", "missing", "unverified", "blank", "stale", "approved"] as const) {
  test(`primary cultivation route uses owned backend activities only: ${approval}`, async () => {
    const original = global.fetch;
    const eventName = approval === "approved" ? "FICTIONAL-approved-returned-activity" : "FICTIONAL-unapproved-activity";
    const activity = { activity_name: eventName, category: "management", notes: "FICTIONAL backend guidance only",
      verification_status: approval === "unverified" ? "source_checked" : "explicitly_verified_for_planning",
      approval_evidence: approval === "missing" ? "" : approval === "blank" ? "   " : "FICTIONAL specific approval",
      date_windows: [{ earliest: "2090-01-03", latest: "2090-01-05" }] };
    const saved = approval === "none" ? null : { personalized_plan: { ...partial,
      approval_status: "approved_activities_only", activities: [activity] }, revision_id: 1, revisions: [], stale: approval === "stale" };
    global.fetch = async url => {
      const path = String(url);
      if (path.endsWith("/auth/login")) return response(session);
      if (path.endsWith("/auth/me")) return response(farmer);
      if (path.includes("/api/cultivation-plans?")) return response({ items: [plan], total: 1, has_more: false });
      if (path.endsWith("/api/farmer-workflow/plans/fictional-plan")) return response({ plan, personalized_plan: saved });
      throw new Error("Unexpected request: primary page cannot invent planning results");
    };
    const rendered = await renderSession(<Protected><CultivationPlanPage /></Protected>, true);
    try {
      await act(async () => rendered.tree.root.findByProps({ id: "selected-plan" }).props.onChange({ target: { value: plan.plan_id } }));
      const json = JSON.stringify(rendered.tree.toJSON());
      for (const text of ["Corn", "fictional-region", "1 Jan 2090", "Partial plan"]) assert.ok(json.includes(text), text);
      for (const text of ["tons/acre", "NSKE", "NPK mixture", "Weekly furrow", "Current Stage", "Completed", "Follow these recommended practices"]) assert.ok(!json.includes(text), text);
      if (approval === "approved") {
        assert.ok(json.includes(eventName)); assert.ok(json.includes("3 Jan 2090")); assert.ok(json.includes("5 Jan 2090"));
      } else {
        assert.ok(!json.includes(eventName)); assert.ok(!json.includes("FICTIONAL backend guidance only"));
        assert.ok(json.includes("No explicitly approved, applicable activities"));
      }
    } finally { act(() => rendered.tree.unmount()); global.fetch = original; }
  });
}

