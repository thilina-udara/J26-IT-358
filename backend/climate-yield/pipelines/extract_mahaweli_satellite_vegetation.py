"""
Products:
- MODIS/061/MOD13Q1 (Terra 250m, 16-day NDVI & EVI)
- MODIS/061/MYD13Q1 (Aqua 250m, 16-day NDVI & EVI)
- MODIS/061/MOD11A2 (Terra 1km, 8-day LST Day in Celsius)

Study Area:
- 9 Mahaweli Systems: H, H1, Udawalawa, B, C, G, L, D, Rambakan Oya
- Bound by constituent districts dissolved from 06_district_boundaries/lka_admin_boundaries.geojson

Time Period:
- 2022-01-01 to 2025-12-31 (Interleaved 8-day cadence)
- Aligned to Sri Lankan agricultural seasons: Maha (Oct-Mar) & Yala (Apr-Sep)
"""

import os
import sys
import json
import argparse
import datetime
import pandas as pd
from shapely.geometry import shape
from shapely.ops import unary_union
import ee

# ------------------------------------------------------------------------------
# 1. Configuration & Directories
# ------------------------------------------------------------------------------
BASE_DIR = r"D:\01_research\climate_research_system"
OUTPUT_DIR = os.path.join(BASE_DIR, "14_satellite_vegetation_data", "processed")
RAW_EXPORTS_DIR = os.path.join(BASE_DIR, "14_satellite_vegetation_data", "raw_exports")
DISTRICT_GEOJSON = os.path.join(
    BASE_DIR, "06_district_boundaries", "lka_admin_boundaries.geojson", "sri_lanka_district_boundaries.geojson"
)

DEFAULT_OUTPUT_CSV = os.path.join(OUTPUT_DIR, "mahaweli_satellite_vegetation_indices_2022_2025.csv")
DEFAULT_VALIDATION_CSV = os.path.join(OUTPUT_DIR, "satellite_vegetation_validation_report.csv")

# Constituent district mapping per Mahaweli system
SYSTEM_DISTRICTS = {
    "H": ["Anuradhapura", "Kurunegala"],
    "H1": ["Anuradhapura", "Matale"],
    "Udawalawa": ["Ratnapura", "Hambantota", "Monaragala"],
    "B": ["Polonnaruwa", "Batticaloa"],
    "C": ["Ampara", "Badulla", "Polonnaruwa"],
    "G": ["Polonnaruwa", "Matale"],
    "L": ["Mullaitivu", "Anuradhapura", "Vavuniya"],
    "D": ["Trincomalee", "Polonnaruwa"],
    "Rambakan Oya": ["Ampara", "Badulla"]
}

# ------------------------------------------------------------------------------
# 2. Season and Water Year Determination
# ------------------------------------------------------------------------------
def get_season_and_water_year(date_str):
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    year = dt.year
    month = dt.month
    
    if month in [10, 11, 12]:
        season = "Maha"
        water_year = f"{year}/{year + 1}"
    elif month in [1, 2, 3]:
        season = "Maha"
        water_year = f"{year - 1}/{year}"
    else:  # April to September
        season = "Yala"
        water_year = f"{year - 1}/{year}"
        
    return season, water_year

