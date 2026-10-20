"""Crop yield anomaly model training and chronological evaluation pipeline."""

import os
import sys
import json
from typing import Dict, List, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import HuberRegressor, Ridge, ElasticNet
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

# Paths
BASE_DIR_BACKEND = r"D:\Project\GitHubClone\J26-IT-358\backend\climate-yield"
BASE_DIR_RESEARCH = r"D:\01_research\climate_research_system"

PRE_SEASON_PATH = os.path.join(BASE_DIR_BACKEND, "data", "crop_features_pre_season.csv")
MID_SEASON_PATH = os.path.join(BASE_DIR_BACKEND, "data", "crop_features_mid_season.csv")

if not os.path.exists(PRE_SEASON_PATH):
    PRE_SEASON_PATH = os.path.join(BASE_DIR_RESEARCH, "data", "crop_features_pre_season.csv")
    MID_SEASON_PATH = os.path.join(BASE_DIR_RESEARCH, "data", "crop_features_mid_season.csv")

# Feature Definitions
FEATURES_PRE_OPERATIONAL = [
    "pre_season_rainfall_30d_mm",
    "pre_season_rainfall_15d_prep_mm",
    "pre_season_temp_mean_c",
    "pre_season_temp_max_peak_c",
    "pre_season_dry_spell_max_days"
]

FEATURES_PRE_RESEARCH = FEATURES_PRE_OPERATIONAL + [
    "pre_season_spi3",
    "pre_season_spi1",
    "pre_season_sm_topsoil_layer1_m3_m3",
    "pre_season_sm_root_zone_approx_m3_m3"
]

FEATURES_MID_SEASON = [
    "mid_season_rainfall_cum_mm",
    "mid_season_temp_mean_c",
    "mid_season_temp_max_peak_c",
    "mid_season_heat_days_ge_34c",
    "mid_season_heat_days_ge_35c",
    "mid_season_dry_spell_max_days",
    "mid_season_heavy_rain_days_ge_50mm",
    "mid_season_spi3",
    "mid_season_spi1",
    "mid_season_sm_topsoil_layer1_mean",
    "mid_season_sm_topsoil_layer1_min",
    "mid_season_sm_root_zone_approx_mean",
    "mid_season_sm_root_zone_approx_min"
]

APPROVED_CROPS = ["Maize", "Chilli", "Green Gram"]

HORIZONS = {
    "Pre-Season (Operational 5-Feat)": {
        "dataset_type": "pre",
        "features": FEATURES_PRE_OPERATIONAL,
        "description": "Daily weather aggregations available with 24-48h latency (no monthly lag)"
    },
    "Pre-Season (Full Research 9-Feat)": {
        "dataset_type": "pre",
        "features": FEATURES_PRE_RESEARCH,
        "description": "Includes monthly SPI and ERA5 soil moisture (caution: official CDS release has 5-7d latency)"
    },
    "Mid-Season (In-Season 13-Feat)": {
        "dataset_type": "mid",
        "features": FEATURES_MID_SEASON,
        "description": "Cumulative in-season daily weather + prior closed-month SPI and soil moisture"
    }
}


def get_candidate_models() -> Dict[str, Any]:
    """Returns the candidate models with locked, defensible configurations."""
    return {
        "Zero-Anomaly Baseline": None,
        "Huber Regressor": HuberRegressor(epsilon=1.35, alpha=0.1, max_iter=1000),
        "Ridge Regression": Ridge(alpha=10.0, random_state=42),
        "ElasticNet": ElasticNet(alpha=0.1, l1_ratio=0.5, max_iter=2000, random_state=42),
        "Shallow HistGradientBoosting": HistGradientBoostingRegressor(
            max_depth=2, min_samples_leaf=20, l2_regularization=1.0, random_state=42
        )
    }


