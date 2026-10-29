export interface ConcentrationSeries { district: string; crop: string; season: string }

export interface ProductionConcentrationIndicator {
  status: "available" | "Insufficient Data";
  reason: string | null;
  crop: string;
  district: string;
  season: string;
  forecast_year: number;
  forecast_2026_kg: number | null;
  selected_forecast_method: string | null;
  historical_reference_kg: number | null;
  reference_years: number[];
  deviation_percent: number | null;
  lower_threshold_percent: number | null;
  upper_threshold_percent: number | null;
  category: "Low" | "Medium" | "High" | null;
  calibration_sample_count: number;
  calibration_years: number[];
  method_description: string;
  limitations: string[];
  source?: { path: string; reference_window: string; calibration_cutoff: number; farmer_records_used: boolean };
}
