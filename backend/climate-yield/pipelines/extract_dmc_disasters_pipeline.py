"""
High-Performance DMC Disaster Dataset Builder (2018 - 2026)
Phase 1: Multi-threaded parallel downloading of all situation reports
Phase 2: Multi-process parallel PDF parsing and extraction across 12 CPU cores
Phase 3: Standardization, deduplication, validation, and reporting
"""

import os
import sys
import re
import csv
import time
import urllib3
import requests
import pandas as pd
import pdfplumber
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# Directory Paths
BASE_DIR = r"D:\01_research\climate_research_system\13_disaster_validation_data"
RAW_DIR = os.path.join(BASE_DIR, "raw_reports")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
CATALOG_PATH = os.path.join(PROCESSED_DIR, "dmc_report_catalog_2018_2026.csv")
OUTPUT_CSV = os.path.join(PROCESSED_DIR, "dmc_disaster_events_2018_2026.csv")
VALIDATION_CSV = os.path.join(PROCESSED_DIR, "dmc_disaster_validation_report.csv")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

COLUMNS = [
    "source_file",
    "source_url",
    "report_title",
    "report_date",
    "disaster_type",
    "province",
    "district",
    "ds_division",
    "event_date",
    "affected_families",
    "affected_persons",
    "deaths",
    "damaged_houses",
    "people_in_safe_locations",
    "crop_information",
    "notes"
]

DISTRICT_PROVINCE_MAP = {
    # Northern
    "jaffna": "Northern", "යාපනය": "Northern", "යාප": "Northern", "aho;g;ghzk": "Northern",
    "kilinochchi": "Northern", "killinochchi": "Northern", "කිලිනොච්චිය": "Northern", "කිලින ොච්චිය": "Northern", "fpspnehr;rp": "Northern",
    "mannar": "Northern", "මන්නාරම": "Northern", "මන් ාරම": "Northern", "kd;dhH": "Northern",
    "vavuniya": "Northern", "වව්නියාව": "Northern", "tTdpah": "Northern",
    "mullaitivu": "Northern", "mulaitivu": "Northern", "මුලතිව්": "Northern", "මුලතිව්න": "Northern", "Ky;iyj;jPT": "Northern",
    
    # North Central
    "anuradhapura": "North Central", "අනුරාධපුර": "North Central", "m.Guk": "North Central",
    "polonnaruwa": "North Central", "පොළොන්නරුව": "North Central", "පොලොන්නරුව": "North Central", "නපොනලොන්": "North Central", "nghyd;dWit": "North Central",
    
    # North Western
    "kurunegala": "North Western", "කුරුණෑගල": "North Western", "කුරුනෑගල": "North Western", "FUdhfy": "North Western",
    "puttalam": "North Western", "පුත්තලම": "North Western", "Gj;jsk": "North Western",
    
    # Central
    "kandy": "Central", "මහනුවර": "Central", "නුවර": "Central", "fz;b": "Central",
    "matale": "Central", "මාතලේ": "Central", "මාතනල්": "Central", "khj;jis": "Central",
    "nuwara eliya": "Central", "nuwaraeliya": "Central", "නුවරඑළිය": "Central", "නුවරඑලිය": "Central", "Etnuypah": "Central",
    
    # Western
    "colombo": "Western", "කොළඹ": "Western", "නකොළඹ": "Western", "nfhOk;G": "Western",
    "gampaha": "Western", "ගම්පහ": "Western", "fk;g`": "Western",
    "kalutara": "Western", "කළුතර": "Western", "fSj;Jiw": "Western",
    
    # Southern
    "galle": "Southern", "ගාල්ල": "Southern", "fhyp": "Southern",
    "matara": "Southern", "මාතර": "Southern", "khj;jiw": "Southern",
    "hambantota": "Southern", "හම්බන්තොට": "Southern", "හම්බන්නතොට": "Southern", "`k;ghe;Njhl;il": "Southern", "`k;gh": "Southern",
    
    # Uva
    "badulla": "Uva", "බදුල්ල": "Uva", "gJs;is": "Uva",
    "monaragala": "Uva", "moneragala": "Uva", "මොනරාගල": "Uva", "nkhduhfy": "Uva",
    
    # Sabaragamuwa
    "ratnapura": "Sabaragamuwa", "rathnapura": "Sabaragamuwa", "රත්නපුර": "Sabaragamuwa", "රත් පුර": "Sabaragamuwa", ",uj;jpdGhp": "Sabaragamuwa",
    "kegalle": "Sabaragamuwa", "kegalla": "Sabaragamuwa", "කෑගල්ල": "Sabaragamuwa", "Nffhiy": "Sabaragamuwa",
    
    # Eastern
    "ampara": "Eastern", "අම්පාර": "Eastern", "mk;ghiw": "Eastern",
    "batticaloa": "Eastern", "මඩකලපුව": "Eastern", "kl;lf;fsg;G": "Eastern",
    "trincomalee": "Eastern", "ත්‍රිකුණාමලය": "Eastern", "ත්‍රීකුණාමලය": "Eastern", "jp.kiy": "Eastern"
}