# ------------------------------------------------------------------------------
# 3. Load & Union District Boundaries
# ------------------------------------------------------------------------------
def load_system_geometries(selected_systems=None):
    print(f"Loading district boundaries from {DISTRICT_GEOJSON}...", flush=True)
    with open(DISTRICT_GEOJSON, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
        
    dist_shapes = {}
    for feat in geojson_data["features"]:
        name = feat["properties"]["adm2_name"]
        dist_shapes[name] = shape(feat["geometry"])
        
    system_geoms = {}
    target_systems = selected_systems if selected_systems else list(SYSTEM_DISTRICTS.keys())
    
    for sys_name in target_systems:
        if sys_name not in SYSTEM_DISTRICTS:
            raise ValueError(f"Unknown system name: {sys_name}")
        dist_list = SYSTEM_DISTRICTS[sys_name]
        geoms = [dist_shapes[d] for d in dist_list if d in dist_shapes]
        if not geoms:
            raise ValueError(f"No geometries found for system {sys_name} ({dist_list})")
        u = unary_union(geoms)
        # Simplify geometry with 0.001 deg (~100m) tolerance for optimal GEE computation
        u_simple = u.simplify(0.001, preserve_topology=True)
        system_geoms[sys_name] = u_simple
        
    print(f"Constructed geometries for {len(system_geoms)} Mahaweli system(s): {list(system_geoms.keys())}", flush=True)
    return system_geoms

# ------------------------------------------------------------------------------
# 4. GEE Processing Pipeline
# ------------------------------------------------------------------------------
def run_extraction(project_id="climate-research-511807",
                   start_date="2022-01-01",
                   end_date="2025-12-31",
                   selected_systems=None,
                   output_csv=None,
                   validation_csv=None):
    
    out_csv = output_csv or DEFAULT_OUTPUT_CSV
    val_csv = validation_csv or DEFAULT_VALIDATION_CSV
    
    print(f"Initializing Google Earth Engine with project '{project_id}'...", flush=True)
    ee.Initialize(project=project_id)
    print("GEE initialized successfully!", flush=True)
    
    system_geoms = load_system_geometries(selected_systems)
    
    # Convert Shapely geometries to ee.Geometry
    ee_system_geoms = {sys_name: ee.Geometry(geom.__geo_interface__) for sys_name, geom in system_geoms.items()}
    
    # MODIS collections
    terra_col = ee.ImageCollection("MODIS/061/MOD13Q1").filterDate(start_date, end_date)
    aqua_col = ee.ImageCollection("MODIS/061/MYD13Q1").filterDate(start_date, end_date)
    lst_col = ee.ImageCollection("MODIS/061/MOD11A2").filterDate(start_date, end_date)
    
    print("Fetching image lists from Earth Engine...", flush=True)
    terra_list = terra_col.getInfo()["features"]
    aqua_list = aqua_col.getInfo()["features"]
    
    print(f"Found {len(terra_list)} Terra MOD13Q1 images and {len(aqua_list)} Aqua MYD13Q1 images.", flush=True)
    
    # Combine and sort by date for interleaved 8-day cadence
    all_images = []
    for f in terra_list:
        ms = f["properties"]["system:time_start"]
        date_str = datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
        all_images.append({
            "id": f["id"],
            "date": date_str,
            "product": "MOD13Q1.061",
            "source_product": "MODIS/061/MOD13Q1; MODIS/061/MOD11A2",
            "source_url": "https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1",
            "satellite": "Terra"
        })
        
    for f in aqua_list:
        ms = f["properties"]["system:time_start"]
        date_str = datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
        all_images.append({
            "id": f["id"],
            "date": date_str,
            "product": "MYD13Q1.061",
            "source_product": "MODIS/061/MYD13Q1; MODIS/061/MOD11A2",
            "source_url": "https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MYD13Q1",
            "satellite": "Aqua"
        })
        
    all_images.sort(key=lambda x: x["date"])
    print(f"Total interleaved composite dates: {len(all_images)}", flush=True)
    
    records = []
    export_date = datetime.date.today().strftime("%Y-%m-%d")
    # Build FeatureCollection of target systems for ultra-fast single-pass reduction
    features_list = [
        ee.Feature(ee_geom, {"mahaweli_system": sys_name, "district": ", ".join(SYSTEM_DISTRICTS[sys_name])})
        for sys_name, ee_geom in ee_system_geoms.items()
    ]
    systems_fc = ee.FeatureCollection(features_list)
    
    total_imgs = len(all_images)
    
    for idx, img_meta in enumerate(all_images):
        img_id = img_meta["id"]
        date_str = img_meta["date"]
        prod_name = img_meta["product"]
        source_product = img_meta["source_product"]
        source_url = img_meta["source_url"]
        
        season, water_year = get_season_and_water_year(date_str)
        print(f"[{idx+1}/{total_imgs}] Processing {prod_name} for date {date_str} ({season}, {water_year})...", flush=True)
        
        vi_img = ee.Image(img_id)
        
        # SummaryQA bit 0-1: 0 (Good), 1 (Marginal), 2 (Snow/Ice), 3 (Cloudy)
        # Keep only QA = 0 and QA = 1
        qa = vi_img.select("SummaryQA")
        qa_mask = qa.bitwiseAnd(3).lte(1)
        
        # Scale factors: 0.0001 for NDVI & EVI
        ndvi_scaled = vi_img.select("NDVI").multiply(0.0001).updateMask(qa_mask).rename("ndvi")
        evi_scaled = vi_img.select("EVI").multiply(0.0001).updateMask(qa_mask).rename("evi")
        cloud_free = qa_mask.unmask(0).rename("cloud_free")
        
        # Match MOD11A2 LST (Terra 8-day 1km composite)
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        dt_start = dt - datetime.timedelta(days=4)
        dt_end = dt + datetime.timedelta(days=12)
        lst_subset = lst_col.filterDate(dt_start.strftime("%Y-%m-%d"), dt_end.strftime("%Y-%m-%d"))
        
        # Scale factor: 0.02, Celsius: (LST * 0.02) - 273.15
        lst_c = lst_subset.select("LST_Day_1km").mean().multiply(0.02).subtract(273.15).rename("lst_c")
        
        # Stack bands into one composite image for single-pass reduction across all systems
        combined_img = ee.Image.cat([ndvi_scaled, evi_scaled, lst_c, cloud_free])
        
        try:
            reduced_fc = combined_img.reduceRegions(
                collection=systems_fc,
                reducer=ee.Reducer.mean().combine(ee.Reducer.count(), "", True),
                scale=500
            ).getInfo()
            
            for feat in reduced_fc.get("features", []):
                props = feat["properties"]
                sys_name = props["mahaweli_system"]
                dist_str = props["district"]
                
                cloud_free_pct = (props.get("cloud_free_mean") or 0.0) * 100.0
                pixel_cnt = int(props.get("ndvi_count") or props.get("cloud_free_count") or 0)
                ndvi_mean = props.get("ndvi_mean")
                evi_mean = props.get("evi_mean")
                lst_mean = props.get("lst_c_mean")
                
                # Rule 8: If cloud-free pixel percentage is below 70%, leave index values blank and flag in notes
                if cloud_free_pct < 70.0 or ndvi_mean is None:
                    ndvi_val = ""
                    evi_val = ""
                    lst_val = ""
                    note = f"Cloud-free pixels below threshold ({cloud_free_pct:.2f}% < 70%); indices suppressed; Exported: {export_date}"
                else:
                    ndvi_val = round(float(ndvi_mean), 4)
                    evi_val = round(float(evi_mean), 4)
                    lst_val = round(float(lst_mean), 4) if lst_mean is not None else ""
                    note = f"Valid observation ({cloud_free_pct:.2f}% cloud-free); Exported: {export_date}"
                    
                records.append({
                    "mahaweli_system": sys_name,
                    "district": dist_str,
                    "date": date_str,
                    "season": season,
                    "water_year": water_year,
                    "ndvi_mean": ndvi_val,
                    "evi_mean": evi_val,
                    "lst_day_mean_c": lst_val,
                    "vci": "",
                    "tci": "",
                    "vhi_mean": "",
                    "pixel_count": pixel_cnt,
                    "cloud_free_pct": round(float(cloud_free_pct), 2),
                    "source_product": source_product,
                    "source_url": source_url,
                    "notes": note
                })
        except Exception as ex:
            print(f"Error on image {img_id} date {date_str}: {ex}", flush=True)
            for sys_name in ee_system_geoms.keys():
                dist_str = ", ".join(SYSTEM_DISTRICTS[sys_name])
                records.append({
                    "mahaweli_system": sys_name,
                    "district": dist_str,
                    "date": date_str,
                    "season": season,
                    "water_year": water_year,
                    "ndvi_mean": "",
                    "evi_mean": "",
                    "lst_day_mean_c": "",
                    "vci": "",
                    "tci": "",
                    "vhi_mean": "",
                    "pixel_count": 0,
                    "cloud_free_pct": 0.0,
                    "source_product": source_product,
                    "source_url": source_url,
                    "notes": f"GEE reduction error: {str(ex)[:100]}; Exported: {export_date}"
                })
                
    df = pd.DataFrame(records)
    for col in ["ndvi_mean", "evi_mean", "lst_day_mean_c", "vci", "tci", "vhi_mean"]:
        df[col] = df[col].astype(object)
    
    # --------------------------------------------------------------------------
    # 5. Compute VCI, TCI, and VHI per Mahaweli System (Kogan 1995)
    # --------------------------------------------------------------------------
    print("\nComputing VCI, TCI, and VHI per Mahaweli system according to Kogan (1995)...", flush=True)
    for sys_name in ee_system_geoms.keys():
        sys_mask = df["mahaweli_system"] == sys_name
        
        valid_ndvi_mask = sys_mask & (df["ndvi_mean"] != "")
        ndvi_vals = df.loc[valid_ndvi_mask, "ndvi_mean"].astype(float)
        
        valid_lst_mask = sys_mask & (df["lst_day_mean_c"] != "")
        lst_vals = df.loc[valid_lst_mask, "lst_day_mean_c"].astype(float)
        
        if len(ndvi_vals) > 0:
            ndvi_min = ndvi_vals.min()
            ndvi_max = ndvi_vals.max()
            denom_ndvi = ndvi_max - ndvi_min if ndvi_max > ndvi_min else 1.0
            vci_series = 100.0 * (ndvi_vals - ndvi_min) / denom_ndvi
            vci_series = vci_series.clip(0.0, 100.0)
            df.loc[valid_ndvi_mask, "vci"] = vci_series.round(2).apply(lambda x: f"{x:.2f}")
            
        if len(lst_vals) > 0:
            lst_min = lst_vals.min()
            lst_max = lst_vals.max()
            denom_lst = lst_max - lst_min if lst_max > lst_min else 1.0
            tci_series = 100.0 * (lst_max - lst_vals) / denom_lst
            tci_series = tci_series.clip(0.0, 100.0)
            df.loc[valid_lst_mask, "tci"] = tci_series.round(2).apply(lambda x: f"{x:.2f}")
            
        valid_both = sys_mask & (df["vci"] != "") & (df["tci"] != "")
        if valid_both.any():
            vci_both = df.loc[valid_both, "vci"].astype(float)
            tci_both = df.loc[valid_both, "tci"].astype(float)
            vhi_series = 0.5 * vci_both + 0.5 * tci_both
            df.loc[valid_both, "vhi_mean"] = vhi_series.round(2).apply(lambda x: f"{x:.2f}")
            
    # Save processed CSV
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    target_columns = [
        "mahaweli_system", "district", "date", "season", "water_year",
        "ndvi_mean", "evi_mean", "lst_day_mean_c", "vci", "tci", "vhi_mean",
        "pixel_count", "cloud_free_pct", "source_product", "source_url", "notes"
    ]
    df = df[target_columns]
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"\nSaved CSV ({len(df)} rows) to:\n  {out_csv}", flush=True)
    
    # --------------------------------------------------------------------------
    # 6. Validation and Validation Report
    # --------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)
    total_rows = len(df)
    unique_systems = df["mahaweli_system"].unique().tolist()
    unique_dates = df["date"].unique().tolist()
    date_min = df["date"].min()
    date_max = df["date"].max()
    
    print(f"Total Rows: {total_rows}")
    print(f"Unique Mahaweli Systems ({len(unique_systems)}): {unique_systems}")
    print(f"Unique Dates: {len(unique_dates)}")
    print(f"Date Range: {date_min} to {date_max}")
    
    duplicates = df.duplicated(subset=["mahaweli_system", "date"], keep=False).sum()
    print(f"Duplicate Rows (mahaweli_system + date): {duplicates}")
    
    cloud_suppressed = (df["cloud_free_pct"] < 70.0).sum()
    pct_suppressed = (cloud_suppressed / total_rows) * 100.0 if total_rows > 0 else 0.0
    print(f"Cloud-suppressed Count (< 70% threshold): {cloud_suppressed} / {total_rows} ({pct_suppressed:.2f}%)")
    
    print("\nMissing values by column:")
    val_rows = [
        {"metric": "total_rows", "value": total_rows},
        {"metric": "unique_systems_count", "value": len(unique_systems)},
        {"metric": "unique_systems", "value": "; ".join(unique_systems)},
        {"metric": "unique_dates_count", "value": len(unique_dates)},
        {"metric": "date_min", "value": date_min},
        {"metric": "date_max", "value": date_max},
        {"metric": "duplicate_system_date_rows", "value": duplicates},
        {"metric": "cloud_suppressed_count", "value": cloud_suppressed},
        {"metric": "pct_cloud_suppressed", "value": f"{pct_suppressed:.2f}%"}
    ]
    
    for col in target_columns:
        n_missing = (df[col] == "").sum() + df[col].isna().sum()
        pct_missing = (n_missing / total_rows) * 100.0 if total_rows > 0 else 0.0
        print(f"  {col:20s}: {n_missing:5d} / {total_rows} ({pct_missing:5.1f}%)")
        val_rows.append({"metric": f"missing_{col}", "value": n_missing})
        val_rows.append({"metric": f"pct_missing_{col}", "value": f"{pct_missing:.2f}%"})
        
    print("\nFIRST 10 ROWS:")
    print(df.head(10)[["mahaweli_system", "date", "season", "ndvi_mean", "lst_day_mean_c", "vhi_mean", "cloud_free_pct"]].to_string())
    
    print("\nLAST 10 ROWS:")
    print(df.tail(10)[["mahaweli_system", "date", "season", "ndvi_mean", "lst_day_mean_c", "vhi_mean", "cloud_free_pct"]].to_string())
    
    val_df = pd.DataFrame(val_rows)
    val_df.to_csv(val_csv, index=False, encoding="utf-8")
    print(f"\nSaved validation report to:\n  {val_csv}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Mahaweli Satellite Vegetation Indices via GEE")
    parser.add_argument("--project", type=str, default="climate-research-511807", help="Google Cloud Project ID")
    parser.add_argument("--start_date", type=str, default="2022-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, default="2025-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--systems", type=str, default="", help="Comma-separated system names (e.g. H or H,H1)")
    parser.add_argument("--output_file", type=str, default="", help="Output CSV path")
    parser.add_argument("--validation_file", type=str, default="", help="Validation report CSV path")
    args = parser.parse_args()
    
    selected = [s.strip() for s in args.systems.split(",") if s.strip()] if args.systems else None
    out_file = args.output_file if args.output_file else None
    val_file = args.validation_file if args.validation_file else None
    
    run_extraction(
        project_id=args.project,
        start_date=args.start_date,
        end_date=args.end_date,
        selected_systems=selected,
        output_csv=out_file,
        validation_csv=val_file
    )
