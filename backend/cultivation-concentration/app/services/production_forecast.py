"""Exploratory 2026 kg forecasts from recorded district-season production only.

No area-to-kg assumptions, live-plan access, model artifacts or network calls.
Protocol and provenance audit: docs/pp1_production_forecast.md.
"""
import csv
import hashlib
import math
from pathlib import Path
from statistics import mean
from app.services.historical_trend import quantile

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/official/official_historical_2001_2025.csv'
CUTOFF = 2025
FORECAST_YEAR = 2026
MIN_FIT = 5
MIN_SELECTION = 5
MIN_CALIBRATION = 8
MODELS = ('naive', 'linear_trend')  # Ties prefer the simpler naive method.
MODEL_NAMES = {'naive': 'Naive: previous year production', 'linear_trend': 'Linear trend: OLS with nonnegative forecast'}
LIMITATIONS = [
    'Exploratory forecast of recorded production. Whether the source values were measured or estimated is undocumented; independent provenance and publication/revision dates are unverified.',
    'A forecast is a historical production reference, not a recommended or economically optimal target. Market demand, prices and losses are not modeled.',
    'The reference range shifts empirical historical forecast errors to 2026. It is not a validated 80% prediction interval or a guarantee of future coverage.',
    'Short histories, serial dependence, weather and structural breaks limit extrapolation. Finite extreme values are retained; OLS and MAE may be sensitive to them.',
    'Evaluation uses recorded-year separation. Actual historical information availability and the completeness of district population coverage are unverified.',
]


def read_rows():
    with DATA.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'district_name', 'crop_name', 'year', 'season', 'production_metric_tons'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('An explicit recorded production quantity in metric tons is required')
        return list(reader)


def to_kg(value, unit='metric tons'):
    if unit not in ('metric tons', 'kg'):
        raise ValueError('Unsupported production unit')
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError('Production must be finite and nonnegative')
    kg = number * (1000 if unit == 'metric tons' else 1)
    if not math.isfinite(kg):
        raise ValueError('Production unit conversion overflow')
    return kg


def linear_model(points):
    center = mean(p['year'] for p in points)
    level = mean(p['production_kg'] for p in points)
    slope = math.fsum((p['year'] - center) * (p['production_kg'] - level) for p in points) / math.fsum((p['year'] - center) ** 2 for p in points)
    if not all(math.isfinite(v) for v in (center, level, slope)):
        raise ValueError('Non-finite trend')
    return dict(center_year=center, level_kg=level, slope_kg_per_year=slope)


def linear_prediction(model, year):
    value = model['level_kg'] + model['slope_kg_per_year'] * (year - model['center_year'])
    if not math.isfinite(value):
        raise ValueError('Non-finite forecast')
    return max(0.0, value)


def choose(errors):
    return min(MODELS, key=lambda name: mean(abs(error[name]) for error in errors))


def reference_range(point, errors):
    lower_error, upper_error = quantile(errors, .1), quantile(errors, .9)
    lower, upper = max(0.0, point + lower_error), max(0.0, point + upper_error)
    if not all(math.isfinite(v) for v in (lower_error, upper_error, lower, upper)):
        raise ValueError('Non-finite reference range')
    return dict(lower=lower, upper=upper, lower_error_kg=lower_error, upper_error_kg=upper_error,
                quantiles=[.1, .9], calibration_count=len(errors), nominal_coverage=None,
                interpretation='Central 80% empirical historical policy-error range; future coverage unvalidated')