VALID_PROVINCES = [
    "Eastern", "Northern", "North Central", "North Western", 
    "Central", "Western", "Southern", "Uva", "Sabaragamuwa"
]

def clean_val(v):
    if v is None:
        return ""
    s = str(v).strip().replace("\n", " ")
    s = re.sub(r"\s+", " ", s)
    return s

def clean_num(v):
    if v is None:
        return ""
    s = str(v).strip().replace(",", "").replace(" ", "")
    if re.match(r"^\d+(\.\d+)?$", s):
        try:
            f = float(s)
            return str(int(f)) if f.is_integer() else str(f)
        except:
            return s
    return ""

def standardize_disaster(txt):
    if not txt:
        return ""
    t = txt.lower()
    
    if any(k in t for k in ["nil", "none", "total", "no incident", "disaster", "epiyik", "situation report", "පරිපාලන"]):
        return ""
    
    if any(k in t for k in ["drought", "dry weather", "water scarcity", "drinking water", "වියළි", "වරட்சி", "குடிநீர்"]):
        return "Drought"
    
    if any(k in t for k in ["flood", "flash flood", "inundat", "overflow", "water logging", "water level", "ජල ගැලීම්", "ගංවතුර", "வெள்ள"]):
        return "Flood"
    
    if any(k in t for k in [
        "landslide", "cutting failure", "cutting faliture", "slope failure", 
        "rock fall", "rockfall", "rock fallen", "earth slip", "subsidence", "නාය", "පස්කඳු", "மண்சரிவு"
    ]):
        return "Landslide"
    
    if any(k in t for k in ["heavy rain", "heavy shower", "torrential", "rain and cutting", "තද වැසි", "கடும் மழை"]):
        return "Heavy Rain"
    
    if any(k in t for k in [
        "high wind", "strong wind", "gale", "tornado", "cyclone", "mine cyclone", 
        "mini cyclone", "wind", "tree fall", "tree fallen", "සුළං", "காற்று"
    ]):
        return "High Wind"
    
    if any(k in t for k in [
        "lightning", "thunder", "hail", "sea swell", "surge", "sea wave", 
        "coastal erosion", "waves of sea", "sea water", "අකුණු", "கடல்"
    ]):
        return "Other Weather Event"
    
    if "rain" in t:
        return "Heavy Rain"
    
    return ""

def get_province(prov_cell, dist_cell):
    if dist_cell:
        d_low = dist_cell.lower()
        for k, p in DISTRICT_PROVINCE_MAP.items():
            if k in d_low:
                return p
    
    if prov_cell:
        p_low = prov_cell.lower()
        if not any(k in p_low for k in ["secretary", "ministry", "ලේකම්", "අමාත්‍යාංශය", "director", "department"]):
            for p in VALID_PROVINCES:
                if p.lower() in p_low:
                    return p
    return ""

def download_task(item):
    source_url, fpath = item
    if os.path.exists(fpath) and os.path.getsize(fpath) >= 1000:
        return fpath, True
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(source_url, headers=headers, timeout=20, verify=False)
        if len(r.content) >= 1000 and r.content.startswith(b"%PDF"):
            with open(fpath, "wb") as f:
                f.write(r.content)
            return fpath, True
        return fpath, False
    except Exception:
        return fpath, False

