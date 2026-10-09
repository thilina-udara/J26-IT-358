"""Retrospective research replay. No automatic sealed-data loader or public API.

Call replay only with separately authorized rows. Real publication/yield evidence
is never synthesized; original application gates and ownership remain unchanged.
"""
import math
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.schemas.production_risk import ProductionRegistry
from app.services.production_risk import evaluate
from ml.preprocessing.build_production_reference import build, normalize


def overlap_cohort(peers, requester, season=None):
    """One requester per inclusive district/crop harvest window; optional recorded season."""
    records={p['plan_id']:p for p in peers if p['plan_id']!=requester['plan_id']}
    records[requester['plan_id']]=requester
    return [q for q in records.values() if (q['district'],q['crop'])==(requester['district'],requester['crop'])
            and (season is None or q.get('season')==season)
            and abs((datetime.fromisoformat(q['expected_harvest_date'])-datetime.fromisoformat(requester['expected_harvest_date'])).days)<=14]


def replay(history, current, registry=None, *, access_authorized=False, reference_end_year=2024):
    if not access_authorized:
        raise PermissionError('Explicit source-specific authorization required before backtest access')
    # Check cohort boundaries before inspecting dates or measurements.
    if reference_end_year not in (2023,2024):
        raise ValueError('Unsupported historical cohort')
    if any(not 2020 <= int(r['Year']) <= reference_end_year for r in history):
        raise ValueError('Reference must contain only 2020–2024 records')
    if any(int(r['Year']) != 2025 for r in current):
        raise ValueError('Replay must contain only 2025 records; 2026 remains excluded')
    # A recorded 2024 season may harvest in 2025: it is not a completed
    # pre-2025 reference simply because its Year column says 2024.
    eligible_history = [r for r in history if datetime.strptime(r['Expected_Harvest_Date'], '%m/%d/%Y').year <= 2024]
    reference = build(eligible_history, reference_end_year=reference_end_year)
    # Normalize replay under an explicit authorized cohort, not the default loader.
    plans, _ = normalize(current, reference_end_year=2025)
    plans.sort(key=lambda p: (p['planting_date'], p['plan_id']))
    evidence = registry or ProductionRegistry()
    seen = []
    results = []
    for p in plans:
        cutoff = datetime.fromisoformat(p['planting_date']).replace(tzinfo=timezone.utc) - timedelta(seconds=1)
        # Assumed submission immediately before planting; ties are processed as a
        # date batch so record-ID ordering cannot manufacture extra overlap.
        submitted = dict(plan_id=p['plan_id'], farmer_id='unverified-farmer-identity', district=p['district'], crop=p['crop'],
            region='unspecified', land_size_acres=p['acres'], planting_date=p['planting_date'],
            expected_harvest_date=p['harvest_date'], updated_at=cutoff.isoformat(), submitted_at=cutoff.isoformat(), status='active')
        peers = [q for q in seen if q['planting_date'] < p['planting_date']
                 and q['expected_harvest_date'] >= p['planting_date']]
        seen.append(submitted)
        cohort = overlap_cohort(peers,submitted)
        samples = [w for w in reference['windows'] if w['scope']==f'descriptive_development_2020_{reference_end_year}'
                   and w['half_window_days']==14 and (w['district'], w['crop'], w['season'])==(p['district'],p['crop'],p['season'])]
        compatible = [e for e in evidence.evidence if sorted(e.reference_window_production_kg)==sorted(w['expected_kg'] for w in samples)
                      and e.historical_observation_end.year<=2024 and e.available_at<=cutoff
                      and all(datetime.fromisoformat(w['harvest_anchor']).date()<=e.historical_observation_end for w in samples)
                      and e.available_at.date()>=e.historical_observation_end and e.verified_at>=e.available_at]
        assessment = evaluate(peers, submitted, p['season'], cutoff,
            ProductionRegistry(evidence=compatible, season_assignments=evidence.season_assignments))
        prior = {q['plan_id']:q for q in plans}
        # Private research calculation, not farmer-facing aggregate disclosure.
        recorded = math.fsum(prior[q['plan_id']]['expected_kg'] for q in cohort)
        cell = next((c for c in reference['reference_distributions'] if c['scope']==f'descriptive_development_2020_{reference_end_year}'
                     and c['half_window_days']==14 and c['recorded_year'] is None
                     and (c['district'],c['crop'],c['season'])==(p['district'],p['crop'],p['season'])),None)
        results.append(dict(case_index=len(results)+1,district=p['district'],crop=p['crop'],season=p['season'],
            expected_harvest_date=p['harvest_date'],planting_date=p['planting_date'],
            retrospective=True,cutoff_assumption='immediately before planting; same-date peers excluded',
            plan_count=len(cohort),planned_acres=math.fsum(q['land_size_acres'] for q in cohort),
            recorded_expected_production_kg=recorded,observed_harvest_production_kg=None,
            assessment=assessment,reference_quantiles=None if cell is None else cell['distributions']['expected_kg'],
            reference_anchor_count=len(samples)))
    return dict(retrospective=True,reference=reference,results=results,
        category_counts=dict(Counter(r['assessment']['experimental_risk_level'] or 'insufficient_evidence' for r in results)),
        limitations=['Submission timestamps assumed, not observed.', 'Record ID is not verified distinct farmer identity.',
                     'Recorded expected production is not verified yield or observed harvest.',
                     'Harvest-year spillover and season mapping need review.',
                     'Research calculations are private; do not publish row-level cases without disclosure review.'])
