"""Leakage-safe relative production concentration indicators for 2026."""
from statistics import median

from app.services.historical_trend import quantile
from app.services.production_forecast import (
    CUTOFF,
    FORECAST_YEAR,
    MIN_FIT,
    MIN_SELECTION,
    MODELS,
    choose,
    linear_model,
    linear_prediction,
    forecast as production_forecast,
    read_rows,
    to_kg,
)

REFERENCE_START = 2010
REFERENCE_END = 2024
MIN_CALIBRATION = 8

LIMITATIONS = [
    "This is a relative production-concentration indicator, not a validated market oversupply, price, or financial-loss risk measure.",
    "The historical CSV's measurement method, independent provenance, publication dates, and population completeness are unverified.",
    "The 2010–2024 median is a descriptive reference; weather, structural breaks, demand, prices, losses, and market capacity are not modeled.",
    "Historical calibration uses expanding-origin forecasts and only information available before each evaluation year. 2026 actual production is not used.",
    "The indicator is independent of registered farmer accounts and cultivation plans.",
]


def _points(rows, district, crop, season):
    amounts = {}
    invalid = set()
    for row in rows:
        if (row.get("district_name"), row.get("crop_name"), row.get("season")) != (district, crop, season):
            continue
        try:
            year = int(row["year"])
            if year > CUTOFF:
                continue
            if row.get("production_unit", "metric tons") != "metric tons":
                raise ValueError
            value = to_kg(row["production_metric_tons"])
            if year in amounts and amounts[year] != value:
                invalid.add(year)
            else:
                amounts[year] = value
        except (KeyError, TypeError, ValueError, OverflowError):
            invalid.add(row.get("year"))
    if invalid:
        return None, sorted(invalid)
    return [dict(year=year, production_kg=value) for year, value in sorted(amounts.items())], []


def _reference(points, before_year):
    selected = [
        point for point in points
        if REFERENCE_START <= point["year"] <= REFERENCE_END and point["year"] < before_year
    ]
    values = [point["production_kg"] for point in selected]
    if not values or median(values) <= 0:
        return None, [point["year"] for point in selected]
    return median(values), [point["year"] for point in selected]


def _deviation(forecast_kg, reference_kg):
    return (forecast_kg / reference_kg - 1) * 100


def _category(value, lower, upper):
    if value < lower:
        return "Low"
    if value > upper:
        return "High"
    return "Medium"


def _calibration(points):
    candidate_errors = []
    deviations = []
    for index in range(MIN_FIT, len(points)):
        past, actual = points[:index], points[index]
        if actual["year"] > CUTOFF or actual["year"] != past[-1]["year"] + 1:
            continue
        predictions = {
            "naive": past[-1]["production_kg"],
            "linear_trend": linear_prediction(linear_model(past), actual["year"]),
        }
        if len(candidate_errors) >= MIN_SELECTION:
            method = choose(candidate_errors)
            reference, reference_years = _reference(points, actual["year"])
            if reference is not None:
                forecast_kg = predictions[method]
                deviations.append({
                    "year": actual["year"],
                    "trained_through": past[-1]["year"],
                    "forecast_kg": forecast_kg,
                    "reference_kg": reference,
                    "reference_years": reference_years,
                    "method": method,
                    "deviation_percent": _deviation(forecast_kg, reference),
                })
        candidate_errors.append({
            name: actual["production_kg"] - predictions[name] for name in MODELS
        })
    return deviations


def indicator(rows, district, crop, season):
    empty = dict(
        status="Insufficient Data",
        reason=None,
        crop=crop,
        district=district,
        season=season,
        forecast_year=FORECAST_YEAR,
        forecast_2026_kg=None,
        selected_forecast_method=None,
        historical_reference_kg=None,
        reference_years=[],
        deviation_percent=None,
        lower_threshold_percent=None,
        upper_threshold_percent=None,
        category=None,
        calibration_sample_count=0,
        calibration_years=[],
        method_description=(
            "2026 production is compared with the median recorded production from "
            "2010–2024. Tercile boundaries are calculated from leakage-safe historical "
            "one-year-ahead forecast-to-reference deviations."
        ),
        limitations=list(LIMITATIONS),
    )
    if season not in ("Maha", "Yala"):
        empty["reason"] = "A single recorded season is required; annual Total is not a seasonal series."
        return empty
    points, invalid_years = _points(rows, district, crop, season)
    if invalid_years:
        empty["reason"] = "Selected historical production contains invalid or conflicting values."
        empty["invalid_years"] = invalid_years
        return empty
    if not points:
        empty["reason"] = "No historical production series is available for this selection."
        return empty
    forecast = production_forecast(rows, district, crop, season)
    if forecast["status"] != "available":
        empty["reason"] = f"2026 production forecast unavailable: {forecast['reason']}"
        return empty
    reference, reference_years = _reference(points, FORECAST_YEAR)
    calibration = _calibration(points)
    if reference is None:
        empty["reason"] = (
            f"Insufficient historical evidence: a positive median reference requires "
            f"recorded values from {REFERENCE_START}–{REFERENCE_END}."
        )
        return empty
    if len(calibration) < MIN_CALIBRATION:
        empty["reason"] = (
            f"Insufficient historical evidence: {MIN_CALIBRATION} eligible historical "
            f"forecast-to-reference deviations are required."
        )
        return empty
    values = [item["deviation_percent"] for item in calibration]
    lower = quantile(values, 1 / 3)
    upper = quantile(values, 2 / 3)
    if lower >= upper:
        empty["reason"] = "Insufficient historical evidence: calibration terciles are degenerate."
        return empty
    forecast_kg = forecast["expected_production_kg"]
    deviation = _deviation(forecast_kg, reference)
    empty.update(
        status="available",
        historical_reference_kg=reference,
        reference_years=reference_years,
        forecast_2026_kg=forecast_kg,
        selected_forecast_method=forecast["model_name"],
        deviation_percent=deviation,
        lower_threshold_percent=lower,
        upper_threshold_percent=upper,
        category=_category(deviation, lower, upper),
        calibration_sample_count=len(calibration),
        calibration_years=[item["year"] for item in calibration],
    )
    return empty


def options(rows=None):
    rows = read_rows() if rows is None else rows
    groups = {
        (row["district_name"], row["crop_name"], row["season"])
        for row in rows
        if row["season"] in ("Maha", "Yala") and int(row["year"]) <= CUTOFF
    }
    return [
        dict(district=district, crop=crop, season=season)
        for district, crop, season in sorted(groups)
    ]


def report(district, crop, season):
    rows = read_rows()
    result = indicator(rows, district, crop, season)
    result["source"] = {
        "path": "data/official/official_historical_2001_2025.csv",
        "reference_window": f"{REFERENCE_START}–{REFERENCE_END}",
        "calibration_cutoff": CUTOFF,
        "farmer_records_used": False,
    }
    return result


def report_for_plan(plan):
    """Calculate the indicator for an owned plan using its declared season."""
    if plan.farmer_declared_season is None:
        result = indicator([], plan.district, plan.crop, "Maha")
        result["season"] = None
        result["reason"] = (
            "A farmer-declared Maha or Yala season is required; the service does "
            "not infer statistical season from planting month."
        )
    else:
        result = report(plan.district, plan.crop, plan.farmer_declared_season)
    result["plan_id"] = plan.plan_id
    result["plan_season"] = plan.farmer_declared_season
    return result
