"""Retrospective research replay; planting dates do not prove availability.

Never reads or writes operational plans. Unknown observation availability is
retained only in the explicitly assumption-based ML replay, never as known plans.
"""
import io
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
import pandas as pd
from app.services.historical_runtime import verified_bytes

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data/legacy/official_farmer_cultivation_2020_2026.csv"
MODEL_DIR = ROOT / "models/experimental/historical_feature_improvement/v1_20261009"
RESEARCH_CROP_ALIASES = {"Chillies": "Green Chillies"}

from app.services.research_metadata import FEATURES, LABELS, BENCHMARKS

_dataset_cache: Optional[pd.DataFrame] = None


def load_historical_dataset() -> pd.DataFrame:
    global _dataset_cache
    if _dataset_cache is not None:
        return _dataset_cache.copy()
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Historical dataset not found at {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df["Planting_Date"] = pd.to_datetime(df["Planting_Date"], format="%m/%d/%Y", errors="raise")
    df["Expected_Harvest_Date"] = pd.to_datetime(df["Expected_Harvest_Date"], format="%m/%d/%Y", errors="raise")
    _dataset_cache = df
    return df.copy()


def get_model_pipeline(model_name: str, target_year: int):
    """Verify reviewed bytes before loading; year split is not model availability."""
    if target_year < 2023:
        raise ValueError("No frozen model predating this decision year")
    # Models were trained with chronological cutoffs:
    # 2023 evaluation uses through_2022
    # 2024 evaluation uses through_2023
    # 2025/2026 evaluation uses through_2024
    if target_year <= 2023:
        through_year = 2022
    elif target_year == 2024:
        through_year = 2023
    else:
        through_year = 2024

    if model_name == "XGBoost":
        model_path = MODEL_DIR / f"selected_xgboost_through_{through_year}.joblib"
    elif model_name == "CatBoost":
        model_path = ROOT / f"models/experimental/catboost_comparison/v1_20261009/catboost_pipeline_through_{through_year}.joblib"
    elif model_name == "Random Forest":
        model_path = ROOT / f"models/experimental/full_original_dataset/v1_20261009/random_forest_through_{through_year}.joblib"
    elif model_name == "LinearSVC":
        model_path = ROOT / f"models/experimental/svm_full_dataset/v1_20261009/linear_svc_through_{through_year}.joblib"
    elif model_name == "RBF SVC":
        model_path = ROOT / f"models/experimental/svm_full_dataset/v1_20261009/rbf_svc_through_{through_year}.joblib"
    else:
        raise ValueError(f"Unsupported model name: {model_name}")

    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {model_path}")

    catalog = json.loads((ROOT / "models/artifact_catalog.json").read_text(encoding="utf-8"))
    data = verified_bytes(model_path.relative_to(ROOT).as_posix(), catalog)
    pipeline = joblib.load(io.BytesIO(data))
    expected = FEATURES if model_name in ("XGBoost", "CatBoost") else FEATURES[:11]
    if list(pipeline.feature_names_in_) != expected:
        raise ValueError("Frozen model feature contract mismatch")
    return pipeline, through_year


def observation_availability(rows: pd.DataFrame, cutoff: date) -> pd.Series:
    """Trust only source/version attested aware timestamps from server-side data.

    Submission, planting, harvest and Year alone never establish when the exact
    recorded revision became observable. This CSV currently has none of these
    availability evidence fields. They cannot be supplied through the demo API.
    """
    boundary = datetime.combine(cutoff, datetime.min.time(), timezone(timedelta(hours=5, minutes=30)))
    def status(row):
        verified = row.get("Observation_Availability_Verified")
        if not isinstance(verified, (bool, np.bool_)) or not verified:
            return "unknown"
        if not isinstance(row.get("Observation_Evidence_Reference"), str) or not row["Observation_Evidence_Reference"].strip():
            return "unknown"
        try:
            stamp = datetime.fromisoformat(str(row["Observation_Available_At"]).replace("Z", "+00:00"))
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                return "unknown"
            return "available" if stamp <= boundary else "after_cutoff"
        except (KeyError, ValueError, TypeError):
            return "unknown"
    return rows.apply(status, axis=1) if len(rows) else pd.Series(index=rows.index, dtype=str)


def historical_features(group, district, crop, season, acres, planting, harvest, cutoff):
    """Frozen retrospective feature semantics, with explicit unknown availability.

    Known late revisions are excluded. Unknown revisions remain an assumption in
    the replay. Production history sums the recorded expected production just as
    in training. Own production is missing, using the frozen training imputer;
    no yield guideline or fabricated yield estimate is supplied. CatBoost keeps
    missing numerical inputs native; other pipelines use their frozen imputer.
    """
    p_dt, h_dt, c_dt = map(pd.Timestamp, (planting, harvest, cutoff))
    replay = group[observation_availability(group, cutoff) != "after_cutoff"]
    prior = replay[(replay.Year < planting.year) & (replay.Expected_Harvest_Date < c_dt)]
    peers = replay[(replay.Planting_Date < c_dt) & (replay.Expected_Harvest_Date >= c_dt)
                   & ((replay.Expected_Harvest_Date - h_dt).abs().dt.days <= 14)]
    annual = {}
    for year, rows in prior.groupby("Year"):
        dates = rows.Expected_Harvest_Date.to_numpy(dtype="datetime64[D]")
        windows, production = [], []
        for anchor in np.unique(dates):
            mask = np.abs((dates - anchor).astype(int)) <= 14
            windows.append(float(rows.Land_Size_Acres.to_numpy()[mask].sum()))
            production.append(float(rows.Expected_Production_kg.to_numpy()[mask].sum()))
        annual[int(year)] = dict(windows=np.array(windows), production=np.array(production),
                                 mean_plan=float(rows.Land_Size_Acres.mean()))
    windows = np.concatenate([v["windows"] for v in annual.values()]) if annual else np.array([])
    production = np.concatenate([v["production"] for v in annual.values()]) if annual else np.array([])
    previous = annual.get(planting.year - 1)
    features = dict(District=district, Crop=crop, Season=season, Land_Size_Acres=float(acres),
        Planting_Month=p_dt.month, Harvest_Month=h_dt.month, Overlap_Plan_Count=len(peers) + 1,
        Own_Expected_Production_kg=np.nan, Past_Window_Count=len(windows),
        Past_Mean_Window_Acres=float(windows.mean()) if len(windows) else np.nan,
        Past_Mean_Window_Production_kg=float(production.mean()) if len(production) else np.nan,
        Previous_Year_Window_Mean_Acres=float(previous["windows"].mean()) if previous else np.nan,
        Previous_Year_Window_Median_Acres=float(np.median(previous["windows"])) if previous else np.nan,
        Previous_Year_Window_Std_Acres=float(previous["windows"].std()) if previous else np.nan,
        Previous_Year_Mean_Plan_Acres=previous["mean_plan"] if previous else np.nan)
    return features, peers, prior


def concentration_indicators(group, harvest, cutoff):
    """Harvest membership and observation availability are independent predicates."""
    window = group[(group.Expected_Harvest_Date - pd.Timestamp(harvest)).abs().dt.days <= 14]
    availability = observation_availability(window, cutoff)
    known = window[availability == "available"]
    # No identities exist in this CSV, so counts are records, never unique farmers.
    def aggregate(rows):
        releasable = len(rows) >= 3
        return dict(record_count=len(rows) if releasable or not len(rows) else None,
                    acres=round(float(rows.Land_Size_Acres.sum()), 2) if releasable else None,
                    disclosure_status="aggregate" if releasable else "sparse_or_zero_coverage")
    return dict(harvest_window_start=(harvest - timedelta(days=14)).isoformat(),
        harvest_window_end=(harvest + timedelta(days=14)).isoformat(),
        matching_scope="same district/crop/declared season; region unavailable; all recorded years",
        historical_dataset_window=aggregate(window), provably_available_window=aggregate(known),
        availability_status="verified_for_all_matching_records" if len(window) and (availability == "available").all()
                            else "no_matching_records" if not len(window) else "not_fully_verified",
        unknown_availability_count=int((availability == "unknown").sum()),
        observed_after_cutoff_count=int((availability == "after_cutoff").sum()),
        interpretation="Dataset presence is not decision-time availability; acreage represents recorded intentions, not actual supply.")


def evaluate_historical_scenario(district: str, crop: str, season: str, land_size_acres: float,
        planting_date: date, expected_harvest_date: date, model_name: str = "XGBoost",
        decision_cutoff: Optional[date] = None, allow_sparse: bool = False) -> Dict[str, Any]:
    cutoff = decision_cutoff or planting_date
    if district not in ("Matara", "Hambantota"):
        raise ValueError("Unsupported pilot district")
    if crop not in ("Bandakka", "Brinjal", "Pumpkin", "Corn", "Mung Beans", "Chillies"):
        raise ValueError("Unsupported pilot crop")
    if season not in ("Maha", "Yala") or not math.isfinite(land_size_acres) or not 0 < land_size_acres <= 100:
        raise ValueError("Invalid season or acreage")
    if expected_harvest_date < planting_date or cutoff > planting_date:
        raise ValueError("Decision cutoff must be on or before planting; harvest must be on or after planting")
    if cutoff.year != planting_date.year:
        raise ValueError("This frozen replay supports decision and planting in the same calendar year only; season/year mapping is unverified")
    dataset = load_historical_dataset()
    # Website wording must match the saved pipeline's original crop category.
    # This research alias does not approve generic chilli agronomic guidance.
    model_crop = RESEARCH_CROP_ALIASES.get(crop, crop)
    group = dataset[(dataset.District == district) & (dataset.Crop == model_crop) & (dataset.Season == season)]
    features, peers, prior = historical_features(group, district, model_crop, season, land_size_acres,
                                               planting_date, expected_harvest_date, cutoff)
    pipeline, trained_through = get_model_pipeline(model_name, cutoff.year)
    feature_names = list(pipeline.feature_names_in_)
    df_features = pd.DataFrame([features])[feature_names]
    def label(value):
        if isinstance(value, (int, np.integer)) and 0 <= int(value) < len(LABELS):
            return LABELS[int(value)]
        if str(value) in LABELS:
            return str(value)
        raise ValueError("Unsupported frozen model class encoding")
    classes = [label(value) for value in pipeline.classes_]
    if set(classes) != set(LABELS):
        raise ValueError("Frozen model class contract mismatch")
    # Public replay abstains on sparse peers. The separately authenticated local
    # workbench may test the frozen model with no matching live-style peers when
    # prior historical features are available; this is still only a proxy class.
    eligible = features["Past_Window_Count"] > 0 and (allow_sparse or len(peers) >= 3)
    prediction = None
    if eligible:
        # CatBoost emits (n, 1), while sklearn classifiers emit (n,).
        # Normalize only a single prediction; never reinterpret the class map.
        raw_prediction = np.asarray(pipeline.predict(df_features))
        if raw_prediction.shape not in ((1,), (1, 1)):
            raise ValueError("Unsupported frozen model prediction shape")
        prediction = label(raw_prediction.reshape(-1)[0])
    probabilities = None
    if eligible and hasattr(pipeline, "predict_proba"):
        probabilities = {name: round(float(prob), 4) for name, prob in
                         zip(classes, pipeline.predict_proba(df_features)[0])}
    peer_acres = round(float(peers.Land_Size_Acres.sum()), 2) if len(peers) >= 3 else None
    indicators = concentration_indicators(group, expected_harvest_date, cutoff)
    explanation = (
        f"Retrospective replay selects plans planted strictly before {cutoff.isoformat()}, "
        "not yet expected to be harvested at cutoff, with harvest anchors within inclusive +/-14 days. "
        "This planting predicate is an assumption, not submission/observation evidence. "
        "A later cutoff may add earlier-planted peers or remove completed peers and change historical inputs; "
        "at the same cutoff, changing planting within the same month leaves peer membership unchanged. "
        "Changing planting month changes Planting_Month. The model predicts a rule-derived historical class; "
        "zero known peers means insufficient evidence, never validated Low risk."
    )
    return dict(status="historical_proxy_prediction" if eligible else "insufficient_research_coverage",
        mode="research_demo_simulation", operational_status="risk_level_not_yet_validated",
        simulated_plan=dict(district=district, crop=crop, season=season, land_size_acres=land_size_acres,
            planting_date=planting_date.isoformat(), expected_harvest_date=expected_harvest_date.isoformat(),
            target_year=planting_date.year, decision_cutoff=cutoff.isoformat(),
            cutoff_timestamp=datetime.combine(cutoff, datetime.min.time(), timezone(timedelta(hours=5, minutes=30))).isoformat(),
            cutoff_source="explicit_decision_cutoff" if decision_cutoff else "defaulted_to_planting_date"),
        model_metadata=dict(model_name=model_name, model_crop_category=model_crop, trained_through=trained_through,
            training_data_cutoff=f"{trained_through}-12-31", training_cutoff_basis="recorded dataset Year upper bound; not publication or model release date",
            model_available_at_cutoff="not_verified; frozen artifacts built retrospectively in October 2026",
            simulated_target_year=planting_date.year, is_out_of_time_holdout=planting_date.year > trained_through,
            holdout_caveat="Chronological separation only; 2023/2024 were development folds and 2025/2026 were previously examined",
            benchmark_metrics=BENCHMARKS.get(model_name, {}).get(str(planting_date.year)),
            benchmark_scope="saved historical labels, not current market risk or accuracy for this modified simulation",
            feature_names=feature_names, feature_count=len(feature_names),
            own_production_status="not_supplied; frozen pipeline missing-value handling; no approved yield estimate",
            probability_status="historical class probabilities; calibration and loss-risk interpretation not established"),
        features={k: None if (k == "Overlap_Plan_Count" and 0 < len(peers) < 3) or (isinstance(v, float) and not math.isfinite(v)) else v for k, v in features.items() if k in feature_names},
        prediction=dict(historical_proxy_label=prediction, predicted_risk_level=prediction,
            class_probabilities=probabilities, overlapping_peer_count=len(peers) if len(peers) >= 3 or not len(peers) else None,
            overlapping_peer_acres=peer_acres, total_window_acres=round(peer_acres + land_size_acres, 2) if peer_acres is not None else None,
            is_isolated_plan=not len(peers), coverage_status="replay_coverage_available" if eligible else "sparse_or_zero_replay_coverage",
            peer_explanation=explanation),
        observation_availability=dict(status="no_matching_records" if not len(group) else "unverified" if (observation_availability(group, cutoff) == "unknown").any() else "timestamp_evidence_present",
            replay_unknown_peer_records=int((observation_availability(peers, cutoff) == "unknown").sum()),
            replay_unknown_prior_records=int((observation_availability(prior, cutoff) == "unknown").sum()),
            source_provenance="unverified; ASC designation does not establish individual record authenticity",
            required_evidence="Exact record-version availability timestamp, timezone, source reference and independent attestation; planting/harvest/Year are insufficient"),
        concentration_indicators=indicators,
        scenario_explanation=explanation,
        # Crop ranking with unknown registration coverage/suitability is withheld.
        diagnostic_alternatives=[],
        recommendation_status="blocked_unvalidated_risk",
        governance_notice="RESEARCH PROXY ONLY: unknown observation availability is assumed in the retrospective replay. "
            "No verified current concentration category, market oversupply, price loss, suitability or complete cultivation schedule follows. "
            "Historical High cannot activate farmer recommendations. Verified current High, comparable coverage, suitability and guideline approvals remain required.")
