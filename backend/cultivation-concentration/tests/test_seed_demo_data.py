"""Focused tests for the guarded local demo-data seed command."""
import sqlite3
from datetime import date

import pytest

from app.seed_demo_data import seed


def test_seed_requires_explicit_development_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("CULTIVATION_DEMO_DATA_ENABLED", raising=False)
    monkeypatch.delenv("CULTIVATION_RESEARCH_DEMO_ENABLED", raising=False)
    with pytest.raises(RuntimeError, match="Demo seeding is disabled"):
        seed(tmp_path / "plans.sqlite3", "owner", date(2026, 1, 1), date(2026, 1, 31), False)


def test_seed_creates_historical_versioned_cohort_and_reset_is_safe(tmp_path, monkeypatch):
    monkeypatch.setenv("CULTIVATION_DEMO_DATA_ENABLED", "true")
    database = tmp_path / "research_demo.sqlite3"
    count = seed(database, "owner", date(2026, 1, 1), date(2026, 3, 31), False)
    assert count == 24
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM cultivation_plans WHERE plan_id LIKE 'demo-2026-%'").fetchone()[0] == 24
        assert db.execute("SELECT COUNT(*) FROM cultivation_plan_versions WHERE plan_id LIKE 'demo-2026-%'").fetchone()[0] == 24
        assert db.execute("SELECT MIN(submitted_at) FROM cultivation_plans WHERE plan_id LIKE 'demo-2026-%'").fetchone()[0] == "2025-12-20T00:00:00+00:00"
    assert seed(database, "owner", date(2026, 1, 1), date(2026, 3, 31), True) == 24
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM cultivation_plans WHERE plan_id LIKE 'demo-2026-%'").fetchone()[0] == 24
