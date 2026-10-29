export interface ProductionSeries { district: string; crop: string; season: string; years: number[] }
export interface ProductionForecast {
  status: "available" | "Insufficient Data"; reason: string | null; mode: string;
  forecast_year: number; training_cutoff_year: number; unit: "kg";
  district: string; crop: string; season: string; expected_production_kg: number | null;
  model: "naive" | "linear_trend" | null; model_name: string | null;
  candidate_forecasts_kg: { naive: number; linear_trend: number } | null;
  trend: { center_year: number; level_kg: number; slope_kg_per_year: number } | null;
  reference_range_kg: { lower: number; upper: number; lower_error_kg: number; upper_error_kg: number; quantiles: number[]; calibration_count: number; interpretation: string } | null;
  training_years: number[];
  history: { year: number; production_kg: number; fitted_kg: number | null }[];
  evaluation: { candidate_mae_kg: { naive: number; linear_trend: number }; candidate_years: number[]; selection_policy_mae_kg: number; naive_same_period_mae_kg: number; policy_years: number[]; definition: string } | null;
  quality: { duplicate_rows_ignored: number; invalid_years: number[]; missing_years: number[]; forecast_floored_at_zero: boolean };
  planned_comparison: { status: string; cumulative_planned_kg: null; reason: string };
  source: { path: string; quantity_column: string; input_unit: string; output_unit: string; conversion_factor: number; measurement_status: string; designation: string; coverage: string; grain: string; raw_rows: number; seasonal_rows: number; annual_total_rows_excluded: number };
  limitations: string[];
}
