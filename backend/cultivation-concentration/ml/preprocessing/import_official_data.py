"""Development-only official importer. Default SQL transaction ends in ROLLBACK.

Execute only against the isolated validator database using its local owner.
Hash refers to the selected development artifact, never final-test file bytes.
Changed record payloads are rejected: revision ordering requires source evidence.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
COLUMNS = ('district_name','crop_name','year','season','cultivated_extent_hectares','production_metric_tons')
DISTRICTS = {'Matara','Hambantota'}
CROPS = {'Mung Beans','Corn','Bandakka','Brinjal','Pumpkin','Chillies'}


def prepare(path, expected_rows=532):
    selected, skipped, rejected, seen = [], Counter(), [], set()
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(COLUMNS):
            raise ValueError('Exact official CSV schema required; farmer/legacy files forbidden')
        for line, row in enumerate(reader, 2):
            # Only year is examined before discarding final-test row contents.
            try:
                year = int(row['year'])
            except (ValueError, TypeError):
                rejected.append((line, 'invalid year')); continue
            if year >= 2024:
                skipped['final-test/outside-development'] += 1; continue
            if row['season'] == 'Total':
                skipped['annual Total'] += 1; continue
            try:
                if not 2001 <= year <= 2023 or row['district_name'] not in DISTRICTS or row['crop_name'] not in CROPS or row['season'] not in {'Maha','Yala'}:
                    raise ValueError('unsupported scope')
                if None in row or any(row[c] is None for c in COLUMNS):
                    raise ValueError('malformed row')
                for column in COLUMNS[-2:]:
                    value = Decimal(row[column])
                    if not value.is_finite() or value < 0:
                        raise ValueError('invalid nonnegative measurement')
                key = (row['district_name'],row['crop_name'],row['season'],year)
                if key in seen:
                    raise ValueError('duplicate canonical key')
                seen.add(key); selected.append(row)
            except (ValueError, InvalidOperation) as exc:
                rejected.append((line,str(exc)))
    coverage = {(r['district_name'],r['crop_name'],r['season']) for r in selected}
    required = {(d,c,s) for d in DISTRICTS for c in CROPS for s in ('Maha','Yala')}
    if expected_rows is not None:
        if len(selected) != expected_rows:
            rejected.append((0,f'expected {expected_rows} seasonal development rows, found {len(selected)}'))
        if coverage != required:
            rejected.append((0,'incomplete district/crop/season coverage'))
        if {int(r['year']) for r in selected} != set(range(2001,2024)):
            rejected.append((0,'incomplete development year coverage'))
    return selected, skipped, rejected


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def make_import_sql(rows, commit=False):
    canonical = sorted(rows, key=lambda r: (r['district_name'],r['crop_name'],r['season'],int(r['year'])))
    artifact_hash = hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    statements = ["BEGIN;", "SELECT pg_advisory_xact_lock(358,2);", "CREATE TEMP TABLE import_counts(inserted int, skipped int); INSERT INTO import_counts VALUES(0,0);",
        "DO $$ BEGIN IF current_database()<>'c2_schema_validation' OR current_user<>'c2_local_owner' THEN RAISE EXCEPTION 'Isolated validation database/owner required'; END IF; END $$;",
        "INSERT INTO c2.data_source(source_key,name,provenance,domain,source_uri) VALUES('official-development-csv','Official-designated CSV; independent origin unverified','official','cultivation','data/official/official_historical_2001_2025.csv') ON CONFLICT(source_key) DO NOTHING;",
        "DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM c2.data_source WHERE source_key='official-development-csv' AND provenance='official' AND domain='cultivation' AND provenance_evidence_uri IS NULL) THEN RAISE EXCEPTION 'Source registration conflict'; END IF; END $$;",
        f"INSERT INTO c2.import_batch(source_id,artifact_sha256,artifact_uri) SELECT source_id,{quote(artifact_hash)},'selection://official-csv/years-2001-2023/Maha-Yala/v1' FROM c2.data_source WHERE source_key='official-development-csv' ON CONFLICT(source_id,artifact_sha256) DO NOTHING;"]
    for name in sorted({r['district_name'] for r in rows}):
        statements.append(f"INSERT INTO c2.district(name) VALUES({quote(name)}) ON CONFLICT(name) DO NOTHING;")
    for name in sorted({r['crop_name'] for r in rows}):
        statements.append(f"INSERT INTO c2.crop(name,definition) VALUES({quote(name)},'As reported by CSV; agronomic definition unverified') ON CONFLICT(name) DO NOTHING;")
    for name in sorted({r['season'] for r in rows}):
        statements.append(f"INSERT INTO c2.season(name,is_annual_total) VALUES({quote(name)},false) ON CONFLICT(name) DO NOTHING;")
    for r in canonical:
        payload = dict(original_values=r, original_units={'cultivated_extent_hectares':'hectares','production_metric_tons':'metric tons'},
                       source_metadata={'path':'data/official/official_historical_2001_2025.csv','source_designation':'official','independent_origin_verified':False,'availability_verified':False})
        serialized = json.dumps(payload,sort_keys=True,separators=(',',':'))
        digest = hashlib.sha256(serialized.encode()).hexdigest()
        key = json.dumps([r['district_name'],r['crop_name'],r['season'],int(r['year'])],separators=(',',':'))
        statements.append(f"""DO $import$
