"""Create disposable fictional plans for local historical analysis tests.

This module is intentionally not imported by the application. It only runs when
invoked as a command and requires CULTIVATION_DEMO_DATA_ENABLED=true.
"""
import argparse
import os
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

from app.services.cultivation_plans import PlanStore


CROPS = ("Bandakka", "Corn", "Mung Beans", "Brinjal", "Pumpkin", "Chillies")
DISTRICTS = ("Matara", "Hambantota")
DEFAULT_FARMERS = ("demo-farmer-02", "demo-farmer-03", "demo-farmer-04")


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _plans(owner_id: str, start: date, end: date) -> list[dict]:
    """Build a balanced, deterministic cohort without pretending it is real data."""
    farmer_ids = (owner_id, *DEFAULT_FARMERS)
    months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    rows: list[dict] = []
    counter = 1
    for month in months:
        planting = date(2026, month, 5)
        if not start <= planting <= end:
            continue
        harvest_month = month + 3
        harvest_year = 2026
        if harvest_month > 12:
            harvest_month -= 12
            harvest_year += 1
        harvest = date(harvest_year, harvest_month, 5)
        for district_index, district in enumerate(DISTRICTS):
            for farmer_index, farmer_id in enumerate(farmer_ids):
                crop = CROPS[(month + district_index + farmer_index) % len(CROPS)]
                region = "matara-central" if district == "Matara" else "hambantota-west"
                rows.append({
                    "plan_id": f"demo-2026-{counter:03d}",
                    "farmer_id": farmer_id,
                    "district": district,
                    "region": region,
                    "crop": crop,
                    "land_size_acres": float(1 + ((month + farmer_index) % 4)),
                    "planting_date": planting.isoformat(),
                    "expected_harvest_date": harvest.isoformat(),
                    "submitted_at": "2025-12-20T00:00:00+00:00",
                    "updated_at": "2025-12-20T00:00:00+00:00",
                    "status": "active",
                    "farmer_declared_season": "Maha" if month <= 5 or month >= 10 else "Yala",
                })
                counter += 1
    return rows


def seed(database: Path, owner_id: str, start: date, end: date, reset: bool) -> int:
    enabled = (
        os.getenv("CULTIVATION_DEMO_DATA_ENABLED", "").lower() == "true"
        or os.getenv("CULTIVATION_RESEARCH_DEMO_ENABLED", "").lower() == "true"
    )
    if not enabled:
        raise RuntimeError(
            "Demo seeding is disabled. Set CULTIVATION_RESEARCH_DEMO_ENABLED=true "
            "or CULTIVATION_DEMO_DATA_ENABLED=true in the local backend environment before running this command."
        )
    resolved = database.resolve()
    operational = Path(os.getenv("CULTIVATION_PLAN_DB", str(Path(__file__).resolve().parents[1] / "storage/cultivation_plans.sqlite3"))).resolve()
    if resolved.name.casefold() != "research_demo.sqlite3" or resolved == operational:
        raise RuntimeError(
            "Data isolation violation: Seeding synthetic demo records into the live operational "
            "farmer database is prohibited. Only an isolated research_demo.sqlite3 target is permitted."
        )
    if end < start:
        raise ValueError("The end date must be on or after the start date.")
    if resolved.exists():
        with closing(sqlite3.connect(f"{resolved.as_uri()}?mode=ro", uri=True)) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "cultivation_plans" in tables and db.execute(
                "SELECT 1 FROM cultivation_plans WHERE plan_id NOT LIKE 'demo-2026-%' LIMIT 1"
            ).fetchone():
                raise RuntimeError("Data isolation violation: target contains non-demo farmer records")
    # PlanStore applies the season migration and creates the plan/version tables.
    PlanStore(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    rows = _plans(owner_id, start, end)
    if not rows:
        raise ValueError("The selected range does not include any supported 2026 planting dates.")

    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS research_demo_metadata (kind TEXT PRIMARY KEY)")
        db.execute("INSERT OR IGNORE INTO research_demo_metadata VALUES ('synthetic_research_only')")
        if reset:
            db.execute("DELETE FROM personalized_plan_versions WHERE plan_id LIKE 'demo-2026-%'")
            db.execute("DELETE FROM cultivation_plan_versions WHERE plan_id LIKE 'demo-2026-%'")
            db.execute("DELETE FROM cultivation_plans WHERE plan_id LIKE 'demo-2026-%'")
        for row in rows:
            db.execute("DELETE FROM cultivation_plan_versions WHERE plan_id=?", (row["plan_id"],))
            db.execute(
                """INSERT OR REPLACE INTO cultivation_plans
                (plan_id, farmer_id, district, region, crop, land_size_acres,
                 planting_date, expected_harvest_date, submitted_at, updated_at,
                 status, farmer_declared_season)
                VALUES (:plan_id, :farmer_id, :district, :region, :crop, :land_size_acres,
                        :planting_date, :expected_harvest_date, :submitted_at, :updated_at,
                        :status, :farmer_declared_season)""",
                row,
            )
            db.execute(
                """INSERT INTO cultivation_plan_versions
                (plan_id, recorded_at, payload)
                VALUES (?, ?, json(?))""",
                (row["plan_id"], row["updated_at"], _payload(row)),
            )
    return len(rows)


def _payload(row: dict) -> str:
    import json

    return json.dumps(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed fictional 2026 cultivation plans for local research testing.")
    default_db = os.getenv("CULTIVATION_RESEARCH_DEMO_DB", "storage/research_demo.sqlite3")
    parser.add_argument("--database", default=default_db)
    parser.add_argument("--owner-id", default="demo-farmer-01", help="Authenticated farmer ID that should own one cohort.")
    parser.add_argument("--from", dest="start", type=_date, default=date(2026, 1, 1))
    parser.add_argument("--to", dest="end", type=_date, default=date(2026, 10, 12))
    parser.add_argument("--reset", action="store_true", help="Replace existing demo-2026-* rows.")
    args = parser.parse_args()
    count = seed(Path(args.database), args.owner_id, args.start, args.end, args.reset)
    print(f"Seeded {count} fictional plans into {Path(args.database).resolve()}.")
    print("Use as_of=2025-12-31T23:59:59Z for the January-October 2026 cohort.")


if __name__ == "__main__":
    main()
