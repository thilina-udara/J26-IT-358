import type { Activity, Candidate, Evidence, Personalized, Submission } from "./contracts";

const REASONS: Record<string, string> = {
  collective_values_protected: "Combined farmer values are withheld for privacy.",
  risk_classification_unvalidated: "A validated current risk level is not available.",
  production_evidence_missing: "Verified production evidence is not available.",
  historical_baseline_missing: "A compatible historical baseline is not available.",
  season_coverage_evidence_missing: "Verified season and participation evidence is not available.",
  classification_reference_missing: "Approved classification reference evidence is not available.",
  density_validation_missing: "Cultivation patterns have no independently validated risk meaning.",
  coverage_or_privacy_limited: "This result is limited by coverage or privacy requirements.",
  suitability_approval_unavailable: "Applicable suitability approval is not available.",
  comparable_coverage_unavailable: "Comparable crop coverage evidence is not available.",
  coverage_scope_mismatch: "The crop coverage sources cannot be compared under the same scope.",
  schedule_incomplete: "This cultivation schedule is partial.",
  applicable_guidance_unavailable: "No approved guidance applies to this planning context.",
  analysis_unavailable: "Your plan was saved, but analysis could not finish.",
  analysis_not_applicable: "Pre-planting analysis does not apply to this record.",
  analysis_not_evaluated: "This assessment was not performed.",
  historical_prediction_unavailable: "Historical prediction requirements are not met.",
  historical_proxy_only: "Historical research context does not establish current farmer risk.",
};
export function evidenceMessages(evidence: Evidence): string[] {
  return Array.from(new Set((evidence.reason_codes ?? []).map(code => REASONS[code] ?? "Additional evidence is unavailable; review the result details.")));
}
export function approvedActivities(result: Personalized): Activity[] {
  if (result.approval_status !== "approved_activities_only") return [];
  return result.activities.filter(a => a.verification_status === "explicitly_verified_for_planning" && typeof a.approval_evidence === "string" && Boolean(a.approval_evidence.trim()));
}
export function eligibleCandidates(candidates: Candidate[]): Candidate[] {
  return candidates.filter(c => c.status === "eligible_alternative" && c.approval_status === "applicable_suitability_approved");
}
export function submissionOutcome(response: Submission) {
  return { planId: response.plan.plan_id, analysisFailed: response.workflow.analysis_status === "failed", retryAnalysis: response.workflow.recovery?.retryable === true };
}
export function safeSource(url?: string): string | undefined {
  if (!url) return undefined;
  try { const parsed = new URL(url); return ["https:", "http:"].includes(parsed.protocol) ? parsed.href : undefined; } catch { return undefined; }
}
