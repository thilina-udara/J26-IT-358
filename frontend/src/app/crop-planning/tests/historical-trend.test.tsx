// Fictional rendering fixtures only; never persisted as farmer or historical data.
import { test } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { TrendChart, TrendResult } from "../components/historical-trend-analysis";
import type { TrendAnalysis } from "../lib/historical-trend";

const example: TrendAnalysis = {
  status: "available", category: "High", district: "Hambantota", crop: "Bandakka", season: "Maha",
  evaluation_year: 2025, unit: "hectares", mode: "Exploratory historical backtest", reason: null,
  baseline_hectares: 100, observed_hectares: 125, deviation_percent: 25,
  thresholds: { lower_percent: -6, upper_percent: 8, lower_hectares: 94, upper_hectares: 108 },
  trend: { center_year: 2012.5, intercept_hectares: 80, slope_hectares_per_year: 1.6 },
  training_years: [2001, 2002, 2024], calibration: [{ year: 2024, trained_through: 2023, deviation_percent: 8 }],
  history: [{ year: 2001, hectares: 60, fitted_hectares: 61.6 }, { year: 2024, hectares: 105, fitted_hectares: 98.4 }, { year: 2025, hectares: 125, fitted_hectares: 100 }],
  quality: { duplicate_rows_ignored: 0, invalid_years: [], missing_years: [], extreme_residual_years: [] },
  limitations: ["Does not prove oversupply or economic loss."],
  source: { path: "fixture.csv", designation: "Fictional test fixture", coverage: "Fixture district", period: "Recorded season", grain: "district-season-year", raw_rows: 3, seasonal_rows: 3, annual_total_rows_excluded: 0 },
};

for (const category of ["Low", "Medium", "High"] as const) {
  test(`trend renders ${category} as relative historical concentration with units and boundaries`, () => {
    const html = renderToStaticMarkup(<TrendResult analysis={{ ...example, category }} />);
    assert.ok(html.includes(`${category} relative historical concentration`));
    assert.ok(html.includes("125 ha") && html.includes("100 ha"));
    assert.ok(html.includes("+25.00%") && html.includes("-6.00%") && html.includes("+8.00%"));
    assert.ok(html.includes("Exploratory historical backtest"));
    assert.ok(html.includes("publication availability unverified"));
    assert.ok(html.includes("fixture.csv") && html.includes("Does not prove oversupply"));
  });
}

test("insufficient analysis never renders a stale or supplied category", () => {
  const html = renderToStaticMarkup(<TrendResult analysis={{ ...example, status: "Insufficient Data", reason: "Too few prior years.", thresholds: null }} />);
  assert.ok(html.includes("Insufficient Data") && html.includes("Too few prior years."));
  assert.ok(!html.includes("High relative historical concentration"));
});

test("chart identifies the recorded series, held-out year and measurement", () => {
  const html = renderToStaticMarkup(<TrendChart analysis={example} />);
  assert.ok(html.includes('role="img"'));
  assert.ok(html.includes("held-out year 2025") && html.includes("Hectares"));
  assert.ok(html.includes("2025: 125 ha (held out)"));
  assert.ok(html.includes("excluded from fitting and thresholds"));
  assert.ok(!renderToStaticMarkup(<TrendChart analysis={{ ...example, history: [] }} />));
});
