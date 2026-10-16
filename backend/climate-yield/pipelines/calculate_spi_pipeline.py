"""
Component 4: Standardized Precipitation Index (SPI) Drought Calculation Pipeline
AI-Powered Climate Early Warning and Crop Yield Impact Decision Support System

Description:
Computes multi-timescale meteorological drought indices (SPI-1, SPI-3, SPI-6)
for all 25 districts of Sri Lanka across 45 years (1981-2025).

Methodology (WMO Standard - McKee et al., 1993):
1. Calculates rolling rainfall accumulation for 1-month, 3-month, and 6-month windows.
2. Groups by district and calendar month (1 to 12) to evaluate seasonal baselines.
3. Fits a 2-parameter Gamma distribution (shape alpha, scale beta) with location fixed to 0.
4. Accounts for zero-precipitation probability: H(x) = q + (1 - q) * G(x).
5. Transforms cumulative probability H(x) into standard normal quantiles (Z-scores).
6. Classifies drought severity into standard WMO drought categories.
"""

import os
import numpy as np
import pandas as pd
from scipy import stats

# ==============================================================================
# 1. File Paths Configuration
# ==============================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Primary input: Monthly weather data with rainfall features
INPUT_FILE = os.path.join(
    CURRENT_DIR, "..", "data", "sri_lanka_weather_monthly.csv"
)
# Fallback to research workspace path if running standalone
if not os.path.exists(INPUT_FILE):
    INPUT_FILE = r"D:\01_research\climate_research_system\01_weather_data\sri_lanka_weather_with_anomalies.csv"

# Output CSV destination
OUTPUT_FILE = os.path.join(CURRENT_DIR, "district_monthly_spi.csv")

# ==============================================================================
# 2. Core SPI Computation Function (Gamma Fitting per Window)
# ==============================================================================
def calculate_spi_for_window(district_data, rainfall_column, window):
    """
    Computes Standardized Precipitation Index for a specified rolling window.
    
    Args:
        district_data (pd.DataFrame): Time-series data for a single district.
        rainfall_column (str): Name of the monthly rainfall column.
        window (int): Rolling window size in months (1, 3, or 6).
        
    Returns:
        pd.Series: Computed SPI values mapped to the original DataFrame index.
    """
    rainfall_series = district_data[rainfall_column].astype(float)

    # Compute rolling cumulative rainfall accumulation
    # min_periods=window ensures no partial-window artifacts at the series start
    rolling_rainfall = rainfall_series.rolling(window=window, min_periods=window).sum()

    spi_values = pd.Series(np.nan, index=district_data.index, dtype=float)

    # Process each calendar month (1=Jan to 12=Dec) independently
    # to compare against historical climatology of the exact same season
    for calendar_month in range(1, 13):
        month_mask = district_data["month"] == calendar_month
        month_rainfall = rolling_rainfall.loc[month_mask].dropna()

        # Require at least 30 historical observations for statistical validity
        if len(month_rainfall) < 30:
            continue

        # Calculate probability of zero rainfall (q)
        probability_zero = (month_rainfall == 0).mean()

        # Isolate positive precipitation values for Gamma distribution fitting
        non_zero_rainfall = month_rainfall[month_rainfall > 0]
        if len(non_zero_rainfall) < 30:
            continue

        try:
            # Fit 2-parameter Gamma distribution with location locked to 0
            shape, location, scale = stats.gamma.fit(non_zero_rainfall, floc=0)

            # Calculate cumulative distribution function (CDF) probabilities
            gamma_probability = stats.gamma.cdf(month_rainfall, shape, loc=0, scale=scale)

            # Adjust CDF probability incorporating the zero-rainfall frequency
            cumulative_probability = probability_zero + (1.0 - probability_zero) * gamma_probability

            # Clip cumulative probability to prevent infinity in the inverse normal transform
            cumulative_probability = np.clip(cumulative_probability, 1e-6, 1.0 - 1e-6)

            # Transform cumulative probability into standard normal Z-score (SPI)
            month_spi = stats.norm.ppf(cumulative_probability)

            # Assign computed SPI back to the district series
            spi_values.loc[month_rainfall.index] = month_spi

        except Exception as e:
            print(f"[Warning] Gamma fit failed for month {calendar_month}: {e}")
            continue

    return spi_values


# ==============================================================================
# 3. Drought Classification Helper Function (WMO Standard)
# ==============================================================================
def classify_drought(spi_value):
    """
    Classifies a continuous SPI score into official WMO drought severity categories.
    """
    if pd.isna(spi_value):
        return np.nan
    elif spi_value <= -2.0:
        return "Extremely Dry"
    elif spi_value <= -1.5:
        return "Severely Dry"
    elif spi_value <= -1.0:
        return "Moderately Dry"
    elif spi_value < 1.0:
        return "Near Normal"
    elif spi_value < 1.5:
        return "Moderately Wet"
    elif spi_value < 2.0:
        return "Severely Wet"
    else:
        return "Extremely Wet"


# ==============================================================================
# 4. Main Execution Routine
# ==============================================================================
def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[Error] Input weather file not found at: {INPUT_FILE}")
        return

    print("Reading monthly weather input data...")
    df = pd.read_csv(INPUT_FILE)

    # Ensure chronological order by district, year, month
    df = df.sort_values(by=["district", "year", "month"]).reset_index(drop=True)

    all_district_results = []
    districts = df["district"].unique()

    print(f"Calculating SPI-1, SPI-3, SPI-6 across {len(districts)} districts...")

    # Process each district separately to maintain independent regional distributions
    for district_name in districts:
        district_data = df[df["district"] == district_name].copy()

        # Compute 1-month, 3-month, and 6-month SPI
        district_data["spi_1"] = calculate_spi_for_window(district_data, "rainfall_monthly_mm", window=1)
        district_data["spi_3"] = calculate_spi_for_window(district_data, "rainfall_monthly_mm", window=3)
        district_data["spi_6"] = calculate_spi_for_window(district_data, "rainfall_monthly_mm", window=6)

        # Map SPI-3 to categorical drought classes
        district_data["drought_class_spi3"] = district_data["spi_3"].apply(classify_drought)

        all_district_results.append(district_data)

    # Combine all district records into a single DataFrame
    final_df = pd.concat(all_district_results, ignore_index=True)

    # Export clean SPI dataset
    final_df.to_csv(OUTPUT_FILE, index=False)

    print("\nGamma-distribution SPI dataset created successfully!")
    print(f"Total rows: {len(final_df):,}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
