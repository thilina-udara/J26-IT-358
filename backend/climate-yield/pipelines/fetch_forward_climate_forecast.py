"""
Weather Forecast and Climate Hazard Screening Pipeline

What this file does:
1. Gets 14-day weather forecasts for representative stations in all 25 districts of Sri Lanka.
2. Checks that the weather data is complete and has reasonable physical numbers.
3. Looks for potential climate hazards (such as dry spells, heavy rain, or high heat).
4. If the weather API fails or data is broken, it safely reports FORECAST_UNAVAILABLE
   so that fake hazard warnings are never created.
"""

import os
import sys
import json
from datetime import datetime, timezone
import requests
from typing import Dict, Any, Optional, List

# Main weather station or town coordinates for each of the 25 districts of Sri Lanka
# These are single point locations (not full district polygon averages)
SRI_LANKA_DISTRICT_REPRESENTATIVE_COORDINATES: Dict[str, Dict[str, Any]] = {
    "Ampara": {"lat": 7.2912, "lon": 81.6724, "location_name": "Ampara Town"},
    "Anuradhapura": {"lat": 8.3114, "lon": 80.4037, "location_name": "Anuradhapura Met Station"},
    "Badulla": {"lat": 6.9934, "lon": 81.0550, "location_name": "Badulla Town"},
    "Batticaloa": {"lat": 7.7310, "lon": 81.6747, "location_name": "Batticaloa Met Station"},
    "Colombo": {"lat": 6.9271, "lon": 79.8612, "location_name": "Colombo Met Headquarters"},
    "Galle": {"lat": 6.0535, "lon": 80.2210, "location_name": "Galle Fort Met Station"},
    "Gampaha": {"lat": 7.0840, "lon": 79.9943, "location_name": "Gampaha Town"},
    "Hambantota": {"lat": 6.1429, "lon": 81.1212, "location_name": "Hambantota Met Station"},
    "Jaffna": {"lat": 9.6615, "lon": 80.0255, "location_name": "Jaffna Met Station"},
    "Kalutara": {"lat": 6.5854, "lon": 79.9607, "location_name": "Kalutara Town"},
    "Kandy": {"lat": 7.2906, "lon": 80.6337, "location_name": "Kandy (Katugastota Met)"},
    "Kegalle": {"lat": 7.2513, "lon": 80.3464, "location_name": "Kegalle Town"},
    "Kilinochchi": {"lat": 9.3803, "lon": 80.3770, "location_name": "Kilinochchi Town"},
    "Kurunegala": {"lat": 7.4863, "lon": 80.3623, "location_name": "Kurunegala Met Station"},
    "Mannar": {"lat": 8.9810, "lon": 79.9044, "location_name": "Mannar Met Station"},
    "Matale": {"lat": 7.4675, "lon": 80.6234, "location_name": "Matale Town"},
    "Matara": {"lat": 5.9549, "lon": 80.5550, "location_name": "Matara Town"},
    "Monaragala": {"lat": 6.8728, "lon": 81.3507, "location_name": "Monaragala Town"},
    "Mullaitivu": {"lat": 9.2671, "lon": 80.8142, "location_name": "Mullaitivu Coastal Station"},
    "Nuwara Eliya": {"lat": 6.9497, "lon": 80.7891, "location_name": "Nuwara Eliya Met Station"},
    "Polonnaruwa": {"lat": 7.9403, "lon": 81.0188, "location_name": "Polonnaruwa Town"},
    "Puttalam": {"lat": 8.0362, "lon": 79.8283, "location_name": "Puttalam Met Station"},
    "Ratnapura": {"lat": 6.6828, "lon": 80.4036, "location_name": "Ratnapura Met Station"},
    "Trincomalee": {"lat": 8.5874, "lon": 81.2152, "location_name": "Trincomalee Met Station"},
    "Vavuniya": {"lat": 8.7514, "lon": 80.4971, "location_name": "Vavuniya Met Station"}
}

# The daily weather variables we expect from the weather provider
REQUIRED_DAILY_VARIABLES = [
    "time",
    "precipitation_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "soil_moisture_0_to_7cm_mean",
    "soil_moisture_7_to_28cm_mean"
]


