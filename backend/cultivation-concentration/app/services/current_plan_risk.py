"""Evidence boundary for current intentions; deliberately no invented classifier."""

def evaluate(indicators):
    return dict(status='insufficient_evidence',risk_level=None,
        methodology_version='current_plan_concentration_v1',label_kind='unlabeled',
        indicator_status=indicators['status'],
        interpretation='Pre-planting registered intention concentration; no claim that prices, market losses or oversupply follow',
        evidence=indicators,
        definitions=dict(overlap='Inclusive expected-harvest anchor +/-14 days, same crop/district/region',
            farmer_count='Distinct farmers, including requester once as a farmer; several legitimate plans remain separate acreage contributions',
            acreage='Each latest available active future plan contributes its acreage once',
            harvest_concentration='Overlapping acres / all future registered same-crop district/region acres',
            regional_pattern='Same-crop window share of all-crop regional window acreage, released only with protected denominator',
            clusters='K-Means similarity and DBSCAN density are context, not risk categories'),
        missing_reference_evidence=['Verified real intention snapshots and documented registration coverage',
            'Comparable crop/region/season/forecast-horizon reference cohorts',
            'Approved operational category definition and threshold version with cutoff availability',
            'Independent agricultural review and prospective checks of the intended concentration construct'],
        classification_explanation='No representative real reference distribution or approved operational thresholds are established; a percentile or cluster ID would not justify Low/Medium/High.')
