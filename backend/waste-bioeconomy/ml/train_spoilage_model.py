"""
Model Training & Benchmarking: Pre-Arrival Post-Harvest Spoilage Risk Scoring
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks & Waste Management
Student: Lakruwan W.M.K. (IT23330382)
Project: J26-IT-358

Core Objectives:
1. Train Dual XGBoost Spoilage Models:
   - XGBoost Regressor (Continuous spoilage loss %; Target: RMSE < 10.0%)
   - XGBoost Classifier (3-tier operational risk classification; Target: Macro F1 > 0.85)
2. Benchmark against 3 Baseline Approaches (Table 1 for Research Thesis):
   - Baseline 1: Static Rule-Based Heuristic (Current Sri Lankan industry threshold)
   - Baseline 2: Linear / Logistic Regression
   - Baseline 3: Random Forest (Ensemble baseline)
3. Evaluate Dual-Stream Mass-Partitioning:
   - Fresh Commercial Produce Mass (kg) = Payload * (1 - Loss%)
   - Bioeconomy Feedstock Cull Mass (kg) = Payload * Loss%
   - Biogas Fallback Routing Trigger
4. Export Native JSON & Joblib Model Artifacts for FastAPI REST serving.
"""

import io
import json
import os
import sys
from typing import Any

# Enforce UTF-8 output on Windows consoles
if sys.platform == "win32" and isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

TRAIN_PATH = os.path.join(DATA_DIR, "train_spoilage_data.csv")
VAL_PATH = os.path.join(DATA_DIR, "val_spoilage_data.csv")
TEST_PATH = os.path.join(DATA_DIR, "test_spoilage_data.csv")

BENCHMARK_CSV_PATH = os.path.join(DATA_DIR, "model_benchmark_comparison_table.csv")
BENCHMARK_JSON_PATH = os.path.join(DATA_DIR, "model_benchmark_comparison_table.json")

# Model Export Paths
REGRESSOR_JSON_PATH = os.path.join(MODELS_DIR, "spoilage_xgboost_regressor.json")
CLASSIFIER_JSON_PATH = os.path.join(MODELS_DIR, "spoilage_xgboost_classifier.json")
PREPROCESSOR_PATH = os.path.join(MODELS_DIR, "encoder_and_scaler.joblib")
METADATA_PATH = os.path.join(MODELS_DIR, "feature_metadata.json")
IMPORTANCE_PATH = os.path.join(MODELS_DIR, "feature_importance_ranking.json")


# ------------------------------------------------------------------------------
# Feature Schema Definitions
# ------------------------------------------------------------------------------
NUMERICAL_FEATURES = [
    "quantity_kg",
    "distance_km",
    "transit_hours",
    "transit_speed_kmh",
    "ambient_temperature_c",
    "effective_temperature_c",
    "ambient_humidity_pct",
    "mechanical_vibration_index",
    "thermal_stress_index",
    "q10_respiration_factor",
    "crop_moisture_pct",
    "crop_c_n_ratio",
    "respiration_rate_baseline",
    "road_vibration_rank",
    "road_vibration_multiplier",
    "packaging_penalty_factor",
    "is_refrigerated",
]

CATEGORICAL_FEATURES = [
    "crop_name",
    "perishability_class",
    "route",
    "season",
    "vehicle_type",
    "road_condition",
    "packaging_type",
]


