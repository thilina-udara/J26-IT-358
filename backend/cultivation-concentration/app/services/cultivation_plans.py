"""SQLite-backed plans; transactions enforce active-plan identity uniqueness."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException
from app.schemas.cultivation_plan import Plan


class PlanStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS cultivation_plans (
                    plan_id TEXT PRIMARY KEY, farmer_id TEXT NOT NULL,
                    district TEXT NOT NULL CHECK(district IN ('Matara','Hambantota')),
                    region TEXT NOT NULL, crop TEXT NOT NULL CHECK(crop IN ('Mung Beans','Corn','Bandakka','Brinjal','Pumpkin','Chillies')),
                    land_size_acres REAL NOT NULL CHECK(land_size_acres > 0),
                    planting_date TEXT NOT NULL, expected_harvest_date TEXT NOT NULL,
                    submitted_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('active','cancelled')),
                    CHECK(expected_harvest_date >= planting_date)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS unique_active_plan ON cultivation_plans
                    (farmer_id,district,region,crop,planting_date,expected_harvest_date)
                    WHERE status='active';
                CREATE INDEX IF NOT EXISTS plan_overlap ON cultivation_plans
                    (district,region,crop,status,expected_harvest_date);
                CREATE TABLE IF NOT EXISTS cultivation_plan_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT NOT NULL, recorded_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS personalized_plan_versions (
                    revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT NOT NULL, farmer_id TEXT NOT NULL,
                    saved_at TEXT NOT NULL, payload TEXT NOT NULL
                );
            ''')
            # Existing rows can establish only their current version at updated_at.
            # Never backdate a reconstructed version to its original submission.
            import json
            for row in db.execute('SELECT * FROM cultivation_plans WHERE plan_id NOT IN (SELECT plan_id FROM cultivation_plan_versions)').fetchall():
                db.execute('INSERT INTO cultivation_plan_versions(plan_id,recorded_at,payload) VALUES(?,?,?)',
                           (row['plan_id'],row['updated_at'],json.dumps(dict(row))))

    def record_version(self, db, plan):
        db.execute('INSERT INTO cultivation_plan_versions(plan_id,recorded_at,payload) VALUES(?,?,?)',
                   (plan.plan_id,plan.updated_at.isoformat(),plan.model_dump_json()))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, db, plan_id, farmer):
        row = db.execute('SELECT * FROM cultivation_plans WHERE plan_id=? AND farmer_id=?', (plan_id,farmer)).fetchone()
        if row is None:
            raise HTTPException(404, 'Plan not found')
        return Plan.model_validate(dict(row))

    def response(self, db, plan):
        start = plan.expected_harvest_date-timedelta(days=14)
        end = plan.expected_harvest_date+timedelta(days=14)
        count, acreage = db.execute('''SELECT COUNT(*), COALESCE(SUM(land_size_acres),0)
            FROM cultivation_plans WHERE district=? AND region=? AND crop=? AND status='active'
            AND expected_harvest_date BETWEEN ? AND ?''',
            (plan.district,plan.region,plan.crop,start.isoformat(),end.isoformat())).fetchone()
        return dict(plan=plan, concentration=dict(plan_count=None,total_acreage=None,status='suppressed_for_privacy',
            harvest_window_start=start,harvest_window_end=end,
            data_coverage_warning='Only submitted active plans are represented; participation, plan accuracy and completeness are unverified. This is planned acreage concentration, not market oversupply. Small-group aggregates may permit inference; share only with authorized participants.'))

    def read(self, plan_id, farmer):
        with self.connection() as db:
            db.execute('BEGIN')
            return self.response(db,self.get(db,plan_id,farmer))

    def save(self, value, farmer, plan_id=None, expected_updated_at=None, personalized=None):
        if value.farmer_id != farmer:
            raise HTTPException(403,'farmer_id must match authenticated farmer')
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                old = self.get(db,plan_id,farmer) if plan_id else None
                if expected_updated_at is not None and (old is None or old.updated_at!=expected_updated_at):
                    raise HTTPException(409,'Plan changed; regenerate before saving')
                identity = plan_id or str(uuid4())
                fields = value.model_dump(mode='json')
                fields.update(plan_id=identity,submitted_at=old.submitted_at.isoformat() if old else now,updated_at=now)
                if old:
                    db.execute('UPDATE cultivation_plans SET '+','.join(c+'=?' for c in fields if c!='plan_id')+' WHERE plan_id=?',
                               [fields[c] for c in fields if c!='plan_id']+[identity])
                else:
                    db.execute('INSERT INTO cultivation_plans ('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')',list(fields.values()))
                saved = self.get(db,identity,farmer)
                self.record_version(db,saved)
                if personalized is not None:
                    import json
                    payload=dict(personalized,cultivation_updated_at=saved.updated_at.isoformat())
                    db.execute('INSERT INTO personalized_plan_versions(plan_id,farmer_id,saved_at,payload) VALUES(?,?,?,?)',
                               (identity,farmer,now,json.dumps(payload)))
                return self.response(db,saved)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409,'An active plan with the same farmer, location, crop and dates already exists') from exc

    def cancel(self, plan_id, farmer):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            plan = self.get(db,plan_id,farmer)
            if plan.status != 'cancelled':
                db.execute("UPDATE cultivation_plans SET status='cancelled', updated_at=? WHERE plan_id=?",
                           (datetime.now(timezone.utc).isoformat(),plan_id))
                self.record_version(db,self.get(db,plan_id,farmer))
            return self.response(db,self.get(db,plan_id,farmer))
