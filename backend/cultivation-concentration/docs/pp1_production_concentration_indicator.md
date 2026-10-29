# 2026 Forecast-Based Cultivation Concentration Indicator

The PP1 indicator is a relative production comparison. It does not use registered
farmer accounts, cultivation plans, XGBoost artifacts, market demand, prices, or
financial outcomes.

## 2026 calculation

For one district, crop, and season:

1. Use the existing production forecast service and its selected 2026 method.
2. Convert the recorded CSV production column from metric tons to kilograms.
3. Calculate the historical reference as the median of observed values in
   2010–2024. Only years actually present and valid are included. A missing year
   is not imputed. A nonpositive or unavailable median makes the indicator
   unavailable.
4. Calculate:

   `deviation_percent = (forecast_2026_kg / historical_reference_kg - 1) * 100`

## Leakage-safe calibration

For every eligible historical evaluation year from 2011–2025, the service:

1. Fits candidate one-year-ahead forecasts using only records before that year.
2. Selects the naive or linear-trend method using only earlier candidate errors,
   matching the existing expanding-origin selection policy.
3. Builds that year's reference from the median of recorded 2010 through the
   preceding year.
4. Retains the forecast-to-reference deviation only when the one-year-ahead
   forecast, positive reference, and selection history are available.

The lower and upper category boundaries are the empirical 1/3 and 2/3
quantiles of those historical deviations. Values below the lower boundary are
Low, values above the upper boundary are High, and values between or equal to
the boundaries are Medium. At least eight eligible calibration observations and
distinct terciles are required; otherwise the API returns `Insufficient Data`.
No 2026 actual value is read.

For Hambantota/Bandakka/Maha, the current dataset yields a 2010–2024 median
reference of 3,217,000 kg, an existing 2026 naive forecast of 3,345,400 kg, and
a deviation of +3.9913%. The 15 eligible historical deviations produce
boundaries of -0.6157% and +9.8572%, so the current relative category is
Medium. This is not a validated market oversupply or economic-loss risk label.
