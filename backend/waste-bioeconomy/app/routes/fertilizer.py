"""
FastAPI Route Handlers for Fertilizer Management, NPK Demand Matching & Regional Logistics
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks & Waste Management
Student: Lakruwan W.M.K. (IT23330382)
Project: J26-IT-358
Supervised by: Prof. Dasuni Nawinna
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from optimization.distribution_router import (
    REGIONAL_HUBS,
    DistributionRouter,
    RegionalLogisticsPlan,
)
from optimization.nutrient_matcher import (
    DEFAULT_FARMER_CLUSTERS,
    AvailableFertilizerSupply,
    CultivationPlotDemand,
    FertilizerCategory,
    GrowthStage,
    NutrientDemandMatcher,
    RegionalMatchingSummary,
)

from app.schemas.fertilizer import (
    DeliveryWaypointSchema,
    DispatchOptimizationRequest,
    DispatchOptimizationResponse,
    FarmAllocationResponse,
    NutrientMatchRequest,
    NutrientMatchResponse,
    VehicleDispatchManifestSchema,
)

router = APIRouter(
    prefix="/api/v1/fertilizer",
    tags=["Fertilizer Management & Regional Circular Logistics"]
)


def _build_default_demands(hub_id: str) -> list[CultivationPlotDemand]:
    """Generates standard regional farmer cultivation demands if omitted."""
    if "NEGAMA" in hub_id.upper() or "ANU" in hub_id.upper():
        return [
            CultivationPlotDemand(
                farmer_id="FARM-ANU-01",
                farmer_name="Priyanta Dissanayake",
                cluster_id="CL-ANU-01",
                cluster_name="Negama Agrarian Center Core Cluster",
                crop_name="Big Onion",
                acreage_ha=1.2,
                growth_stage=GrowthStage.BASAL_LAND_PREP,
                latitude=8.1350,
                longitude=80.3980,
                soil_organic_matter_pct=0.95,
            ),
            CultivationPlotDemand(
                farmer_id="FARM-ANU-02",
                farmer_name="Chandana Senanayake",
                cluster_id="CL-ANU-02",
                cluster_name="Eppawala Commercial Field Crop Cluster",
                crop_name="Maize",
                acreage_ha=2.0,
                growth_stage=GrowthStage.VEGETATIVE_GROWTH,
                latitude=8.1450,
                longitude=80.4120,
                soil_organic_matter_pct=1.20,
            ),
            CultivationPlotDemand(
                farmer_id="FARM-ANU-03",
                farmer_name="Nihal Jayasinghe",
                cluster_id="CL-ANU-03",
                cluster_name="Kekirawa Onion & Grain Cluster",
                crop_name="Chilli",
                acreage_ha=0.8,
                growth_stage=GrowthStage.FLOWERING_FRUIT_SET,
                latitude=8.0420,
                longitude=80.5960,
                soil_organic_matter_pct=1.05,
            ),
        ]

    # Default: Dambulla Hub
    return [
        CultivationPlotDemand(
            farmer_id="FARM-DAM-01",
            farmer_name="Sunil Bandara",
            cluster_id="CL-DAM-01",
            cluster_name="Kandalama North Cluster",
            crop_name="Tomato",
            acreage_ha=1.5,
            growth_stage=GrowthStage.BASAL_LAND_PREP,
            latitude=7.8540,
            longitude=80.7020,
            soil_organic_matter_pct=1.15,
        ),
        CultivationPlotDemand(
            farmer_id="FARM-DAM-02",
            farmer_name="Anura Kumara Jayalath",
            cluster_id="CL-DAM-02",
            cluster_name="Galewela Mixed Vegetable Cluster",
            crop_name="Brinjal",
            acreage_ha=1.0,
            growth_stage=GrowthStage.VEGETATIVE_GROWTH,
            latitude=7.7560,
            longitude=80.5720,
            soil_organic_matter_pct=1.30,
        ),
        CultivationPlotDemand(
            farmer_id="FARM-DAM-03",
            farmer_name="Gamini Wickramasinghe",
            cluster_id="CL-DAM-03",
            cluster_name="Sigiriya - Inamaluwa Agro-Forestry Cluster",
            crop_name="Tomato",
            acreage_ha=1.2,
            growth_stage=GrowthStage.FLOWERING_FRUIT_SET,
            latitude=7.9540,
            longitude=80.7280,
            soil_organic_matter_pct=1.45,
        ),
    ]


def _build_default_supplies(hub_id: str) -> list[AvailableFertilizerSupply]:
    """Generates standard hub inventory if omitted."""
    return [
        AvailableFertilizerSupply(
            supply_id=f"SUP-{hub_id[-4:]}-01",
            hub_id=hub_id,
            fertilizer_category=FertilizerCategory.SOLID_ORGANIC_COMPOST,
            available_mass_kg=6000.0,
            n_pct=2.1,
            p2o5_pct=1.05,
            k2o_pct=1.85,
            organic_carbon_pct=24.5,
            c_n_ratio=14.8,
            unit_sale_price_lkr_kg=18.0,
        ),
        AvailableFertilizerSupply(
            supply_id=f"SUP-{hub_id[-4:]}-02",
            hub_id=hub_id,
            fertilizer_category=FertilizerCategory.LIQUID_DIGESTATE_SLURRY,
            available_mass_kg=2500.0,
            n_pct=3.8,
            p2o5_pct=0.9,
            k2o_pct=1.4,
            organic_carbon_pct=18.0,
            c_n_ratio=9.5,
            unit_sale_price_lkr_kg=12.0,
        ),
    ]


def _format_matching_response(summary: RegionalMatchingSummary) -> NutrientMatchResponse:
    return NutrientMatchResponse(
        hub_id=summary.hub_id,
        total_farms_served=summary.total_farms_served,
        total_acreage_covered_ha=summary.total_acreage_covered_ha,
        total_solid_compost_allocated_kg=summary.total_solid_compost_allocated_kg,
        total_liquid_digestate_allocated_kg=summary.total_liquid_digestate_allocated_kg,
        total_urea_displaced_kg=summary.total_urea_displaced_kg,
        total_tsp_displaced_kg=summary.total_tsp_displaced_kg,
        total_mop_displaced_kg=summary.total_mop_displaced_kg,
        total_foreign_exchange_savings_lkr=summary.total_foreign_exchange_savings_lkr,
        allocations=[
            FarmAllocationResponse(
                farmer_id=a.farmer_id,
                farmer_name=a.farmer_name,
                cluster_id=a.cluster_id,
                cluster_name=a.cluster_name,
                crop_name=a.crop_name,
                acreage_ha=a.acreage_ha,
                growth_stage=a.growth_stage,
                allocated_fertilizer_category=a.allocated_fertilizer_category,
                allocated_mass_kg=a.allocated_mass_kg,
                nutrient_supplied_n_kg=a.nutrient_supplied_n_kg,
                nutrient_supplied_p2o5_kg=a.nutrient_supplied_p2o5_kg,
                nutrient_supplied_k2o_kg=a.nutrient_supplied_k2o_kg,
                target_demand_n_kg=a.target_demand_n_kg,
                target_demand_p2o5_kg=a.target_demand_p2o5_kg,
                target_demand_k2o_kg=a.target_demand_k2o_kg,
                nitrogen_fulfillment_pct=a.nitrogen_fulfillment_pct,
                phosphorus_fulfillment_pct=a.phosphorus_fulfillment_pct,
                potassium_fulfillment_pct=a.potassium_fulfillment_pct,
                urea_displaced_kg=a.urea_displaced_kg,
                tsp_displaced_kg=a.tsp_displaced_kg,
                mop_displaced_kg=a.mop_displaced_kg,
                chemical_fertilizer_cost_saved_lkr=a.chemical_fertilizer_cost_saved_lkr,
                organic_fertilizer_cost_lkr=a.organic_fertilizer_cost_lkr,
                net_economic_benefit_lkr=a.net_economic_benefit_lkr,
                agronomic_rationale=a.agronomic_rationale,
                mismatch_warning=a.mismatch_warning,
            )
            for a in summary.allocations
        ],
        agronomic_compliance_notes=summary.agronomic_compliance_notes,
    )


def _format_dispatch_response(plan: RegionalLogisticsPlan) -> DispatchOptimizationResponse:
    manifest_schemas: list[VehicleDispatchManifestSchema] = []
    for m in plan.manifests:
        waypoints = [
            DeliveryWaypointSchema(
                stop_number=w.stop_number,
                farmer_id=w.farmer_id,
                farmer_name=w.farmer_name,
                cluster_name=w.cluster_name,
                latitude=w.latitude,
                longitude=w.longitude,
                dropoff_fertilizer_category=w.dropoff_fertilizer_category,
                dropoff_mass_kg=w.dropoff_mass_kg,
                distance_from_prev_stop_km=w.distance_from_prev_stop_km,
                cumulative_distance_km=w.cumulative_distance_km,
                estimated_arrival_minutes=w.estimated_arrival_minutes,
            )
            for w in m.waypoints
        ]
        manifest_schemas.append(VehicleDispatchManifestSchema(
            manifest_id=m.manifest_id,
            vehicle_type=m.vehicle_type,
            vehicle_name=m.vehicle_name,
            capacity_kg=m.capacity_kg,
            assigned_payload_kg=m.assigned_payload_kg,
            capacity_utilization_pct=m.capacity_utilization_pct,
            origin_hub_name=m.origin_hub_name,
            origin_latitude=m.origin_latitude,
            origin_longitude=m.origin_longitude,
            total_transit_distance_km=m.total_transit_distance_km,
            total_transit_hours=m.total_transit_hours,
            diesel_consumed_liters=m.diesel_consumed_liters,
            fuel_cost_lkr=m.fuel_cost_lkr,
            crew_labor_cost_lkr=m.crew_labor_cost_lkr,
            fixed_dispatch_cost_lkr=m.fixed_dispatch_cost_lkr,
            total_trip_cost_lkr=m.total_trip_cost_lkr,
            unit_delivery_cost_lkr_kg=m.unit_delivery_cost_lkr_kg,
            transport_ghg_emissions_kg_co2e=m.transport_ghg_emissions_kg_co2e,
            waypoints=waypoints,
        ))

    return DispatchOptimizationResponse(
        plan_id=plan.plan_id,
        origin_hub_id=plan.origin_hub_id,
        origin_hub_name=plan.origin_hub_name,
        total_fertilizer_dispatched_kg=plan.total_fertilizer_dispatched_kg,
        total_distance_covered_km=plan.total_distance_covered_km,
        total_diesel_liters=plan.total_diesel_liters,
        total_logistics_cost_lkr=plan.total_logistics_cost_lkr,
        average_unit_cost_lkr_kg=plan.average_unit_cost_lkr_kg,
        total_ghg_emissions_kg_co2e=plan.total_ghg_emissions_kg_co2e,
        active_vehicles_count=plan.active_vehicles_count,
        manifests=manifest_schemas,
        logistics_notes=plan.logistics_notes,
    )


@router.post(
    "/match-demand",
    response_model=NutrientMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Match Organic Fertilizer Supplies to Regional Farmer NPK Demands",
    description=(
        "Cross-references mature solid organic compost & liquid anaerobic digestate against active "
        "cultivation plans from Component 2. Enforces Department of Agriculture (DoA) growth-stage rules: "
        "mandates solid compost for basal land prep, allows liquid digestate for vegetative growth, "
        "and strictly blocks high-N digestate during flowering/fruit setting."
    ),
)
def match_nutrient_demand(request: NutrientMatchRequest) -> NutrientMatchResponse:
    try:
        # Supplies
        if request.supplies:
            supplies = [
                AvailableFertilizerSupply(
                    supply_id=s.supply_id,
                    hub_id=s.hub_id,
                    fertilizer_category=FertilizerCategory(s.fertilizer_category),
                    available_mass_kg=s.available_mass_kg,
                    n_pct=s.n_pct,
                    p2o5_pct=s.p2o5_pct,
                    k2o_pct=s.k2o_pct,
                    organic_carbon_pct=s.organic_carbon_pct,
                    c_n_ratio=s.c_n_ratio,
                    unit_sale_price_lkr_kg=s.unit_sale_price_lkr_kg,
                )
                for s in request.supplies
            ]
        else:
            supplies = _build_default_supplies(request.hub_id)

        # Demands
        if request.demands:
            demands = [
                CultivationPlotDemand(
                    farmer_id=d.farmer_id,
                    farmer_name=d.farmer_name,
                    cluster_id=d.cluster_id,
                    cluster_name=d.cluster_name,
                    crop_name=d.crop_name,
                    acreage_ha=d.acreage_ha,
                    growth_stage=GrowthStage(d.growth_stage),
                    latitude=d.latitude,
                    longitude=d.longitude,
                    soil_organic_matter_pct=d.soil_organic_matter_pct or 1.2,
                    soil_ph=d.soil_ph or 6.8,
                )
                for d in request.demands
            ]
        else:
            demands = _build_default_demands(request.hub_id)

        matcher = NutrientDemandMatcher()
        summary = matcher.match_demands(supplies=supplies, demands=demands)
        return _format_matching_response(summary)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error matching nutrient demands: {exc!s}"
        ) from exc


@router.post(
    "/optimize-dispatch",
    response_model=DispatchOptimizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Solve Capacitated Vehicle Routing (CVRP) for Fertilizer Distribution",
    description=(
        "Computes optimal vehicle routing trajectories from regional hubs (Dambulla or Negama) "
        "to rural farmer clusters using a 2-Opt local search heuristic. Calculates diesel fuel consumption "
        "(@ LKR 350/L), turnaround time, unit transport cost (LKR/kg), and Scope 1 transport GHG emissions."
    ),
)
def optimize_distribution_dispatch(request: DispatchOptimizationRequest) -> DispatchOptimizationResponse:
    try:
        router_engine = DistributionRouter()

        if request.orders:
            orders = request.orders
        else:
            # Auto-generate orders from default matching
            demands = _build_default_demands(request.hub_id)
            supplies = _build_default_supplies(request.hub_id)
            matcher = NutrientDemandMatcher()
            summary = matcher.match_demands(supplies, demands)
            orders = [
                {
                    "farmer_id": a.farmer_id,
                    "farmer_name": a.farmer_name,
                    "cluster_name": a.cluster_name,
                    "latitude": d.latitude,
                    "longitude": d.longitude,
                    "fertilizer_category": a.allocated_fertilizer_category,
                    "dropoff_mass_kg": a.allocated_mass_kg,
                }
                for a, d in zip(summary.allocations, demands, strict=False)
            ]

        plan = router_engine.solve_dispatch_plan(
            hub_id=request.hub_id,
            orders=orders,
            preferred_vehicle_type=request.preferred_vehicle_type,
        )
        return _format_dispatch_response(plan)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error solving logistics dispatch routing: {exc!s}"
        ) from exc


@router.post(
    "/end-to-end-redistribution",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Closed-Loop Demand Matching & Delivery Dispatch Manifest Generation",
    description="Connects nutrient matching directly with distribution vehicle manifests in a single call.",
)
def end_to_end_redistribution(request: NutrientMatchRequest) -> dict[str, Any]:
    try:
        # 1. Match Demands
        match_res = match_nutrient_demand(request)

        # 2. Build Delivery Orders
        demands = request.demands or _build_default_demands(request.hub_id)
        orders = []
        for alloc in match_res.allocations:
            # Match with coordinates
            matching_plot = next((d for d in demands if d.farmer_id == alloc.farmer_id), None)
            lat = matching_plot.latitude if matching_plot else 7.8540
            lon = matching_plot.longitude if matching_plot else 80.7020
            orders.append({
                "farmer_id": alloc.farmer_id,
                "farmer_name": alloc.farmer_name,
                "cluster_name": alloc.cluster_name,
                "latitude": lat,
                "longitude": lon,
                "fertilizer_category": alloc.allocated_fertilizer_category,
                "dropoff_mass_kg": alloc.allocated_mass_kg,
            })

        # 3. Solve Logistics Plan
        router_engine = DistributionRouter()
        logistics_plan = router_engine.solve_dispatch_plan(hub_id=request.hub_id, orders=orders)
        dispatch_res = _format_dispatch_response(logistics_plan)

        return {
            "status": "CIRCULAR_REDISTRIBUTION_SOLVED",
            "hub_id": request.hub_id,
            "nutrient_demand_matching": match_res.model_dump(),
            "logistics_dispatch_plan": dispatch_res.model_dump(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing end-to-end redistribution: {exc!s}"
        ) from exc


@router.get(
    "/clusters",
    response_model=list[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Pre-Registered Regional Farmer Clusters & Soil Profiles",
    description="Returns verified farming clusters across Dambulla and Anuradhapura with soil type, baseline OM %, and GPS coordinates.",
)
def get_regional_clusters() -> list[dict[str, Any]]:
    return DEFAULT_FARMER_CLUSTERS


@router.get(
    "/hubs",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="List Regional Bioeconomy Hub Locations",
    description="Returns regional processing and distribution hubs (Dambulla Dedicated Economic Centre and Negama Agrarian Service Centre).",
)
def get_regional_hubs() -> dict[str, Any]:
    return REGIONAL_HUBS


@router.get(
    "/growth-stages",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="List Department of Agriculture Growth Stages & Allocation Rules",
    description="Explains DoA agronomic growth-stage safety rules for solid compost and liquid digestate.",
)
def get_growth_stage_rules() -> dict[str, Any]:
    return {
        "BASAL_LAND_PREP": {
            "allowed_fertilizer": "SOLID_ORGANIC_COMPOST",
            "blocked_fertilizer": "LIQUID_DIGESTATE_SLURRY",
            "agronomic_reason": "Solid compost elevates soil organic matter and restores soil physical structure before planting.",
        },
        "VEGETATIVE_GROWTH": {
            "allowed_fertilizer": "LIQUID_DIGESTATE_SLURRY / SOLID_ORGANIC_COMPOST",
            "preferred_fertilizer": "LIQUID_DIGESTATE_SLURRY",
            "agronomic_reason": "High soluble ammonium N in liquid digestate promotes rapid vegetative canopy development.",
        },
        "FLOWERING_FRUIT_SET": {
            "allowed_fertilizer": "SOLID_ORGANIC_COMPOST",
            "blocked_fertilizer": "LIQUID_DIGESTATE_SLURRY",
            "agronomic_reason": "CRITICAL FILTER: Excess vegetative nitrogen during flowering induces flower abortion and rot. Potassium is prioritized.",
        },
        "MATURITY_HARVEST": {
            "allowed_fertilizer": "SOLID_ORGANIC_COMPOST (Low dosage)",
            "blocked_fertilizer": "LIQUID_DIGESTATE_SLURRY",
            "agronomic_reason": "Maintains residual microbial soil health without delaying maturity.",
        },
    }
