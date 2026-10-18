"""Isolated synthetic demonstration dataset and clustering generator for research benchmarking.

STRICT RESEARCH INTEGRITY CONSTRAINTS:
1. Never reads from or writes to the live operational farmer plans database.
2. Does not expose or reuse restricted historical farmer records or private cohorts.
3. Does not fabricate operational risk labels or yield promises.
4. Generates a balanced, deterministic synthetic cohort of plans across pilot districts
   explicitly for demonstrating K-Means spatial partitions and DBSCAN density/outlier behavior.
"""
from typing import Any, Dict, List
from app.services.plan_clustering import analyze

# Explicitly labeled synthetic farmer identifiers - completely distinct from operational accounts
SYNTHETIC_FARMERS = (
    "synthetic-demo-farmer-01",
    "synthetic-demo-farmer-02",
    "synthetic-demo-farmer-03",
    "synthetic-demo-farmer-04",
    "synthetic-demo-farmer-05",
    "synthetic-demo-farmer-06",
)

DISTRICT_REGIONS = {
    "Matara": ("matara-central", "matara-east", "matara-west"),
    "Hambantota": ("hambantota-central", "hambantota-east", "hambantota-west"),
}


def build_synthetic_cohort(district: str) -> List[Dict[str, Any]]:
    """Generate a balanced, deterministic synthetic plan cohort for a pilot district.
    
    Contains:
    - Dense neighborhood of similar crops, regions, and dates (forming DBSCAN dense clusters).
    - Diverse acreage and crop variations (forming distinct K-Means partitions).
    - An isolated atypical group with 3 distinct synthetic farmers (demonstrating DBSCAN noise/outliers).
    """
    regions = DISTRICT_REGIONS.get(district, ("central-region", "east-region", "west-region"))
    plans: List[Dict[str, Any]] = []
    counter = 1

    # Dense Neighborhood 1: Corn & Bandakka in region 0
    for i in range(8):
        f_id = SYNTHETIC_FARMERS[i % len(SYNTHETIC_FARMERS)]
        crop = "Corn" if i % 2 == 0 else "Bandakka"
        plans.append({
            "plan_id": f"syn-{district.lower()[:3]}-{counter:03d}",
            "farmer_id": f_id,
            "district": district,
            "region": regions[0],
            "crop": crop,
            "land_size_acres": float(2.0 + (i % 3) * 0.5),
            "planting_date": "2026-11-05",
            "expected_harvest_date": "2027-02-15",
            "status": "active",
            "farmer_declared_season": "Maha",
        })
        counter += 1

    # Dense Neighborhood 2: Brinjal & Pumpkin in region 1
    for i in range(6):
        f_id = SYNTHETIC_FARMERS[(i + 2) % len(SYNTHETIC_FARMERS)]
        crop = "Brinjal" if i % 2 == 0 else "Pumpkin"
        plans.append({
            "plan_id": f"syn-{district.lower()[:3]}-{counter:03d}",
            "farmer_id": f_id,
            "district": district,
            "region": regions[1],
            "crop": crop,
            "land_size_acres": float(1.5 + (i % 2) * 0.5),
            "planting_date": "2026-11-20",
            "expected_harvest_date": "2027-03-05",
            "status": "active",
            "farmer_declared_season": "Maha",
        })
        counter += 1

    # Atypical Outlier Group: 3 distinct synthetic farmers with unusual acreage/dates in region 2
    outlier_specs = [
        (SYNTHETIC_FARMERS[0], "Chillies", 14.5, "2026-12-15", "2027-04-25"),
        (SYNTHETIC_FARMERS[1], "Mung Beans", 9.0, "2026-12-01", "2027-03-28"),
        (SYNTHETIC_FARMERS[2], "Pumpkin", 11.0, "2026-12-20", "2027-04-10"),
    ]
    for f_id, crop, acres, p_date, h_date in outlier_specs:
        plans.append({
            "plan_id": f"syn-{district.lower()[:3]}-{counter:03d}",
            "farmer_id": f_id,
            "district": district,
            "region": regions[2],
            "crop": crop,
            "land_size_acres": acres,
            "planting_date": p_date,
            "expected_harvest_date": h_date,
            "status": "active",
            "farmer_declared_season": "Maha",
        })
        counter += 1

    return plans


def run_synthetic_research_clustering(district: str) -> Dict[str, Any]:
    """Execute actual K-Means and DBSCAN clustering on the synthetic demonstration cohort."""
    synthetic_plans = build_synthetic_cohort(district)
    result = analyze(
        synthetic_plans,
        district=district,
        clusters=3,
        eps=1.0,
        min_samples=2,
    )
    result["mode"] = "synthetic_research_demo"
    result["provenance"] = "synthetic_research_benchmark_cohort"
    result["notice"] = "Synthetic Research Demonstration — Not Real Farmer Data. Real farmer plans are isolated and unread."
    result["synthetic_plan_count"] = len(synthetic_plans)
    result["distinct_synthetic_farmers"] = len({p["farmer_id"] for p in synthetic_plans})
    return result
