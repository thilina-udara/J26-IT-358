"""
FastAPI Route Handlers for MILP C:N Compost Ratio Optimization & Bioeconomy Bridging
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks & Waste Management
Student: Lakruwan W.M.K. (IT23330382)
Project: J26-IT-358
"""

import os
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, status
from optimization.compost_optimizer import CompostOptimizer, CompostRecipeResult

from app.core.risk_service import CROP_AGRONOMIC_PROFILES, RiskScoringService
from app.schemas.compost import (
    BiogasDiversionMetrics,
    BlendIngredient,
    CompostOptimizationRequest,
    CompostOptimizationResponse,
    EndToEndConsignmentResponse,
    FeedstockInfo,
    MatureCompostForecast,
    SLSIComplianceAudit,
)
from app.schemas.risk import RiskPredictionRequest

router = APIRouter(
    prefix="/api/v1/compost",
    tags=["MILP Compost Optimization & Circular Bioeconomy Networks"]
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FEEDSTOCK_CSV_PATH = os.path.join(BASE_DIR, "data", "standardized_composting_feedstocks.csv")


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or pd.isna(val):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _format_compost_response(recipe: CompostRecipeResult) -> CompostOptimizationResponse:
    """Formats internal CompostRecipeResult dataclass into Pydantic response."""
    blend_ingredients = [
        BlendIngredient(
            feedstock_id=str(item.get("feedstock_id", "")),
            feedstock_name=str(item.get("feedstock_name", "")),
            category=str(item.get("category", "")),
            mass_kg=float(item.get("mass_kg", 0.0)),
            mass_pct=float(item.get("mass_pct", 0.0)),
            unit_cost_lkr_kg=float(item.get("unit_cost_lkr_kg", 0.0)),
            cost_lkr=float(item.get("cost_lkr", 0.0)),
        )
        for item in recipe.blend_breakdown
    ]

    forecast: MatureCompostForecast | None = None
    if recipe.finished_compost_forecast:
        forecast = MatureCompostForecast(
            finished_compost_yield_kg=float(recipe.finished_compost_forecast["finished_compost_yield_kg"]),
            mass_reduction_pct=float(recipe.finished_compost_forecast["mass_reduction_pct"]),
            finished_organic_carbon_pct=float(recipe.finished_compost_forecast["finished_organic_carbon_pct"]),
            finished_total_nitrogen_pct=float(recipe.finished_compost_forecast["finished_total_nitrogen_pct"]),
            finished_phosphorus_p2o5_pct=float(recipe.finished_compost_forecast["finished_phosphorus_p2o5_pct"]),
            finished_potassium_k2o_pct=float(recipe.finished_compost_forecast["finished_potassium_k2o_pct"]),
            finished_c_n_ratio=float(recipe.finished_compost_forecast["finished_c_n_ratio"]),
            finished_lead_ppm=float(recipe.finished_compost_forecast.get("finished_lead_ppm", 0.0)),
            finished_cadmium_ppm=float(recipe.finished_compost_forecast.get("finished_cadmium_ppm", 0.0)),
            finished_chromium_ppm=float(recipe.finished_compost_forecast.get("finished_chromium_ppm", 0.0)),
            finished_arsenic_ppm=float(recipe.finished_compost_forecast.get("finished_arsenic_ppm", 0.0)),
            finished_zinc_ppm=float(recipe.finished_compost_forecast.get("finished_zinc_ppm", 0.0)),
            finished_ec_ds_m=float(recipe.finished_compost_forecast.get("finished_ec_ds_m", 1.5)),
            finished_ph=float(recipe.finished_compost_forecast.get("finished_ph", 7.2)),
        )

    audit: SLSIComplianceAudit | None = None
    if recipe.slsi_compliance_audit:
        audit = SLSIComplianceAudit(
            standard=str(recipe.slsi_compliance_audit.get("standard", "SLSI 1246:2003 (Sri Lanka Organic Compost)")),
            criteria=recipe.slsi_compliance_audit.get("criteria", {}),
            heavy_metals=recipe.slsi_compliance_audit.get("heavy_metals"),
            physical_properties=recipe.slsi_compliance_audit.get("physical_properties"),
            overall_certified_compliant=bool(recipe.slsi_compliance_audit.get("overall_certified_compliant", False)),
        )

    biogas: BiogasDiversionMetrics | None = None
    if recipe.biogas_metrics:
        biogas = BiogasDiversionMetrics(
            diversion_trigger_reason=str(recipe.biogas_metrics.get("diversion_trigger_reason", "")),
            input_wet_mass_kg=float(recipe.biogas_metrics.get("input_wet_mass_kg", 0.0)),
            volatile_solids_kg=float(recipe.biogas_metrics.get("volatile_solids_kg", 0.0)),
            methane_yield_m3=float(recipe.biogas_metrics.get("methane_yield_m3", 0.0)),
            total_biogas_m3=float(recipe.biogas_metrics.get("total_biogas_m3", 0.0)),
            green_electricity_kwh=float(recipe.biogas_metrics.get("green_electricity_kwh", 0.0)),
            avoided_ghg_emissions_kg_co2e=float(recipe.biogas_metrics.get("avoided_ghg_emissions_kg_co2e", 0.0)),
            byproduct_digestate_fertilizer_kg=float(recipe.biogas_metrics.get("byproduct_digestate_fertilizer_kg", 0.0)),
        )

    return CompostOptimizationResponse(
        status=recipe.status,
        is_feasible=recipe.is_feasible,
        routing_destination=recipe.routing_destination,
        total_batch_mass_kg=round(recipe.total_batch_mass_kg, 2),
        total_batch_cost_lkr=round(recipe.total_batch_cost_lkr, 2),
        unit_cost_lkr_per_kg=round(recipe.unit_cost_lkr_per_kg, 2),
        mix_moisture_pct=round(recipe.mix_moisture_pct, 2),
        mix_c_n_ratio=round(recipe.mix_c_n_ratio, 2),
        mix_bulk_density_kg_m3=round(recipe.mix_bulk_density_kg_m3, 2),
        blend_breakdown=blend_ingredients,
        finished_compost_forecast=forecast,
        slsi_compliance_audit=audit,
        biogas_metrics=biogas,
        optimization_notes=recipe.optimization_notes,
    )


@router.post(
    "/optimize-blend",
    response_model=CompostOptimizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute Cost-Optimal Composting Blending Recipe (MILP)",
    description=(
        "Formulates and solves a Mixed-Integer Linear Program in PuLP (with HiGHS/SciPy solvers) "
        "to determine the cost-minimizing combination of carbonaceous bulking agents (paddy straw, sawdust) "
        "and cattle manure inoculant required to absorb incoming agricultural cull waste while strictly satisfying "
        "SLSI 1246:2003 C:N (25-30:1) and moisture (55-65%) standards. Includes automated anaerobic biogas fallback."
    ),
)
def optimize_compost_blend(request: CompostOptimizationRequest) -> CompostOptimizationResponse:
    try:
        # Infer agronomic moisture and C:N if omitted
        moisture = request.incoming_moisture_pct
        cn = request.incoming_c_n_ratio

        if moisture is None or cn is None:
            crop_key = "Tomato"
            for k in CROP_AGRONOMIC_PROFILES:
                if k.lower() in request.incoming_waste_name.lower():
                    crop_key = k
                    break
            profile = CROP_AGRONOMIC_PROFILES[crop_key]
            if moisture is None:
                moisture = float(profile["moisture_pct"])
            if cn is None:
                cn = float(profile["c_n_ratio"])

        optimizer = CompostOptimizer()
        recipe = optimizer.optimize_blend(
            incoming_waste_name=request.incoming_waste_name,
            incoming_waste_kg=request.incoming_waste_kg,
            incoming_moisture_pct=moisture,
            incoming_c_n_ratio=cn,
            target_batch_kg=request.target_batch_kg or 1000.0,
            min_cn=request.min_cn or 25.0,
            max_cn=request.max_cn or 30.0,
            min_moisture=request.min_moisture or 55.0,
            max_moisture=request.max_moisture or 65.0,
            min_inoculant_pct=request.min_inoculant_pct or 5.0,
            allow_biogas_fallback=request.allow_biogas_fallback if request.allow_biogas_fallback is not None else True,
        )

        return _format_compost_response(recipe)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing compost optimization MILP: {exc!s}"
        ) from exc


