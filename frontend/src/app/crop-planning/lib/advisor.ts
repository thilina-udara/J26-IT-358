import { CROPS, type Crop, type Workflow } from "./contracts";
import { eligibleCandidates } from "./evidence";

export type ValidatedRisk = "Low" | "Medium" | "High";

export function validatedRisk(report: Workflow): ValidatedRisk | null {
  const assessment = report.assessment;
  if (report.analysis_status !== "completed" || assessment.status !== "risk_level_validated") return null;
  return assessment.risk_level === "Low" || assessment.risk_level === "Medium" || assessment.risk_level === "High"
    ? assessment.risk_level : null;
}

export function recommendedCrops(report: Workflow, original: Crop) {
  if (validatedRisk(report) !== "High" || report.recommendations.status !== "alternatives_available") return [];
  const seen = new Set<Crop>([original]);
  return eligibleCandidates(report.recommendations.alternatives ?? []).filter(candidate => {
    if (!CROPS.includes(candidate.crop) || seen.has(candidate.crop)) return false;
    seen.add(candidate.crop);
    return true;
  }).slice(0, 3);
}
