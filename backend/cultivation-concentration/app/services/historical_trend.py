"""Read-only, recorded-year retrospective analysis of district seasonal extent.

No live-plan database, model artifact, external service or XGBoost dependency.
See docs/pp1_historical_trend.md for the predeclared exploratory protocol.
"""
import csv
import hashlib
import math
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/official/official_historical_2001_2025.csv'
MIN_FIT = 5
MIN_CALIBRATION = 8
UNIT = 'hectares'
LIMITATIONS = [
    'Exploratory chronological backtest on recorded years; source origin and publication/revision availability are unverified.',
    'District seasonal totals are compared only with the same recorded district/crop/season population. Live registered plans are not compared with these totals.',
    'Low/Medium/High are relative historical concentration bands, not validated agricultural risk, market oversupply or economic loss.',
    'OLS can be sensitive to structural breaks and extreme observations. Valid extremes are retained; no automatic trimming or winsorization.',
    'Empirical terciles are descriptive thresholds, not prediction intervals or calibrated probabilities; small samples and serial dependence limit stability.',
]


def read_rows():
    with DATA.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'district_name', 'crop_name', 'year', 'season', 'cultivated_extent_hectares'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Expected district-season cultivated extent in explicitly named hectares column')
        return list(reader)


def quantile(values, probability):
    """Type-7 empirical quantile: linear interpolation at (n-1)*p."""
    values = sorted(values)
    index = (len(values) - 1) * probability
    left = int(index)
    return values[left] + (values[min(left + 1, len(values) - 1)] - values[left]) * (index - left)


def fit(points):
    """Centered ordinary least squares, with actual calendar year distances."""
    center = mean(p['year'] for p in points)
    average = mean(p['hectares'] for p in points)
    denominator = math.fsum((p['year'] - center) ** 2 for p in points)
    slope = math.fsum((p['year'] - center) * (p['hectares'] - average) for p in points) / denominator
    if not all(math.isfinite(v) for v in (average, slope)):
        raise ValueError('Non-finite trend')
    return {'center_year': center, 'intercept_hectares': average, 'slope_hectares_per_year': slope}


def predict(model, year):
    value = model['intercept_hectares'] + model['slope_hectares_per_year'] * (year - model['center_year'])
    if not math.isfinite(value):
        raise ValueError('Non-finite forecast')
    return value


def classify(deviation, lower, upper):
    if not all(math.isfinite(v) for v in (deviation, lower, upper)) or lower >= upper:
        raise ValueError('Distinct finite thresholds required')
    return 'Low' if deviation < lower else ('High' if deviation > upper else 'Medium')


