"""Frontend presentation vocabulary, separate from research decision gates."""
from typing import Literal

DisclosureStatus = Literal['collective_values_withheld']
PlanningApprovalStatus = Literal['approved_activities_only',
    'no_approved_applicable_activities', 'approval_not_recorded']
ReasonCode = Literal[
    'collective_values_protected', 'risk_classification_unvalidated',
    'production_evidence_missing', 'historical_baseline_missing',
    'season_coverage_evidence_missing', 'classification_reference_missing',
    'density_validation_missing', 'coverage_or_privacy_limited',
    'suitability_approval_unavailable', 'comparable_coverage_unavailable',
    'coverage_scope_mismatch', 'schedule_incomplete', 'applicable_guidance_unavailable',
    'analysis_unavailable', 'analysis_not_applicable', 'analysis_not_evaluated',
    'historical_proxy_only', 'historical_prediction_unavailable',
]