def forecast(rows, district, crop, season):
    result = dict(status='Insufficient Data', reason=None, mode='Exploratory recorded-production forecast',
        forecast_year=FORECAST_YEAR, training_cutoff_year=CUTOFF, unit='kg', district=district, crop=crop, season=season,
        expected_production_kg=None, reference_range_kg=None, model=None, model_name=None, trend=None, candidate_forecasts_kg=None,
        training_years=[], history=[], candidate_backtests=[], policy_backtests=[], evaluation=None,
        quality=dict(duplicate_rows_ignored=0, invalid_years=[], missing_years=[], forecast_floored_at_zero=False),
        planned_comparison=dict(status='Planned production comparison unavailable', cumulative_planned_kg=None,
            reason='No verified production estimate with matching crop/district/season and population coverage; registered farmer plans are not comparable with district totals.'),
        limitations=list(LIMITATIONS))
    if season not in ('Maha', 'Yala'):
        result['reason'] = 'Forecast a single recorded season; annual Total rows cannot be added to seasonal totals.'
        return result
    amounts, invalid = {}, set()
    for row in rows:
        if (row.get('district_name'), row.get('crop_name'), row.get('season')) != (district, crop, season):
            continue
        try:
            year = int(row['year'])
        except (ValueError, TypeError, KeyError):
            result['reason'] = 'Invalid year in selected series.'
            return result
        # Do not inspect 2026/future production values or units, even if present.
        if year > CUTOFF:
            continue
        try:
            if row.get('production_unit', 'metric tons') != 'metric tons':
                raise ValueError('The source column must contain metric tons')
            value = to_kg(row['production_metric_tons'])
            if year in amounts:
                if amounts[year] != value:
                    invalid.add(year)
                else:
                    result['quality']['duplicate_rows_ignored'] += 1
            else:
                amounts[year] = value
        except (ValueError, TypeError, KeyError, OverflowError):
            invalid.add(year)
    result['quality']['invalid_years'] = sorted(invalid)
    if invalid:
        result['reason'] = 'Selected historical production has missing, negative, non-finite, conflicting or inconsistent-unit values.'
        return result
    points = [dict(year=year, production_kg=value) for year, value in sorted(amounts.items())]
    result['training_years'] = list(sorted(amounts))
    result['history'] = [dict(point, fitted_kg=None) for point in points]
    if points:
        result['quality']['missing_years'] = sorted(set(range(points[0]['year'], CUTOFF + 1)) - set(amounts))
    if len(points) < MIN_FIT or not points or points[-1]['year'] != CUTOFF:
        result['reason'] = 'Need at least five historical observations and a recorded 2025 value for a comparable one-year-ahead 2026 forecast.'
        return result
    try:
        errors = []
        for index in range(MIN_FIT, len(points)):
            past, actual = points[:index], points[index]
            if actual['year'] != past[-1]['year'] + 1:
                continue  # Missing years are not interpolated or treated as zero.
            predictions = dict(naive=past[-1]['production_kg'], linear_trend=linear_prediction(linear_model(past), actual['year']))
            # Choose this historical year's model only from strictly earlier errors.
            if len(errors) >= MIN_SELECTION:
                model = choose(errors)
                error = actual['production_kg'] - predictions[model]
                result['policy_backtests'].append(dict(year=actual['year'], trained_through=past[-1]['year'],
                    selection_years=[record['year'] for record in errors], model=model,
                    forecast_kg=predictions[model], observed_kg=actual['production_kg'], error_kg=error,
                    naive_error_kg=actual['production_kg'] - predictions['naive']))
            record = dict(year=actual['year'], trained_through=past[-1]['year'], observed_kg=actual['production_kg'],
                          forecasts_kg=predictions, **{name: actual['production_kg'] - predictions[name] for name in MODELS})
            if not all(math.isfinite(record[name]) for name in MODELS):
                raise ValueError('Non-finite error')
            errors.append(record)
        result['candidate_backtests'] = errors
        if len(result['policy_backtests']) < MIN_CALIBRATION:
            result['reason'] = 'Need five earlier selection errors plus eight subsequent one-year policy errors for an empirical reference range.'
            return result
        selected = choose(errors)
        trend = linear_model(points)
        candidates = dict(naive=points[-1]['production_kg'], linear_trend=linear_prediction(trend, FORECAST_YEAR))
        point = candidates[selected]
        reference = reference_range(point, [r['error_kg'] for r in result['policy_backtests']])
        if not math.isfinite(point):
            raise ValueError('Non-finite forecast')
        result.update(status='available', model=selected, model_name=MODEL_NAMES[selected], trend=trend,
            expected_production_kg=point, reference_range_kg=reference, candidate_forecasts_kg=candidates,
            history=[dict(p, fitted_kg=linear_prediction(trend, p['year']) if selected == 'linear_trend' else None) for p in points],
            evaluation=dict(candidate_mae_kg={name: mean(abs(r[name]) for r in errors) for name in MODELS},
                candidate_years=[r['year'] for r in errors],
                selection_policy_mae_kg=mean(abs(r['error_kg']) for r in result['policy_backtests']),
                naive_same_period_mae_kg=mean(abs(r['naive_error_kg']) for r in result['policy_backtests']),
                policy_years=[r['year'] for r in result['policy_backtests']],
                definition='Expanding-origin, one-calendar-year-ahead forecasts; each past method choice uses earlier errors only. 2026 method uses all candidate errors through 2025; MAE ties prefer naive.'))
        if selected == 'linear_trend':
            raw = trend['level_kg'] + trend['slope_kg_per_year'] * (FORECAST_YEAR - trend['center_year'])
            result['quality']['forecast_floored_at_zero'] = raw < 0
        return result
    except (ValueError, OverflowError, ZeroDivisionError):
        result.update(status='Insufficient Data', expected_production_kg=None, reference_range_kg=None,
                      model=None, model_name=None, trend=None, candidate_forecasts_kg=None, candidate_backtests=[], policy_backtests=[],
                      evaluation=None, history=[], reason='Forecast arithmetic is unstable or non-finite; no production estimate is displayed.')
        return result


def options(rows=None):
    rows = read_rows() if rows is None else rows
    groups = {}
    for row in rows:
        year = int(row['year'])
        if year > CUTOFF or row['season'] not in ('Maha', 'Yala'):
            continue
        key = (row['district_name'], row['crop_name'], row['season'])
        groups.setdefault(key, set()).add(year)
    return [dict(district=d, crop=c, season=s, years=sorted(years)) for (d, c, s), years in sorted(groups.items())]


def report(district, crop, season):
    rows = read_rows()
    result = forecast(rows, district, crop, season)
    result['source'] = dict(path=DATA.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(DATA.read_bytes()).hexdigest(),
        quantity_column='production_metric_tons', input_unit='metric tons', output_unit='kg', conversion_factor=1000,
        measurement_status='Whether measured, estimated or derived is undocumented', provenance_verified=False,
        publication_dates_verified=False, designation='Repository official-designated CSV; independent origin unverified',
        coverage='Recorded district/crop/season totals; completeness of regional population coverage is unverified',
        grain='One district/crop/season/year aggregate, not individual farmer records',
        raw_rows=len(rows), seasonal_rows=sum(r['season'] in ('Maha', 'Yala') for r in rows),
        annual_total_rows_excluded=sum(r['season'] == 'Total' for r in rows))
    return result
