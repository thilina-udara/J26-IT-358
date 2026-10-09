"""Standalone registration/storage tests with fictional owners and temporary SQLite."""
import pytest
from fastapi import HTTPException
from app.schemas.cultivation_plan import PlanInput
from app.services.cultivation_plans import PlanStore
from app.services.plan_clustering import snapshot


def value(**changes):
    fields = dict(farmer_id="fictional-owner", district="Matara", region=" North ",
        crop="Corn", land_size_acres=2, planting_date="2030-01-01",
        expected_harvest_date="2030-04-01")
    fields.update(changes)
    return PlanInput.model_validate(fields)


def test_persistence_revision_cutoff_and_idempotent_cancellation(tmp_path):
    store = PlanStore(tmp_path / "fictional.sqlite3")
    saved = store.save(value(), "fictional-owner")["plan"]
    assert saved.region == "north"
    assert store.read(saved.plan_id, "fictional-owner")["concentration"]["total_acreage"] is None
    reopened = PlanStore(store.path)
    updated = reopened.save(value(land_size_acres=3), "fictional-owner", saved.plan_id)["plan"]
    assert updated.submitted_at == saved.submitted_at
    assert snapshot(reopened, saved.updated_at)[0]["land_size_acres"] == 2
    cancelled = reopened.cancel(saved.plan_id, "fictional-owner")["plan"]
    assert cancelled.status == "cancelled"
    assert reopened.cancel(saved.plan_id, "fictional-owner")["plan"].updated_at == cancelled.updated_at
    assert snapshot(reopened, cancelled.updated_at) == []


def test_duplicate_and_conflicting_update_are_atomic(tmp_path):
    store = PlanStore(tmp_path / "fictional.sqlite3")
    first = store.save(value(), "fictional-owner")["plan"]
    second = store.save(value(region="south"), "fictional-owner")["plan"]
    with pytest.raises(HTTPException) as error:
        store.save(value(land_size_acres=9), "fictional-owner")
    assert error.value.status_code == 409
    with pytest.raises(HTTPException):
        store.save(value(), "fictional-owner", second.plan_id)
    assert store.read(second.plan_id, "fictional-owner")["plan"].region == "south"
    with store.connection() as db:
        assert db.execute("SELECT count(*) FROM cultivation_plan_versions").fetchone()[0] == 2
    assert store.read(first.plan_id, "fictional-owner")["plan"].land_size_acres == 2


def test_ownership_district_isolation_and_optimistic_revision_check(tmp_path):
    store = PlanStore(tmp_path / "fictional.sqlite3")
    saved = store.save(value(), "fictional-owner")["plan"]
    other = store.save(value(district="Hambantota"), "fictional-owner")["plan"]
    assert other.plan_id != saved.plan_id
    for action in (lambda: store.read(saved.plan_id, "fictional-other"),
                   lambda: store.cancel(saved.plan_id, "fictional-other")):
        with pytest.raises(HTTPException) as error:
            action()
        assert error.value.status_code == 404
    with pytest.raises(HTTPException) as error:
        store.save(value(), "fictional-other")
    assert error.value.status_code == 403
    store.save(value(land_size_acres=3), "fictional-owner", saved.plan_id)
    with pytest.raises(HTTPException) as error:
        store.save(value(), "fictional-owner", saved.plan_id, saved.updated_at)
    assert error.value.status_code == 409
