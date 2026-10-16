"""
Create disaster-validation linkage between DMC disaster dataset (2018-2026)
and Mahaweli irrigated non-Paddy crop extent dataset (2022-2025).
"""

import os
import sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

# Paths
MAHAWELI_CSV = r"D:\01_research\climate_research_system\11_mahaweli_irrigated_crops\processed\sepc_mahaweli_nonpaddy_crop_extent_2022_2025.csv"
DMC_CSV = r"D:\01_research\climate_research_system\13_disaster_validation_data\processed\dmc_disaster_events_2018_2026.csv"
OUT_LINK_CSV = r"D:\01_research\climate_research_system\13_disaster_validation_data\processed\mahaweli_crop_disaster_validation_link.csv"
OUT_SUMMARY_CSV = r"D:\01_research\climate_research_system\13_disaster_validation_data\processed\mahaweli_crop_disaster_validation_summary.csv"

# District mapping for DMC records
DISTRICT_KEYWORDS = {
    'anuradhapura': ['anuradhapura', 'අනුරාධපුර', 'm.guk'],
    'kurunegala': ['kurunegala', 'කුරුණෑගල', 'කුරුනෑගල', 'fudhfy'],
    'polonnaruwa': ['polonnaruwa', 'පොළොන්නරුව', 'පොලොන්නරුව', 'nghyd;dwit', 'නපොනලොන්'],
    'matale': ['matale', 'මාතලේ', 'මාතනල්', 'khj;jis'],
    'badulla': ['badulla', 'බදුල්ල', 'gjs;is'],
    'ampara': ['ampara', 'අම්පාර', 'mk;ghiw'],
    'batticaloa': ['batticaloa', 'මඩකලපුව', 'kl;lf;fsg;g'],
    'trincomalee': ['trincomalee', 'ත්‍රිකුණාමලය', 'ත්‍රීකුණාමලය', 'jp.kiy'],
    'mullaitivu': ['mullaitivu', 'mulaitivu', 'මුලතිව්', 'මුලතිව්න', 'ky;iyj;jpt'],
    'vavuniya': ['vavuniya', 'වව්නියාව', 'ttdpah'],
    'ratnapura': ['ratnapura', 'rathnapura', 'රත්නපුර', 'රත් පුර', ',uj;jpdghp'],
    'hambantota': ['hambantota', 'හම්බන්තොට', 'හම්බන්නතොට', '`k;ghe;njhl;il', '`k;gh'],
    'monaragala': ['monaragala', 'moneragala', 'මොනරාගල', 'nkhduhfy'],
    'kandy': ['kandy', 'මහනුවර', 'නුවර', 'fz;b'],
    'nuwara eliya': ['nuwara eliya', 'nuwaraeliya', 'නුවරඑළිය', 'නුවරඑලිය', 'etnuypah']
}

def identify_dmc_district(row):
    dist_txt = str(row['district']).lower() if pd.notna(row['district']) else ''
    ds_txt = str(row['ds_division']).lower() if pd.notna(row['ds_division']) else ''
    combined = dist_txt + ' ' + ds_txt
    for d, kws in DISTRICT_KEYWORDS.items():
        if any(kw in combined for kw in kws):
            return d
    return ''

# Mahaweli System to Constituent Districts
SYSTEM_DISTRICTS = {
    'Mahaweli H': ['anuradhapura', 'kurunegala'],
    'Mahaweli H 1': ['anuradhapura', 'matale'],
    'Udawalawa': ['ratnapura', 'hambantota', 'monaragala'],
    'Mahaweli B': ['polonnaruwa', 'batticaloa'],
    'Mahaweli C': ['ampara', 'badulla', 'polonnaruwa'],
    'Mahaweli G': ['polonnaruwa', 'matale'],
    'Mahaweli L': ['mullaitivu', 'anuradhapura', 'vavuniya'],
    'Mahaweli D': ['trincomalee', 'polonnaruwa'],
    'Rambakenoya': ['ampara', 'badulla'],
    'Rambakanoya': ['ampara', 'badulla'],
    'Mahaweli Areas': list(DISTRICT_KEYWORDS.keys())
}

# Season Cultivation Windows (Crop Calendar aligned)
SEASON_DATES = {
    '2022/2023 Maha': ('2022-10-01', '2023-03-31'),
    '2023 Yala': ('2023-04-01', '2023-09-30'),
    '2023/2024 Maha': ('2023-10-01', '2024-03-31'),
    '2024 Yala': ('2024-04-01', '2024-09-30'),
    '2024/2025 Maha': ('2024-10-01', '2025-03-31'),
    '2025 Yala': ('2025-04-01', '2025-09-30'),
}

