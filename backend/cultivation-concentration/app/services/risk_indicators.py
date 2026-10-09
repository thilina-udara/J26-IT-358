"""Cutoff-qualified descriptive indicators; no yield assumptions or risk labels."""
from datetime import date, timedelta
import math
from app.services.plan_clustering import MIN_FARMERS, analyze, snapshot


def prepare_indicators(repository, cutoff, district, region, crop, season, harvest_date, prepared_snapshot=None):
    if harvest_date <= cutoff.date():
        raise ValueError('Harvest must be after the forecast cutoff')
    region = ' '.join(region.split()).casefold()
    if not region:
        raise ValueError('Region cannot be blank')
    eligible = snapshot(repository,cutoff) if prepared_snapshot is None else prepared_snapshot
    cohort = [p for p in eligible if (p['district'],p['region'],p['crop'])==(district,region,crop)]
    start,end = harvest_date-timedelta(days=14),harvest_date+timedelta(days=14)
    overlapping = [p for p in cohort if start<=date.fromisoformat(p['expected_harvest_date'])<=end]
    result = dict(as_of=cutoff.isoformat(),district=district,region=region,crop=crop,season=season,
                  harvest_window_start=start.isoformat(),harvest_window_end=end.isoformat(),
                  label=dict(kind='unlabeled',value=None),
                  coverage_warning='Registered active pre-planting intentions only; participation and harvest estimates unverified. No oversupply inference.',
                  estimated_production_kg=None,production_status='unavailable: no verified, cutoff-available yield guidelines configured',
                  historical_concentration_baseline=None,
                  historical_status='unavailable: region/season/window/sampling/provenance/availability compatibility not established',
                  season_status='Caller-supplied context; stored plans lack verified season mapping, so no season-specific filtering is claimed.')
    if len({p['farmer_id'] for p in overlapping}) < MIN_FARMERS:
        result['status']='suppressed_or_insufficient'
        return result
    acreage=math.fsum(p['land_size_acres'] for p in overlapping)
    all_acreage=math.fsum(p['land_size_acres'] for p in cohort)
    result.update(status='available',overlapping_farmer_count=len({p['farmer_id'] for p in overlapping}),
                  overlapping_plan_count=len(overlapping),total_planned_acreage=acreage,
                  harvest_overlap_intensity=acreage/all_acreage,
                  overlap_definition='Share of same-district/region/crop future planned acreage in the inclusive anchor +/-14-day window; not duration overlap or daily harvested supply.')
    regional=[p for p in eligible if (p['district'],p['region'])==(district,region)
              and start<=date.fromisoformat(p['expected_harvest_date'])<=end]
    other_crops=[p for p in regional if p['crop']!=crop]
    # Denominator could otherwise reveal a protected other-crop complement.
    if len({p['farmer_id'] for p in other_crops})>=MIN_FARMERS:
        result['regional_crop_context']=dict(status='available',
            crop_share_of_regional_window_acreage=acreage/math.fsum(p['land_size_acres'] for p in regional),
            definition='Same-crop window acreage / all-crop window acreage in the same district and region; descriptive share, not demand or crop interchangeability')
    else:
        result['regional_crop_context']=dict(status='suppressed_or_insufficient',
            reason='Other-crop denominator has fewer than three distinct farmers; complementary share withheld')
    from app.services.privacy import analyst_view
    clustering=analyst_view(analyze(eligible,district))
    # District-level context only; never infer a target's assignment from released summaries.
    result['cluster_context']=dict(scope='district eligible snapshot; not target-group membership',
        configuration=clustering.get('configuration'),kmeans=clustering['kmeans'],
        dbscan=clustering['dbscan'],noise=clustering['noise'])
    return result
