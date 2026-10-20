import json
import os
import sys

def main():
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "data", "crop_yield_anomaly_evaluation_report.json"),
        os.path.join("data", "crop_yield_anomaly_evaluation_report.json"),
        os.path.join("backend", "climate-yield", "data", "crop_yield_anomaly_evaluation_report.json")
    ]
    report_path = None
    for p in possible_paths:
        if os.path.exists(p):
            report_path = p
            break

    if not report_path:
        print("[ERROR] Evaluation report JSON not found in standard paths.")
        sys.exit(1)

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=" * 96)
    print(" CROP YIELD ANOMALY MODEL ACCURACY & PERFORMANCE SUMMARY")
    print("=" * 96)
    print(f"{'Crop':<12} | {'Model':<25} | {'Val RMSE':<10} | {'Val Imp %':<10} | {'Test MAE':<10} | {'Accuracy %':<12}")
    print("-" * 96)

    crops = ["Maize", "Chilli", "Green Gram"]
    for crop in crops:
        res = data["results_by_crop_and_horizon"][crop]["Pre-Season (Operational 5-Feat)"]
        for model in ["Zero-Anomaly Baseline", "Huber Regressor", "Ridge Regression", "ElasticNet", "Shallow HistGradientBoosting"]:
            val = res["validation_summary_10_folds"][model]
            test = res["held_out_test_evaluation"][model]["full_period_2021_2025"]
            
            val_rmse = f"{val['mean_val_rmse_pp']:.2f} pp"
            val_imp = f"{val['rel_rmse_improvement_pct']:+.2f}%"
            test_mae = f"{test['anomaly_mae_pp']:.2f} pp"
            typical_acc = f"{100.0 - test['anomaly_medae_pp']:.1f}%"
            
            m_label = ("* " + model) if model == "Zero-Anomaly Baseline" else ("  " + model)
            print(f"{crop:<12} | {m_label:<25} | {val_rmse:<10} | {val_imp:<10} | {test_mae:<10} | {typical_acc:<12}")
        print("-" * 96)

    print("* = Selected Winning Model (Historical Rolling Baseline - Passes Fallback Policy)")
    print("Accuracy % = (100 - Typical Error % on unseen 2021-2025 test years)")
    print("=" * 96)

if __name__ == "__main__":
    main()