@router.post(
    "/end-to-end",
    response_model=EndToEndConsignmentResponse,
    status_code=status.HTTP_200_OK,
    summary="End-to-End In-Transit Risk Scoring & Automated Bioeconomy Recipe Bridging",
    description=(
        "Unified operational dispatch endpoint: Ingests pre-arrival truck telemetry, calculates XGBoost "
        "post-harvest spoilage loss %, partitions payload into commercial produce (Stream 1) and cull waste (Stream 2), "
        "and automatically solves the MILP recipe for 100% circular absorption of the cull waste."
    ),
)
def process_end_to_end_consignment(request: RiskPredictionRequest) -> EndToEndConsignmentResponse:
    try:
        risk_service = RiskScoringService.get_instance()
        risk_res = risk_service.predict_risk(request)

        # Look up crop profile for C:N and moisture
        crop_name = risk_res.crop_name
        profile = CROP_AGRONOMIC_PROFILES.get(crop_name, CROP_AGRONOMIC_PROFILES["Tomato"])
        cull_waste_kg = risk_res.stream_2_bioeconomy_feedstock_kg

        optimizer = CompostOptimizer()
        # Scale target batch to absorb cull waste while maintaining typical 25-40% waste fraction
        calc_batch_kg = max(500.0, cull_waste_kg * 3.0)

        recipe = optimizer.optimize_blend(
            incoming_waste_name=crop_name,
            incoming_waste_kg=cull_waste_kg,
            incoming_moisture_pct=float(profile["moisture_pct"]),
            incoming_c_n_ratio=float(profile["c_n_ratio"]),
            target_batch_kg=calc_batch_kg,
        )

        consignment_summary = {
            "crop_name": risk_res.crop_name,
            "total_payload_kg": risk_res.total_payload_kg,
            "predicted_spoilage_loss_pct": risk_res.predicted_spoilage_loss_pct,
            "risk_tier": risk_res.risk_tier,
            "stream_1_fresh_produce_kg": risk_res.stream_1_fresh_produce_kg,
            "stream_1_fresh_pct": risk_res.stream_1_fresh_pct,
            "stream_1_recommended_channel": risk_res.stream_1_recommended_channel,
            "stream_2_bioeconomy_feedstock_kg": risk_res.stream_2_bioeconomy_feedstock_kg,
            "stream_2_waste_pct": risk_res.stream_2_waste_pct,
            "stream_2_destination": risk_res.stream_2_destination,
            "stress_indices": risk_res.stress_indices.model_dump(),
        }

        return EndToEndConsignmentResponse(
            consignment_summary=consignment_summary,
            bioeconomy_solution=_format_compost_response(recipe),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing end-to-end consignment workflow: {exc!s}"
        ) from exc


