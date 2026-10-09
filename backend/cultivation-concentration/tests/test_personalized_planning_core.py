"""Standalone planning tests. Approval overlays and agronomic fixtures are fictional."""
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.schemas.alternatives import EvidenceRegistry
from app.schemas.cultivation_plan import Plan
from app.schemas.personalized_planning import PlanningRequest
from app.services.personalized_planning import DATA, generate


class OwnedPlanRepository:
    """Read-only repository contract; real persistence is covered by API tests."""
    def __init__(self, **changes):
        values = dict(plan_id="fictional-plan", farmer_id="fictional-owner",
            district="Matara", region="north", crop="Bandakka", land_size_acres=2.4710538147,
            planting_date="2030-01-01", expected_harvest_date="2030-04-01", status="active",
            submitted_at="2020-01-01T00:00:00Z", updated_at="2020-01-01T00:00:00Z")
        values.update(changes)
        self.plan = Plan.model_validate(values)

    def read(self, plan_id, farmer):
        if (plan_id, farmer) != (self.plan.plan_id, self.plan.farmer_id):
            raise HTTPException(404, "Owned plan not found")
        return {"plan": self.plan}


def request(**changes):
    values = dict(plan_id="fictional-plan", final_crop="Bandakka", district="Matara",
        region="north", land_size_acres=2.4710538147, planting_date="2030-01-01",
        season="Maha", planting_method="direct_sowing", as_of="2020-06-01T00:00:00Z")
    values.update(changes)
    return PlanningRequest.model_validate(values)


@pytest.fixture
def fixture(tmp_path):
    entry = dict(entry_id="fictional-claim", crop_name="Bandakka",
        verification_status="source_checked", source_url="https://example.invalid/fictional",
        district_applicability=["Matara"], season=["Maha"], variety=None,
        guideline_category="harvest", activity_name="Fictional harvest", notes="Fixture only",
        timing_reference="direct_sowing", days_offset={"min": 50, "max": 56},
        repeat_interval_days=2, max_occurrences=4,
        rate_per_hectare={"min": 10, "max": 20}, unit="kg/ha")
    approval = dict(entry_id="fictional-claim", claim_verified=True,
        approved_by="fictional-reviewer", evidence_reference="fictional-approval",
        available_at="2020-01-01T00:00:00Z", approved_at="2020-01-01T00:00:00Z",
        district="Matara", region="north", season="Maha", planting_method="direct_sowing")
    def run(changes=None, approval_changes=None, entry_changes=None, approvals=True,
            repository=None, farmer="fictional-owner"):
        record = dict(entry, **(entry_changes or {}))
        (tmp_path / "verified_entries.json").write_text(
            json.dumps({"entries": [record]}), encoding="utf-8")
        return generate(repository or OwnedPlanRepository(), request(**(changes or {})), farmer,
            [dict(approval, **(approval_changes or {}))] if approvals else [],
            EvidenceRegistry(), tmp_path)
    return run


def test_schedules_unit_scaling_and_expected_harvest(fixture):
    result = fixture()
    activity = result["activities"][0]
    assert result["status"] == "partial_plan"
    assert result["expected_harvest_date"] == "2030-04-01"
    assert activity["quantity"]["min"] == pytest.approx(10)
    assert activity["quantity"]["max"] == pytest.approx(20)
    assert len(activity["date_windows"]) == 4
    assert activity["date_windows"][0]["earliest"] == "2030-02-20"
    assert activity["date_windows"][-1]["latest"] == "2030-02-26"
    assert "fertilizer" in result["missing_categories"]
    assert "farmer_id" not in json.dumps(result)


@pytest.mark.parametrize("changes", [{"district": "Hambantota"}, {"region": "south"},
    {"season": "Yala"}, {"variety": "other"}, {"planting_method": "transplanting"}])
def test_approval_applicability_isolation(fixture, changes):
    assert fixture(changes=changes)["activities"] == []


def test_missing_future_unverified_and_yield_claims(fixture):
    assert fixture(approvals=False)["activities"] == []
    assert fixture(approval_changes={"claim_verified": False})["activities"] == []
    assert fixture(approval_changes={"available_at": "2021-01-01T00:00:00Z"})["activities"] == []
    assert fixture(entry_changes={"guideline_category": "yield"})["activities"] == []


def test_transplant_anchor_and_unsupported_units(fixture):
    result = fixture(changes={"planting_method": "transplanting"},
        approval_changes={"planting_method": "transplanting"},
        entry_changes={"timing_reference": "transplanting", "unit": "unknown"})
    assert result["activities"][0]["date_windows"][0]["earliest"] == "2030-02-20"
    assert result["activities"][0]["quantity"] is None
    undated = fixture(entry_changes={"timing_reference": "flowering"})
    assert undated["activities"][0]["date_windows"] == []
    assert any("undated guidance" in warning for warning in undated["warnings"])


@pytest.mark.parametrize("changes,repository,farmer,status", [
    ({}, OwnedPlanRepository(), "fictional-other", 404),
    ({}, OwnedPlanRepository(status="cancelled"), "fictional-owner", 409),
    ({"as_of": "2019-01-01T00:00:00Z"}, OwnedPlanRepository(), "fictional-owner", 409),
    ({"as_of": "2099-01-01T00:00:00Z"}, OwnedPlanRepository(), "fictional-owner", 422)])
def test_ownership_revision_and_cutoff(fixture, changes, repository, farmer, status):
    with pytest.raises(HTTPException) as error:
        fixture(changes=changes, repository=repository, farmer=farmer)
    assert error.value.status_code == status


def test_packaged_guidance_requires_explicit_approval():
    records = json.loads((Path(DATA) / "verified_entries.json").read_text(encoding="utf-8"))
    assert records["entries"]
    assert all(entry["planning_activation"] is False for entry in records["entries"])
    result = generate(OwnedPlanRepository(), request(), "fictional-owner", [], EvidenceRegistry())
    assert result["activities"] == []