def validate_api_response(raw_json: Any, expected_days: int) -> tuple[bool, Optional[str]]:
    """
    Checks if the weather API response is valid and makes physical sense.
    Returns (True, None) if good, or (False, error_message) if bad.
    """
    # 1. Make sure response is a dictionary
    if not isinstance(raw_json, dict):
        return False, "Response is not a valid JSON object"

    daily = raw_json.get("daily")
    if not isinstance(daily, dict):
        return False, "Missing 'daily' object in API response"

    # 2. Check each required weather variable
    for var in REQUIRED_DAILY_VARIABLES:
        if var not in daily:
            return False, f"Missing required variable '{var}' in daily data"
        val_list = daily[var]
        if not isinstance(val_list, list):
            return False, f"Variable '{var}' is not a list"
        if len(val_list) != expected_days:
            return False, f"Variable '{var}' length ({len(val_list)}) does not match expected days ({expected_days})"
        
        # Check for empty / None values
        for idx, val in enumerate(val_list):
            if val is None:
                return False, f"Null value encountered in '{var}' at day index {idx}"
            if var != "time" and not isinstance(val, (int, float)):
                return False, f"Non-numeric value '{val}' in numerical array '{var}' at index {idx}"

    # 3. Check for physically impossible numbers
    precip = daily["precipitation_sum"]
    tmax = daily["temperature_2m_max"]
    sm1 = daily["soil_moisture_0_to_7cm_mean"]

    # Rain cannot be negative and cannot be more than 1000 mm in a single day
    if any(p < 0.0 or p > 1000.0 for p in precip):
        return False, "Precipitation values outside plausible physical bounds [0, 1000 mm]"
    # Temperature in Sri Lanka should stay between -5 C and 55 C
    if any(t < -5.0 or t > 55.0 for t in tmax):
        return False, "Maximum temperature outside plausible physical bounds [-5, 55 C]"
    # Soil moisture volumetric fraction must be between 0.0 and 1.0
    if any(s < 0.0 or s > 1.0 for s in sm1):
        return False, "Soil moisture fraction outside plausible volumetric bounds [0.0, 1.0]"

    return True, None


