"""
Trains, evaluates, and exports Model 1 (AI-Powered Climate Early Warning Classifier):
- Chronological Split (Train: 1981-2020 [26,088 samples]; Test: 2021-2025 [3,262 samples])
- Handles multi-class hazard imbalance with balanced sample weights
- Compares Random Forest vs Tuned Multi-Class XGBoost
- Computes Macro F1, Balanced Accuracy, Per-Class Precision/Recall, and ROC-AUC
- Exports:
    1. ml/early_warning_classifier.pkl
    2. ml/early_warning_evaluation_metrics.json
    3. ml/early_warning_confusion_matrix.png
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score,
    precision_score, recall_score, classification_report,
    confusion_matrix, roc_auc_score
)
import xgboost as xgb

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(CURRENT_DIR, "early_warning_training_dataset.csv")

if not os.path.exists(DATA_PATH):
    parent_data = os.path.join(CURRENT_DIR, "..", "ml", "early_warning_training_dataset.csv")
    if os.path.exists(parent_data):
        DATA_PATH = parent_data
    else:
        print(f"ERROR: Dataset not found at: {DATA_PATH}")
        sys.exit(1)

print("=" * 85)
print("TRAINING AI-POWERED CLIMATE EARLY WARNING MULTI-HAZARD CLASSIFIER")
print("=" * 85)
print(f"Dataset: {DATA_PATH}")

df = pd.read_csv(DATA_PATH)
print(f"Loaded: {len(df):,} total 14-day observations across 25 districts (1981-2025).")

# 1. Chronological Split (Train: 1981-2020; Test: 2021-2025)
train_mask = df["year"] <= 2020
test_mask = df["year"] >= 2021

train_df = df[train_mask].copy()
test_df = df[test_mask].copy()

print(f"\nChronological Split (Zero Future Data Leakage):")
print(f"  Training Set (1981 - 2020): {len(train_df):,} samples ({len(train_df)/len(df)*100:.1f}%)")
print(f"  Testing Set  (2021 - 2025): {len(test_df):,} samples ({len(test_df)/len(df)*100:.1f}%)")

NUM_FEATURES = [
    "rainfall_14d_sum_mm",
    "rainfall_max_1d_mm",
    "temp_max_14d_peak_c",
    "temp_mean_14d_c",
    "temp_min_14d_c",
    "humidity_mean_pct",
    "consecutive_heat_days",
    "consecutive_dry_days",
    "soil_moisture_topsoil_m3_m3",
    "spi3_current"
]
CAT_FEATURES = ["district", "climate_zone", "month"]

# One-hot encoding for categorical variables
df_encoded = pd.get_dummies(df[CAT_FEATURES + NUM_FEATURES], columns=CAT_FEATURES, drop_first=False)
feature_names = list(df_encoded.columns)

X_train = df_encoded[train_mask]
y_train = train_df["hazard_risk_tier"].values

X_test = df_encoded[test_mask]
y_test = test_df["hazard_risk_tier"].values

# Compute balanced sample weights to handle rare severe/extreme events
sample_weights_train = compute_sample_weight("balanced", y_train)

# ------------------------------------------------------------------------------
# 2. Train Candidate 1: Random Forest Classifier
# ------------------------------------------------------------------------------
print("\n[1/2] Training Balanced Random Forest Classifier...")
rf_model = RandomForestClassifier(
    n_estimators=250,
    max_depth=14,
    min_samples_split=4,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=42,
    n_jobs=4
)
rf_model.fit(X_train, y_train)
pred_rf = rf_model.predict(X_test)
proba_rf = rf_model.predict_proba(X_test)

acc_rf = accuracy_score(y_test, pred_rf)
bal_acc_rf = balanced_accuracy_score(y_test, pred_rf)
f1_macro_rf = f1_score(y_test, pred_rf, average="macro")
f1_weighted_rf = f1_score(y_test, pred_rf, average="weighted")
roc_auc_rf = roc_auc_score(y_test, proba_rf, multi_class="ovr")

print(f"  -> Random Forest: Accuracy: {acc_rf*100:.2f}% | Balanced Acc: {bal_acc_rf*100:.2f}% | Macro F1: {f1_macro_rf:.4f} | ROC-AUC: {roc_auc_rf:.4f}")

# ------------------------------------------------------------------------------
# 3. Train Candidate 2: Multi-Class Tuned XGBoost Classifier
# ------------------------------------------------------------------------------
print("\n[2/2] Training Multi-Class Tuned XGBoost Classifier...")
xgb_model = xgb.XGBClassifier(
    n_estimators=300,
    learning_rate=0.04,
    max_depth=6,
    subsample=0.85,
    colsample_bytree=0.85,
    objective="multi:softprob",
    num_class=4,
    random_state=42,
    n_jobs=4
)
xgb_model.fit(X_train, y_train, sample_weight=sample_weights_train)
pred_xgb = xgb_model.predict(X_test)
proba_xgb = xgb_model.predict_proba(X_test)

acc_xgb = accuracy_score(y_test, pred_xgb)
bal_acc_xgb = balanced_accuracy_score(y_test, pred_xgb)
f1_macro_xgb = f1_score(y_test, pred_xgb, average="macro")
f1_weighted_xgb = f1_score(y_test, pred_xgb, average="weighted")
roc_auc_xgb = roc_auc_score(y_test, proba_xgb, multi_class="ovr")

print(f"  -> XGBoost Classifier: Accuracy: {acc_xgb*100:.2f}% | Balanced Acc: {bal_acc_xgb*100:.2f}% | Macro F1: {f1_macro_xgb:.4f} | ROC-AUC: {roc_auc_xgb:.4f}")

# ------------------------------------------------------------------------------
# 4. Tournament Selection
# ------------------------------------------------------------------------------
print("\n" + "=" * 85)
print("CLASSIFIER TOURNAMENT RESULTS (UNSEEN 2021-2025 TEST SPLIT):")
print("=" * 85)
print(f"{'MODEL ARCHITECTURE':<30} | {'ACCURACY':<12} | {'BALANCED ACC':<14} | {'MACRO F1':<12} | {'ROC-AUC':<10}")
print("-" * 85)
print(f"{'1. Random Forest Classifier':<30} | {acc_rf*100:>8.2f}%    | {bal_acc_rf*100:>10.2f}%   | {f1_macro_rf:>10.4f}   | {roc_auc_rf:>8.4f}")
print(f"{'2. Tuned XGBoost Classifier':<30} | {acc_xgb*100:>8.2f}%    | {bal_acc_xgb*100:>10.2f}%   | {f1_macro_xgb:>10.4f}   | {roc_auc_xgb:>8.4f}")
print("=" * 85)

# Choose winner based on Balanced Accuracy & Macro F1
if bal_acc_xgb >= bal_acc_rf:
    winning_model_name = "Tuned Multi-Class XGBoost Classifier"
    winning_model = xgb_model
    winning_pred = pred_xgb
    winning_proba = proba_xgb
    w_acc, w_bal_acc, w_f1, w_auc = acc_xgb, bal_acc_xgb, f1_macro_xgb, roc_auc_xgb
else:
    winning_model_name = "Balanced Random Forest Classifier"
    winning_model = rf_model
    winning_pred = pred_rf
    winning_proba = proba_rf
    w_acc, w_bal_acc, w_f1, w_auc = acc_rf, bal_acc_rf, f1_macro_rf, roc_auc_rf

print(f"\nWINNING MODEL: {winning_model_name}")

# Detailed Per-Class Classification Report
tier_names = ["0: Normal/Low", "1: Moderate Alert", "2: Severe Alert", "3: Extreme Crisis"]
print("\nPer-Class Breakdown:")
print(classification_report(y_test, winning_pred, target_names=tier_names, digits=4))

# Confusion Matrix
cm = confusion_matrix(y_test, winning_pred)

# ------------------------------------------------------------------------------
# 5. Generate Publication-Quality Visual Confusion Matrix
# ------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
cax = ax.matshow(cm, cmap="Blues", alpha=0.85)

for i in range(cm.shape[0]):
    for j in range(cm.shape[1]):
        ax.text(x=j, y=i, s=f"{cm[i, j]:,}", va="center", ha="center", fontsize=11, fontweight="bold",
                color="white" if cm[i, j] > cm.max() / 2 else "black")

fig.colorbar(cax)
ax.set_xticks(range(4))
ax.set_yticks(range(4))
ax.set_xticklabels(["Tier 0\nNormal", "Tier 1\nModerate", "Tier 2\nSevere", "Tier 3\nExtreme"], fontsize=10)
ax.set_yticklabels(["Tier 0 Normal", "Tier 1 Moderate", "Tier 2 Severe", "Tier 3 Extreme"], fontsize=10)
ax.set_xlabel("AI Predicted Risk Tier", fontsize=12, fontweight="bold", labelpad=10)
ax.set_ylabel("Ground-Truth Hazard Tier", fontsize=12, fontweight="bold", labelpad=10)
ax.set_title(f"Early Warning Confusion Matrix (2021–2025 Unseen Test Split)\nModel: {winning_model_name} | Accuracy: {w_acc*100:.2f}%",
             fontsize=12, fontweight="bold", pad=15)

plot_path = os.path.join(CURRENT_DIR, "early_warning_confusion_matrix.png")
plt.tight_layout()
plt.savefig(plot_path)
plt.close()
print(f"Saved visual confusion matrix to: {plot_path}")

# ------------------------------------------------------------------------------
# 6. Save Evaluation Metrics JSON
# ------------------------------------------------------------------------------
metrics_data = {
    "service_name": "climate-early-warning-service",
    "training_period": "1981 - 2020",
    "test_period": "2021 - 2025",
    "total_samples": len(df),
    "train_samples": len(train_df),
    "test_samples": len(test_df),
    "winning_model": winning_model_name,
    "metrics": {
        "accuracy_pct": round(float(w_acc * 100), 2),
        "balanced_accuracy_pct": round(float(w_bal_acc * 100), 2),
        "macro_f1_score": round(float(w_f1), 4),
        "roc_auc_ovr": round(float(w_auc), 4),
        "confusion_matrix": cm.tolist()
    },
    "comparison": {
        "random_forest": {
            "accuracy_pct": round(float(acc_rf * 100), 2),
            "balanced_accuracy_pct": round(float(bal_acc_rf * 100), 2),
            "macro_f1": round(float(f1_macro_rf), 4),
            "roc_auc": round(float(roc_auc_rf), 4)
        },
        "xgboost_classifier": {
            "accuracy_pct": round(float(acc_xgb * 100), 2),
            "balanced_accuracy_pct": round(float(bal_acc_xgb * 100), 2),
            "macro_f1": round(float(f1_macro_xgb), 4),
            "roc_auc": round(float(roc_auc_xgb), 4)
        }
    }
}

metrics_json_path = os.path.join(CURRENT_DIR, "early_warning_evaluation_metrics.json")
with open(metrics_json_path, "w") as f:
    json.dump(metrics_data, f, indent=2)
print(f"Saved quantitative metrics to: {metrics_json_path}")

# ------------------------------------------------------------------------------
# 7. Serialize Artifact for Production Backend
# ------------------------------------------------------------------------------
artifact = {
    "model_type": winning_model_name,
    "model": winning_model,
    "feature_columns": feature_names,
    "num_features": NUM_FEATURES,
    "cat_features": CAT_FEATURES,
    "tier_labels": {
        0: "Normal / Low Risk",
        1: "Moderate Alert",
        2: "Severe Alert",
        3: "Extreme Crisis"
    },
    "metrics": metrics_data["metrics"]
}

pkl_path = os.path.join(CURRENT_DIR, "early_warning_classifier.pkl")
with open(pkl_path, "wb") as f:
    pickle.dump(artifact, f)
print(f"Saved winning model artifact to: {pkl_path}")

# Copy to backend ml folder if present
GIT_ML_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "Project", "GitHubClone", "J26-IT-358", "backend", "climate-yield", "ml"))
if os.path.exists(GIT_ML_DIR):
    for f_name, src_file in [
        ("early_warning_classifier.pkl", pkl_path),
        ("early_warning_evaluation_metrics.json", metrics_json_path),
        ("early_warning_confusion_matrix.png", plot_path),
        ("train_early_warning_classifier.py", os.path.abspath(__file__))
    ]:
        dest_file = os.path.join(GIT_ML_DIR, f_name)
        with open(src_file, "rb") as rf, open(dest_file, "wb") as wf:
            wf.write(rf.read())
        print(f"  Copied to backend: {dest_file}")

print("\n" + "=" * 85)
print("AI CLIMATE EARLY WARNING CLASSIFIER READY FOR PRODUCTION INFERENCE!")
print("=" * 85)
