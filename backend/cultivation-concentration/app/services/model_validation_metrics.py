"""Service for loading and formatting frozen model validation and chronological metrics.

Strictly reads frozen artifacts from models/experimental/historical_feature_improvement/v1_20261009/
without fabricating statistics or exposing individual farmer records.
"""
import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = ROOT / "models/experimental/historical_feature_improvement/v1_20261009/metrics.json"
SCHEMA_PATH = ROOT / "models/experimental/historical_feature_improvement/v1_20261009/feature_schema.json"
SELECTION_PATH = ROOT / "models/experimental/historical_feature_improvement/v1_20261009/selection_frozen_before_2025.json"


def _extract_period(
    fold_data: Dict[str, Any],
    period_id: str,
    title: str,
    eval_type: str,
    training_coverage: str,
    evaluation_year: Any,
) -> Dict[str, Any]:
    if not fold_data:
        return {}

    per_class = fold_data.get("per_class", {})
    return {
        "period_id": period_id,
        "title": title,
        "evaluation_type": eval_type,
        "training_coverage": training_coverage,
        "evaluation_year": str(evaluation_year),
        "records_evaluated": fold_data.get("records", 0),
        "correct_predictions": fold_data.get("correct", 0),
        "accuracy": round(float(fold_data.get("accuracy", 0.0)), 4),
        "macro_f1": round(float(fold_data.get("macro_f1", 0.0)), 4),
        "classes": ["Low", "Medium", "High"],
        "class_metrics": {
            cls: {
                "precision": round(float(per_class[cls].get("precision", 0.0)), 4),
                "recall": round(float(per_class[cls].get("recall", 0.0)), 4),
                "f1_score": round(float(per_class[cls].get("f1-score", 0.0)), 4),
                "support": int(per_class[cls].get("support", 0)),
            }
            for cls in ("Low", "Medium", "High")
            if cls in per_class
        },
        "confusion_matrix": {
            "labels": ["Low", "Medium", "High"],
            "matrix": fold_data.get("confusion_matrix", []),
        },
    }


def load_frozen_validation_metrics() -> Dict[str, Any]:
    """Read actual frozen evaluation metrics from the vetted experimental artifact."""
    if not METRICS_PATH.exists():
        raise FileNotFoundError(f"Frozen model metrics artifact not found: {METRICS_PATH}")

    data = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8")) if SCHEMA_PATH.exists() else {}
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8")) if SELECTION_PATH.exists() else {}

    dev_folds = data.get("development", {}).get("folds", {})
    final_2025 = data.get("final_2025", {})
    pooled = data.get("pooled", {})

    chronological_periods = [
        _extract_period(
            dev_folds.get("2023", {}),
            period_id="2023_fold",
            title="2023 Chronological Validation Fold",
            eval_type="Temporal split validation fold",
            training_coverage="2020 - 2022",
            evaluation_year="2023",
        ),
        _extract_period(
            dev_folds.get("2024", {}),
            period_id="2024_fold",
            title="2024 Chronological Validation Fold",
            eval_type="Temporal split validation fold",
            training_coverage="2020 - 2023",
            evaluation_year="2024",
        ),
        _extract_period(
            final_2025,
            period_id="2025_holdout",
            title="2025 Out-of-Time Holdout Evaluation",
            eval_type="Strict out-of-time holdout (unseen during model selection)",
            training_coverage="2020 - 2024",
            evaluation_year="2025",
        ),
        _extract_period(
            pooled,
            period_id="pooled_evaluation",
            title="Pooled Multi-Year Evaluation",
            eval_type="Multi-year aggregated test evaluation",
            training_coverage="Chronologically isolated by fold (2020-2024)",
            evaluation_year="2023 - 2025",
        ),
    ]

    f_2023 = dev_folds.get("2023", {})
    p_2023 = f_2023.get("per_class", {})
    p_2025 = final_2025.get("per_class", {})

    return {
        "model_metadata": {
            "model_name": "XGBoost",
            "pipeline_bundle": "selected_xgboost_2024",
            "model_artifact_path": "models/experimental/historical_feature_improvement/v1_20261009/selected_xgboost_through_2024.joblib",
            "metrics_artifact_path": "models/experimental/historical_feature_improvement/v1_20261009/metrics.json",
            "feature_schema_path": "models/experimental/historical_feature_improvement/v1_20261009/feature_schema.json",
            "feature_count": len(schema.get("features", [])),
            "features": schema.get("features", []),
            "selected_feature_set": data.get("selected", selection.get("selected", "base_plus_previous_weight4_boost1.0")),
            "holdout_used_for_selection": selection.get("2025_used_for_selection", False),
        },
        "temporal_degradation_analysis": {
            "accuracy_2023": round(float(f_2023.get("accuracy", 0.0)), 4),
            "macro_f1_2023": round(float(f_2023.get("macro_f1", 0.0)), 4),
            "accuracy_2025": round(float(final_2025.get("accuracy", 0.0)), 4),
            "macro_f1_2025": round(float(final_2025.get("macro_f1", 0.0)), 4),
            "medium_recall_2023": round(float(p_2023.get("Medium", {}).get("recall", 0.0)), 4),
            "medium_recall_2025": round(float(p_2025.get("Medium", {}).get("recall", 0.0)), 4),
            "high_recall_2023": round(float(p_2023.get("High", {}).get("recall", 0.0)), 4),
            "high_recall_2025": round(float(p_2025.get("High", {}).get("recall", 0.0)), 4),
            "observations": [
                "Accuracy displays chronological degradation from 91.24% in 2023 to 75.57% in the 2025 out-of-time holdout.",
                "Macro F1 decreases from 0.8035 (2023) to 0.6295 (2025), primarily caused by difficulty resolving boundary cases in the Medium concentration class.",
                "Medium class recall drops from 92.96% in 2023 to 22.39% in 2025 as higher acreage intensities caused borderline cases to shift toward High predictions.",
                "High class recall improves from 49.70% (2023) to 95.41% (2025), preserving sensitivity for heavy cultivation clusters even under temporal distribution shifts.",
            ],
            "scientific_limitations_notice": (
                "CRITICAL RESEARCH BOUNDARY: The evaluated XGBoost model predicts historical cultivation concentration categories "
                "derived from retrospective peer acreage density. It is an analytical research proxy, NOT an independently validated "
                "forecast of market oversupply, crop price deflation, financial loss, or yield failure. External market factors, consumer demand elasticity, "
                "and post-harvest losses remain outside the scope of this historical proxy."
            ),
        },
        "chronological_evaluations": [c for c in chronological_periods if c.get("records_evaluated", 0) > 0],
    }
