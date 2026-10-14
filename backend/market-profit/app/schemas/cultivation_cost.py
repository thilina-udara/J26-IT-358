from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.common import BudgetEntryMode, SeasonEnum, validate_crop_id_value, validate_district_id_value


class CultivationCostBreakdown(BaseModel):
    """Detailed category breakdown of cultivation costs in LKR."""
    land_preparation_cost: Optional[Decimal] = Field(None, ge=Decimal("0.0"), description="Land preparation, tilling, plowing (LKR)")
    seeds_plants_cost: Optional[Decimal] = Field(None, ge=Decimal("0.0"), description="Seeds, seedlings, nurseries (LKR)")
    fertilizer_cost: Optional[Decimal] = Field(None, ge=Decimal("0.0"), description="Organic and chemical fertilizers (LKR)")
    pesticide_weedicide_cost: Optional[Decimal] = Field(None, ge=Decimal("0.0"), description="Crop protection agrochemicals (LKR)")
    labor_cost: Optional[Decimal] = Field(None, ge=Decimal("0.0"), description="Hired and family manual labor (LKR)")
    machinery_fuel_cost: Optional[Decimal] = Field(None, ge=Decimal("0.0"), description="Machinery rental, fuel, irrigation pumps (LKR)")
    transport_packaging_cost: Optional[Decimal] = Field(None, ge=Decimal("0.0"), description="Packaging crates, bagging, transport to market (LKR)")
    miscellaneous_cost: Optional[Decimal] = Field(None, ge=Decimal("0.0"), description="Contingencies, field maintenance (LKR)")

    def sum_provided(self) -> Decimal:
        """Calculate the sum of all provided (non-None) categories."""
        total = Decimal("0.0")
        for val in [
            self.land_preparation_cost,
            self.seeds_plants_cost,
            self.fertilizer_cost,
            self.pesticide_weedicide_cost,
            self.labor_cost,
            self.machinery_fuel_cost,
            self.transport_packaging_cost,
            self.miscellaneous_cost
        ]:
            if val is not None:
                total += val
        return total


class CultivationBudgetBase(BaseModel):
    """Base schema for cultivation budgets."""
    crop_id: str = Field(..., description="Crop identifier")
    district_id: str = Field(..., description="Cultivation district code")
    season: SeasonEnum = Field(..., description="Maha, Yala, or Year-round")
    year: int = Field(..., ge=2020, le=2050, description="Agrarian calendar year")
    entry_mode: BudgetEntryMode = Field(default=BudgetEntryMode.DETAILED, description="quick (total only) or detailed (breakdown)")
    land_extent_acres: Decimal = Field(default=Decimal("1.00"), gt=Decimal("0.0"), description="Cultivated extent in acres")
    total_cost: Optional[Decimal] = Field(None, gt=Decimal("0.0"), description="Total cultivation cost in LKR")
    breakdown: Optional[CultivationCostBreakdown] = Field(None, description="Detailed category breakdown")
    expected_yield_kg: Decimal = Field(..., gt=Decimal("0.0"), description="Expected total harvest output in kg")
    unit: str = Field(default="kg", description="Harvest measurement unit")
    currency: str = Field(default="LKR", description="Currency ISO code")
    data_source: str = Field(default="Farmer Reported", description="Source of budget information")
    notes: Optional[str] = Field(None, description="Additional agronomic notes")

    @field_validator("crop_id")
    @classmethod
    def check_crop(cls, v: str) -> str:
        return validate_crop_id_value(v)

    @field_validator("district_id")
    @classmethod
    def check_district(cls, v: str) -> str:
        return validate_district_id_value(v)

    @model_validator(mode="after")
    def validate_budget_mode(self) -> "CultivationBudgetBase":
        """
        Validate entry mode consistency:
        - Quick mode: requires total_cost > 0; breakdown categories must remain null.
        - Detailed mode: requires breakdown; calculates or verifies total_cost as the sum of provided categories.
        """
        if self.entry_mode == BudgetEntryMode.QUICK:
            if self.total_cost is None or self.total_cost <= Decimal("0.0"):
                raise ValueError("In 'quick' budget mode, a positive total_cost must be explicitly specified.")
            if self.breakdown is not None:
                # Ensure we do not mix quick total with breakdown
                self.breakdown = None

        elif self.entry_mode == BudgetEntryMode.DETAILED:
            if self.breakdown is None:
                raise ValueError("In 'detailed' budget mode, a cost breakdown must be provided.")
            computed_sum = self.breakdown.sum_provided()
            if computed_sum <= Decimal("0.0"):
                raise ValueError("In 'detailed' budget mode, at least one cost category must be greater than zero.")
            if self.total_cost is None:
                self.total_cost = computed_sum
            elif self.total_cost != computed_sum:
                raise ValueError(
                    f"Provided total_cost ({self.total_cost}) does not match the sum of itemized breakdown categories ({computed_sum})."
                )

        return self


class CultivationBudgetCreate(CultivationBudgetBase):
    """Payload schema for creating a new cultivation budget record."""
    pass


class CultivationBudgetResponse(BaseModel):
    """Response representation of a saved cultivation budget."""
    id: int
    crop_id: str
    district_id: str
    season: str
    year: int
    entry_mode: str
    land_extent_acres: Decimal
    total_cost: Decimal
    land_preparation_cost: Optional[Decimal] = None
    seeds_plants_cost: Optional[Decimal] = None
    fertilizer_cost: Optional[Decimal] = None
    pesticide_weedicide_cost: Optional[Decimal] = None
    labor_cost: Optional[Decimal] = None
    machinery_fuel_cost: Optional[Decimal] = None
    transport_packaging_cost: Optional[Decimal] = None
    miscellaneous_cost: Optional[Decimal] = None
    expected_yield_kg: Decimal
    unit: str
    currency: str
    data_source: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
