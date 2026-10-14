"""Public research boundary: no publication permission, no private-data access.

No HTTP route may serialize the internal evaluator's output. This allowlist
releases caller inputs and previously reported frozen benchmark metadata only.
Neither enabling the demo nor authenticating establishes publication permission.
No runtime flag or HTTP field can promote the private source to public data.
"""
from datetime import datetime, timedelta, timezone
from app.schemas.research_demo import HistoricalScenarioRequest, HistoricalScenarioResponse
from app.services.research_metadata import BENCHMARKS, FEATURES

DISCLOSURE = "collective_values_withheld"
EXPLANATION = (
    "Cutoff and planting are separate scenario inputs. Earlier planting does not prove observation availability. "
    "Historical publication permissions are not established. Peer statistics, derived features, coverage, "
    "model classes and probabilities are withheld for all cohorts, including zero and singleton groups. "
    "Changing dates or acreage cannot authorize disclosure. No public historical inference is performed."
)


def public_scenario(payload: HistoricalScenarioRequest) -> HistoricalScenarioResponse:
    """Population-independent response; never opens historical CSV/model files.

    The offline internal evaluator still computes the frozen retrospective proxy
    for authorized private research. Its output is deliberately not an argument
    to this serializer, preventing new derived fields or exports from leaking.
    """
    cutoff = payload.decision_cutoff or payload.planting_date
    names = FEATURES if payload.model_name in ("XGBoost", "CatBoost") else FEATURES[:11]
    own = dict(District=payload.district, Crop=payload.crop, Season=payload.season,
               Land_Size_Acres=payload.land_size_acres, Planting_Month=payload.planting_date.month,
               Harvest_Month=payload.expected_harvest_date.month)
    metadata = dict(model_name=payload.model_name, trained_through=2024, training_data_cutoff="2024-12-31",
        training_cutoff_basis="recorded dataset Year upper bound; not publication or model release date",
        model_available_at_cutoff="not_verified; frozen artifacts built retrospectively in October 2026",
        simulated_target_year=payload.planting_date.year, is_out_of_time_holdout=False,
        holdout_caveat="No public inference or untouched holdout claim; statistical-season/year mapping is unverified",
        benchmark_metrics=BENCHMARKS[payload.model_name].get(str(payload.planting_date.year)),
        benchmark_scope="Previously reported frozen historical metrics only; not accuracy for this scenario or current risk",
        feature_names=names, feature_count=len(names),
        own_production_status="not_supplied; no approved yield estimate",
        probability_status="withheld; private-input inference could disclose historical membership")
    return HistoricalScenarioResponse(
        status="historical_result_withheld", mode="research_demo_simulation",
        operational_status="risk_level_not_yet_validated", disclosure_status=DISCLOSURE,
        reason_codes=["historical_publication_permission_unverified", "collective_values_protected", "historical_proxy_withheld"],
        simulated_plan=dict(district=payload.district, crop=payload.crop, season=payload.season,
            land_size_acres=payload.land_size_acres, planting_date=payload.planting_date.isoformat(),
            expected_harvest_date=payload.expected_harvest_date.isoformat(), target_year=payload.planting_date.year,
            decision_cutoff=cutoff.isoformat(), cutoff_timestamp=datetime.combine(cutoff, datetime.min.time(),
                timezone(timedelta(hours=5, minutes=30))).isoformat(),
            cutoff_source="explicit_decision_cutoff" if payload.decision_cutoff else "defaulted_to_planting_date"),
        model_metadata=metadata, features={name: own.get(name) for name in names},
        prediction=dict(coverage_status=DISCLOSURE, peer_explanation=EXPLANATION),
        observation_availability=dict(status="not_established",
            source_provenance="unverified; historical status does not establish public publication permission",
            required_evidence="Exact-version availability, source verification and an independently reviewed publication/disclosure policy"),
        concentration_indicators=dict(harvest_window_start=(payload.expected_harvest_date-timedelta(days=14)).isoformat(),
            harvest_window_end=(payload.expected_harvest_date+timedelta(days=14)).isoformat(),
            matching_scope="same district/crop/declared season; region unavailable",
            historical_dataset_window=dict(disclosure_status=DISCLOSURE),
            provably_available_window=dict(disclosure_status=DISCLOSURE), availability_status="not_disclosed",
            interpretation="Protected values do not imply zero, absence of peers, or Low risk"),
        scenario_explanation=EXPLANATION, recommendation_status="blocked_unvalidated_risk",
        governance_notice="RESEARCH INPUTS ONLY: historical outputs are withheld pending publication/disclosure approval. "
            "Unknown observation availability cannot establish zero temporal leakage. A historical proxy cannot validate current "
            "oversupply, price loss, crop suitability or an agricultural schedule. Independent approvals remain required.")
