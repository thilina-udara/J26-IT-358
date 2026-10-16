"""
Component 4: Irrigation Reservoir Storage Ingestion Pipeline
AI-Powered Climate Early Warning and Crop Yield Impact Decision Support System

Description:
Automated retrieval of daily operational storage, capacity percentage, rainfall,
and spilling status for 74 Major and 43 Medium irrigation reservoirs in Sri Lanka.
Source: Department of Irrigation Water Management Division & Google Sheets Dashboard.
"""

import os
import io
import urllib.request
import pandas as pd

# ==============================================================================
# 1. Output Directory Configuration
# ==============================================================================
# Save downloaded reservoir spreadsheets in a local 'reservoir_data' folder
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(CURRENT_DIR, "reservoir_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================================================================
# 2. Irrigation Reservoir Sheets Registry
# ==============================================================================
# Defines the specific Google Sheet tabs (gid) and descriptions for Major/Medium reservoirs
SHEETS = [
    {
        "filename": "major_reservoirs_maha_daily_2020_2026.csv",
        "gid": "673998835",
        "desc": "Major Reservoirs Maha season daily effective storage (2020/21 to 2025/26) and long-term average (74 reservoirs)"
    },
    {
        "filename": "major_reservoirs_yala_daily_2022_2026.csv",
        "gid": "1244158041",
        "desc": "Major Reservoirs Yala season daily effective storage (2022 to 2026) and long-term average (74 reservoirs)"
    },
    {
        "filename": "medium_reservoirs_maha_daily_2024_2026.csv",
        "gid": "155979206",
        "desc": "Medium Reservoirs Maha season daily effective storage (2024/25 to 2025/26) (43 reservoirs)"
    },
    {
        "filename": "medium_reservoirs_yala_daily_2023_2026.csv",
        "gid": "1831537855",
        "desc": "Medium Reservoirs Yala season daily effective storage (2023 to 2026) and long-term average (43 reservoirs)"
    },
    {
        "filename": "major_reservoirs_current_daily_snapshot.csv",
        "gid": "1212294664",
        "desc": "Major Reservoirs current operational daily status (water depth, capacity %, rainfall, spilling)"
    },
    {
        "filename": "medium_reservoirs_current_daily_snapshot.csv",
        "gid": "562386515",
        "desc": "Medium Reservoirs current operational daily status (water depth, capacity %, rainfall, spilling)"
    },
    {
        "filename": "major_reservoirs_inflows_sluice_issues.csv",
        "gid": "217395621",
        "desc": "Major Reservoirs operational table with sluice issues (cusec), rainfall (mm), water depth (m)"
    }
]

# ==============================================================================
# 3. Download & Ingestion Routine
# ==============================================================================
summary = []

for s in SHEETS:
    gid = s["gid"]
    fname = s["filename"]
    out_path = os.path.join(OUTPUT_DIR, fname)
    
    # Construct the published CSV export URL from the Google Sheets dashboard
    csv_url = f"https://docs.google.com/spreadsheets/d/e/2PACX-1vTcSGhi9RESl7CMCl1TQnrKe07Gx5Q696YiSB9jneIHqIP9lifpqSErgI3D5k9KtQXSdW5JpycIIr5e/pub?gid={gid}&single=true&output=csv"
    
    print(f"Downloading {fname} (gid: {gid})...")
    req = urllib.request.Request(csv_url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            
            # Save raw bytes to local CSV file
            with open(out_path, "wb") as f:
                f.write(content)
                
            # Parse into pandas to log schema and record statistics
            df = pd.read_csv(io.BytesIO(content))
            file_size_kb = len(content) / 1024
            
            summary.append({
                "file_name": fname,
                "gid": gid,
                "rows": len(df),
                "cols": len(df.columns),
                "size_kb": round(file_size_kb, 1),
                "description": s["desc"],
                "columns": ", ".join(list(df.columns[:8])) + ("..." if len(df.columns) > 8 else "")
            })
            print(f"  -> Saved: {out_path} ({len(df):,} rows, {len(df.columns)} cols, {file_size_kb:.1f} KB)")
    except Exception as e:
        print(f"  -> [Failed] Could not download {fname}: {e}")

# ==============================================================================
# 4. Inventory Metadata Generation
# ==============================================================================
summary_df = pd.DataFrame(summary)
summary_path = os.path.join(OUTPUT_DIR, "irrigation_data_inventory.csv")
summary_df.to_csv(summary_path, index=False)

print(f"\nInventory metadata saved to: {summary_path}")
print(summary_df[["file_name", "rows", "cols", "size_kb"]].to_string())
