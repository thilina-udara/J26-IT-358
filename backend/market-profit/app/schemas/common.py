import json
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Set

# Path resolution to project root shared/constants
CURRENT_FILE = Path(__file__).resolve()
ROOT_DIR = CURRENT_FILE.parents[4] if len(CURRENT_FILE.parents) >= 5 else CURRENT_FILE.parent
CROPS_FILE = ROOT_DIR / "shared" / "constants" / "crop_catalog.json"
DISTRICTS_FILE = ROOT_DIR / "shared" / "constants" / "srilanka_districts.json"

# Fallback IDs based on the project constants catalog
DEFAULT_CROP_IDS = {
    "CR_MAIZE", "CR_CHILLI", "CR_MUNG_BEAN", "CR_TOMATO",
    "CR_BRINJAL", "CR_OKRA", "CR_PUMPKIN"
}

DEFAULT_DISTRICT_IDS = {
    "LK-11", "LK-12", "LK-13", "LK-21", "LK-22", "LK-23",
    "LK-31", "LK-32", "LK-33", "LK-41", "LK-42", "LK-43",
    "LK-44", "LK-45", "LK-51", "LK-52", "LK-53", "LK-61",
    "LK-62", "LK-71", "LK-72", "LK-81", "LK-82", "LK-91", "LK-92"
}


def load_valid_crop_ids() -> Set[str]:
    """Load valid crop IDs from shared catalog with safe fallback."""
    if CROPS_FILE.exists():
        try:
            with open(CROPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {crop["crop_id"] for crop in data.get("crops", [])}
        except Exception:
            return DEFAULT_CROP_IDS
    return DEFAULT_CROP_IDS


def load_valid_district_ids() -> Set[str]:
    """Load valid Sri Lankan district IDs from shared catalog with safe fallback."""
    if DISTRICTS_FILE.exists():
        try:
            with open(DISTRICTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {district["id"] for district in data.get("districts", [])}
        except Exception:
            return DEFAULT_DISTRICT_IDS
    return DEFAULT_DISTRICT_IDS


VALID_CROP_IDS = load_valid_crop_ids()
VALID_DISTRICT_IDS = load_valid_district_ids()


def validate_crop_id_value(value: str) -> str:
    """Validate crop identifier against the shared crop catalog."""
    if value not in VALID_CROP_IDS:
        valid_list = sorted(list(VALID_CROP_IDS))
        raise ValueError(
            f"Invalid crop_id '{value}'. Must be one of registered crops: {', '.join(valid_list)}"
        )
    return value


def validate_district_id_value(value: str) -> str:
    """Validate district identifier against the 25 Sri Lankan district codes."""
    if value not in VALID_DISTRICT_IDS:
        raise ValueError(
            f"Invalid district_id '{value}'. Must be a valid Sri Lankan district code (e.g., 'LK-11' to 'LK-92')"
        )
    return value


# Standard Dedicated Economic Centres (DECs) and major market hubs in Sri Lanka
STANDARD_MARKETS = {
    "DEC_DAMBULLA": "Dambulla Dedicated Economic Centre",
    "DEC_PETTAH": "Pettah Manning Market",
    "DEC_KEPPETIPOLA": "Keppetipola Dedicated Economic Centre",
    "DEC_MEEGODA": "Meegoda Dedicated Economic Centre",
    "DEC_THAMBUTHTHEGAMA": "Thambuththegama Dedicated Economic Centre",
    "DEC_KURUNEGALA": "Kurunegala Central Market",
    "DEC_KANDY": "Kandy Central Market",
    "DEC_EMBILIPITIYA": "Embilipitiya Dedicated Economic Centre",
    "DEC_NUWARA_ELIYA": "Nuwara Eliya Economic Centre",
    "DEC_VEYANGODA": "Veyangoda Dedicated Economic Centre"
}


class PredictionStatus(str, Enum):
    """Lifecycle state of an ML prediction request."""
    PENDING = "pending"
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class ProfitRiskLevel(str, Enum):
    """Standardized profit risk categories."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class DemandLevel(str, Enum):
    """Standardized demand level categories (independent of supply-side oversupply)."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class DemandRecordType(str, Enum):
    """Provenance and generation type for market demand records."""
    OBSERVED = "observed"
    ESTIMATED = "estimated"
    SYNTHETIC = "synthetic"


class PriceType(str, Enum):
    """Market price point classification."""
    WHOLESALE = "wholesale"
    RETAIL = "retail"
    FARMGATE = "farmgate"


class BudgetEntryMode(str, Enum):
    """Cultivation cost entry method."""
    QUICK = "quick"
    DETAILED = "detailed"


class SeasonEnum(str, Enum):
    """Sri Lankan agrarian seasons."""
    MAHA = "Maha"
    YALA = "Yala"
    YEAR_ROUND = "Year-round"


from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    """Metadata for paginated queries."""
    total: int = Field(..., description="Total matching records count")
    page: int = Field(..., ge=1, description="Current page index (1-based)")
    page_size: int = Field(..., ge=1, le=100, description="Items returned per page")
    total_pages: int = Field(..., description="Total available pages")
