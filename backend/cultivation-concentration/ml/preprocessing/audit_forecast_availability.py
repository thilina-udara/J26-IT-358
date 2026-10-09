"""Read-only availability audit; dates and seasonal cutoffs have no defaults.

Optional cutoffs CSV: Target_Year,Season,Forecast_Cutoff (ISO-8601 datetime).
Cutoffs must be supported externally; configuration alone is not evidence.
Only development predictions (2002-2023) are inspected. No models are run.
"""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISTRICTS = {"Matara", "Hambantota"}
CROPS = {"Mung Beans", "Corn", "Bandakka", "Brinjal", "Pumpkin", "Chillies"}
DATE_FIELDS = {
    "publication_date", "published_at", "source_publication_date",
    "revision_date", "revised_at", "data_available_at", "availability_timestamp",
}


def parse_timestamp(value):
    """Require timezone-aware timestamps; never assume time for a date-only value."""
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("Availability/cutoff requires an explicit time and timezone")
    return stamp.astimezone(timezone.utc)


def check_availability(available_at=None, cutoff=None, evidence_verified=False):
    if not available_at:
        return "unverified: missing availability timestamp"
    try:
        available = parse_timestamp(available_at)
    except (ValueError, TypeError, AttributeError):
        return "unverified: invalid or ambiguous availability timestamp"
    if not evidence_verified:
        return "unverified: timestamp lacks verified source/version evidence"
    if not cutoff:
        return "unverified: forecast cutoff not configured"
    boundary = parse_timestamp(cutoff)
    return "available" if available <= boundary else "unavailable at cutoff"


def load_cutoffs(path=None):
    if path is None:
        return {}
    result = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"Target_Year", "Season", "Forecast_Cutoff"}
        if not required <= set(reader.fieldnames or []):
            raise ValueError("Cutoff CSV requires Target_Year,Season,Forecast_Cutoff")
        for row in reader:
            key = (int(row["Target_Year"]), row["Season"])
            if key[1] not in {"Maha", "Yala"} or key in result:
                raise ValueError("Invalid season or duplicate cutoff")
            parse_timestamp(row["Forecast_Cutoff"])
            result[key] = row["Forecast_Cutoff"]
    return result


def inspect_inputs(official_path, training_path):
    with Path(official_path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        official_headers = reader.fieldnames or []
        observations = []
        for row in reader:
            # Ignore final test outcomes; 2022 is the latest history needed.
            if not 2001 <= int(row["year"]) <= 2022:
                continue
            if row["district_name"] in DISTRICTS and row["crop_name"] in CROPS and row["season"] in {"Maha", "Yala"}:
                observations.append(row)
    with Path(training_path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        training_headers = reader.fieldnames or []
        targets = []
        for row in reader:
            if not 2002 <= int(row["Target_Year"]) <= 2023:
                continue
            if row["District"] in DISTRICTS and row["Crop"] in CROPS and row["Season"] in {"Maha", "Yala"}:
                targets.append(row)
    return official_headers, training_headers, observations, targets


def audit_targets(observations, targets, cutoffs=None):
    cutoffs = {} if cutoffs is None else cutoffs
    result = []
    for target in targets:
        year = int(target["Target_Year"])
        if not 2002 <= year <= 2023:
            raise ValueError("Test rows forbidden in audit")
        prior = [row for row in observations
                 if (row["district_name"], row["crop_name"], row["season"]) ==
                 (target["District"], target["Crop"], target["Season"])
                 and int(row["year"]) < year]
        years = sorted(int(row["year"]) for row in prior)
        if len(years) != len(set(years)):
            raise ValueError("Duplicate historical observation")
        cutoff = cutoffs.get((year, target["Season"]))
        # Presence of a date column never independently proves source authenticity.
        statuses = [check_availability(row.get("data_available_at") or row.get("availability_timestamp"), cutoff) for row in prior]
        result.append(dict(District=target["District"], Crop=target["Crop"], Season=target["Season"],
                           Target_Year=year, Historical_Years=years, Historical_Count=len(prior),
                           Count_Matches_Training=len(prior) == int(target["Prior_History_Count"]),
                           Forecast_Cutoff=cutoff, Availability_Verified=False,
                           Availability_Statuses=statuses))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, default=ROOT / "data/official/official_historical_2001_2025.csv")
    parser.add_argument("--training", type=Path, default=ROOT / "data/processed/official_training_dataset.csv")
    parser.add_argument("--cutoffs", type=Path, help="Externally evidenced Maha/Yala forecast cutoffs CSV; no dates assumed")
    args = parser.parse_args(argv)
    oh, th, observations, targets = inspect_inputs(args.official, args.training)
    cutoffs = load_cutoffs(args.cutoffs)
    report = audit_targets(observations, targets, cutoffs)
    for name, headers in (("Official", oh), ("Training", th)):
        print(f"{name} timestamp columns: " + (", ".join(c for c in headers if c.lower() in DATE_FIELDS) or "none"))
    print(f"Development predictions audited: {len(report)}; verified availability: 0")
    print("Required inputs: prior group-specific cultivated area and production; yield derived from both; record coverage determines history count. District/crop/season and forecast year must be specified at cutoff.")
    print("District | Crop | Season | Target year | Historical years | Count | Cutoff | Availability")
    for row in report:
        print(f"{row['District']} | {row['Crop']} | {row['Season']} | {row['Target_Year']} | {','.join(map(str,row['Historical_Years']))} | {row['Historical_Count']} | {row['Forecast_Cutoff'] or 'not configured'} | unverified")
    mismatches = sum(not row["Count_Matches_Training"] for row in report)
    print(f"Historical count mismatches: {mismatches}")
    print("Publication-lag risk: prior-year production/area may be released after the next planting cutoff. Final historical revisions may differ from values originally available. Year labels are not publication evidence.")
    print("Pre-planting assumptions currently needed: every included prior observation and its exact version was available before the evidenced season-specific cutoff; reporting years align with the intended crop season. Neither assumption is verified.")
    print("Future implementation: retain source references, publication timestamps and version-specific revision/availability timestamps. Select the latest verified version available at or before each cutoff; exclude unavailable or unverified observations and recompute features/counts. Do not use a later revision with an earlier original publication date. Audit target-definition changes separately; this audit leaves labels unchanged.")
    print("No pre-planting validity established. No files written; no models run; final test not inspected or evaluated.")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
