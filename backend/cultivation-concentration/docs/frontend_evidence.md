# Farmer-facing evidence states

These are additive annotations on existing endpoints. Existing fields, scientific
decisions, privacy filters, authentication, and approval requirements are preserved.
There is no universal success flag: read execution, evidence, disclosure, and
approval separately. Never infer that HTTP 200/201 means validated risk or a complete
approved schedule. Examples below are response excerpts using fictional context.

## Existing statuses to reuse

| Dimension | Existing field | Interpretation |
| --- | --- | --- |
| Execution | workflow `analysis_status` | `completed`: services ran; `failed`: saved-plan analysis failed; `not_applicable`: historical/started plan excluded by the existing policy |
| Internal computation | `assessment.indicators.status`, concentration comparison `status` | `available` describes internal computation only; `suppressed_or_insufficient` deliberately combines privacy and coverage limitations |
| Disclosure | CRUD concentration `status`, existing `privacy_policy` | `suppressed_for_privacy` and `collective_numeric_values_withheld_from_farmer` prohibit collective numeric display |
| Current scientific validation | assessment `status`, `risk_level` | `risk_level_unvalidated` with null means no validated current classification; alternatives retain `unknown_unvalidated` |
| Evidence sufficiency | `insufficient_evidence`, `missing_evidence` | Required evidence is unavailable; use explanations rather than constructing fallback labels |
| Conditional comparison | `eligible_alternative`, `comparison_available`, `no_lower_concentration_alternative` | Approved suitability and comparable coverage can permit a conditional comparison; this does not validate risk or establish production/profit benefits |
| Automatic recommendation | `recommendations.status` | `blocked_unvalidated_risk`: automatic recommendations remain unavailable |
| Planning completeness | planning `status` | `partial_plan` always remains partial, including when some activities are approved |
| Saved planning | `stale`, `based_on_updated_at` | A saved result can be outdated independently of its evidence status |
| Historical research | `historical_prediction.status`, `scope` | `historical_proxy_prediction` is separate research context; `insufficient_evidence` means no prediction is supported |

Experimental production/reference assessments retain their own validation fields.
Do not copy their categories or historical proxy labels into a current-risk card.

## Minimal new metadata

`disclosure_status: "collective_values_withheld"` appears on farmer-filtered
envelopes (owned risk assessments, alternative comparisons, and filtered workflow
sections). It applies to their entire nested payload. It describes the disclosure
policy even when computation was unavailable, without revealing suppressed counts.
It never overrides the existing internal computation status. List envelopes filtered
directly by the service annotate each item. Individual owned plan fields are not
passed through the collective-data filter.

Alternative comparison entries add `approval_status`:

- `applicable_suitability_approved`: suitability passed the existing approval and
  applicability gate at the cutoff. Coverage and comparison eligibility still need
  their existing independent checks.
- `applicable_suitability_unavailable`: no qualifying suitability approval exists.

Personalized responses add `approval_status`:

- `approved_activities_only`: the returned activities carry explicit planning
  verification and approval evidence. This does not approve the complete schedule.
- `no_approved_applicable_activities`: no activities passed the existing gates.
- `approval_not_recorded`: a legacy saved response has activities but does not
  record sufficient explicit approval metadata. Do not present them as approved.

Saved planning retrieval annotates legacy responses without rewriting stored
payloads, revisions, or timestamps. Optional Pydantic metadata fields allow older
payloads to remain valid. Missing/null metadata means unknown; never assume approval.

## Stable reason codes and neutral display text

`reason_codes` is an additive array. Order is not significant; codes can coexist.
Use these codes for UI logic and existing explanations/warnings for details. Unknown
future codes should fall back to a neutral unavailable message, not a risk label.

| Code | Suggested frontend explanation |
| --- | --- |
| `collective_values_protected` | Combined values are withheld to protect other farmers. |
| `risk_classification_unvalidated` | A validated current risk level is not available. |
| `production_evidence_missing` | Verified production evidence is not available. |
| `historical_baseline_missing` | A compatible historical baseline is not available. |
| `season_coverage_evidence_missing` | Verified season and participation evidence is not available. |
| `classification_reference_missing` | Approved classification reference evidence is not available. |
| `density_validation_missing` | Cultivation patterns have no independently validated risk meaning. |
| `coverage_or_privacy_limited` | The result is limited by coverage or privacy requirements. |
| `suitability_approval_unavailable` | Applicable suitability approval is not available. |
| `comparable_coverage_unavailable` | Comparable crop coverage evidence is not available. |
| `coverage_scope_mismatch` | Crop coverage sources cannot be compared under the same scope. |
| `schedule_incomplete` | This cultivation schedule is partial. |
| `applicable_guidance_unavailable` | No approved guidance applies to this planning context. |
| `analysis_unavailable` | Your plan was saved, but analysis could not finish. |
| `analysis_not_applicable` | Current pre-planting analysis does not apply to this record. |
| `analysis_not_evaluated` | This assessment was not performed. |
| `historical_prediction_unavailable` | Historical prediction requirements are not met. |
| `historical_proxy_only` | This is a historical research proxy, not current farmer risk. |

Workflow execution reason codes belong to the workflow envelope; assessment codes
belong to the assessment. Detailed prediction requirements remain in historical
`reason`. A single code is not a substitute for the scoped status and evidence fields.

## Safe response excerpts

Computed but withheld, with no validated current risk:

```json
{
  "status": "risk_level_unvalidated",
  "risk_level": null,
  "disclosure_status": "collective_values_withheld",
  "reason_codes": ["risk_classification_unvalidated", "collective_values_protected"],
  "indicators": {"status": "available", "crop": "Corn", "region": "north"}
}
```

No approved applicable planning activities:

```json
{
  "status": "partial_plan",
  "approval_status": "no_approved_applicable_activities",
  "reason_codes": ["schedule_incomplete", "applicable_guidance_unavailable"],
  "activities": [],
  "missing_categories": ["establishment", "fertilizer", "harvest", "land_preparation", "management"]
}
```

Saved plan with recoverable analysis failure (HTTP 201):

```json
{
  "status": "analysis_unavailable",
  "analysis_status": "failed",
  "reason_codes": ["analysis_unavailable"],
  "recovery": {
    "plan_saved": true, "retryable": true, "method": "POST",
    "endpoint": "/api/farmer-workflow/analyze",
    "request": {"plan_id": "<fictional-owned-plan-id>", "season": null}
  }
}
```

Retry the saved ID rather than resubmitting creation. HTTP 401/403/404/409/422/503
retain their existing `detail` response contracts; they are request errors, not
successful evidence results. Preserve ownership and role handling in the UI.

## Privacy and frontend integration

Never display absent collective counts, acreage, shares, cluster memberships, or
invented numeric ranges. Display only the owner's plan values where provided as
individual plan fields. Changing acreage, dates, or regions and re-running analysis
does not authorize collective disclosure. Metadata contains fixed categorical codes,
not additional partitions, numeric ranges, or risk thresholds.

Show separate cards for current descriptive analysis, historical research context,
conditional crop comparison, and partial planning. Read per-candidate approval and
eligibility together. Use existing session APIs and no farmer-ID selectors. Existing
clients can ignore additive metadata; new clients must treat missing metadata as
unknown and must not interpret `available` alone as permission to display values.
