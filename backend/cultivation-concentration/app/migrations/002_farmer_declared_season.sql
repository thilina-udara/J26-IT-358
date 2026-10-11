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
ALTER TABLE cultivation_plans ADD COLUMN farmer_declared_season TEXT
    CHECK(farmer_declared_season IS NULL OR farmer_declared_season IN ('Maha','Yala'));
