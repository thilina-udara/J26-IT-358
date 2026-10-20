-- Migration 001: Farmer Transport Tracking & Barcode Management
-- Component 3: Algorithmic Optimization of Circular Bioeconomy Networks (Waste Management & Organic Fertilizer)

CREATE TABLE IF NOT EXISTS barcode_stickers (
    barcode_no TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'available' CHECK(status IN ('available', 'assigned', 'in_transit', 'delivered', 'cancelled')),
    assigned_farmer_id TEXT,
    assigned_transport_id TEXT,
    issued_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE TABLE IF NOT EXISTS transports (
    id TEXT PRIMARY KEY,
    farmer_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Draft' CHECK(status IN ('Draft', 'Ready', 'In Transit', 'Delivered', 'Cancelled')),
    destination_center TEXT NOT NULL,
    total_kg REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE TABLE IF NOT EXISTS transport_items (
    id TEXT PRIMARY KEY,
    transport_id TEXT NOT NULL,
    barcode_no TEXT NOT NULL UNIQUE,
    crop_category TEXT NOT NULL CHECK(crop_category IN ('Vegetable', 'Fruit')),
    food_name TEXT NOT NULL,
    kg REAL NOT NULL CHECK(kg > 0),
    destination_center TEXT NOT NULL,
    origin_district TEXT NOT NULL,
    distance_km REAL NOT NULL,
    transit_hours REAL NOT NULL,
    harvest_datetime TEXT NOT NULL,
    transport_date TEXT NOT NULL,
    transport_time TEXT NOT NULL,
    transport_type TEXT NOT NULL,
    vehicle_no TEXT NOT NULL,
    packing_type TEXT NOT NULL,
    maturity TEXT NOT NULL CHECK(maturity IN ('Under-ripe', 'Ripe', 'Over-ripe')),
    is_covered INTEGER NOT NULL DEFAULT 0,
    has_cooling INTEGER NOT NULL DEFAULT 0,
    is_washed INTEGER NOT NULL DEFAULT 0,
    is_graded INTEGER NOT NULL DEFAULT 1,
    ambient_temp_c REAL,
    ambient_humidity_pct REAL,
    is_rainy INTEGER NOT NULL DEFAULT 0,
    predicted_waste_pct REAL,
    predicted_waste_kg REAL,
    risk_level TEXT CHECK(risk_level IN ('Low', 'Medium', 'High', 'LOW', 'MEDIUM', 'HIGH')),
    advice_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    FOREIGN KEY (transport_id) REFERENCES transports(id) ON DELETE CASCADE,
    FOREIGN KEY (barcode_no) REFERENCES barcode_stickers(barcode_no)
);

CREATE INDEX IF NOT EXISTS idx_transports_farmer ON transports(farmer_id);
CREATE INDEX IF NOT EXISTS idx_transports_status ON transports(status);
CREATE INDEX IF NOT EXISTS idx_transport_items_transport ON transport_items(transport_id);
CREATE INDEX IF NOT EXISTS idx_transport_items_barcode ON transport_items(barcode_no);
CREATE INDEX IF NOT EXISTS idx_barcode_stickers_status ON barcode_stickers(status);

-- Seed pre-issued barcode stickers series (BC-000001 through BC-000050)
INSERT OR IGNORE INTO barcode_stickers (barcode_no, status, issued_at, updated_at) VALUES
('BC-000001', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000002', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000003', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000004', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000005', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000006', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000007', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000008', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000009', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000010', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000011', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000012', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000013', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000014', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000015', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000016', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000017', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000018', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000019', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000020', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000021', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000022', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000023', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000024', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000025', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000026', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000027', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000028', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000029', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000030', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000031', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000032', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000033', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000034', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000035', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000036', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000037', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000038', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000039', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000040', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000041', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000042', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000043', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000044', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000045', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000046', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000047', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000048', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000049', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z'),
('BC-000050', 'available', '2026-10-20T00:00:00Z', '2026-10-20T00:00:00Z');