def fetch_forward_climate_forecast(
    district: str, 
    forecast_days: int = 14,
    request_timeout_seconds: int = 10,
    session: Optional[requests.Session] = None
) -> Dict[str, Any]:
    """
    Downloads weather forecast for a district and checks for potential climate hazards.
    If the API fails, it safely returns FORECAST_UNAVAILABLE with no fake alerts.
    """
    # Check that district is valid
    if district not in SRI_LANKA_DISTRICT_REPRESENTATIVE_COORDINATES:
        raise ValueError(
            f"Invalid district: '{district}'. Must be one of the 25 official Sri Lankan districts: "
            f"{list(SRI_LANKA_DISTRICT_REPRESENTATIVE_COORDINATES.keys())}"
        )

    # Forecast horizon check (1 to 16 days)
    if not (1 <= forecast_days <= 16):
        raise ValueError(f"forecast_days must be between 1 and 16. Received: {forecast_days}")

    loc_info = SRI_LANKA_DISTRICT_REPRESENTATIVE_COORDINATES[district]
    lat, lon = loc_info["lat"], loc_info["lon"]
    loc_name = loc_info["location_name"]

    # Record the time when we asked for the forecast (in UTC)
    retrieval_utc = datetime.now(timezone.utc).isoformat()

    # Build Open-Meteo forecast API URL
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=precipitation_sum,temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
        f"soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean"
        f"&timezone=Asia/Colombo"
        f"&forecast_days={forecast_days}"
    )

    client = session or requests

    # 1. Download weather data from external API
    raw_json = None
    fetch_error = None
    try:
        response = client.get(url, timeout=request_timeout_seconds)
        if response.status_code != 200:
            fetch_error = f"HTTP Error {response.status_code}: {response.text[:200]}"
        else:
            raw_json = response.json()
    except Exception as exc:
        fetch_error = f"Request Exception: {type(exc).__name__} - {str(exc)}"

    # 2. Check if the downloaded data is clean and valid
    is_valid = False
    val_error = None
    if raw_json is not None:
        is_valid, val_error = validate_api_response(raw_json, forecast_days)

    # 3. If download or validation failed, return a safe UNAVAILABLE response
    if not is_valid:
        error_detail = fetch_error or val_error or "Unknown data corruption"
        return _build_unavailable_forecast_payload(
            district=district,
            loc_name=loc_name,
            lat=lat,
            lon=lon,
            forecast_days=forecast_days,
            retrieval_utc=retrieval_utc,
            error_detail=error_detail
        )

    # 4. Extract daily weather series
    daily = raw_json["daily"]
    time_dates = daily["time"]
    precip_list = [round(float(v), 2) for v in daily["precipitation_sum"]]
    temp_max_list = [round(float(v), 1) for v in daily["temperature_2m_max"]]
    temp_min_list = [round(float(v), 1) for v in daily["temperature_2m_min"]]
    temp_mean_list = [round(float(v), 1) for v in daily["temperature_2m_mean"]]
    soil_0_7 = [round(float(v), 3) for v in daily["soil_moisture_0_to_7cm_mean"]]
    soil_7_28 = [round(float(v), 3) for v in daily["soil_moisture_7_to_28cm_mean"]]

    # Combine topsoil (0-7 cm) and root zone (7-28 cm) soil moisture
    root_zone_sm = [
        round((s1 * 0.25) + (s2 * 0.75), 3)
        for s1, s2 in zip(soil_0_7, soil_7_28)
    ]

    total_rain_mm = round(float(sum(precip_list)), 1)
    max_t = round(float(max(temp_max_list)), 1)
    min_t = round(float(min(temp_min_list)), 1)
    mean_t = round(float(sum(temp_mean_list) / len(temp_mean_list)), 1)
    min_sm = round(float(min(root_zone_sm)), 3)

    # Count dry days (days with less than 1.0 mm rain)
    consec_dry = 0
    curr_dry = 0
    for p in precip_list:
        if p < 1.0:
            curr_dry += 1
            if curr_dry > consec_dry:
                consec_dry = curr_dry
        else:
            curr_dry = 0

    # Count days with hot weather (temperatures of 33 C or higher)
    heat_days = sum(1 for t in temp_max_list if t >= 33.0)

    # 5. Check if any weather thresholds are breached
    hazard_alerts: List[str] = []
    primary_hazard = "NO_HAZARD_THRESHOLD_BREACHED"

    # Heavy rain screening: this is a weather watch, NOT a confirmed river flood
    if total_rain_mm >= 150.0 or any(p >= 75.0 for p in precip_list):
        primary_hazard = "HIGH_PRECIPITATION_WATCH"
        hazard_alerts.append(
            f"Elevated cumulative precipitation projected: {total_rain_mm} mm over next {forecast_days} days "
            f"(Peak daily: {max(precip_list)} mm). Provisional atmospheric screening watch. "
            f"(Note: Flood risk depends on catchment hydrology, river discharge, and drainage capacity; "
            f"this does not constitute a confirmed flood prediction)."
        )

    # Dry spell screening
    elif consec_dry >= 10 or (total_rain_mm < 15.0 and min_sm < 0.18):
        primary_hazard = "DRY_SPELL_WATCH"
        hazard_alerts.append(
            f"Provisional dry-spell screening watch: {consec_dry} consecutive dry days projected with minimum "
            f"root-zone soil moisture reaching {min_sm} m3/m3. Crop water stress possible in coarse-textured soils."
        )

    # High heat screening
    if heat_days >= 4:
        if primary_hazard == "NO_HAZARD_THRESHOLD_BREACHED":
            primary_hazard = "HEAT_STRESS_WATCH"
        hazard_alerts.append(
            f"Provisional heat-stress screening watch: {heat_days} days projected with maximum temperatures "
            f"exceeding 33.0 C (Peak: {max_t} C). Sensitive flowering stages may experience thermal stress."
        )

    # If no hazard thresholds were breached
    if not hazard_alerts:
        hazard_alerts.append(
            "Forecasted meteorological variables remain within normal historical screening ranges. "
            "No provisional hazard threshold was breached."
        )

    model_gen_ms = raw_json.get("generationtime_ms")

    return {
        "status": "FORECAST_AVAILABLE",
        "metadata": {
            "data_category": "FORWARD_NUMERICAL_WEATHER_PREDICTION",
            "forecast_provider": "Open-Meteo API",
            "underlying_models": "Seamless global ensemble (ECMWF IFS ~9km, NOAA GFS ~13km)",
            "model_cycle_update_frequency": "4x daily (00Z, 06Z, 12Z, 18Z cycles; seamless interpolation)",
            "provider_generation_time_ms": model_gen_ms,
            "retrieval_timestamp_utc": retrieval_utc,
            "valid_time_window": {
                "start_date": time_dates[0],
                "end_date": time_dates[-1],
                "horizon_days": forecast_days,
                "timezone": "Asia/Colombo"
            },
            "representative_location": {
                "district": district,
                "station_or_town_name": loc_name,
                "latitude": lat,
                "longitude": lon,
                "spatial_representation": "Point forecast at representative station/town. NOT an area-weighted district polygon integral."
            },
            "units": {
                "precipitation": "mm (liquid equivalent)",
                "temperature": "degrees Celsius (C)",
                "soil_moisture": "m3/m3 (volumetric water content 0.0 - 1.0)",
                "consecutive_dry_days": "days (daily precipitation < 1.0 mm)",
                "heat_stress_days": "days (daily Tmax >= 33.0 C)"
            },
            "telemetry_health": {
                "is_live_telemetry": True,
                "data_integrity_validated": True,
                "validation_error": None
            },
            "scientific_caveat": (
                "Provisional research screening indicators based on 14-day numerical weather predictions. "
                "Does NOT constitute a full-season crop yield prediction or an official disaster declaration."
            )
        },
        "climate_hazard_screening": {
            "primary_hazard_classification": primary_hazard,
            "provisional_screening_alerts": hazard_alerts,
            "screening_metrics": {
                "total_rainfall_mm": total_rain_mm,
                "mean_temperature_c": mean_t,
                "max_temperature_c": max_t,
                "min_temperature_c": min_t,
                "min_soil_moisture_m3_m3": min_sm,
                "consecutive_dry_days": consec_dry,
                "heat_stress_days_count": heat_days
            }
        },
        "daily_forecast_series": [
            {
                "date": time_dates[i],
                "precipitation_mm": precip_list[i],
                "temperature_max_c": temp_max_list[i],
                "temperature_min_c": temp_min_list[i],
                "temperature_mean_c": temp_mean_list[i],
                "soil_moisture_root_zone_m3_m3": root_zone_sm[i]
            }
            for i in range(len(time_dates))
        ]
    }