DECLARE src bigint; batch bigint; did bigint; cid bigint; sid bigint; rid bigint; vid bigint; existing_hash text;
BEGIN
 SELECT source_id INTO src FROM c2.data_source WHERE source_key='official-development-csv';
 SELECT batch_id INTO batch FROM c2.import_batch WHERE source_id=src AND artifact_sha256={quote(artifact_hash)};
 SELECT district_id INTO did FROM c2.district WHERE name={quote(r['district_name'])};
 SELECT crop_id INTO cid FROM c2.crop WHERE name={quote(r['crop_name'])};
 SELECT season_id INTO sid FROM c2.season WHERE name={quote(r['season'])};
 SELECT record_id INTO rid FROM c2.source_record WHERE source_id=src AND district_id=did AND crop_id=cid AND season_id=sid AND observation_year={int(r['year'])} AND grain='district_season';
 IF rid IS NOT NULL THEN
   SELECT payload_sha256 INTO existing_hash FROM c2.record_version WHERE record_id=rid ORDER BY revision_number DESC LIMIT 1;
   IF existing_hash IS DISTINCT FROM {quote(digest)} THEN RAISE EXCEPTION 'Changed or incomplete observation: explicit evidence-backed revision workflow required'; END IF;
   IF NOT EXISTS(SELECT 1 FROM c2.cultivation_observation o JOIN c2.record_version v USING(version_id) JOIN c2.availability_evidence a USING(version_id) WHERE v.record_id=rid AND v.payload_sha256={quote(digest)}) THEN RAISE EXCEPTION 'Incomplete existing import'; END IF;
   UPDATE import_counts SET skipped=skipped+1;
 ELSE
   INSERT INTO c2.source_record(source_id,provenance,domain,natural_key,observation_year,district_id,crop_id,season_id,grain)
   VALUES(src,'official','cultivation',{quote(key)},{int(r['year'])},did,cid,sid,'district_season') RETURNING record_id INTO rid;
   INSERT INTO c2.record_version(record_id,source_id,batch_id,revision_number,payload_sha256,raw_payload)
   VALUES(rid,src,batch,0,{quote(digest)},{quote(serialized)}::jsonb) RETURNING version_id INTO vid;
   INSERT INTO c2.cultivation_observation(version_id,record_id,district_id,crop_id,season_id,grain,measure_kind,land_acres,production_kg)
   VALUES(vid,rid,did,cid,sid,'district_season','observed', {quote(r['cultivated_extent_hectares'])}::numeric*2.4710538147,{quote(r['production_metric_tons'])}::numeric*1000);
   INSERT INTO c2.availability_evidence(version_id,precision_notes) VALUES(vid,'UNVERIFIED: publication, revision and availability timestamps absent; origin not independently verified');
   UPDATE import_counts SET inserted=inserted+1;
 END IF;
END $import$;""")
    statements.extend(["SELECT inserted,skipped,0 AS rejected FROM import_counts;", "COMMIT;" if commit else "ROLLBACK;"])
    return '\n'.join(statements)


def execute(sql, psql, port):
    if not 1 <= port <= 65535:
        raise ValueError('Invalid local port')
    result = subprocess.run([str(psql),'-X','-h','127.0.0.1','-p',str(port),'-U','c2_local_owner','-d','c2_schema_validation','-v','ON_ERROR_STOP=1','-f','-'], input=sql,text=True,capture_output=True)
    if result.returncode:
        raise RuntimeError('Import failed; entire transaction rolled back. Database rejected rows; inserted=0 persisted.\n'+result.stderr)
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'data/official/official_historical_2001_2025.csv')
    parser.add_argument('--port',type=int,help='Explicit isolated local validator port; no default connection')
    parser.add_argument('--psql',type=Path,default=Path('C:/Program Files/PostgreSQL/18/bin/psql.exe'))
    parser.add_argument('--commit',action='store_true',help='Persist into isolated local validation database only')
    args=parser.parse_args()
    if args.input.resolve() != (ROOT/'data/official/official_historical_2001_2025.csv').resolve():
        parser.error('Only the designated official CSV is accepted by the CLI')
    rows,skipped,rejected=prepare(args.input)
    print(f'Selected={len(rows)}; skipped={dict(skipped)}; rejected={len(rejected)}; expected coverage=24 groups')
    if rejected:
        print(rejected);return 1
    sql=make_import_sql(rows,args.commit)
    if args.port is None:
        if args.commit:parser.error('--commit requires explicit isolated database port')
        print('Dry-run preflight only: inserted=0, no database connection or records persisted.');return 0
    try:
        print(execute(sql,args.psql,args.port))
    except RuntimeError as exc:
        print(exc);return 1
    print('Committed isolated import.' if args.commit else 'Dry-run insert counts are provisional; all writes rolled back.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
