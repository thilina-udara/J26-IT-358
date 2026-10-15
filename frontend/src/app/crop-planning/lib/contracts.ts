export const CROPS = ["Mung Beans", "Corn", "Bandakka", "Brinjal", "Pumpkin", "Chillies"] as const;
export const DISTRICTS = ["Matara", "Hambantota"] as const;
export type Crop = typeof CROPS[number];
export type District = typeof DISTRICTS[number];
export type Season = "Maha" | "Yala";
export interface Farmer { farmer_id: string; login_identifier: string | null; authentication_method: string; created_at: string | null }
export interface Session { access_token: string; token_type: string; expires_at: string; expires_in: number; farmer: Farmer }
export interface Credentials { login_identifier: string; password: string }
export interface PlanFields {
  district: District; region: string; crop: Crop; land_size_acres: number;
  planting_date: string; expected_harvest_date: string; farmer_declared_season: Season | null;
}
export interface Plan extends PlanFields { plan_id: string; farmer_id: string; status: "active" | "cancelled"; submitted_at: string; updated_at: string }
export interface PlanPage { items: Plan[]; total: number; limit: number; offset: number; has_more: boolean; next_offset: number | null }
export interface Evidence { status: string; disclosure_status?: string | null; approval_status?: string | null; reason_codes?: string[]; missing_evidence?: string[] }
export interface Assessment extends Evidence { risk_level?: string | null; indicators?: { status: string }; interpretation?: string }
export interface Workflow extends Evidence {
  plan_id: string; analysis_status: string; assessment: Assessment;
  historical_prediction: Evidence & { scope?: string; reason?: string };
  recommendations: { status: string; alternatives?: Candidate[]; explanation?: string };
  season_context?: { farmer_declared_season: Season | null; requested_season: Season | null; effective_analysis_season: Season | null; conflict: boolean };
  recovery?: { plan_saved: boolean; retryable: boolean };
}
export interface Submission { plan: Plan; workflow: Workflow }
export interface Candidate extends Evidence { crop: Crop; risk_level: string; recommendation_explanation?: string }
export interface Comparison extends Evidence { alternatives: Candidate[]; comparisons: Candidate[] }
export interface Activity {
  activity_name: string; category: string; verification_status: string; approval_evidence?: string;
  source_url?: string; notes?: string; timing_reference?: string;
  date_windows: { earliest: string; latest: string }[];
  quantity?: { min: number; max: number; unit: string } | null;
}
export interface Personalized extends Evidence {
  plan_id: string; final_crop: Crop; activities: Activity[]; warnings: string[];
  missing_categories: string[]; expected_harvest_date: string; based_on_updated_at: string;
}
export interface SavedPlanning { personalized_plan: Personalized; revision_id: number; revisions: { revision_id: number; saved_at: string }[]; stale: boolean }
export interface PlanningRequest {
  plan_id: string; final_crop: Crop; district: District; region: string; land_size_acres: number;
  planting_date: string; expected_harvest_date: string; season: Season;
  variety: string | null; planting_method: "direct_sowing" | "transplanting" | null;
  corn_product: "field_grain" | "sweet" | "baby" | null;
  nursery_sowing_date: string | null; emergence_date: string | null; flowering_date: string | null;
}
export interface HistoricalScenarioRequest {
  district: District;
  crop: Crop;
  season: Season;
  land_size_acres: number;
  planting_date: string;
  expected_harvest_date: string;
  decision_cutoff?: string;
  model_name?: "XGBoost" | "CatBoost" | "Random Forest" | "LinearSVC" | "RBF SVC";
}

export interface HistoricalScenarioResponse {
  disclosure_status: string;
  reason_codes: string[];
  status: string;
  mode: string;
  operational_status: string;
  simulated_plan: {
    district: string;
    crop: string;
    season: string;
    land_size_acres: number;
    planting_date: string;
    expected_harvest_date: string;
    target_year: number;
    decision_cutoff: string;
    cutoff_timestamp: string;
    cutoff_source: string;
  };
  model_metadata: {
    model_name: string;
    trained_through: number;
    simulated_target_year: number;
    is_out_of_time_holdout: boolean;
    training_data_cutoff: string;
    training_cutoff_basis: string;
    model_available_at_cutoff: string;
    holdout_caveat: string;
    benchmark_scope: string;
    feature_count: number;
    feature_names: string[];
    own_production_status: string;
    probability_status: string;
    benchmark_metrics: Record<string, number> | null;
  };
  features: Record<string, any>;
  prediction: {
    historical_proxy_label: string | null;
    predicted_risk_level: string | null;
    class_probabilities: Record<string, number> | null;
    overlapping_peer_count: number | null;
    overlapping_peer_acres: number | null;
    total_window_acres: number | null;
    coverage_status: string;
    is_isolated_plan: boolean | null;
    peer_explanation: string;
  };
  observation_availability: {
    status: string; replay_unknown_peer_records: number | null; replay_unknown_prior_records: number | null;
    source_provenance: string; required_evidence: string;
  };
  concentration_indicators: {
    harvest_window_start: string; harvest_window_end: string; matching_scope: string;
    historical_dataset_window: { record_count: number | null; acres: number | null; disclosure_status: string };
    provably_available_window: { record_count: number | null; acres: number | null; disclosure_status: string };
    availability_status: string; unknown_availability_count: number | null; observed_after_cutoff_count: number | null;
    interpretation: string;
  };
  scenario_explanation: string;
  recommendation_status: string;
  diagnostic_alternatives: Array<{
    crop: string;
    historical_overlapping_plans: number;
    historical_overlapping_acres: number;
    status: string;
  }>;
  governance_notice: string;
}

export interface ResearchDemoStatus {
  enabled: boolean;
  allowed_date_range: { min_date: string; max_date: string };
  supported_districts: string[];
  supported_crops: string[];
  supported_models: string[];
  benchmark_overview: Record<string, any>;
  isolated_database: string;
}
