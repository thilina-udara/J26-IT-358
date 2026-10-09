"""Standalone recommendation checks; all plans and evidence are fictional."""
import json
import sqlite3
from contextlib import contextmanager

import pytest
from fastapi import HTTPException

from app.schemas.alternatives import AlternativeRequest, EvidenceRegistry
from app.services.alternatives import compare_alternatives
from app.services.privacy import farmer_view


class FictionalRepository:
    """Minimal version-table contract; does not test registration persistence."""
    def __init__(self, path):
        self.path = path
        with self.connection() as db:
            db.execute("CREATE TABLE cultivation_plan_versions "
                       "(version_id INTEGER PRIMARY KEY, recorded_at TEXT, payload TEXT)")
            for crop, acres in (("Corn", 5), ("Brinjal", 2)):
                for index, harvest in enumerate(("2030-03-18", "2030-04-01", "2030-04-15")):
                    plan = dict(plan_id=f"fictional-{crop}-{index}",
                        farmer_id=f"fictional-farmer-{index}", district="Matara",
                        region="north", crop=crop, land_size_acres=acres,
                        planting_date="2030-01-01", expected_harvest_date=harvest,
                        status="active", submitted_at="2020-01-01T00:00:00+00:00")
                    db.execute("INSERT INTO cultivation_plan_versions(recorded_at,payload) "
                               "VALUES (?,?)", (plan["submitted_at"], json.dumps(plan)))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()


def request(**changes):
    value = dict(selected_crop="Corn", district="Matara", region="north",
                 land_size_acres=2, planting_date="2030-01-01",
                 expected_harvest_date="2030-04-01", as_of="2020-06-01T00:00:00Z")
    value.update(changes)
    return AlternativeRequest.model_validate(value)


def evidence():
    base = dict(district="Matara", region="north", source_reference="fictional-source",
        verified_by="fictional-reviewer", verified_at="2020-01-01T00:00:00Z",
        available_at="2020-01-01T00:00:00Z", valid_from="2029-01-01",
        valid_to="2031-12-31", verified=True)
    return dict(suitability=[dict(base, evidence_id="fictional-suitability", crop="Brinjal",
        min_land_acres=1, max_land_acres=10, min_harvest_days=80, max_harvest_days=100,
        applicable_without_additional_inputs=True,
        applicability_statement="Fictional fixture, not agricultural guidance")],
        coverage=[dict(base, evidence_id="fictional-coverage-" + crop, crop=crop,
            comparable_registration_scope=True, registration_scope_id="fictional-scope",
            coverage_statement="Fictional coverage") for crop in ("Corn", "Brinjal")])


@pytest.fixture
def repository(tmp_path):
    return FictionalRepository(tmp_path / "fictional.sqlite3")


def compare(repository, registry=None, **changes):
    return compare_alternatives(repository, request(**changes), "fictional-requester",
        EvidenceRegistry.model_validate(evidence() if registry is None else registry))


def test_conditional_alternative_and_farmer_disclosure(repository):
    result = compare(repository)
    assert result["status"] == "alternatives_available"
    assert result["selected_concentration"]["scenario_inclusive_acreage"] == 17
    alternative = result["alternatives"][0]
    assert alternative["crop"] == "Brinjal"
    assert alternative["planned_concentration"]["scenario_inclusive_acreage"] == 8
    assert alternative["risk_level"] == "unknown_unvalidated"
    assert all(entry["crop"] != "Corn" for entry in result["comparisons"])
    released = json.dumps(farmer_view(result))
    for forbidden in ("scenario_inclusive_acreage", "planned_acreage",
                      "overlapping_farmer_count", "fictional-farmer-", "farmer_id"):
        assert forbidden not in released


def test_suitable_crop_is_not_recommended_without_lower_concentration(repository):
    with repository.connection() as db:
        rows = db.execute("SELECT version_id,payload FROM cultivation_plan_versions").fetchall()
        for row in rows:
            plan = json.loads(row["payload"])
            if plan["crop"] == "Brinjal":
                plan["land_size_acres"] = 10
                db.execute("UPDATE cultivation_plan_versions SET payload=? WHERE version_id=?",
                           (json.dumps(plan), row["version_id"]))
    result = compare(repository)
    assert result["alternatives"] == []
    brinjal = next(entry for entry in result["comparisons"] if entry["crop"] == "Brinjal")
    assert brinjal["status"] == "comparison_available"
    assert brinjal["lower_observed_planned_concentration"] is False


@pytest.mark.parametrize("kind", ["missing", "future", "scope", "suitability", "land"])
def test_evidence_requirements_fail_closed(repository, kind):
    registry = evidence()
    if kind == "missing":
        registry = {}
    elif kind == "future":
        registry["suitability"][0]["available_at"] = "2021-01-01T00:00:00Z"
    elif kind == "scope":
        registry["coverage"][1]["registration_scope_id"] = "different-scope"
    elif kind == "suitability":
        registry["suitability"][0]["applicable_without_additional_inputs"] = False
    else:
        registry["suitability"][0]["max_land_acres"] = 1
    assert compare(repository, registry)["alternatives"] == []


@pytest.mark.parametrize("changes", [dict(district="Hambantota"), dict(region="south"),
    dict(expected_harvest_date="2030-04-02"), dict(as_of="2019-01-01T00:00:00Z")])
def test_isolation_cutoff_and_window_privacy(repository, changes):
    assert compare(repository, **changes)["alternatives"] == []


@pytest.mark.parametrize("changes,status", [
    (dict(replacing_plan_id="fictional-Corn-0"), 404),
    (dict(as_of="2099-01-01T00:00:00Z"), 422),
    (dict(as_of="2020-01-01T00:00:00"), 422)])
def test_ownership_and_cutoff_validation(repository, changes, status):
    with pytest.raises(HTTPException) as error:
        compare(repository, **changes)
    assert error.value.status_code == status
