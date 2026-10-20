import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def inspect_db(db_path: Path, name: str):
    print("=" * 70)
    print(f"DATABASE: {name}")
    print(f"FILE: {db_path}")
    print("=" * 70)
    
    if not db_path.exists():
        print("Status: Database file does not exist yet.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print(f"Tables ({len(tables)}): {', '.join(tables)}\n")

    for table in tables:
        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"--- Table: {table} ({count} rows) ---")
        
        # Column names
        cols = [d[0] for d in cur.execute(f"SELECT * FROM {table} LIMIT 0").description]
        print(f"Columns: {', '.join(cols)}")

        # Fetch sample rows
        rows = cur.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 3").fetchall()
        if rows:
            print("Sample Rows (latest 3):")
            for r in rows:
                row_dict = dict(r)
                print(" ", row_dict)
        print()
    conn.close()

if __name__ == "__main__":
    c3_db = BASE_DIR / "backend" / "waste-bioeconomy" / "storage" / "transport_tracking.sqlite3"
    inspect_db(c3_db, "Component 3: Transport Tracking & Spoilage (Waste Bioeconomy)")

    c1_db = BASE_DIR / "backend" / "cultivation-concentration" / "storage" / "cultivation_plans.sqlite3"
    inspect_db(c1_db, "Component 1: Cultivation Plans & Crop Concentration")
