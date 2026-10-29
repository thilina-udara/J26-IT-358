// Rendering fixtures only; no invented values are persisted or served to users.
import { test } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ProductionChart, ProductionResult } from "../components/production-forecast";
import type { ProductionForecast } from "../lib/production-forecast";

const fixture: ProductionForecast = {
  status: "available", reason: null, mode: "Exploratory recorded-production forecast", forecast_year: 2026, training_cutoff_year: 2025,
  unit: "kg", crop: "Bandakka", district: "Hambantota", season: "Maha", expected_production_kg: 100000,
  model: "naive", model_name: "Naive: previous year production", trend: null,
  candidate_forecasts_kg: { naive: 100000, linear_trend: 110000 },
  reference_range_kg: { lower: 80000, upper: 120000, lower_error_kg: -20000, upper_error_kg: 20000, quantiles: [.1, .9], calibration_count: 10, interpretation: "Empirical reference" },
  training_years: [2001, 2024, 2025], history: [{ year: 2001, production_kg: 50000, fitted_kg: null }, { year: 2024, production_kg: 90000, fitted_kg: null }, { year: 2025, production_kg: 100000, fitted_kg: null }],
  evaluation: { candidate_mae_kg: { naive: 10000, linear_trend: 20000 }, candidate_years: [2024, 2025], selection_policy_mae_kg: 12000, naive_same_period_mae_kg: 11000, policy_years: [2024, 2025], definition: "Past selection uses earlier errors only." },
  quality: { duplicate_rows_ignored: 0, invalid_years: [], missing_years: [], forecast_floored_at_zero: false },
  planned_comparison: { status: "Planned production comparison unavailable", cumulative_planned_kg: null, reason: "No comparable population coverage." },
  source: { path: "fixture.csv", quantity_column: "production_metric_tons", input_unit: "metric tons", output_unit: "kg", conversion_factor: 1000, measurement_status: "Undocumented", designation: "Rendering fixture", coverage: "Fixture coverage", grain: "district/season/year", raw_rows: 3, seasonal_rows: 3, annual_total_rows_excluded: 0 },
  limitations: ["Not a validated economic optimum."],
};

test("production forecast displays kg, model, errors, reference range and source limitations", () => {
  const html = renderToStaticMarkup(<ProductionResult forecast={fixture} />);
  for (const text of ["100,000 kg", "80,000 kg", "120,000 kg", "12,000 kg", "Naive: previous year", "metric tons", "production_metric_tons", "Planned production comparison unavailable", "provenance unverified", "not a validated 80% prediction interval"]) assert.ok(html.includes(text), text);
  assert.ok(!html.includes("relative historical concentration"));
});

test("insufficient production data hides a supplied stale point, range and chart", () => {
  const f: ProductionForecast = { ...fixture, status: "Insufficient Data", reason: "Production data missing." };
  const html = renderToStaticMarkup(<ProductionResult forecast={f} />);
  assert.ok(html.includes("Insufficient Data") && html.includes("Production data missing."));
  assert.ok(!html.includes("100,000 kg") && !html.includes('role="img"'));
});

test("production chart marks 2026 as forecast rather than an observed value", () => {
  const html = renderToStaticMarkup(<ProductionChart forecast={fixture} />);
  assert.ok(html.includes("Production (kg)"));
  assert.ok(html.includes("2026: 100,000 kg forecast, not observed"));
  assert.ok(html.includes("2025: 100,000 kg recorded"));
  assert.ok(!html.includes("2026: 100,000 kg recorded"));
});

test("zero forecast and empirical range are displayed as valid kg quantities", () => {
  const f: ProductionForecast = { ...fixture, expected_production_kg: 0,
    reference_range_kg: { ...fixture.reference_range_kg!, lower: 0, upper: 0 } };
  assert.ok(renderToStaticMarkup(<ProductionResult forecast={f} />).includes("0 kg"));
});