def parse_report_file(item):
    source_file, source_url, report_title, report_date, fpath = item
    if not os.path.exists(fpath) or os.path.getsize(fpath) < 1000:
        return []
    
    extracted = []
    try:
        with pdfplumber.open(fpath) as pdf:
            curr_prov = ""
            curr_dist = ""
            curr_dis = ""
            
            for pno, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if not tables:
                    continue
                
                for table in tables:
                    if len(table) < 2:
                        continue
                    
                    is_20_col = False
                    first_rows_txt = " ".join([" ".join([clean_val(c) for c in r]) for r in table[:4]]).lower()
                    if len(table[0]) >= 20 or "in relatives" in first_rows_txt or "ඥාති" in first_rows_txt:
                        is_20_col = True
                    
                    for row in table:
                        if len(row) < 8:
                            continue
                        
                        clean_row = [clean_val(c) for c in row]
                        row_str = " ".join(clean_row).lower()
                        
                        if any(k in row_str for k in [
                            "district total", "province total", "national total", "grand total", 
                            "දිස්ත්‍රික් එකතුව", "දිස්ික් එකතුෙ", "පළාත් ඵකතුව", "මුළු එකතුව", "$l;Lj;njhif"
                        ]):
                            continue
                        
                        if any(k in row_str for k in [
                            "administrative purvie", "date of commenced", "epiyik mwpf", "situation report", 
                            "ministry of disaster", "private secretary", "hon. minister", "ආරම්භක දිනය", "පරිපාලන ප්‍රදේශය"
                        ]):
                            continue
                        
                        d_idx = -1
                        for idx, c in enumerate(clean_row):
                            if c and re.search(r"\b20\d\d[./-]\d\d", c):
                                d_idx = idx
                                break
                        
                        if d_idx >= 2:
                            raw_dist = clean_row[d_idx - 3] if d_idx - 3 >= 0 else ""
                            if raw_dist and not any(k in raw_dist.lower() for k in ["district", "දිස්ත්‍රික්", "khtl;l", "#", "province", "පළාත"]):
                                curr_dist = raw_dist
                            
                            ds_cell = clean_row[d_idx - 2] if d_idx - 2 >= 0 else ""
                            
                            raw_dis = clean_row[d_idx - 1] if d_idx - 1 >= 0 else ""
                            dis_std = standardize_disaster(raw_dis)
                            if dis_std:
                                curr_dis = dis_std
                            elif not dis_std and curr_dis:
                                dis_std = curr_dis
                            
                            if not dis_std:
                                dis_std = standardize_disaster(ds_cell)
                                if dis_std:
                                    ds_cell = ""
                            
                            if not dis_std:
                                continue
                            
                            date_cell = clean_row[d_idx]
                            
                            if is_20_col and len(clean_row) >= 19:
                                safe_people = clean_num(clean_row[d_idx + 3]) if d_idx + 3 < len(clean_row) else ""
                                fam = clean_num(clean_row[d_idx + 6]) if d_idx + 6 < len(clean_row) else ""
                                people = clean_num(clean_row[d_idx + 7]) if d_idx + 7 < len(clean_row) else ""
                                deaths = clean_num(clean_row[d_idx + 8]) if d_idx + 8 < len(clean_row) else ""
                                h_full = clean_num(clean_row[d_idx + 11]) if d_idx + 11 < len(clean_row) else ""
                                h_part = clean_num(clean_row[d_idx + 12]) if d_idx + 12 < len(clean_row) else ""
                                remarks = clean_row[-1]
                            else:
                                fam = clean_num(clean_row[d_idx + 1]) if d_idx + 1 < len(clean_row) else ""
                                people = clean_num(clean_row[d_idx + 2]) if d_idx + 2 < len(clean_row) else ""
                                deaths = clean_num(clean_row[d_idx + 3]) if d_idx + 3 < len(clean_row) else ""
                                h_full = clean_num(clean_row[d_idx + 6]) if d_idx + 6 < len(clean_row) else ""
                                h_part = clean_num(clean_row[d_idx + 7]) if d_idx + 7 < len(clean_row) else ""
                                safe_people = clean_num(clean_row[d_idx + 12]) if d_idx + 12 < len(clean_row) else ""
                                remarks = clean_row[-1]
                            
                            dmg_houses = ""
                            h_notes = []
                            if h_full and h_full != "0":
                                h_notes.append(f"Fully damaged: {h_full}")
                            if h_part and h_part != "0":
                                h_notes.append(f"Partially damaged: {h_part}")
                            
                            if h_full and h_part:
                                try:
                                    dmg_houses = str(int(h_full) + int(h_part))
                                except:
                                    dmg_houses = f"{h_full} (fully) + {h_part} (partially)"
                            elif h_full:
                                dmg_houses = h_full
                            elif h_part:
                                dmg_houses = h_part
                            
                            crop_info = ""
                            if any(k in remarks.lower() for k in [
                                "crop", "crops", "paddy", "cultivat", "harvest", "vegetable", 
                                "acre", "hectare", "farming", "කුඹුරු", "වගා", "ගොවි", "பயிர்", "நெல்"
                            ]):
                                crop_info = remarks
                            
                            raw_prov = clean_row[0] if d_idx - 3 > 0 else ""
                            prov = get_province(raw_prov, curr_dist)
                            if not prov and curr_prov:
                                prov = curr_prov
                            elif prov:
                                curr_prov = prov
                            
                            notes_parts = [f"PDF page {pno + 1}"]
                            if h_notes:
                                notes_parts.append("; ".join(h_notes))
                            if remarks and remarks != crop_info:
                                notes_parts.append(remarks)
                            notes = " | ".join(notes_parts)
                            
                            extracted.append({
                                "source_file": source_file,
                                "source_url": source_url,
                                "report_title": report_title,
                                "report_date": report_date,
                                "disaster_type": dis_std,
                                "province": prov,
                                "district": curr_dist,
                                "ds_division": ds_cell,
                                "event_date": date_cell,
                                "affected_families": fam,
                                "affected_persons": people,
                                "deaths": deaths,
                                "damaged_houses": dmg_houses,
                                "people_in_safe_locations": safe_people,
                                "crop_information": crop_info,
                                "notes": notes
                            })
    except Exception:
        pass
    
    return extracted