TARGET_DISASTERS = ['Drought', 'Flood', 'Heavy Rain', 'Landslide', 'High Wind']

def main():
    print("=" * 60)
    print("MAHAWELI NON-PADDY CROP EXTENT - DMC DISASTER LINKAGE")
    print("=" * 60)
    
    # Load Datasets
    mahaweli_df = pd.read_csv(MAHAWELI_CSV)
    dmc_df = pd.read_csv(DMC_CSV, low_memory=False)
    
    print(f"Loaded Mahaweli records: {len(mahaweli_df)}")
    print(f"Loaded DMC disaster events: {len(dmc_df)}")
    
    # Pre-process DMC dates and numeric impacts
    dmc_df['r_date'] = pd.to_datetime(dmc_df['report_date'], errors='coerce')
    dmc_df['num_persons'] = pd.to_numeric(dmc_df['affected_persons'], errors='coerce').fillna(0)
    dmc_df['num_families'] = pd.to_numeric(dmc_df['affected_families'], errors='coerce').fillna(0)
    dmc_df['std_district'] = dmc_df.apply(identify_dmc_district, axis=1)
    
    # Filter DMC to target disasters
    dmc_weather = dmc_df[dmc_df['disaster_type'].isin(TARGET_DISASTERS)].copy()
    
    # Linkage columns to populate
    disaster_event_found = []
    disaster_types = []
    earliest_disaster_date = []
    latest_disaster_date = []
    number_of_reports = []
    affected_persons_max = []
    affected_families_max = []
    validation_status = []
    
    for idx, row in mahaweli_df.iterrows():
        season = row['season']
        system = row['mahaweli_system']
        crop = row['crop']
        
        start_d, end_d = SEASON_DATES.get(season, ('', ''))
        # Adjust for Green Gram Meda Kanna (Mid-season in Yala starts in March)
        if 'green gram' in str(crop).lower() and 'yala' in season.lower():
            start_d = start_d.replace('-04-01', '-03-01')
        
        # Check overall DMC archive availability for this season window
        dmc_season = dmc_weather[(dmc_weather['r_date'] >= start_d) & (dmc_weather['r_date'] <= end_d)]
        if len(dmc_season) == 0:
            disaster_event_found.append(False)
            disaster_types.append("")
            earliest_disaster_date.append("")
            latest_disaster_date.append("")
            number_of_reports.append(0)
            affected_persons_max.append("")
            affected_families_max.append("")
            validation_status.append("DMC coverage unavailable")
            continue
        
        dists = SYSTEM_DISTRICTS.get(system, [])
        if not dists:
            disaster_event_found.append(False)
            disaster_types.append("")
            earliest_disaster_date.append("")
            latest_disaster_date.append("")
            number_of_reports.append(0)
            affected_persons_max.append("")
            affected_families_max.append("")
            validation_status.append("Requires manual review")
            continue
        
        # Filter DMC events matching system districts
        sub = dmc_season[dmc_season['std_district'].isin(dists)]
        
        if len(sub) == 0:
            disaster_event_found.append(False)
            disaster_types.append("")
            earliest_disaster_date.append("")
            latest_disaster_date.append("")
            number_of_reports.append(0)
            affected_persons_max.append("")
            affected_families_max.append("")
            validation_status.append("No disaster reported")
        else:
            disaster_event_found.append(True)
            u_types = sorted(sub['disaster_type'].dropna().unique().tolist())
            disaster_types.append("; ".join(u_types))
            earliest_disaster_date.append(str(sub['report_date'].min()))
            latest_disaster_date.append(str(sub['report_date'].max()))
            number_of_reports.append(len(sub))
            
            p_max = sub['num_persons'].max()
            f_max = sub['num_families'].max()
            affected_persons_max.append(str(int(p_max)) if p_max > 0 else "")
            affected_families_max.append(str(int(f_max)) if f_max > 0 else "")
            
            if system == 'Mahaweli Areas':
                # Aggregate system-wide total row covers multi-basin geography
                validation_status.append("Requires manual review")
            else:
                validation_status.append("Disaster reported")
    
    # Add columns to Mahaweli dataframe
    mahaweli_df['disaster_event_found'] = disaster_event_found
    mahaweli_df['disaster_types'] = disaster_types
    mahaweli_df['earliest_disaster_date'] = earliest_disaster_date
    mahaweli_df['latest_disaster_date'] = latest_disaster_date
    mahaweli_df['number_of_reports'] = number_of_reports
    mahaweli_df['affected_persons_max'] = affected_persons_max
    mahaweli_df['affected_families_max'] = affected_families_max
    mahaweli_df['validation_status'] = validation_status
    
    # Save the linked dataset
    mahaweli_df.to_csv(OUT_LINK_CSV, index=False, encoding='utf-8')
    print(f"\nSaved linked dataset to:\n  {OUT_LINK_CSV}")
    
    # Compute Validation & Summary Statistics
    total_records = len(mahaweli_df)
    disaster_reported_count = (mahaweli_df['validation_status'] == 'Disaster reported').sum()
    no_disaster_count = (mahaweli_df['validation_status'] == 'No disaster reported').sum()
    manual_review_count = (mahaweli_df['validation_status'] == 'Requires manual review').sum()
    coverage_unavail_count = (mahaweli_df['validation_status'] == 'DMC coverage unavailable').sum()
    
    print("\n" + "=" * 60)
    print("VALIDATION STATUS SUMMARY")
    print("=" * 60)
    print(f"Total Crop-Season-System Records : {total_records}")
    print(f"  - Disaster reported             : {disaster_reported_count} ({disaster_reported_count*100/total_records:.1f}%)")
    print(f"  - No disaster reported          : {no_disaster_count} ({no_disaster_count*100/total_records:.1f}%)")
    print(f"  - Requires manual review        : {manual_review_count} ({manual_review_count*100/total_records:.1f}%)")
    print(f"  - DMC coverage unavailable      : {coverage_unavail_count} ({coverage_unavail_count*100/total_records:.1f}%)")
    
    # Disaster Type Frequency across records where disaster reported or under review
    disaster_freq = {}
    for d_str in mahaweli_df['disaster_types'].dropna():
        if not d_str: continue
        for d in d_str.split('; '):
            disaster_freq[d] = disaster_freq.get(d, 0) + 1
    
    print("\nDisaster Type Frequency across Mahaweli records:")
    for d, cnt in sorted(disaster_freq.items(), key=lambda x: -x[1]):
        print(f"  {d:<22}: {cnt} records")
    
    # Yearly / Seasonal Coverage
    seasonal_summary = mahaweli_df.groupby(['season', 'data_year', 'water_year', 'validation_status']).size().unstack(fill_value=0)
    print("\nSeasonal & Water Year Disaster Coverage:")
    print(seasonal_summary.to_string())
    
    # Build Detailed Summary Report CSV
    summary_rows = []
    # Section 1: Overview counts
    summary_rows.append({"category": "Overview", "metric": "total_crop_season_system_records", "value": total_records})
    summary_rows.append({"category": "Overview", "metric": "records_disaster_reported", "value": disaster_reported_count})
    summary_rows.append({"category": "Overview", "metric": "records_no_disaster_reported", "value": no_disaster_count})
    summary_rows.append({"category": "Overview", "metric": "records_requiring_manual_review", "value": manual_review_count})
    summary_rows.append({"category": "Overview", "metric": "records_dmc_coverage_unavailable", "value": coverage_unavail_count})
    
    # Section 2: Disaster Type Frequency
    for d, cnt in sorted(disaster_freq.items(), key=lambda x: -x[1]):
        summary_rows.append({"category": "Disaster Type Frequency", "metric": f"records_with_{d.lower().replace(' ', '_')}", "value": cnt})
    
    # Section 3: Seasonal Coverage
    season_grp = mahaweli_df.groupby(['season', 'validation_status']).size().unstack(fill_value=0)
    for s in season_grp.index:
        for status_col in season_grp.columns:
            cnt = season_grp.loc[s, status_col]
            summary_rows.append({"category": "Seasonal Coverage", "metric": f"{s} - {status_col}", "value": cnt})
            
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUT_SUMMARY_CSV, index=False, encoding='utf-8')
    print(f"\nSaved summary report to:\n  {OUT_SUMMARY_CSV}")
    
    # Print First 10 and Last 10 Linked Rows
    display_cols = [
        'season', 'mahaweli_system', 'crop', 'disaster_event_found', 
        'disaster_types', 'number_of_reports', 'affected_persons_max', 'validation_status'
    ]
    print("\n" + "=" * 60)
    print("FIRST 10 LINKED RECORDS:")
    print("=" * 60)
    print(mahaweli_df[display_cols].head(10).to_string())
    
    print("\n" + "=" * 60)
    print("LAST 10 LINKED RECORDS:")
    print("=" * 60)
    print(mahaweli_df[display_cols].tail(10).to_string())

if __name__ == '__main__':
    main()
