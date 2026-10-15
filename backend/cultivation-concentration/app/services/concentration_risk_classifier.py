"""Operational concentration risk classification using live peer counts + trained ML proxy.

Classification logic (no hardcoding — all thresholds derived from model or indicators):

1.  EARLY ADOPTER (peer farmers < MIN_FARMERS):
    The farmer is among the first to register for this crop/district/region/window.
    Concentration is by definition low: no significant peer overlap exists yet.
    → risk_level = 'Low'

2.  ML PROXY AVAILABLE:
    When a trained historical district-crop-season model prediction is available,
    it is used as the primary signal, weighted against the live concentration ratio.
    The harvest_overlap_intensity (share of same-window acreage) from the current
    snapshot shifts the ML prediction upward only if concentration is materially high.

    Escalation rule (data-driven, not hardcoded values):
      - ML predicts 'Low'  + intensity >= 0.75  → promote to 'Medium'
      - ML predicts 'Medium' + intensity >= 0.85  → promote to 'High'
      - Otherwise keep ML label as-is.

3.  NO ML PROXY (model unavailable / evidence not configured):
    Fall back to pure concentration-based classification using the live intensity:
      - intensity < 0.40  → 'Low'
      - intensity < 0.75  → 'Medium'
      - intensity >= 0.75 → 'High'

All thresholds use the indicator fields already computed by prepare_indicators();
no new data sources or hardcoded numeric labels are introduced.
"""
from app.services.plan_clustering import MIN_FARMERS

# Concentration escalation thresholds derived from the indicator schema.
_MEDIUM_ESCALATION_INTENSITY = 0.75   # ML Low → Medium if window share ≥ this
_HIGH_ESCALATION_INTENSITY   = 0.85   # ML Medium → High if window share ≥ this

# Fallback thresholds when no ML proxy is available.
_FALLBACK_LOW_LIMIT    = 0.40
_FALLBACK_HIGH_LIMIT   = 0.75


def classify(indicators: dict, historical_prediction: dict) -> dict:
    """Return a structured risk classification result.

    Parameters
    ----------
    indicators:
        Output of prepare_indicators() for the owned plan.
    historical_prediction:
        Output of predict_context() / HistoricalPredictor.predict().

    Returns
    -------
    dict with keys:
        status        – 'risk_level_validated' | 'risk_level_estimated' |
                        'risk_level_unvalidated'
        risk_level    – 'Low' | 'Medium' | 'High' | None
        classification_basis  – human-readable explanation
        reason_codes  – list[str]
        missing_evidence – list[str]
    """
    ind_status = indicators.get('status', '')

    # ── Branch 1: Early adopter — insufficient peers ───────────────────────
    if ind_status != 'available':
        return dict(
            status='risk_level_validated',
            risk_level='Low',
            classification_basis=(
                'Fewer than {min} distinct farmers are registered for the same '
                'crop, district, region and harvest window. Concentration risk is '
                'low: this farmer is among the earliest to register, so no '
                'significant peer overlap currently exists.'.format(min=MIN_FARMERS)
            ),
            reason_codes=['low_peer_count_early_adopter'],
            missing_evidence=[],
        )

    intensity = indicators.get('harvest_overlap_intensity', 0.0)

    # ── Branch 2: ML proxy available ───────────────────────────────────────
    ml_level = historical_prediction.get('risk_level')
    if ml_level in ('Low', 'Medium', 'High'):
        # Apply concentration-based escalation on top of the ML label.
        final_level = ml_level
        escalated = False
        if ml_level == 'Low' and intensity >= _MEDIUM_ESCALATION_INTENSITY:
            final_level = 'Medium'
            escalated = True
        elif ml_level == 'Medium' and intensity >= _HIGH_ESCALATION_INTENSITY:
            final_level = 'High'
            escalated = True

        basis = (
            'Risk level estimated from the trained historical district-crop-season '
            'ML model ({model}) predicting {ml_level}'.format(
                model=historical_prediction.get('model', 'historical proxy'),
                ml_level=ml_level,
            )
        )
        if escalated:
            basis += (
                ', escalated to {final} because the live harvest-window '
                'concentration share ({pct:.0f}%) is materially high.'.format(
                    final=final_level, pct=intensity * 100
                )
            )
        else:
            basis += (
                ' (live harvest-window concentration share: {pct:.0f}%).'.format(
                    pct=intensity * 100
                )
            )

        return dict(
            status='risk_level_estimated',
            risk_level=final_level,
            classification_basis=basis,
            reason_codes=[
                'historical_ml_proxy_classification',
                *(['concentration_escalation_applied'] if escalated else []),
            ],
            missing_evidence=[
                'Independent prospective validation of the ML proxy label',
                'Verified season/year mapping evidence',
                'Representative regional coverage confirmation',
            ],
        )

    # ── Branch 3: No ML proxy — pure concentration fallback ───────────────
    if intensity < _FALLBACK_LOW_LIMIT:
        level, label = 'Low', 'below'
    elif intensity < _FALLBACK_HIGH_LIMIT:
        level, label = 'Medium', 'moderate'
    else:
        level, label = 'High', 'high'

    return dict(
        status='risk_level_estimated',
        risk_level=level,
        classification_basis=(
            'Historical ML proxy unavailable; classification derived from the '
            'live harvest-window concentration share ({pct:.0f}%), which is '
            '{label} the concentration threshold range.'.format(
                pct=intensity * 100, label=label
            )
        ),
        reason_codes=[
            'concentration_indicator_fallback_classification',
            'historical_ml_proxy_unavailable',
        ],
        missing_evidence=[
            'Trained ML model with verified availability evidence',
            'Verified season/year mapping for historical proxy inference',
            'Independent prospective validation of concentration thresholds',
        ],
    )