def analyse(rows, district, crop, season, evaluation_year):
    result = dict(status='Insufficient Data', category=None, district=district, crop=crop, season=season,
                  evaluation_year=evaluation_year, unit=UNIT, mode='Exploratory historical backtest',
                  baseline_hectares=None, observed_hectares=None, deviation_percent=None,
                  thresholds=None, trend=None, training_years=[], calibration=[], history=[],
                  quality={'duplicate_rows_ignored': 0, 'invalid_years': [], 'missing_years': []},
                  limitations=list(LIMITATIONS), reason=None)
    if season not in ('Maha', 'Yala'):
        result['reason'] = 'Use an individual season; annual Total rows must not be added to seasonal rows.'
        return result
    grouped = {}
    invalid = set()
    for row in rows:
        if (row.get('district_name'), row.get('crop_name'), row.get('season')) != (district, crop, season):
            continue
        try:
            year = int(row['year'])
        except (ValueError, TypeError, KeyError):
            result['reason'] = 'A selected series record has an invalid year.'
            return result
        # Do not examine future measurement values, units or revisions.
        if year > evaluation_year:
            continue
        try:
            value = float(row['cultivated_extent_hectares'])
            if row.get('extent_unit', UNIT) != UNIT or not math.isfinite(value) or value < 0:
                raise ValueError('Invalid measurement or unit')
            if year in grouped:
                if value != grouped[year]:
                    invalid.add(year)  # Conflicting revisions have no known precedence.
                else:
                    result['quality']['duplicate_rows_ignored'] += 1
            else:
                grouped[year] = value
        except (ValueError, TypeError, KeyError):
            invalid.add(year)
    result['quality']['invalid_years'] = sorted(invalid)
    # Do not silently drop a bad measurement and still assign a category.
    if invalid:
        result['reason'] = 'Missing, negative, non-finite, conflicting measurements or inconsistent units in the selected period.'
        return result
    points = [dict(year=year, hectares=value) for year, value in sorted(grouped.items())]
    training = [p for p in points if p['year'] < evaluation_year]
    result['training_years'] = [p['year'] for p in training]
    result['history'] = [dict(p, fitted_hectares=None) for p in points]
    result['observed_hectares'] = grouped.get(evaluation_year)
    if training:
        result['quality']['missing_years'] = sorted(set(range(training[0]['year'], evaluation_year)) - set(result['training_years']))
    if len(training) < MIN_FIT or grouped.get(evaluation_year) is None:
        result['reason'] = 'Need an observed held-out year and at least five earlier seasonal observations.'
        return result
    if training[-1]['year'] != evaluation_year - 1:
        result['reason'] = 'The immediately preceding year is missing; one-year forecast calibration is not comparable.'
        return result
    try:
        model = fit(training)
        baseline = predict(model, evaluation_year)
        result['trend'] = model
        result['baseline_hectares'] = baseline
        result['history'] = [dict(p, fitted_hectares=predict(model, p['year'])) for p in points]
        if baseline <= 0:
            result['reason'] = 'The estimated baseline is zero or negative; percentage deviation is undefined.'
            return result
        # Expanding-origin, one-calendar-year-ahead errors; each validation year
        # and all later values are excluded from its own trend fit.
        for index in range(MIN_FIT, len(training)):
            past, observation = training[:index], training[index]
            if observation['year'] != past[-1]['year'] + 1:
                continue
            forecast = predict(fit(past), observation['year'])
            if forecast <= 0:
                continue
            deviation = (observation['hectares'] / forecast - 1) * 100
            if not math.isfinite(deviation):
                raise ValueError('Non-finite calibration deviation')
            result['calibration'].append(dict(year=observation['year'], trained_through=past[-1]['year'],
                baseline_hectares=forecast, observed_hectares=observation['hectares'], deviation_percent=deviation))
        if len(result['calibration']) < MIN_CALIBRATION:
            result['reason'] = 'Need at least eight earlier rolling-origin errors to estimate descriptive terciles.'
            return result
        errors = [v['deviation_percent'] for v in result['calibration']]
        lower, upper = quantile(errors, 1 / 3), quantile(errors, 2 / 3)
        if math.isclose(lower, upper, rel_tol=1e-12, abs_tol=1e-12):
            result['reason'] = 'Historical deviations have tied terciles; three concentration bands are not identifiable.'
            return result
        observed = grouped[evaluation_year]
        deviation = (observed / baseline - 1) * 100
        boundaries = [baseline * (1 + value / 100) for value in (lower, upper)]
        if not all(math.isfinite(v) for v in (deviation, *boundaries)):
            raise ValueError('Non-finite deviation or boundary')
        result.update(status='available', category=classify(deviation, lower, upper), deviation_percent=deviation,
            thresholds=dict(lower_percent=lower, upper_percent=upper,
                            lower_hectares=boundaries[0], upper_hectares=boundaries[1]))
        residuals = [p['hectares'] - predict(model, p['year']) for p in training]
        q1, q3 = quantile(residuals, .25), quantile(residuals, .75)
        iqr = q3 - q1
        result['quality']['extreme_residual_years'] = [p['year'] for p, r in zip(training, residuals)
            if r < q1 - 1.5 * iqr or r > q3 + 1.5 * iqr]
        return result
    except (ValueError, OverflowError, ZeroDivisionError):
        # Never serialize non-finite numbers as JSON or manufacture a category.
        result.update(status='Insufficient Data', category=None, baseline_hectares=None, thresholds=None,
                      deviation_percent=None, trend=None, history=[], calibration=[],
                      reason='Trend arithmetic is unstable or non-finite; no classification is supported.')
        return result


def options(rows=None):
    rows = read_rows() if rows is None else rows
    groups = {}
    for row in rows:
        if row.get('season') not in ('Maha', 'Yala'):
            continue
        key = (row['district_name'], row['crop_name'], row['season'])
        groups.setdefault(key, set()).add(int(row['year']))
    return [dict(district=d, crop=c, season=s, years=sorted(years)) for (d, c, s), years in sorted(groups.items())]


def report(district, crop, season, evaluation_year=None):
    rows = read_rows()
    available = next((s for s in options(rows) if (s['district'], s['crop'], s['season']) == (district, crop, season)), None)
    year = evaluation_year if evaluation_year is not None else (available['years'][-1] if available else 2025)
    result = analyse(rows, district, crop, season, year)
    result['source'] = dict(path=DATA.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(DATA.read_bytes()).hexdigest(),
        designation='Repository official-designated CSV; independent origin unverified',
        unit=UNIT, measurement='cultivated_extent_hectares', grain='one district/crop/season/year aggregate',
        coverage='Recorded district seasonal totals; regional census coverage and publication vintages unverified',
        period='Complete recorded season, not a harvest overlap window or partial-season nowcast',
        raw_rows=len(rows), seasonal_rows=sum(r['season'] in ('Maha', 'Yala') for r in rows),
        annual_total_rows_excluded=sum(r['season'] == 'Total' for r in rows))
    return result
