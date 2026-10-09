"""Read-only research reference adapter; artifacts never establish verification."""
import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

from app.schemas.production_risk import ProductionRegistry
from app.services.production_risk import evaluate as production_evaluate

VERSION = 'district_expected_production_reference_v1'
SCOPE = 'frozen_reference_2020_2021'
DEFAULT_PATH = Path(__file__).resolve().parents[2] / 'data/research/production_reference/v1/district_expected_production_reference_v1_8c03ae057cad2ef9.json'
PRIVATE = ('current_expected_production_kg', 'overlapping_plan_count', 'overlapping_acres',
           'historical_reference_median_kg', 'historical_p33_kg', 'historical_p67_kg', 'reference_sample_size')


def load_reference(path=DEFAULT_PATH):
    """Check content fingerprint and CSV companion without opening source records."""
    path = Path(path)
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()[:16]
    bundle = json.loads(content)
    if path.stem != f'{VERSION}_{digest}' or bundle['version'] != VERSION:
        raise ValueError('Reference fingerprint/version mismatch')
    if bundle['permitted_years'] != [2020, 2021, 2022, 2023]:
        raise ValueError('Unsupported reference cohort')
    method = bundle['method']
    if (method['percentile_method'] != 'linear' or method['cross_season_year_members'] is not False
            or method['overlapping_anchors_independent'] is not False):
        raise ValueError('Unsupported window definition')
    cells = bundle['reference_distributions']
    with path.with_name(path.stem + '_distributions.csv').open(newline='', encoding='utf-8') as stream:
        companion = list(csv.DictReader(stream))
    if len(cells) != len(companion):
        raise ValueError('Reference CSV row mismatch')
    seen = set()
    for cell, row in zip(cells, companion):
        key = tuple(cell[k] for k in ('scope', 'half_window_days', 'district', 'crop', 'season', 'recorded_year'))
        if key in seen:
            raise ValueError('Duplicate reference key')
        seen.add(key)
        for name in ('scope', 'half_window_days', 'district', 'crop', 'season', 'recorded_year', 'plan_sample_size', 'anchor_sample_size'):
            if row[name] != ('' if cell[name] is None else str(cell[name])):
                raise ValueError('Reference CSV key/count mismatch')
        for metric, stats in cell['distributions'].items():
            for stat, value in stats.items():
                if not math.isfinite(value) or float(row[f'{metric}_{stat}']) != value:
                    raise ValueError('Reference CSV quantile mismatch')
    return bundle


def evaluate(plans, owned, season, cutoff, registry, path=DEFAULT_PATH):
    result = dict(experimental_risk_level=None, status='insufficient_evidence', validation_status='unvalidated',
                  reference_version=None, **{k: None for k in PRIVATE}, new_farmer_production_kg=None,
                  explanation='Research-only expected-production concentration; not observed oversupply or market loss.',
                  limitations=['Correlated harvest anchors are not independent samples.',
                               'Recorded expected production is not observed harvest production.',
                               'Qualitative outputs do not provide differential privacy.'], reasons=[])
    try:
        bundle = load_reference(path)
        result['reference_version'] = bundle['version']
        match = dict(scope=SCOPE, half_window_days=14, district=owned['district'], crop=owned['crop'], season=season)
        cell = next((c for c in bundle['reference_distributions'] if all(c[k] == v for k, v in match.items())
                     and c['recorded_year'] is None), None)
        windows = [w for w in bundle['windows'] if all(w[k] == v for k, v in match.items())]
        if cell is None or cell['plan_sample_size'] < 3 or cell['anchor_sample_size'] < 3:
            raise ValueError('Matching reference absent or too sparse for software comparison; adequacy still requires review')
        if any(w['recorded_year'] not in (2020, 2021) or
               date.fromisoformat(w['window_start']) != date.fromisoformat(w['harvest_anchor']) - timedelta(days=14) or
               date.fromisoformat(w['window_end']) != date.fromisoformat(w['harvest_anchor']) + timedelta(days=14) for w in windows):
            raise ValueError('Reference window/cohort mismatch')
        values = [w['expected_kg'] for w in windows]
        lower, median, upper = np.percentile(values, [33, 50, 67], method='linear')
        if len(values) != cell['anchor_sample_size'] or any(not math.isclose(float(v), cell['distributions']['expected_kg'][k])
                for v, k in zip((lower, median, upper), ('P33', 'median', 'P67'))):
            raise ValueError('Reference distribution does not match windows')
        # Explicit trusted attestation must name this immutable artifact and its scope.
        # Numeric equivalence alone never grants availability, yield or coverage verification.
        entries = [e for e in registry.evidence if (e.district, e.crop, e.season) == (owned['district'], owned['crop'], season)
                   and Path(path).stem in e.reference and SCOPE in e.reference_definition
                   and sorted(e.reference_window_production_kg) == sorted(values)
                   and e.available_at.date() >= e.historical_observation_end
                   and e.verified_at >= e.available_at
                   and e.historical_observation_end >= max(date.fromisoformat(w['harvest_anchor']) for w in windows)]
        if not entries:
            raise ValueError('Artifact lacks verified cutoff-available yield, coverage and season-comparability attestation')
        # Defense in depth: even direct callers cannot include unavailable or inactive versions.
        eligible = [p for p in plans if p.get('status', 'active') == 'active'
                    and datetime.fromisoformat(p['updated_at']) <= cutoff
                    and datetime.fromisoformat(p.get('submitted_at', p['updated_at'])) <= cutoff
                    and date.fromisoformat(p['planting_date']) > cutoff.date()]
        if not any(p['plan_id'] == owned['plan_id'] for p in eligible):
            raise ValueError('Owned plan unavailable at cutoff')
        if cutoff.date() >= date.fromisoformat(owned['planting_date']):
            raise ValueError('Analysis is not before planting')
        assessed = production_evaluate(eligible, owned, season, cutoff,
            ProductionRegistry(evidence=entries, season_assignments=registry.season_assignments))
        result['reasons'].extend(assessed['reasons'])
        if assessed['experimental_risk_level'] is None:
            return result
        result.update(status='experimental_available', experimental_risk_level=assessed['experimental_risk_level'],
                      reference_sample_size=cell['anchor_sample_size'], reference_plan_sample_size=cell['plan_sample_size'],
                      current_expected_production_kg=assessed['expected_total_production_kg'],
                      historical_reference_median_kg=float(median), historical_p33_kg=float(lower), historical_p67_kg=float(upper),
                      overlapping_plan_count=assessed['overlapping_plan_count'], overlapping_acres=assessed['overlapping_acres'],
                      new_farmer_production_kg=assessed['new_farmer_production_kg'], reference_scope=SCOPE)
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        result['reasons'].append(str(exc) if not isinstance(exc, OSError) else 'Reference artifact unavailable')
    return result


def farmer_response(result):
    """Withhold exact aggregates even when group size increases, preventing differencing."""
    return dict(result, **{k: None for k in (*PRIVATE, 'reference_plan_sample_size')},
                privacy_status='collective_and_reference_metrics_withheld_from_farmer')
