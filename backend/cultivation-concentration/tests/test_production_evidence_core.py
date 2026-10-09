"""Standalone experimental evidence gates; no real yield or risk claims."""
from datetime import datetime, timezone
from app.schemas.production_risk import ProductionRegistry
from app.services.production_risk import evaluate, farmer_response
from app.services.production_reference import evaluate as reference_evaluate


def test_missing_evidence_withholds_production_and_categories(tmp_path):
    owned = dict(plan_id="fictional", farmer_id="fictional-owner", district="Matara",
        crop="Corn", land_size_acres=2, planting_date="2030-01-01",
        expected_harvest_date="2030-04-01", updated_at="2020-01-01T00:00:00+00:00")
    cutoff = datetime(2026, 1, 1, tzinfo=timezone.utc)
    registry = ProductionRegistry()
    result = evaluate([owned], owned, "Maha", cutoff, registry)
    assert result["experimental_risk_level"] is None
    assert result["expected_total_production_kg"] is None
    assert farmer_response(result)["overlapping_acres"] is None
    reference = reference_evaluate([owned], owned, "Maha", cutoff, registry,
                                   path=tmp_path / "missing-reference.json")
    assert reference["status"] == "insufficient_evidence"
    assert reference["experimental_risk_level"] is None