def compute_metrics(
    y_true_pct: np.ndarray,
    y_pred_pct: np.ndarray,
    y_base_mtha: np.ndarray,
    y_actual_mtha: np.ndarray,
    neutral_threshold: float = 5.0
) -> Dict[str, float]:
    """Computes all required anomaly and physical yield metrics."""
    # Anomaly Space
    anomaly_mae = mean_absolute_error(y_true_pct, y_pred_pct)
    anomaly_rmse = root_mean_squared_error(y_true_pct, y_pred_pct)
    anomaly_medae = float(np.median(np.abs(y_true_pct - y_pred_pct)))
    
    # Anomaly R2 (unclipped)
    var_true = np.var(y_true_pct)
    if var_true > 1e-9:
        anomaly_r2 = r2_score(y_true_pct, y_pred_pct)
    else:
        anomaly_r2 = np.nan

    # Reconstructed Absolute Yield
    y_pred_mtha = y_base_mtha * (1.0 + y_pred_pct / 100.0)
    yield_mae = mean_absolute_error(y_actual_mtha, y_pred_mtha)
    yield_rmse = root_mean_squared_error(y_actual_mtha, y_pred_mtha)
    
    var_yield = np.var(y_actual_mtha)
    if var_yield > 1e-9:
        yield_r2 = r2_score(y_actual_mtha, y_pred_mtha)
    else:
        yield_r2 = np.nan

    # Directional Accuracy
    is_shock = np.abs(y_true_pct) > neutral_threshold
    correct_shocks = (np.sign(y_pred_pct[is_shock]) == np.sign(y_true_pct[is_shock])).sum()
    correct_neutral = (np.abs(y_pred_pct[~is_shock]) <= neutral_threshold).sum()
    direction_acc = ((correct_shocks + correct_neutral) / len(y_true_pct)) * 100.0

    return {
        "anomaly_mae_pp": round(float(anomaly_mae), 2),
        "anomaly_rmse_pp": round(float(anomaly_rmse), 2),
        "anomaly_medae_pp": round(anomaly_medae, 2),
        "anomaly_r2": round(float(anomaly_r2), 4) if pd.notna(anomaly_r2) else None,
        "yield_mae_mtha": round(float(yield_mae), 3),
        "yield_rmse_mtha": round(float(yield_rmse), 3),
        "yield_r2": round(float(yield_r2), 4) if pd.notna(yield_r2) else None,
        "direction_accuracy_pct": round(float(direction_acc), 1)
    }