@router.get(
    "/feedstocks",
    response_model=list[FeedstockInfo],
    status_code=status.HTTP_200_OK,
    summary="List Standardized Composting Feedstocks & Biochemical Nutrients",
    description="Returns available carbonaceous, nitrogenous, and microbial inoculant feedstocks with moisture, C:N, and procurement cost.",
)
def list_available_feedstocks() -> list[FeedstockInfo]:
    try:
        if not os.path.exists(FEEDSTOCK_CSV_PATH):
            raise FileNotFoundError(f"Feedstock file missing at: {FEEDSTOCK_CSV_PATH}")

        df = pd.read_csv(FEEDSTOCK_CSV_PATH)
        feedstocks: list[FeedstockInfo] = []
        for _, row in df.iterrows():
            feedstocks.append(FeedstockInfo(
                feedstock_id=str(row["feedstock_id"]),
                feedstock_name=str(row["feedstock_name"]),
                category=str(row["feedstock_category_canonical"]),
                moisture_pct=_safe_float(row["moisture_pct"]),
                c_n_ratio=_safe_float(row["c_n_ratio"]),
                carbon_pct_dry=_safe_float(row["carbon_pct_dry"]),
                nitrogen_pct_dry=_safe_float(row["nitrogen_pct_dry"]),
                phosphorus_pct_dry=_safe_float(row.get("phosphorus_pct_dry"), 0.5),
                potassium_pct_dry=_safe_float(row.get("potassium_pct_dry"), 1.0),
                bulk_density_kg_m3=_safe_float(row["bulk_density_kg_m3"]),
                unit_cost_lkr_kg=_safe_float(row["unit_procurement_cost_lkr_kg"]),
                lead_ppm=_safe_float(row.get("lead_ppm"), 2.0),
                cadmium_ppm=_safe_float(row.get("cadmium_ppm"), 0.05),
                chromium_ppm=_safe_float(row.get("chromium_ppm"), 3.0),
                arsenic_ppm=_safe_float(row.get("arsenic_ppm"), 0.3),
                zinc_ppm=_safe_float(row.get("zinc_ppm"), 25.0),
                ec_ds_m=_safe_float(row.get("ec_ds_m"), 1.5),
                ph_level=_safe_float(row.get("ph_level"), 7.0),
            ))
        return feedstocks
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading feedstock catalogue: {exc!s}"
        ) from exc