class StaticRuleBasedBaseline:
    """
    Empirical Static Rule-Based Threshold Model representing current Sri Lankan
    agricultural logistics practice (heuristics based on temperature & travel duration).
    """

    def predict_loss(self, df: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in df.iterrows():
            temp = float(row["ambient_temperature_c"])
            hrs = float(row["transit_hours"])
            if temp > 28.0 and hrs > 7.0:
                preds.append(26.0)
            elif temp > 25.0 or hrs > 5.0:
                preds.append(17.5)
            else:
                preds.append(8.5)
        return np.array(preds, dtype=np.float64)

    def predict_class(self, df: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in df.iterrows():
            temp = float(row["ambient_temperature_c"])
            hrs = float(row["transit_hours"])
            if temp > 28.0 and hrs > 7.0:
                preds.append(2)  # HIGH
            elif temp > 25.0 or hrs > 5.0:
                preds.append(1)  # MEDIUM
            else:
                preds.append(0)  # LOW
        return np.array(preds, dtype=np.int64)


def prepare_datasets() -> dict[str, Any]:
    """Loads stratified partitions and builds leakage-safe feature transformations."""
    for path in [TRAIN_PATH, VAL_PATH, TEST_PATH]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required split not found at: {path}. Run stage6 first!")

    train_df = pd.read_csv(TRAIN_PATH)
    val_df = pd.read_csv(VAL_PATH)
    test_df = pd.read_csv(TEST_PATH)

    print(" Loaded Stratified Splits:")
    print(f"   * Train Set      : {len(train_df):5d} records")
    print(f"   * Validation Set : {len(val_df):5d} records")
    print(f"   * Test Set (Hold): {len(test_df):5d} records")

    # Fit OneHotEncoder STRICTLY on train
    encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    encoder.fit(train_df[CATEGORICAL_FEATURES])
    cat_feature_names = list(encoder.get_feature_names_out(CATEGORICAL_FEATURES))

    all_feature_names = NUMERICAL_FEATURES + cat_feature_names

    # Transform categorical features
    train_cat = encoder.transform(train_df[CATEGORICAL_FEATURES])
    val_cat = encoder.transform(val_df[CATEGORICAL_FEATURES])
    test_cat = encoder.transform(test_df[CATEGORICAL_FEATURES])

    # Convert to pure numpy 2D float64 arrays
    train_num = np.asarray(train_df[NUMERICAL_FEATURES].values, dtype=np.float64)
    val_num = np.asarray(val_df[NUMERICAL_FEATURES].values, dtype=np.float64)
    test_num = np.asarray(test_df[NUMERICAL_FEATURES].values, dtype=np.float64)

    x_train = np.hstack((train_num, np.asarray(train_cat, dtype=np.float64)))
    x_val = np.hstack((val_num, np.asarray(val_cat, dtype=np.float64)))
    x_test = np.hstack((test_num, np.asarray(test_cat, dtype=np.float64)))

    # Fit StandardScaler STRICTLY on train (for linear models)
    scaler = StandardScaler()
    scaler.fit(x_train)
    x_train_scaled = np.asarray(scaler.transform(x_train), dtype=np.float64)
    x_test_scaled = np.asarray(scaler.transform(x_test), dtype=np.float64)

    # Targets
    y_train_reg = np.asarray(train_df["spoilage_loss_pct"].values, dtype=np.float64)
    y_val_reg = np.asarray(val_df["spoilage_loss_pct"].values, dtype=np.float64)
    y_test_reg = np.asarray(test_df["spoilage_loss_pct"].values, dtype=np.float64)

    y_train_clf = np.asarray(train_df["risk_class"].values, dtype=np.int64)
    y_val_clf = np.asarray(val_df["risk_class"].values, dtype=np.int64)
    y_test_clf = np.asarray(test_df["risk_class"].values, dtype=np.int64)

    return {
        "train_df": train_df,
        "val_df": val_df,
        "test_df": test_df,
        "x_train": x_train,
        "x_val": x_val,
        "x_test": x_test,
        "x_train_scaled": x_train_scaled,
        "x_test_scaled": x_test_scaled,
        "y_train_reg": y_train_reg,
        "y_val_reg": y_val_reg,
        "y_test_reg": y_test_reg,
        "y_train_clf": y_train_clf,
        "y_val_clf": y_val_clf,
        "y_test_clf": y_test_clf,
        "feature_names": all_feature_names,
        "encoder": encoder,
        "scaler": scaler,
    }


def train_and_evaluate() -> dict[str, Any]:
    print("=" * 80)
    print("STEP 1: SUPERVISED ML SPOILAGE RISK MODEL TRAINING & BENCHMARKING")
    print("=" * 80)
    os.makedirs(MODELS_DIR, exist_ok=True)

    data = prepare_datasets()
    test_df: pd.DataFrame = data["test_df"]
    x_train: np.ndarray = data["x_train"]
    x_val: np.ndarray = data["x_val"]
    x_test: np.ndarray = data["x_test"]
    x_train_scaled: np.ndarray = data["x_train_scaled"]
    x_test_scaled: np.ndarray = data["x_test_scaled"]

    y_train_reg: np.ndarray = data["y_train_reg"]
    y_val_reg: np.ndarray = data["y_val_reg"]
    y_test_reg: np.ndarray = data["y_test_reg"]

    y_train_clf: np.ndarray = data["y_train_clf"]
    y_val_clf: np.ndarray = data["y_val_clf"]
    y_test_clf: np.ndarray = data["y_test_clf"]

    feature_names: list[str] = data["feature_names"]
    encoder: OneHotEncoder = data["encoder"]
    scaler: StandardScaler = data["scaler"]

    benchmark_rows = []

    # --------------------------------------------------------------------------
    # 1. Baseline 1: Static Rule-Based Threshold
    # --------------------------------------------------------------------------
    print("\n--- 1. EVALUATING BASELINE 1: STATIC RULE-BASED THRESHOLD ---")
    rule_model = StaticRuleBasedBaseline()
    rule_pred_reg = rule_model.predict_loss(test_df)
    rule_pred_clf = rule_model.predict_class(test_df)

    rule_rmse = float(np.sqrt(mean_squared_error(y_test_reg, rule_pred_reg)))
    rule_mae = float(mean_absolute_error(y_test_reg, rule_pred_reg))
    rule_acc = float(accuracy_score(y_test_clf, rule_pred_clf) * 100.0)
    rule_p = float(precision_score(y_test_clf, rule_pred_clf, average="macro"))
    rule_r = float(recall_score(y_test_clf, rule_pred_clf, average="macro"))
    rule_f1 = float(f1_score(y_test_clf, rule_pred_clf, average="macro"))

    print(f"   * Accuracy: {rule_acc:.2f}% | Macro F1: {rule_f1:.4f} | Precision: {rule_p:.4f} | Recall: {rule_r:.4f}")
    print(f"   * Regressor RMSE: {rule_rmse:.2f}% | MAE: {rule_mae:.2f}%")

    benchmark_rows.append({
        "Model": "Static Rule-Based Baseline",
        "Type": "Heuristic Rule",
        "Accuracy (%)": round(rule_acc, 2),
        "Precision": round(rule_p, 4),
        "Recall": round(rule_r, 4),
        "Macro F1": round(rule_f1, 4),
        "RMSE (%)": round(rule_rmse, 2),
        "MAE (%)": round(rule_mae, 2)
    })

    # --------------------------------------------------------------------------
    # 2. Baseline 2: Linear / Logistic Regression
    # --------------------------------------------------------------------------
    print("\n--- 2. TRAINING BASELINE 2: RIDGE & LOGISTIC REGRESSION ---")
    ridge = Ridge(alpha=1.0, random_state=42)
    ridge.fit(x_train_scaled, y_train_reg)
    ridge_pred = ridge.predict(x_test_scaled)
    ridge_rmse = float(np.sqrt(mean_squared_error(y_test_reg, ridge_pred)))
    ridge_mae = float(mean_absolute_error(y_test_reg, ridge_pred))

    log_reg = LogisticRegression(max_iter=1000, random_state=42)
    log_reg.fit(x_train_scaled, y_train_clf)
    log_pred_clf = log_reg.predict(x_test_scaled)
    log_acc = float(accuracy_score(y_test_clf, log_pred_clf) * 100.0)
    log_p = float(precision_score(y_test_clf, log_pred_clf, average="macro"))
    log_r = float(recall_score(y_test_clf, log_pred_clf, average="macro"))
    log_f1 = float(f1_score(y_test_clf, log_pred_clf, average="macro"))

    print(f"   * Accuracy: {log_acc:.2f}% | Macro F1: {log_f1:.4f} | Precision: {log_p:.4f} | Recall: {log_r:.4f}")
    print(f"   * Regressor RMSE: {ridge_rmse:.2f}% | MAE: {ridge_mae:.2f}%")

    benchmark_rows.append({
        "Model": "Linear / Logistic Regression",
        "Type": "Parametric Linear",
        "Accuracy (%)": round(log_acc, 2),
        "Precision": round(log_p, 4),
        "Recall": round(log_r, 4),
        "Macro F1": round(log_f1, 4),
        "RMSE (%)": round(ridge_rmse, 2),
        "MAE (%)": round(ridge_mae, 2)
    })

    # --------------------------------------------------------------------------
    # 3. Baseline 3: Random Forest (Ensemble)
    # --------------------------------------------------------------------------
    print("\n--- 3. TRAINING BASELINE 3: RANDOM FOREST ENSEMBLE ---")
    rf_reg = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    rf_reg.fit(x_train, y_train_reg)
    rf_pred_reg = rf_reg.predict(x_test)
    rf_rmse = float(np.sqrt(mean_squared_error(y_test_reg, rf_pred_reg)))
    rf_mae = float(mean_absolute_error(y_test_reg, rf_pred_reg))

    rf_clf = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    rf_clf.fit(x_train, y_train_clf)
    rf_pred_clf = rf_clf.predict(x_test)
    rf_acc = float(accuracy_score(y_test_clf, rf_pred_clf) * 100.0)
    rf_p = float(precision_score(y_test_clf, rf_pred_clf, average="macro"))
    rf_r = float(recall_score(y_test_clf, rf_pred_clf, average="macro"))
    rf_f1 = float(f1_score(y_test_clf, rf_pred_clf, average="macro"))

    print(f"   * Accuracy: {rf_acc:.2f}% | Macro F1: {rf_f1:.4f} | Precision: {rf_p:.4f} | Recall: {rf_r:.4f}")
    print(f"   * Regressor RMSE: {rf_rmse:.2f}% | MAE: {rf_mae:.2f}%")

    benchmark_rows.append({
        "Model": "Random Forest",
        "Type": "Bagging Ensemble",
        "Accuracy (%)": round(rf_acc, 2),
        "Precision": round(rf_p, 4),
        "Recall": round(rf_r, 4),
        "Macro F1": round(rf_f1, 4),
        "RMSE (%)": round(rf_rmse, 2),
        "MAE (%)": round(rf_mae, 2)
    })

    # --------------------------------------------------------------------------
    # 4. Proposed Solution: XGBoost Regressor & Classifier
    # --------------------------------------------------------------------------
    print("\n--- 4. TRAINING PROPOSED SOLUTION: DUAL XGBOOST MODELS ---")
    xgb_reg = xgb.XGBRegressor(
        n_estimators=400,
        learning_rate=0.04,
        max_depth=6,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        early_stopping_rounds=25,
        eval_metric="rmse"
    )
    xgb_reg.fit(
        x_train, y_train_reg,
        eval_set=[(x_train, y_train_reg), (x_val, y_val_reg)],
        verbose=False
    )
    xgb_pred_reg = np.asarray(xgb_reg.predict(x_test), dtype=np.float64)
    xgb_rmse = float(np.sqrt(mean_squared_error(y_test_reg, xgb_pred_reg)))
    xgb_mae = float(mean_absolute_error(y_test_reg, xgb_pred_reg))
    xgb_r2 = float(r2_score(y_test_reg, xgb_pred_reg))

    xgb_clf = xgb.XGBClassifier(
        n_estimators=400,
        learning_rate=0.04,
        max_depth=6,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="multi:softprob",
        num_class=3,
        random_state=42,
        early_stopping_rounds=25,
        eval_metric="mlogloss"
    )
    xgb_clf.fit(
        x_train, y_train_clf,
        eval_set=[(x_train, y_train_clf), (x_val, y_val_clf)],
        verbose=False
    )
    xgb_pred_clf = np.asarray(xgb_clf.predict(x_test), dtype=np.int64)
    xgb_acc = float(accuracy_score(y_test_clf, xgb_pred_clf) * 100.0)
    xgb_p = float(precision_score(y_test_clf, xgb_pred_clf, average="macro"))
    xgb_r = float(recall_score(y_test_clf, xgb_pred_clf, average="macro"))
    xgb_f1 = float(f1_score(y_test_clf, xgb_pred_clf, average="macro"))
    xgb_f1_weighted = float(f1_score(y_test_clf, xgb_pred_clf, average="weighted"))

    print(f"   * Accuracy: {xgb_acc:.2f}% | Macro F1: {xgb_f1:.4f} (Weighted: {xgb_f1_weighted:.4f})")
    print(f"   * Precision: {xgb_p:.4f} | Recall: {xgb_r:.4f}")
    print(f"   * Regressor RMSE: {xgb_rmse:.2f}% (Target: < 10.0%) | MAE: {xgb_mae:.2f}% | R²: {xgb_r2:.4f}")

    benchmark_rows.append({
        "Model": "XGBoost (Proposed Component 3)",
        "Type": "Gradient Boosted Trees",
        "Accuracy (%)": round(xgb_acc, 2),
        "Precision": round(xgb_p, 4),
        "Recall": round(xgb_r, 4),
        "Macro F1": round(xgb_f1, 4),
        "RMSE (%)": round(xgb_rmse, 2),
        "MAE (%)": round(xgb_mae, 2)
    })

    # Confusion Matrix
    cm = confusion_matrix(y_test_clf, xgb_pred_clf)
    print("\n XGBoost Confusion Matrix (Rows=True, Cols=Predicted):")
    print("               Pred LOW   Pred MED   Pred HIGH")
    tier_labels = ["LOW   ", "MEDIUM", "HIGH  "]
    for i, row in enumerate(cm):
        print(f"   True {tier_labels[i]}:  {row[0]:6d}     {row[1]:6d}     {row[2]:6d}")

    # --------------------------------------------------------------------------
    # 5. Export Benchmark Table (Thesis Table 1)
    # --------------------------------------------------------------------------
    benchmark_df = pd.DataFrame(benchmark_rows)
    benchmark_df.to_csv(BENCHMARK_CSV_PATH, index=False)
    benchmark_df.to_json(BENCHMARK_JSON_PATH, orient="records", indent=2)

    print("\n" + "=" * 80)
    print("RESEARCH BENCHMARK COMPARISON TABLE (PROPOSAL TABLE 1):")
    print("=" * 80)
    print(benchmark_df.to_string(index=False))
    print(f"\n [SAVED] Benchmark table saved to:\n   * {BENCHMARK_CSV_PATH}\n   * {BENCHMARK_JSON_PATH}")

    # --------------------------------------------------------------------------
    # 6. Feature Importance Extraction
    # --------------------------------------------------------------------------
    importance_scores = xgb_reg.feature_importances_
    importance_dict = {
        name: float(score) for name, score in zip(feature_names, importance_scores)
    }
    sorted_importance = sorted(importance_dict.items(), key=lambda item: item[1], reverse=True)

    print("\n--- TOP 10 INFLUENTIAL SPOILAGE RISK DRIVERS (XGBOOST GAIN) ---")
    top_10 = sorted_importance[:10]
    for rank, (fname, score) in enumerate(top_10, 1):
        print(f"   {rank:2d}. {fname:<32}: {score * 100:.2f}% gain")

    with open(IMPORTANCE_PATH, "w", encoding="utf-8") as f:
        json.dump({"ranking": sorted_importance}, f, indent=2)

    # --------------------------------------------------------------------------
    # 7. Dual-Stream Mass Partitioning Demonstration (User's Exact Logic)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("DUAL-STREAM MASS PARTITIONING DEMONSTRATION (FRESH VS. WASTE CULLS)")
    print("=" * 80)
    sample_indices = [5, 42, 108, 250, 500]
    for idx in sample_indices:
        test_row = test_df.iloc[idx]
        actual_loss = float(test_row["spoilage_loss_pct"])
        pred_loss = float(xgb_pred_reg[idx])
        payload = float(test_row["quantity_kg"])

        # Dual Stream calculations
        fresh_mass_kg = payload * (1.0 - pred_loss / 100.0)
        cull_waste_kg = payload * (pred_loss / 100.0)
        risk_class_idx = int(xgb_pred_clf[idx])
        risk_name = ["LOW", "MEDIUM", "HIGH"][risk_class_idx]
        biogas_flag = 1 if (float(test_row["crop_moisture_pct"]) > 90.0 and pred_loss > 25.0) or (float(test_row["crop_c_n_ratio"]) < 18.0) else 0

        print(f"\nTrip #{idx + 1:04d}: [{test_row['crop_name']}] | Route: {test_row['route']} | Payload: {payload:.1f} kg")
        print(f"   * Ambient Temp: {test_row['ambient_temperature_c']}°C | Duration: {test_row['transit_hours']} hrs | Road: {test_row['road_condition']}")
        print(f"   * Predicted Spoilage Loss : {pred_loss:.1f}% (Actual Ground-Truth: {actual_loss:.1f}%)")
        print(f"   * Urgency Risk Tier       : {risk_name}")
        print(f"   --> STREAM 1 (Fresh Marketable Produce) : {fresh_mass_kg:7.1f} kg ({100 - pred_loss:5.1f}%) -> Commercial Retail")
        print(f"   --> STREAM 2 (Bioeconomy Feedstock Mass): {cull_waste_kg:7.1f} kg ({pred_loss:5.1f}%) -> Circular Bioeconomy")
        if biogas_flag == 1:
            print("       [ROUTING] Biogas Fallback Activated (Extreme moisture/acidic rot diverted to Anaerobic Digestion)")
        else:
            print("       [ROUTING] Aerobic Composting Mixer (Routed to PuLP MILP C:N Optimizer)")

    # --------------------------------------------------------------------------
    # 8. Save Model Weights & Artifacts
    # --------------------------------------------------------------------------
    xgb_reg.save_model(REGRESSOR_JSON_PATH)
    xgb_clf.save_model(CLASSIFIER_JSON_PATH)

    preprocessor_bundle = {
        "encoder": encoder,
        "scaler": scaler,
        "numerical_features": NUMERICAL_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "all_feature_names": feature_names
    }
    joblib.dump(preprocessor_bundle, PREPROCESSOR_PATH)

    metadata = {
        "project": "J26-IT-358 Component 3",
        "student": "Lakruwan W.M.K. (IT23330382)",
        "models": {
            "regressor": {
                "algorithm": "XGBoost Regressor (3.4.1)",
                "target": "spoilage_loss_pct",
                "rmse": round(xgb_rmse, 3),
                "mae": round(xgb_mae, 3),
                "r2": round(xgb_r2, 4),
                "target_met": xgb_rmse < 10.0
            },
            "classifier": {
                "algorithm": "XGBoost Classifier (3.4.1)",
                "target": "risk_class (0=LOW, 1=MEDIUM, 2=HIGH)",
                "accuracy_pct": round(xgb_acc, 2),
                "macro_f1": round(xgb_f1, 4),
                "weighted_f1": round(xgb_f1_weighted, 4),
                "target_met": xgb_f1 > 0.85
            }
        },
        "features": {
            "numerical_count": len(NUMERICAL_FEATURES),
            "categorical_count": len(CATEGORICAL_FEATURES),
            "total_encoded_features": len(feature_names),
            "feature_names": feature_names
        },
        "artifacts": {
            "regressor_json": os.path.basename(REGRESSOR_JSON_PATH),
            "classifier_json": os.path.basename(CLASSIFIER_JSON_PATH),
            "preprocessor_bundle": os.path.basename(PREPROCESSOR_PATH),
            "benchmark_table": os.path.basename(BENCHMARK_CSV_PATH)
        }
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "=" * 80)
    print("STEP 1 TRAINING COMPLETED SUCCESSFULLY!")
    print(f" Artifacts Saved to {MODELS_DIR}:")
    print(f"   * Regressor Model : {os.path.basename(REGRESSOR_JSON_PATH)}")
    print(f"   * Classifier Model: {os.path.basename(CLASSIFIER_JSON_PATH)}")
    print(f"   * Preprocessor    : {os.path.basename(PREPROCESSOR_PATH)}")
    print(f"   * Model Metadata  : {os.path.basename(METADATA_PATH)}")
    print("=" * 80)

    return metadata


if __name__ == "__main__":
    train_and_evaluate()
