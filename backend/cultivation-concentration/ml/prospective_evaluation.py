"""Read-only scoring of frozen forecasts against separately collected future outcomes.

Run from the backend: python -m ml.prospective_evaluation --database PATH --output NEW.json
No registration database is initialized, historical CSV replayed, or model fitted.
"""
import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from app.schemas.prospective import Forecast, Outcome, Protocol

LABELS = ['Low', 'Medium', 'High']


def aware(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Timezone-aware audit timestamps required')
    return result


def verified_rows(db, table):
    # Table names are internal constants, never CLI input.
    result = {}
    for row in db.execute(f'SELECT * FROM {table}'):
        if hashlib.sha256(row['payload'].encode()).hexdigest() != row['digest']:
            raise ValueError(f'Audit integrity failed: {table}')
        payload = json.loads(row['payload'])
        result[row['id']] = (row, payload)
    return result


def scores(pairs):
    actual, predicted = zip(*pairs)
    precision, recall, f1, _ = precision_recall_fscore_support(
        actual, predicted, labels=LABELS, zero_division=0)
    return {
        'eligible_records': len(pairs), 'accuracy': float(accuracy_score(actual, predicted)),
        'macro_precision': float(precision.mean()), 'macro_recall': float(recall.mean()),
        'macro_f1': float(f1.mean()),
        'per_class': {label: dict(precision=float(p), recall=float(r), f1=float(f))
                      for label, p, r, f in zip(LABELS, precision, recall, f1)},
        'confusion_matrix': confusion_matrix(actual, predicted, labels=LABELS).tolist(),
        'class_distribution': {label: actual.count(label) for label in LABELS},
        'majority_class_baseline': max(Counter(actual).values()) / len(actual),
        'majority_baseline_interpretation': 'Retrospective cohort class-frequency benchmark, not a selected predictor',
    }


def evaluate(database, as_of=None):
    stamp = as_of or datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
        raise ValueError('Evaluation as_of must be timezone-aware and no later than now')
    path = Path(database).resolve(strict=True)
    groups = defaultdict(list)
    counts = Counter()
    # Read-only connection and one consistent read transaction; never instantiate PlanStore.
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        protocols = verified_rows(db, 'prospective_protocols')
        assessments = verified_rows(db, 'prospective_assessments')
        outcomes = verified_rows(db, 'prospective_outcomes')
        for identifier, (row, assessment) in assessments.items():
            cutoff = aware(assessment['cutoff'])
            if cutoff > stamp:
                counts['assessment_after_as_of'] += 1
                continue
            counts['assessments_at_as_of'] += 1
            if identifier != assessment['assessment_id'] or aware(row['recorded_at']) != cutoff or aware(assessment['assessment_timestamp']) != cutoff:
                raise ValueError('Assessment timestamp/identity mismatch')
            own = assessment['own_plan']['plan']
            for version in [assessment['own_plan'], *assessment['peer_versions']]:
                plan = version['plan']
                if (not aware(plan['submitted_at']) <= aware(plan['updated_at']) <= aware(version['recorded_at']) <= cutoff
                        or plan['status'] != 'active' or datetime.fromisoformat(plan['planting_date']).date() <= cutoff.date()
                        or plan['district'] != own['district']
                        or plan['crop'] != own['crop'] or plan['region'] != own['region']):
                    raise ValueError('Snapshot availability/scope violation')
            forecast = Forecast.model_validate(assessment['experimental_forecast'])
            if forecast.status != 'experimental_forecast':
                counts['unavailable_forecast'] += 1
                continue
            protocol = assessment.get('protocol')
            if protocol is None:
                raise ValueError('Forecast without preregistered independent protocol')
            registered_row, registered = protocols[protocol['protocol_id']]
            Protocol.model_validate({k: v for k, v in protocol.items() if k != 'registered_at'})
            if registered != protocol or aware(registered_row['recorded_at']) != aware(protocol['registered_at']) or aware(protocol['registered_at']) > cutoff:
                raise ValueError('Protocol integrity/availability violation')
            if forecast.target_definition_version != protocol['definition_version'] or any(
                    artifact.available_at > cutoff for artifact in (forecast.model, forecast.historical_reference)):
                raise ValueError('Forecast availability/target violation')
            if identifier not in outcomes:
                counts['awaiting_independent_outcome'] += 1
                continue
            outcome_row, value = outcomes[identifier]
            outcome = Outcome.model_validate({k: v for k, v in value.items() if k not in ('recorded_at', 'actor')})
            recorded = aware(outcome_row['recorded_at'])
            if recorded != aware(value['recorded_at']) or outcome.assessment_id != identifier:
                raise ValueError('Outcome timestamp/identity mismatch')
            if recorded > stamp:
                counts['outcome_after_as_of'] += 1
                continue
            due = aware(assessment['outcome_due_at'])
            if (due - cutoff != timedelta(days=protocol['horizon_days']) or not cutoff < due <= outcome.observed_at <= recorded
                    or outcome.target_definition_version != protocol['definition_version']):
                raise ValueError('Independent outcome horizon/definition violation')
            # Never pool different districts, definitions, models, references or horizons.
            key = (own['district'], protocol['protocol_id'], forecast.model.version, forecast.model.sha256,
                   forecast.historical_reference.version, forecast.historical_reference.sha256)
            groups[key].append((outcome.category, forecast.category))
            counts['scored'] += 1
    cohorts = []
    for key, pairs in sorted(groups.items()):
        district, protocol_id, model, model_hash, reference, reference_hash = key
        cohorts.append(dict(district=district, protocol_id=protocol_id, model_version=model,
                            model_sha256=model_hash, historical_reference_version=reference,
                            historical_reference_sha256=reference_hash, **scores(pairs)))
    return dict(schema_version=1, as_of=stamp.isoformat(), label_order=LABELS, counts=dict(counts),
                cohorts=cohorts, status='scored' if cohorts else 'no_eligible_independent_outcomes',
                limitations=['Independent provenance is an authorized human attestation, not proof verified by software.',
                             'Historical/current concentration formula replay is never scored by this utility.',
                             'Repeated plans from the same farmer are correlated; no independence or confidence interval is claimed.',
                             'Restricted offline aggregate report; not a farmer-facing disclosure.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--as-of', type=aware)
    args = parser.parse_args()
    report = evaluate(args.database, args.as_of)
    # Exclusive creation protects earlier evaluation results.
    with open(args.output, 'x', encoding='utf-8') as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write('\n')
    print(json.dumps({'status': report['status'], 'counts': report['counts']}))


if __name__ == '__main__':
    main()
