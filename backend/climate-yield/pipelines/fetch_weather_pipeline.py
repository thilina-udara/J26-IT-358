"""
Weather Data Ingestion Pipeline

Description:
Fetches 45 years (1981 to 2025) of daily meteorological data for all 25 districts
of Sri Lanka using the NASA POWER Agroclimatology (AG) API.
"""

import os
import time
import requests
import pandas as pd
from tqdm import tqdm

# ==============================================================================
# 1. Output File Configuration
# ==============================================================================
# Save the output CSV file in the same directory as this script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(CURRENT_DIR, "sri_lanka_weather_daily.csv")

# ==============================================================================
# 2. Sri Lanka 25 Districts Centroid Coordinates
# ==============================================================================
# Aligned with shared/constants/srilanka_districts.json
DISTRICTS = [
    {"district": "Ampara", "lat": 7.2919, "lon": 81.6724},
    {"district": "Anuradhapura", "lat": 8.3114, "lon": 80.4037},
    {"district": "Badulla", "lat": 6.9934, "lon": 81.0550},
    {"district": "Batticaloa", "lat": 7.7310, "lon": 81.6747},
    {"district": "Colombo", "lat": 6.9271, "lon": 79.8612},
    {"district": "Galle", "lat": 6.0329, "lon": 80.2168},
    {"district": "Gampaha", "lat": 7.0873, "lon": 80.0144},
    {"district": "Hambantota", "lat": 6.1429, "lon": 81.1212},
    {"district": "Jaffna", "lat": 9.6615, "lon": 80.0255},
    {"district": "Kalutara", "lat": 6.5854, "lon": 79.9607},
    {"district": "Kandy", "lat": 7.2906, "lon": 80.6337},
    {"district": "Kegalle", "lat": 7.2513, "lon": 80.3464},
    {"district": "Kilinochchi", "lat": 9.3803, "lon": 80.3770},
    {"district": "Kurunegala", "lat": 7.4863, "lon": 80.3647},
    {"district": "Mannar", "lat": 8.9810, "lon": 79.9044},
    {"district": "Matale", "lat": 7.4675, "lon": 80.6234},
    {"district": "Matara", "lat": 5.9549, "lon": 80.5550},
    {"district": "Monaragala", "lat": 6.8728, "lon": 81.3507},
    {"district": "Mullaitivu", "lat": 9.2671, "lon": 80.8128},
    {"district": "Nuwara Eliya", "lat": 6.9497, "lon": 80.7891},
    {"district": "Polonnaruwa", "lat": 7.9403, "lon": 81.0188},
    {"district": "Puttalam", "lat": 8.0362, "lon": 79.8283},
    {"district": "Ratnapura", "lat": 6.6828, "lon": 80.3992},
    {"district": "Trincomalee", "lat": 8.5874, "lon": 81.2152},
    {"district": "Vavuniya", "lat": 8.7542, "lon": 80.4982}
]

# ==============================================================================
# 3. NASA POWER API Parameters & Date Range
# ==============================================================================
START_DATE = "19810101"  # January 1, 1981
END_DATE = "20251231"    # December 31, 2025
PARAMETERS = "PRECTOTCORR,T2M,T2M_MAX,T2M_MIN,RH2M,WS2M"
BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

all_records = []

print(f"Connecting to NASA POWER API for {len(DISTRICTS)} districts...")

# Loop through each district and query the NASA POWER point API
for loc in tqdm(DISTRICTS, desc="Collecting Daily Weather Data"):
    params = {
        "parameters": PARAMETERS,
        "community": "AG",      # Agroclimatology user community
        "longitude": loc["lon"],
        "latitude": loc["lat"],
        "start": START_DATE,
        "end": END_DATE,
        "format": "JSON"
    }
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=30)
        if response.status_code == 200:
            payload = response.json().get("properties", {}).get("parameter", {})
            dates = list(payload.get("T2M", {}).keys())
            
            # Unpack each date and store the weather parameters
            for d in dates:
                all_records.append({
                    "date": pd.to_datetime(d, format="%Y%m%d").strftime("%Y-%m-%d"),
                    "district": loc["district"],
                    "rainfall_mm": payload["PRECTOTCORR"].get(d),
                    "temp_mean": payload["T2M"].get(d),
                    "temp_max": payload["T2M_MAX"].get(d),
                    "temp_min": payload["T2M_MIN"].get(d),
                    "humidity": payload["RH2M"].get(d),
                    "wind_speed": payload["WS2M"].get(d)
                })
        else:
            print(f"\n[Warning] {loc['district']} failed. Status code: {response.status_code}")
    except Exception as e:
        print(f"\n[Error] {loc['district']}: {str(e)}")
        
    # Politeness delay to avoid hitting rate limits
    time.sleep(0.5)

# ==============================================================================
# 4. Data Cleaning & Export to CSV
# ==============================================================================
# Convert raw records list to pandas DataFrame
df = pd.DataFrame(all_records)

# Replace NASA POWER missing value sentinel (-999.0) with NaN / null
df.replace(-999.0, pd.NA, inplace=True)

# Export clean daily weather records to CSV
df.to_csv(OUTPUT_FILE, index=False)

print(f"\nCompleted successfully! Dataset saved to -> {OUTPUT_FILE}")
print(f"Total rows collected: {len(df):,}")
