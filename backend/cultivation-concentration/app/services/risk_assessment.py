"""Explain indicators without unvalidated risk levels or invented evidence."""
from app.services.risk_indicators import prepare_indicators


def assess(repository,cutoff,district,region,crop,season,harvest_date):
    values=prepare_indicators(repository,cutoff,district,region,crop,season,harvest_date)
    return explain(values)


def explain(values):
    explanations={
        'overlapping_farmer_count':'Distinct farmers with active available plans for the same district, region and crop in the inclusive +/-14-day harvest window.',
        'total_planned_acreage':'Each matching active plan contributes acreage once; recorded intentions are not verified district totals.',
        'harvest_overlap_intensity':'Window acreage divided by all future planned acreage for this district/region/crop; a concentration share, not a probability of loss.',
        'cluster_context':'District-level similarity/density context, not target-group membership. DBSCAN noise is not automatically High risk.'}
    missing=['Verified yield evidence and estimated production','Compatible regional historical concentration baseline',
             'Verified season mapping and participation coverage','Evidence-derived thresholds and agricultural expert reference labels',
             'Target-specific cluster membership and independently validated density meaning']
    if values['status']!='available':
        missing.append('Insufficient releasable farmer coverage; numeric indicators suppressed')
    reasons=['risk_classification_unvalidated','production_evidence_missing',
             'historical_baseline_missing','season_coverage_evidence_missing',
             'classification_reference_missing','density_validation_missing']
    if values['status']!='available':reasons.append('coverage_or_privacy_limited')
    return dict(status='risk_level_unvalidated',risk_level=None,indicators=values,
                reason_codes=reasons,
                explanations=explanations,missing_evidence=missing,
                interpretation='Descriptive pre-planting concentration assessment; no Low/Medium/High classification or observed market oversupply claim.')
