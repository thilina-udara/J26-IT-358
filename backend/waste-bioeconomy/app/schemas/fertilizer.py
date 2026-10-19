"""
Pydantic Schemas for Fertilizer Management, NPK Demand Matching & Regional Logistics
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks & Waste Management
Student: Lakruwan W.M.K. (IT23330382)
Project: J26-IT-358
"""

from typing import Any

from pydantic import BaseModel, Field


class FarmerPlotDemandSchema(BaseModel):
    farmer_id: str = Field(..., examples=["FARM-DAM-01"])
    farmer_name: str = Field(..., examples=["Sunil Bandara"])
    cluster_id: str = Field(..., examples=["CL-DAM-01"])
    cluster_name: str = Field(..., examples=["Kandalama North Cluster"])
    crop_name: str = Field(..., examples=["Tomato"])
    acreage_ha: float = Field(..., gt=0, examples=[1.5])
    growth_stage: str = Field(
        ...,
        examples=["BASAL_LAND_PREP"],
        description="Growth stage: BASAL_LAND_PREP, VEGETATIVE_GROWTH, FLOWERING_FRUIT_SET, MATURITY_HARVEST"
    )
    latitude: float = Field(..., examples=[7.8540])
    longitude: float = Field(..., examples=[80.7020])
    soil_organic_matter_pct: float | None = Field(1.2, examples=[1.15])
    soil_ph: float | None = Field(6.8, examples=[6.8])


class FertilizerSupplySchema(BaseModel):
    supply_id: str = Field(..., examples=["SUP-DAM-01"])
    hub_id: str = Field(..., examples=["HUB-DAMBULLA"])
    fertilizer_category: str = Field(
        ...,
        examples=["SOLID_ORGANIC_COMPOST"],
        description="SOLID_ORGANIC_COMPOST or LIQUID_DIGESTATE_SLURRY"
    )
    available_mass_kg: float = Field(..., gt=0, examples=[5000.0])
    n_pct: float = Field(2.0, examples=[2.0])
    p2o5_pct: float = Field(1.0, examples=[1.0])
    k2o_pct: float = Field(1.8, examples=[1.8])
    organic_carbon_pct: float = Field(22.0, examples=[22.0])
    c_n_ratio: float = Field(15.0, examples=[15.0])
    unit_sale_price_lkr_kg: float = Field(18.0, examples=[18.0])


class NutrientMatchRequest(BaseModel):
    hub_id: str = Field("HUB-DAMBULLA", examples=["HUB-DAMBULLA"])
    supplies: list[FertilizerSupplySchema] | None = None
    demands: list[FarmerPlotDemandSchema] | None = None


class FarmAllocationResponse(BaseModel):
    farmer_id: str
    farmer_name: str
    cluster_id: str
    cluster_name: str
    crop_name: str
    acreage_ha: float
    growth_stage: str
    allocated_fertilizer_category: str
    allocated_mass_kg: float
    nutrient_supplied_n_kg: float
    nutrient_supplied_p2o5_kg: float
    nutrient_supplied_k2o_kg: float
    target_demand_n_kg: float
    target_demand_p2o5_kg: float
    target_demand_k2o_kg: float
    nitrogen_fulfillment_pct: float
    phosphorus_fulfillment_pct: float
    potassium_fulfillment_pct: float
    urea_displaced_kg: float
    tsp_displaced_kg: float
    mop_displaced_kg: float
    chemical_fertilizer_cost_saved_lkr: float
    organic_fertilizer_cost_lkr: float
    net_economic_benefit_lkr: float
    agronomic_rationale: str
    mismatch_warning: str | None = None


class NutrientMatchResponse(BaseModel):
    hub_id: str
    total_farms_served: int
    total_acreage_covered_ha: float
    total_solid_compost_allocated_kg: float
    total_liquid_digestate_allocated_kg: float
    total_urea_displaced_kg: float
    total_tsp_displaced_kg: float
    total_mop_displaced_kg: float
    total_foreign_exchange_savings_lkr: float
    allocations: list[FarmAllocationResponse]
    agronomic_compliance_notes: list[str]


class DeliveryWaypointSchema(BaseModel):
    stop_number: int
    farmer_id: str
    farmer_name: str
    cluster_name: str
    latitude: float
    longitude: float
    dropoff_fertilizer_category: str
    dropoff_mass_kg: float
    distance_from_prev_stop_km: float
    cumulative_distance_km: float
    estimated_arrival_minutes: float


class VehicleDispatchManifestSchema(BaseModel):
    manifest_id: str
    vehicle_type: str
    vehicle_name: str
    capacity_kg: float
    assigned_payload_kg: float
    capacity_utilization_pct: float
    origin_hub_name: str
    origin_latitude: float
    origin_longitude: float
    total_transit_distance_km: float
    total_transit_hours: float
    diesel_consumed_liters: float
    fuel_cost_lkr: float
    crew_labor_cost_lkr: float
    fixed_dispatch_cost_lkr: float
    total_trip_cost_lkr: float
    unit_delivery_cost_lkr_kg: float
    transport_ghg_emissions_kg_co2e: float
    waypoints: list[DeliveryWaypointSchema]


class DispatchOptimizationRequest(BaseModel):
    hub_id: str = Field("HUB-DAMBULLA", examples=["HUB-DAMBULLA"])
    orders: list[dict[str, Any]] | None = None
    preferred_vehicle_type: str | None = Field(None, examples=["MEDIUM_TRUCK"])


class DispatchOptimizationResponse(BaseModel):
    plan_id: str
    origin_hub_id: str
    origin_hub_name: str
    total_fertilizer_dispatched_kg: float
    total_distance_covered_km: float
    total_diesel_liters: float
    total_logistics_cost_lkr: float
    average_unit_cost_lkr_kg: float
    total_ghg_emissions_kg_co2e: float
    active_vehicles_count: int
    manifests: list[VehicleDispatchManifestSchema]
    logistics_notes: list[str]