def _build_unavailable_forecast_payload(
    district: str,
    loc_name: str,
    lat: float,
    lon: float,
    forecast_days: int,
    retrieval_utc: str,
    error_detail: str
) -> Dict[str, Any]:
    """
    Creates a safe response when weather data cannot be downloaded or is broken.
    This ensures we never create false hazard warnings if the network or API is down.
    """
    return {
        "status": "FORECAST_UNAVAILABLE",
        "metadata": {
            "data_category": "FORWARD_NUMERICAL_WEATHER_PREDICTION",
            "forecast_provider": "Open-Meteo API",
            "retrieval_timestamp_utc": retrieval_utc,
            "valid_time_window": {
                "start_date": None,
                "end_date": None,
                "horizon_days": forecast_days,
                "timezone": "Asia/Colombo"
            },
            "representative_location": {
                "district": district,
                "station_or_town_name": loc_name,
                "latitude": lat,
                "longitude": lon,
                "spatial_representation": "Point forecast at representative station/town."
            },
            "telemetry_health": {
                "is_live_telemetry": False,
                "data_integrity_validated": False,
                "validation_error": error_detail
            },
            "scientific_caveat": (
                "Live forecast data could not be verified. No hazard classification or yield impact can be evaluated."
            )
        },
        "climate_hazard_screening": {
            "primary_hazard_classification": "FORECAST_UNAVAILABLE",
            "provisional_screening_alerts": [
                f"Live forecast telemetry is currently unavailable ({error_detail}). "
                "No live hazard alerts or agricultural impacts can be evaluated."
            ],
            "screening_metrics": None
        },
        "daily_forecast_series": []
    }