def main():
    print("=" * 60, flush=True)
    print("DMC DISASTER DATASET BUILDER (2018 - 2026)", flush=True)
    print("=" * 60, flush=True)
    
    if not os.path.exists(CATALOG_PATH):
        print(f"Error: Catalog not found at {CATALOG_PATH}", flush=True)
        return
    
    catalog_df = pd.read_csv(CATALOG_PATH)
    catalog_df = catalog_df.dropna(subset=["source_file", "source_url"])
    catalog_df = catalog_df[catalog_df["source_file"].astype(str).str.strip() != ""]
    catalog_df = catalog_df[catalog_df["source_file"].astype(str).str.lower().str.endswith(".pdf")]
    total_reports = len(catalog_df)
    print(f"Total valid PDF reports in catalog: {total_reports}", flush=True)
    
    # ----------------------------------------------------
    # PHASE 1: High-Speed Multi-Threaded Download
    # ----------------------------------------------------
    print("\n[PHASE 1] Checking / Downloading PDF files (30 worker threads)...", flush=True)
    download_items = []
    for _, r in catalog_df.iterrows():
        fpath = os.path.join(RAW_DIR, r["source_file"])
        download_items.append((r["source_url"], fpath))
    
    t0_dl = time.time()
    dl_done = 0
    with ThreadPoolExecutor(max_workers=30) as dl_exec:
        futures = [dl_exec.submit(download_task, item) for item in download_items]
        for f in as_completed(futures):
            dl_done += 1
            if dl_done % 500 == 0 or dl_done == total_reports:
                dt = time.time() - t0_dl
                pct = dl_done * 100 / total_reports
                speed = dl_done / dt if dt > 0 else 0
                print(f"  Downloaded/Checked: {dl_done}/{total_reports} ({pct:5.1f}%) | Speed: {speed:4.1f} files/s | Elapsed: {dt/60:4.1f}m", flush=True)
    
    print(f"Phase 1 complete in {(time.time() - t0_dl)/60:.2f} minutes!", flush=True)
    
    # ----------------------------------------------------
    # PHASE 2: Multi-Process Parsing Across CPU Cores
    # ----------------------------------------------------
    print("\n[PHASE 2] Parsing reports and extracting disaster tables (12 CPU cores)...", flush=True)
    parse_items = []
    for _, r in catalog_df.iterrows():
        fpath = os.path.join(RAW_DIR, r["source_file"])
        parse_items.append((
            r["source_file"],
            r["source_url"],
            r["report_title"],
            r["report_date"],
            fpath
        ))
    
    # Initialize output CSV with headers
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
    
    t0_parse = time.time()
    parsed_count = 0
    total_extracted_rows = 0
    batch_rows = []
    
    with ProcessPoolExecutor(max_workers=12) as parse_exec:
        futures = {parse_exec.submit(parse_report_file, item): item for item in parse_items}
        for future in as_completed(futures):
            parsed_count += 1
            try:
                res = future.result()
                if res:
                    batch_rows.extend(res)
            except Exception:
                pass
            
            if parsed_count % 200 == 0 or parsed_count == total_reports:
                if batch_rows:
                    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=COLUMNS)
                        writer.writerows(batch_rows)
                    total_extracted_rows += len(batch_rows)
                    batch_rows = []
                
                dt = time.time() - t0_parse
                pct = parsed_count * 100 / total_reports
                speed = parsed_count / dt if dt > 0 else 0
                print(f"  Parsed: {parsed_count}/{total_reports} ({pct:5.1f}%) | "
                      f"Incident rows: {total_extracted_rows} | Speed: {speed:4.1f} rep/s | Elapsed: {dt/60:4.1f}m", flush=True)
    
    if batch_rows:
        with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writerows(batch_rows)
        total_extracted_rows += len(batch_rows)
    
    print(f"Phase 2 complete in {(time.time() - t0_parse)/60:.2f} minutes!", flush=True)
    print(f"Total raw disaster event rows extracted: {total_extracted_rows}", flush=True)
    
    # ----------------------------------------------------
    # PHASE 3: Deduplication & Validation
    # ----------------------------------------------------
    print("\n[PHASE 3] Running deduplication and validation...", flush=True)
    df = pd.read_csv(OUTPUT_CSV)
    
    dup_cols = ["source_file", "report_date", "disaster_type", "province", "district", "ds_division"]
    duplicates_count = int(df.duplicated(subset=dup_cols, keep="first").sum())
    print(f"Duplicate rows identified by {dup_cols}: {duplicates_count}", flush=True)
    
    if duplicates_count > 0:
        df = df.drop_duplicates(subset=dup_cols, keep="first").reset_index(drop=True)
        print(f"Removed duplicates. Final clean row count: {len(df)}", flush=True)
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    else:
        print(f"Dataset has 0 duplicates! Clean row count: {len(df)}", flush=True)
    
    # Validation Metrics
    total_rows = len(df)
    unique_disaster_types = df["disaster_type"].dropna().unique().tolist()
    unique_districts = df["district"].dropna().unique().tolist()
    
    df["year"] = pd.to_datetime(df["report_date"], errors="coerce").dt.year
    unique_years = sorted([int(y) for y in df["year"].dropna().unique()])
    date_min = str(df["report_date"].min())
    date_max = str(df["report_date"].max())
    
    missing_counts = {col: int(df[col].isna().sum() + (df[col] == "").sum()) for col in COLUMNS}
    
    print("\n" + "=" * 60, flush=True)
    print("DMC DISASTER DATASET VALIDATION REPORT", flush=True)
    print("=" * 60, flush=True)
    print(f"Total Row Count: {total_rows}", flush=True)
    print(f"Unique Disaster Types ({len(unique_disaster_types)}):", flush=True)
    print(" ", unique_disaster_types, flush=True)
    print(f"\nUnique Districts ({len(unique_districts)}):", flush=True)
    for d in unique_districts[:15]:
        print(f"  - {d}", flush=True)
    if len(unique_districts) > 15:
        print(f"  ... and {len(unique_districts) - 15} more districts", flush=True)
    print(f"\nUnique Years ({len(unique_years)}):", flush=True)
    print(" ", unique_years, flush=True)
    print(f"\nDate Range: {date_min} to {date_max}", flush=True)
    print("\nMissing-Value Counts by Column:", flush=True)
    for col in COLUMNS:
        cnt = missing_counts[col]
        pct = (cnt / total_rows * 100) if total_rows > 0 else 0
        print(f"  {col:<26}: {cnt:>6} / {total_rows} ({pct:5.1f}%)", flush=True)
    
    print("\nDuplicate Check Result:", flush=True)
    print(f"  Duplicates found: {duplicates_count}", flush=True)
    
    print("\nFirst 10 Rows:", flush=True)
    display_cols = ["report_date", "disaster_type", "province", "district", "ds_division", "affected_families", "affected_persons"]
    print(df[display_cols].head(10).to_string(), flush=True)
    
    print("\nLast 10 Rows:", flush=True)
    print(df[display_cols].tail(10).to_string(), flush=True)
    
    # Save Validation Report CSV
    validation_records = [
        {"metric": "total_rows", "value": total_rows},
        {"metric": "unique_disaster_types_count", "value": len(unique_disaster_types)},
        {"metric": "unique_disaster_types", "value": "; ".join(unique_disaster_types)},
        {"metric": "unique_districts_count", "value": len(unique_districts)},
        {"metric": "unique_districts", "value": "; ".join([str(d) for d in unique_districts[:30]])},
        {"metric": "unique_years_count", "value": len(unique_years)},
        {"metric": "unique_years", "value": "; ".join(map(str, unique_years))},
        {"metric": "date_range_start", "value": date_min},
        {"metric": "date_range_end", "value": date_max},
        {"metric": "duplicate_rows_count", "value": duplicates_count}
    ]
    for col in COLUMNS:
        validation_records.append({
            "metric": f"missing_{col}",
            "value": missing_counts[col]
        })
    
    val_df = pd.DataFrame(validation_records)
    val_df.to_csv(VALIDATION_CSV, index=False, encoding="utf-8")
    print(f"\nValidation report saved to {VALIDATION_CSV}", flush=True)
    print(f"Clean master dataset saved to {OUTPUT_CSV}", flush=True)

if __name__ == "__main__":
    main()
