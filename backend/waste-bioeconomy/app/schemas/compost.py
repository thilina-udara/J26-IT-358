"""
Pydantic Schemas for MILP C:N Compost Ratio Optimization & Bioeconomy Bridging
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks & Waste Management
Student: Lakruwan W.M.K. (IT23330382)
Project: J26-IT-358
"""

from typing import Any

from pydantic import BaseModel, Field


class FeedstockInfo(BaseModel):
    feedstock_id: str
    feedstock_name: str
    category: str
    moisture_pct: float
    c_n_ratio: float
    carbon_pct_dry: float
    nitrogen_pct_dry: float
    phosphorus_pct_dry: float = 0.5
    potassium_pct_dry: float = 1.0
    bulk_density_kg_m3: float
    unit_cost_lkr_kg: float
    lead_ppm: float = 2.0
    cadmium_ppm: float = 0.05
    chromium_ppm: float = 3.0
    arsenic_ppm: float = 0.3
    zinc_ppm: float = 25.0
    ec_ds_m: float = 1.5
    ph_level: float = 7.0


class BlendIngredient(BaseModel):
    feedstock_id: str
    feedstock_name: str
    category: str
    mass_kg: float
    mass_pct: float
    unit_cost_lkr_kg: float = 0.0
    cost_lkr: float


class SLSIComplianceCriteria(BaseModel):
    projected: float
    threshold: str
    passed: bool


class SLSIComplianceAudit(BaseModel):
    standard: str = "SLSI 1246:2003 (Sri Lanka Organic Compost)"
    criteria: dict[str, Any]
    heavy_metals: dict[str, Any] | None = None
    physical_properties: dict[str, Any] | None = None
    overall_certified_compliant: bool


class MatureCompostForecast(BaseModel):
    finished_compost_yield_kg: float
    mass_reduction_pct: float
    finished_organic_carbon_pct: float
    finished_total_nitrogen_pct: float
    finished_phosphorus_p2o5_pct: float
    finished_potassium_k2o_pct: float
    finished_c_n_ratio: float
    finished_lead_ppm: float | None = None
    finished_cadmium_ppm: float | None = None
    finished_chromium_ppm: float | None = None
    finished_arsenic_ppm: float | None = None
    finished_zinc_ppm: float | None = None
    finished_ec_ds_m: float | None = None
    finished_ph: float | None = None


class BiogasDiversionMetrics(BaseModel):
    diversion_trigger_reason: str
    input_wet_mass_kg: float
    volatile_solids_kg: float
    methane_yield_m3: float
    total_biogas_m3: float
    green_electricity_kwh: float
    avoided_ghg_emissions_kg_co2e: float
    byproduct_digestate_fertilizer_kg: float


class CompostOptimizationRequest(BaseModel):
    incoming_waste_name: str = Field(..., examples=["Tomato"], description="Crop/feedstock cull name")
    incoming_waste_kg: float = Field(..., gt=0, examples=[250.0], description="Quantity of cull waste to absorb in kg")
    incoming_moisture_pct: float | None = Field(None, examples=[94.1], description="Moisture % (auto-inferred if omitted)")
    incoming_c_n_ratio: float | None = Field(None, examples=[13.5], description="C:N ratio (auto-inferred if omitted)")
    target_batch_kg: float | None = Field(1000.0, gt=0, examples=[1000.0], description="Target total compost batch mass")
    min_cn: float | None = Field(25.0, examples=[25.0], description="Minimum C:N ratio (SLSI 1246 standard)")
    max_cn: float | None = Field(30.0, examples=[30.0], description="Maximum C:N ratio (SLSI 1246 standard)")
    min_moisture: float | None = Field(55.0, examples=[55.0], description="Minimum initial pile moisture %")
    max_moisture: float | None = Field(65.0, examples=[65.0], description="Maximum initial pile moisture %")
    min_inoculant_pct: float | None = Field(5.0, examples=[5.0], description="Minimum cattle manure inoculant %")
    allow_biogas_fallback: bool | None = Field(True, description="Enable automatic anaerobic diversion for high-moisture slurry")


class CompostOptimizationResponse(BaseModel):
    status: str
    is_feasible: bool
    routing_destination: str
    total_batch_mass_kg: float
    total_batch_cost_lkr: float
    unit_cost_lkr_per_kg: float
    mix_moisture_pct: float
    mix_c_n_ratio: float
    mix_bulk_density_kg_m3: float
    blend_breakdown: list[BlendIngredient]
    finished_compost_forecast: MatureCompostForecast | None = None
    slsi_compliance_audit: SLSIComplianceAudit | None = None
    biogas_metrics: BiogasDiversionMetrics | None = None
    optimization_notes: list[str]


class EndToEndConsignmentResponse(BaseModel):
    consignment_summary: dict[str, Any]
    bioeconomy_solution: CompostOptimizationResponse
