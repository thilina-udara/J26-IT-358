"""Authorized ASC 2025 retrospective evaluation; 2024 and all other years excluded."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from ml.asc_2025_backtest import replay
from ml.preprocessing.build_production_reference import REQUIRED, save

LABELS = ('Low', 'Medium', 'High', 'insufficient_evidence')


def load_authorized(path, *, authorize_2025=False):
    if not authorize_2025:
        raise PermissionError('Explicit ASC 2025 authorization required')
    history, current, excluded = [], [], 0
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not set(REQUIRED) <= set(reader.fieldnames or []):
            raise ValueError('Missing required columns')
        for row in reader:
            year = int(row['Year'])
            if 2020 <= year <= 2023:
                history.append({k:row[k] for k in REQUIRED})
            elif year == 2025:
                current.append({k:row[k] for k in REQUIRED})
            else:
                # No dates, identities or measurements inspected/validated/hashed.
                excluded += 1
    return history, current, excluded


def counts(rows):
    values = Counter(r['assessment']['experimental_risk_level'] or 'insufficient_evidence' for r in rows)
    return dict(total=len(rows), **{label:values[label] for label in LABELS})


def evaluate_file(path, *, authorize_2025=False):
    history, current, excluded = load_authorized(path, authorize_2025=authorize_2025)
    result = replay(history, current, access_authorized=True, reference_end_year=2023)
    rows = result['results']
    result.update(source='ASC reported by dataset owner; independently unverified',
        classification_status='EXPERIMENTAL / UNVALIDATED',
        loaded_history_rows=len(history), loaded_2025_rows=len(current), excluded_rows_routed_by_year_only=excluded,
        summary=counts(rows), by_district={d:counts([r for r in rows if r['district']==d]) for d in ('Matara','Hambantota')},
        by_district_crop={d:{c:counts([r for r in rows if r['district']==d and r['crop']==c])
            for c in sorted({r['crop'] for r in rows})} for d in ('Matara','Hambantota')},
        insufficient_reason_counts=dict(Counter(reason for r in rows for reason in r['assessment']['reasons'])))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--authorize-asc-2025',action='store_true')
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    result=evaluate_file(args.input,authorize_2025=args.authorize_asc_2025)
    reference_path,_=save(result['reference'],args.output_dir/'references')
    result['reference_artifact']=reference_path.name
    encoded=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n'
    digest=hashlib.sha256(encoded.encode()).hexdigest()[:16]
    path=args.output_dir/f'asc_2025_retrospective_{digest}.json'
    try:
        with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(encoded)
    except FileExistsError:
        if path.read_text(encoding='utf-8')!=encoded:raise ValueError('Existing evaluation differs; preserved')
    print(json.dumps(dict(artifact=str(path),summary=result['summary'],by_district=result['by_district'],
        by_district_crop=result['by_district_crop'],reason_counts=result['insufficient_reason_counts'])))


if __name__=='__main__':main()