def run_forward_chaining_validation(
    df_crop_train: pd.DataFrame,
    features: List[str]
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Executes the 10-fold expanding-window cross validation across crop years 2003-2020.
    """
    models = get_candidate_models()
    fold_records = []
    model_fold_rmses = {m: [] for m in models}
    model_fold_maes = {m: [] for m in models}
    model_fold_yield_rmses = {m: [] for m in models}
    model_fold_dir_accs = {m: [] for m in models}

    for val_year in range(2011, 2021):
        fold_idx = val_year - 2010
        train_slice = df_crop_train[df_crop_train["crop_year"] < val_year]
        val_slice = df_crop_train[df_crop_train["crop_year"] == val_year]

        X_train = train_slice[features].copy()
        y_train = train_slice["yield_anomaly_pct"].values
        X_val = val_slice[features].copy()
        y_val = val_slice["yield_anomaly_pct"].values

        val_base_mtha = val_slice["historical_baseline_yield_mt_ha"].values
        val_actual_mtha = val_slice["yield_metric_tons_per_hectare"].values

        # Impute missing values with training median (if any)
        for col in features:
            med = X_train[col].median()
            X_train[col] = X_train[col].fillna(med)
            X_val[col] = X_val[col].fillna(med)

        # Scale features strictly on training fold
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train.values)
        X_val_scaled = scaler.transform(X_val.values)

        for name, model in models.items():
            if model is None:
                # Zero-Anomaly Baseline predicts 0.0% anomaly
                pred_val = np.zeros_like(y_val)
            elif "HistGradientBoosting" in name:
                model.fit(X_train.values, y_train)
                pred_val = model.predict(X_val.values)
            else:
                model.fit(X_train_scaled, y_train)
                pred_val = model.predict(X_val_scaled)

            metrics = compute_metrics(y_val, pred_val, val_base_mtha, val_actual_mtha)
            model_fold_rmses[name].append(metrics["anomaly_rmse_pp"])
            model_fold_maes[name].append(metrics["anomaly_mae_pp"])
            model_fold_yield_rmses[name].append(metrics["yield_rmse_mtha"])
            model_fold_dir_accs[name].append(metrics["direction_accuracy_pct"])

            fold_records.append({
                "fold": fold_idx,
                "train_years": f"2003-{val_year-1}",
                "val_year": val_year,
                "model": name,
                "n_train": len(train_slice),
                "n_val": len(val_slice),
                **metrics
            })

    # Summary across the 10 folds
    summary = {}
    base_rmse_mean = float(np.mean(model_fold_rmses["Zero-Anomaly Baseline"]))

    for name in models:
        mean_rmse = float(np.mean(model_fold_rmses[name]))
        std_rmse = float(np.std(model_fold_rmses[name]))
        mean_mae = float(np.mean(model_fold_maes[name]))
        mean_yield_rmse = float(np.mean(model_fold_yield_rmses[name]))
        mean_dir_acc = float(np.mean(model_fold_dir_accs[name]))

        rel_imp = ((base_rmse_mean - mean_rmse) / base_rmse_mean) * 100.0 if base_rmse_mean > 0 else 0.0

        # Count fold wins against baseline
        wins = 0
        for i in range(10):
            if model_fold_rmses[name][i] < model_fold_rmses["Zero-Anomaly Baseline"][i]:
                wins += 1

        passes_gate = (rel_imp >= 3.0) and (wins >= 7)

        summary[name] = {
            "mean_val_rmse_pp": round(mean_rmse, 2),
            "std_val_rmse_pp": round(std_rmse, 2),
            "mean_val_mae_pp": round(mean_mae, 2),
            "mean_val_yield_rmse_mtha": round(mean_yield_rmse, 3),
            "mean_val_direction_acc_pct": round(mean_dir_acc, 1),
            "rel_rmse_improvement_pct": round(rel_imp, 2),
            "fold_wins_out_of_10": wins,
            "passes_acceptance_gates": passes_gate
        }

    return summary, fold_records


def select_winning_model(val_summary: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
    """
    Selects the winning model based on the locked parsimony protocol:
    1. Must pass gates (>= 3.0% rel RMSE improvement AND >= 7/10 fold wins).
    2. Ties within 1.0% relative improvement resolved by simpler architecture:
       Baseline > Huber > Ridge > ElasticNet > HistGB.
    3. If no candidate passes, fallback to Zero-Anomaly Baseline.
    """
    passing_candidates = [
        (name, metrics["rel_rmse_improvement_pct"], metrics["std_val_rmse_pp"])
        for name, metrics in val_summary.items()
        if metrics["passes_acceptance_gates"] and name != "Zero-Anomaly Baseline"
    ]

    if not passing_candidates:
        return "Zero-Anomaly Baseline", "Crop-decoupled fallback: no candidate achieved >= 3.0% validation RMSE reduction and >= 7/10 fold wins."

    # Sort primarily by relative improvement descending
    passing_candidates.sort(key=lambda x: x[1], reverse=True)
    best_cand = passing_candidates[0]

    # Check for ties within 1.0% of the best
    tied = [c for c in passing_candidates if (best_cand[1] - c[1]) <= 1.0]
    
    # Priority order for simplicity
    priority = ["Huber Regressor", "Ridge Regression", "ElasticNet", "Shallow HistGradientBoosting"]
    tied.sort(key=lambda c: priority.index(c[0]) if c[0] in priority else 99)

    winner_name = tied[0][0]
    reason = f"Met acceptance gates with {tied[0][1]:.2f}% validation RMSE improvement and selected via parsimony rule."
    return winner_name, reason


def evaluate_final_test_set(
    df_crop: pd.DataFrame,
    features: List[str],
    winning_model_name: str
) -> Dict[str, Any]:
    """
    Evaluates all models on the held-out 2021-2025 test dataset (N=677 eligible across crops).
    Executed exactly once per experimental protocol.
    """
    train_data = df_crop[df_crop["dataset_split"] == "TRAIN"].copy()
    test_data = df_crop[df_crop["dataset_split"] == "TEST"].copy()

    X_train = train_data[features].copy()
    y_train = train_data["yield_anomaly_pct"].values
    X_test = test_data[features].copy()
    y_test = test_data["yield_anomaly_pct"].values

    test_base_mtha = test_data["historical_baseline_yield_mt_ha"].values
    test_actual_mtha = test_data["yield_metric_tons_per_hectare"].values

    # Median Imputation
    for col in features:
        med = X_train[col].median()
        X_train[col] = X_train[col].fillna(med)
        X_test[col] = X_test[col].fillna(med)

    # Scale strictly on training set
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train.values)
    X_test_scaled = scaler.transform(X_test.values)

    models = get_candidate_models()
    test_results = {}

    for name, model in models.items():
        if model is None:
            pred_test = np.zeros_like(y_test)
        elif "HistGradientBoosting" in name:
            model.fit(X_train.values, y_train)
            pred_test = model.predict(X_test.values)
        else:
            model.fit(X_train_scaled, y_train)
            pred_test = model.predict(X_test_scaled)

        # Full Test Set (2021-2025)
        full_metrics = compute_metrics(y_test, pred_test, test_base_mtha, test_actual_mtha)

        # 2021-2022 Shock Sub-Period
        shock_mask = test_data["crop_year"].isin([2021, 2022]).values
        shock_metrics = compute_metrics(
            y_test[shock_mask], pred_test[shock_mask],
            test_base_mtha[shock_mask], test_actual_mtha[shock_mask]
        )

        # 2023-2025 Post-Shock Sub-Period
        post_shock_mask = test_data["crop_year"].isin([2023, 2024, 2025]).values
        post_shock_metrics = compute_metrics(
            y_test[post_shock_mask], pred_test[post_shock_mask],
            test_base_mtha[post_shock_mask], test_actual_mtha[post_shock_mask]
        )

        test_results[name] = {
            "full_period_2021_2025": {
                "n_records": int(len(test_data)),
                **full_metrics
            },
            "macro_shock_subperiod_2021_2022": {
                "n_records": int(shock_mask.sum()),
                **shock_metrics
            },
            "post_shock_subperiod_2023_2025": {
                "n_records": int(post_shock_mask.sum()),
                **post_shock_metrics
            }
        }

    return test_results


def run_pipeline() -> Tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """Runs the complete crop yield anomaly model training and evaluation."""
    print("=" * 80)
    print("STARTING CROP YIELD ANOMALY MODEL TRAINING & EVALUATION")
    print("=" * 80)

    # 1. Load Data
    print(f"Loading pre-season dataset: {PRE_SEASON_PATH}")
    df_pre = pd.read_csv(PRE_SEASON_PATH)
    print(f"Loading mid-season dataset: {MID_SEASON_PATH}")
    df_mid = pd.read_csv(MID_SEASON_PATH)

    # 2. Filter Eligible Records
    df_pre_elig = df_pre[df_pre["is_eligible_for_anomaly_training"] == 1].copy()
    df_mid_elig = df_mid[df_mid["is_eligible_for_anomaly_training"] == 1].copy()

    print(f"Eligible Records Verified: Pre-Season={len(df_pre_elig)}, Mid-Season={len(df_mid_elig)}")
    assert len(df_pre_elig) == 2957, f"Expected 2957 eligible rows, got {len(df_pre_elig)}"
    assert len(df_mid_elig) == 2957, f"Expected 2957 eligible rows, got {len(df_mid_elig)}"

    overall_report = {
        "experiment": "Phase 2 Crop Yield Anomaly Model Training and Evaluation",
        "approved_crops": APPROVED_CROPS,
        "eligible_train_records": int((df_pre_elig["dataset_split"] == "TRAIN").sum()),
        "eligible_test_records": int((df_pre_elig["dataset_split"] == "TEST").sum()),
        "horizons": list(HORIZONS.keys()),
        "results_by_crop_and_horizon": {}
    }

    all_comparison_rows = []
    all_fold_rows = []

    for crop in APPROVED_CROPS:
        print(f"\n" + "#" * 60)
        print(f"EVALUATING CROP: {crop.upper()}")
        print("#" * 60)

        crop_report = {}

        for horizon_name, h_info in HORIZONS.items():
            print(f"\n--- Horizon: {horizon_name} ---")
            df_active = df_pre_elig if h_info["dataset_type"] == "pre" else df_mid_elig
            df_crop = df_active[df_active["crop_name"] == crop].copy()
            df_crop_train = df_crop[df_crop["dataset_split"] == "TRAIN"].copy()
            df_crop_test = df_crop[df_crop["dataset_split"] == "TEST"].copy()

            features = h_info["features"]

            # Run 10-fold chronological forward chaining
            val_summary, fold_records = run_forward_chaining_validation(df_crop_train, features)
            for fr in fold_records:
                fr["crop"] = crop
                fr["horizon"] = horizon_name
                all_fold_rows.append(fr)

            # Model Selection Gate
            winner_model, selection_reason = select_winning_model(val_summary)

            print(f"Validation Selection: WINNER = {winner_model}")
            print(f"  Reason: {selection_reason}")
            print(f"  Validation Summary:")
            for m_name, m_stats in val_summary.items():
                print(f"    {m_name:30s}: RMSE={m_stats['mean_val_rmse_pp']:5.2f} pp | Rel Imp={m_stats['rel_rmse_improvement_pct']:+5.2f}% | Wins={m_stats['fold_wins_out_of_10']}/10 | Gate={m_stats['passes_acceptance_gates']}")

            # Final Once-Only Held-Out Test Evaluation
            test_results = evaluate_final_test_set(df_crop, features, winner_model)

            # Assemble Comparison Table Row
            base_val_rmse = val_summary["Zero-Anomaly Baseline"]["mean_val_rmse_pp"]
            base_test_rmse = test_results["Zero-Anomaly Baseline"]["full_period_2021_2025"]["anomaly_rmse_pp"]

            for m_name in val_summary:
                m_val = val_summary[m_name]
                m_test = test_results[m_name]["full_period_2021_2025"]
                m_shock = test_results[m_name]["macro_shock_subperiod_2021_2022"]
                m_post = test_results[m_name]["post_shock_subperiod_2023_2025"]

                test_rel_imp = ((base_test_rmse - m_test["anomaly_rmse_pp"]) / base_test_rmse) * 100.0 if base_test_rmse > 0 else 0.0

                all_comparison_rows.append({
                    "crop": crop,
                    "horizon": horizon_name,
                    "model": m_name,
                    "is_selected_model": (m_name == winner_model),
                    "val_rmse_pp": m_val["mean_val_rmse_pp"],
                    "val_mae_pp": m_val["mean_val_mae_pp"],
                    "val_rel_rmse_imp_pct": m_val["rel_rmse_improvement_pct"],
                    "val_fold_wins": m_val["fold_wins_out_of_10"],
                    "val_passes_gate": m_val["passes_acceptance_gates"],
                    "test_rmse_pp_2021_2025": m_test["anomaly_rmse_pp"],
                    "test_mae_pp_2021_2025": m_test["anomaly_mae_pp"],
                    "test_rel_imp_pct": round(test_rel_imp, 2),
                    "test_yield_rmse_mtha": m_test["yield_rmse_mtha"],
                    "test_yield_mae_mtha": m_test["yield_mae_mtha"],
                    "test_yield_r2": m_test["yield_r2"],
                    "test_dir_acc_pct": m_test["direction_accuracy_pct"],
                    "test_shock_rmse_2021_2022": m_shock["anomaly_rmse_pp"],
                    "test_post_shock_rmse_2023_2025": m_post["anomaly_rmse_pp"]
                })

            crop_report[horizon_name] = {
                "selected_winning_model": winner_model,
                "selection_reason": selection_reason,
                "features_used": features,
                "validation_summary_10_folds": val_summary,
                "held_out_test_evaluation": test_results
            }

        overall_report["results_by_crop_and_horizon"][crop] = crop_report

    df_comparison = pd.DataFrame(all_comparison_rows)
    df_folds = pd.DataFrame(all_fold_rows)

    # Save Output Artifacts
    output_dirs = [
        os.path.join(BASE_DIR_BACKEND, "data"),
        os.path.join(BASE_DIR_RESEARCH, "data")
    ]

    for od in output_dirs:
        os.makedirs(od, exist_ok=True)
        report_json_path = os.path.join(od, "crop_yield_anomaly_evaluation_report.json")
        comp_csv_path = os.path.join(od, "crop_yield_anomaly_model_comparison.csv")
        fold_csv_path = os.path.join(od, "crop_yield_anomaly_fold_results.csv")

        with open(report_json_path, "w", encoding="utf-8") as f:
            json.dump(overall_report, f, indent=2)
        df_comparison.to_csv(comp_csv_path, index=False)
        df_folds.to_csv(fold_csv_path, index=False)

    print("\n" + "=" * 80)
    print("Crop yield anomaly model training and evaluation complete.")
    print(f"Artifacts saved successfully to {output_dirs[0]}")
    print("=" * 80)

    return overall_report, df_comparison, df_folds


if __name__ == "__main__":
    report, comp_df, fold_df = run_pipeline()
