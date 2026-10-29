export interface TrendSeries { district: string; crop: string; season: string; years: number[] }
export interface TrendAnalysis {
  status: "available" | "Insufficient Data";
  category: "Low" | "Medium" | "High" | null;
  district: string; crop: string; season: string; evaluation_year: number;
  mode: string; unit: string; reason: string | null;
  baseline_hectares: number | null; observed_hectares: number | null; deviation_percent: number | null;
  thresholds: { lower_percent: number; upper_percent: number; lower_hectares: number; upper_hectares: number } | null;
  trend: { center_year: number; intercept_hectares: number; slope_hectares_per_year: number } | null;
  training_years: number[];
  calibration: { year: number; trained_through: number; deviation_percent: number }[];
  history: { year: number; hectares: number; fitted_hectares: number | null }[];
  quality: { duplicate_rows_ignored: number; invalid_years: number[]; missing_years: number[]; extreme_residual_years?: number[] };
  limitations: string[];
  source: { path: string; designation: string; coverage: string; period: string; grain: string; raw_rows: number; seasonal_rows: number; annual_total_rows_excluded: number };
}
