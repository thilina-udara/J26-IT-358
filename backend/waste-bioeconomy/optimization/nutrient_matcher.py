"""
Nutrient Demand Matching & Agronomic Growth-Stage Allocation Engine

Features:
1. Cross-references mature solid organic compost & liquid digestate with Component 2 cultivation plans.
2. Enforces Sri Lanka Department of Agriculture (DoA) growth-stage rules:
   - Basal Land Preparation: Solid organic compost allocated for soil organic carbon restoration.
   - Vegetative Growth: Liquid digestate slurry prioritized for rapid soluble nitrogen bioavailability.
   - Flowering & Fruit Setting: Strict Mismatch Filter blocks high-N digestate (prevents flower abortion/rot).
3. Computes synthetic fertilizer displacement (Urea, Triple Superphosphate - TSP, Muriate of Potash - MOP).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GrowthStage(str, Enum):
    BASAL_LAND_PREP = "BASAL_LAND_PREP"
    VEGETATIVE_GROWTH = "VEGETATIVE_GROWTH"
    FLOWERING_FRUIT_SET = "FLOWERING_FRUIT_SET"
    MATURITY_HARVEST = "MATURITY_HARVEST"


class FertilizerCategory(str, Enum):
    SOLID_ORGANIC_COMPOST = "SOLID_ORGANIC_COMPOST"
    LIQUID_DIGESTATE_SLURRY = "LIQUID_DIGESTATE_SLURRY"


# ------------------------------------------------------------------------------
# Agronomic Baselines (DoA Sri Lanka & HARTI Recommended Nutrient Targets kg/ha)
# ------------------------------------------------------------------------------
CROP_NUTRIENT_DEMANDS_KG_HA: dict[str, dict[str, float]] = {
    "Tomato": {"n": 100.0, "p2o5": 50.0, "k2o": 100.0, "basal_compost_min_kg_ha": 2500.0},
    "Big Onion": {"n": 90.0, "p2o5": 45.0, "k2o": 75.0, "basal_compost_min_kg_ha": 2000.0},
    "Chilli": {"n": 110.0, "p2o5": 55.0, "k2o": 90.0, "basal_compost_min_kg_ha": 2500.0},
    "Yard Long Bean": {"n": 45.0, "p2o5": 60.0, "k2o": 75.0, "basal_compost_min_kg_ha": 1500.0},
    "Brinjal": {"n": 120.0, "p2o5": 60.0, "k2o": 90.0, "basal_compost_min_kg_ha": 2500.0},
    "Okra": {"n": 80.0, "p2o5": 40.0, "k2o": 60.0, "basal_compost_min_kg_ha": 1800.0},
    "Maize": {"n": 120.0, "p2o5": 45.0, "k2o": 40.0, "basal_compost_min_kg_ha": 1500.0},
    "Pumpkin": {"n": 75.0, "p2o5": 50.0, "k2o": 80.0, "basal_compost_min_kg_ha": 2000.0},
    "Paddy": {"n": 80.0, "p2o5": 30.0, "k2o": 40.0, "basal_compost_min_kg_ha": 1200.0},
}

# Regional Farmer Clusters (Dambulla & Negama/Anuradhapura Corridors)
DEFAULT_FARMER_CLUSTERS: list[dict[str, Any]] = [
    {
        "cluster_id": "CL-DAM-01",
        "cluster_name": "Kandalama North Cluster",
        "region": "Dambulla",
        "hub_id": "HUB-DAMBULLA",
        "latitude": 7.8540,
        "longitude": 80.7020,
        "soil_type": "Reddish Brown Earths (RBE)",
        "soil_organic_matter_pct": 1.15,  # Organic matter depleted
        "soil_ph": 6.8,
    },
    {
        "cluster_id": "CL-DAM-02",
        "cluster_name": "Galewela Mixed Vegetable Cluster",
        "region": "Dambulla",
        "hub_id": "HUB-DAMBULLA",
        "latitude": 7.7560,
        "longitude": 80.5720,
        "soil_type": "Reddish Brown Earths (RBE)",
        "soil_organic_matter_pct": 1.30,
        "soil_ph": 6.5,
    },
    {
        "cluster_id": "CL-DAM-03",
        "cluster_name": "Sigiriya - Inamaluwa Agro-Forestry Cluster",
        "region": "Dambulla",
        "hub_id": "HUB-DAMBULLA",
        "latitude": 7.9540,
        "longitude": 80.7280,
        "soil_type": "Low Humic Gley (LHG)",
        "soil_organic_matter_pct": 1.45,
        "soil_ph": 7.1,
    },
    {
        "cluster_id": "CL-ANU-01",
        "cluster_name": "Negama Agrarian Center Core Cluster",
        "region": "Anuradhapura",
        "hub_id": "HUB-NEGAMA",
        "latitude": 8.1350,
        "longitude": 80.3980,
        "soil_type": "Reddish Brown Earths (RBE)",
        "soil_organic_matter_pct": 0.95,  # Severely degraded
        "soil_ph": 6.7,
    },
    {
        "cluster_id": "CL-ANU-02",
        "cluster_name": "Eppawala Commercial Field Crop Cluster",
        "region": "Anuradhapura",
        "hub_id": "HUB-NEGAMA",
        "latitude": 8.1450,
        "longitude": 80.4120,
        "soil_type": "Non-Calcic Brown Soils",
        "soil_organic_matter_pct": 1.20,
        "soil_ph": 6.9,
    },
    {
        "cluster_id": "CL-ANU-03",
        "cluster_name": "Kekirawa Onion & Grain Cluster",
        "region": "Anuradhapura",
        "hub_id": "HUB-NEGAMA",
        "latitude": 8.0420,
        "longitude": 80.5960,
        "soil_type": "Reddish Brown Earths (RBE)",
        "soil_organic_matter_pct": 1.05,
        "soil_ph": 6.6,
    },
]


@dataclass
class CultivationPlotDemand:
    farmer_id: str
    farmer_name: str
    cluster_id: str
    cluster_name: str
    crop_name: str
    acreage_ha: float
    growth_stage: GrowthStage
    latitude: float
    longitude: float
    soil_organic_matter_pct: float = 1.2
    soil_ph: float = 6.8


@dataclass
class AvailableFertilizerSupply:
    supply_id: str
    hub_id: str
    fertilizer_category: FertilizerCategory
    available_mass_kg: float
    n_pct: float
    p2o5_pct: float
    k2o_pct: float
    organic_carbon_pct: float
    c_n_ratio: float
    unit_sale_price_lkr_kg: float = 18.0


@dataclass
class FarmAllocationResult:
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


@dataclass
class RegionalMatchingSummary:
    hub_id: str
    total_farms_served: int
    total_acreage_covered_ha: float
    total_solid_compost_allocated_kg: float
    total_liquid_digestate_allocated_kg: float
    total_urea_displaced_kg: float
    total_tsp_displaced_kg: float
    total_mop_displaced_kg: float
    total_foreign_exchange_savings_lkr: float
    allocations: list[FarmAllocationResult] = field(default_factory=list)
    agronomic_compliance_notes: list[str] = field(default_factory=list)


class NutrientDemandMatcher:
    """
    Solves stoichiometric fertilizer demand matching while strictly enforcing
    Department of Agriculture (DoA) growth-stage restrictions.
    """

    # Prevailing subsidized/market prices for synthetic fertilizer in Sri Lanka (LKR/kg)
    UREA_PRICE_PER_KG = 220.0  # 46% N
    TSP_PRICE_PER_KG = 280.0   # 46% P2O5
    MOP_PRICE_PER_KG = 260.0   # 60% K2O

    def match_demands(
        self,
        supplies: list[AvailableFertilizerSupply],
        demands: list[CultivationPlotDemand],
    ) -> RegionalMatchingSummary:
        """
        Executes constrained matching of organic compost and liquid digestate
        against active crop growth stages.
        """
        # Index supplies by category
        supply_pool: dict[FertilizerCategory, float] = {
            FertilizerCategory.SOLID_ORGANIC_COMPOST: 0.0,
            FertilizerCategory.LIQUID_DIGESTATE_SLURRY: 0.0,
        }
        supply_specs: dict[FertilizerCategory, AvailableFertilizerSupply] = {}

        for sup in supplies:
            supply_pool[sup.fertilizer_category] += sup.available_mass_kg
            supply_specs[sup.fertilizer_category] = sup

        allocations: list[FarmAllocationResult] = []
        total_urea_displaced = 0.0
        total_tsp_displaced = 0.0
        total_mop_displaced = 0.0
        total_fx_savings = 0.0
        total_acreage = 0.0

        for plot in demands:
            total_acreage += plot.acreage_ha
            crop_spec = CROP_NUTRIENT_DEMANDS_KG_HA.get(
                plot.crop_name,
                CROP_NUTRIENT_DEMANDS_KG_HA["Tomato"]
            )

            # Gross nutrient requirements for plot
            req_n = crop_spec["n"] * plot.acreage_ha
            req_p = crop_spec["p2o5"] * plot.acreage_ha
            req_k = crop_spec["k2o"] * plot.acreage_ha

            # ------------------------------------------------------------------
            # Department of Agriculture Growth-Stage Gatekeeper
            # ------------------------------------------------------------------
            if plot.growth_stage == GrowthStage.BASAL_LAND_PREP:
                # Basal requires solid compost for organic matter and soil restructuring
                category = FertilizerCategory.SOLID_ORGANIC_COMPOST
                target_mass = max(
                    crop_spec["basal_compost_min_kg_ha"] * plot.acreage_ha,
                    (req_n / 0.02) * 0.60  # 60% of total N delivered via basal compost
                )
                rationale = (
                    f"Basal land prep for {plot.crop_name}: Solid organic compost mandatory to elevate "
                    f"soil organic matter above 2.0% and provide gradual mineralizing N-P-K nutrient reservoir."
                )
                mismatch_warning = None

            elif plot.growth_stage == GrowthStage.VEGETATIVE_GROWTH:
                # Vegetative growth can assimilate high soluble nitrogen in digestate or top-dress compost
                if supply_pool[FertilizerCategory.LIQUID_DIGESTATE_SLURRY] > 100.0:
                    category = FertilizerCategory.LIQUID_DIGESTATE_SLURRY
                    # 50% of vegetative nitrogen fulfilled via liquid digestate
                    target_mass = (req_n * 0.50) / 0.035
                    rationale = (
                        f"Active vegetative stage for {plot.crop_name}: High soluble ammonium N in liquid "
                        f"digestate slurry provides immediate foliar and root bioavailability for canopy expansion."
                    )
                else:
                    category = FertilizerCategory.SOLID_ORGANIC_COMPOST
                    target_mass = (req_n * 0.40) / 0.02
                    rationale = (
                        f"Vegetative stage top-dressing for {plot.crop_name}: Solid compost top-dress allocated "
                        f"due to liquid digestate depletion."
                    )
                mismatch_warning = None

            elif plot.growth_stage == GrowthStage.FLOWERING_FRUIT_SET:
                # CRITICAL: STRICT AGRONOMIC MISMATCH FILTER
                # Never allocate high-N liquid digestate slurry during flowering/fruit set!
                category = FertilizerCategory.SOLID_ORGANIC_COMPOST
                target_mass = (req_k * 0.50) / 0.018  # Focus on potassium uptake
                rationale = (
                    f"Flowering & fruit set stage for {plot.crop_name}: Solid compost allocated for potassium (K2O) "
                    f"and phosphorus enrichment. Promotes cell elongation, fruit firmness, and brix content."
                )
                mismatch_warning = (
                    "AGRONOMIC SAFETY FILTER ACTIVATED: Liquid anaerobic digestate blocked. Excess soluble N "
                    "during flowering causes flower abortion, excessive vegetative flushing, and blossom-end rot."
                )

            else:  # MATURITY_HARVEST
                category = FertilizerCategory.SOLID_ORGANIC_COMPOST
                target_mass = 200.0 * plot.acreage_ha
                rationale = (
                    f"Pre-harvest maturity for {plot.crop_name}: Light organic maintenance conditioning "
                    f"to prevent post-harvest soil exhaustion."
                )
                mismatch_warning = None

            # Check available inventory in pool
            available = supply_pool.get(category, 0.0)
            allocated_mass = min(available, target_mass)
            supply_pool[category] -= allocated_mass

            # Fetch nutrient specs
            sup_item = supply_specs.get(category)
            n_pct = sup_item.n_pct if sup_item else (2.0 if category == FertilizerCategory.SOLID_ORGANIC_COMPOST else 3.5)
            p_pct = sup_item.p2o5_pct if sup_item else 1.0
            k_pct = sup_item.k2o_pct if sup_item else 1.8
            unit_price = sup_item.unit_sale_price_lkr_kg if sup_item else 18.0

            n_supplied = allocated_mass * (n_pct / 100.0)
            p_supplied = allocated_mass * (p_pct / 100.0)
            k_supplied = allocated_mass * (k_pct / 100.0)

            # Synthetic fertilizer displacement
            urea_disp = n_supplied / 0.46
            tsp_disp = p_supplied / 0.46
            mop_disp = k_supplied / 0.60

            chem_cost_saved = (
                (urea_disp * self.UREA_PRICE_PER_KG) +
                (tsp_disp * self.TSP_PRICE_PER_KG) +
                (mop_disp * self.MOP_PRICE_PER_KG)
            )
            organic_cost = allocated_mass * unit_price
            net_benefit = chem_cost_saved - organic_cost

            total_urea_displaced += urea_disp
            total_tsp_displaced += tsp_disp
            total_mop_displaced += mop_disp
            total_fx_savings += chem_cost_saved

            allocations.append(FarmAllocationResult(
                farmer_id=plot.farmer_id,
                farmer_name=plot.farmer_name,
                cluster_id=plot.cluster_id,
                cluster_name=plot.cluster_name,
                crop_name=plot.crop_name,
                acreage_ha=round(plot.acreage_ha, 2),
                growth_stage=plot.growth_stage.value,
                allocated_fertilizer_category=category.value,
                allocated_mass_kg=round(allocated_mass, 1),
                nutrient_supplied_n_kg=round(n_supplied, 2),
                nutrient_supplied_p2o5_kg=round(p_supplied, 2),
                nutrient_supplied_k2o_kg=round(k_supplied, 2),
                target_demand_n_kg=round(req_n, 2),
                target_demand_p2o5_kg=round(req_p, 2),
                target_demand_k2o_kg=round(req_k, 2),
                nitrogen_fulfillment_pct=round(min(100.0, (n_supplied / req_n) * 100.0), 1) if req_n > 0 else 0.0,
                phosphorus_fulfillment_pct=round(min(100.0, (p_supplied / req_p) * 100.0), 1) if req_p > 0 else 0.0,
                potassium_fulfillment_pct=round(min(100.0, (k_supplied / req_k) * 100.0), 1) if req_k > 0 else 0.0,
                urea_displaced_kg=round(urea_disp, 2),
                tsp_displaced_kg=round(tsp_disp, 2),
                mop_displaced_kg=round(mop_disp, 2),
                chemical_fertilizer_cost_saved_lkr=round(chem_cost_saved, 2),
                organic_fertilizer_cost_lkr=round(organic_cost, 2),
                net_economic_benefit_lkr=round(net_benefit, 2),
                agronomic_rationale=rationale,
                mismatch_warning=mismatch_warning,
            ))

        hub_id = supplies[0].hub_id if supplies else "HUB-DAMBULLA"
        solid_total = sum(
            a.allocated_mass_kg for a in allocations
            if a.allocated_fertilizer_category == FertilizerCategory.SOLID_ORGANIC_COMPOST.value
        )
        liquid_total = sum(
            a.allocated_mass_kg for a in allocations
            if a.allocated_fertilizer_category == FertilizerCategory.LIQUID_DIGESTATE_SLURRY.value
        )

        notes = [
            f"Cross-referenced {len(demands)} active farm plots across {total_acreage:.2f} hectares.",
            "Enforced DoA Growth-Stage safety gating: 100% compliance on blocking high-N digestate during flowering.",
            f"Displaced {total_urea_displaced:.1f} kg Urea, {total_tsp_displaced:.1f} kg TSP, and {total_mop_displaced:.1f} kg MOP.",
            f"Generated LKR {total_fx_savings:,.2f} in synthetic fertilizer import substitution."
        ]

        return RegionalMatchingSummary(
            hub_id=hub_id,
            total_farms_served=len(allocations),
            total_acreage_covered_ha=round(total_acreage, 2),
            total_solid_compost_allocated_kg=round(solid_total, 1),
            total_liquid_digestate_allocated_kg=round(liquid_total, 1),
            total_urea_displaced_kg=round(total_urea_displaced, 1),
            total_tsp_displaced_kg=round(total_tsp_displaced, 1),
            total_mop_displaced_kg=round(total_mop_displaced, 1),
            total_foreign_exchange_savings_lkr=round(total_fx_savings, 2),
            allocations=allocations,
            agronomic_compliance_notes=notes,
        )
