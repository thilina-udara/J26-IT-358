"""Optional trusted artifact provisioning, never a user-selectable pickle loader."""
import hashlib
import io
import json
import os
import platform
from datetime import datetime, date
from importlib.metadata import version
from pathlib import Path
from app.services.historical_prediction import HistoricalPredictor, FEATURES, LABEL_DEFINITION, unavailable

ROOT = Path(__file__).resolve().parents[2]
# Deployment can select an alias, never a filesystem path or an alternate catalog.
BUNDLES = {'selected_xgboost_2024': ('models/experimental/historical_feature_improvement/v1_20261009', 2024)}


class ProvisioningError(ValueError):
    pass


class UnavailablePredictor:
    def __init__(self, reason): self.reason = reason
    def context(self, *args): return unavailable(self.reason)


def verified_bytes(name, catalog):
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ProvisioningError('Historical artifact path is outside the trusted component')
    expected = catalog['files'].get(name)
    if not expected:
        raise ProvisioningError('Historical artifact is not in the trusted catalog')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ProvisioningError('Historical artifact hash mismatch')
    return data


def aware(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None: raise ProvisioningError('Historical evidence timestamps must be timezone-aware')
    return result


def evidence_bundle(path, expected, trained_through, model_digest):
    data = Path(path).read_bytes()
    if not expected or hashlib.sha256(data).hexdigest() != expected:
        raise ProvisioningError('Historical availability manifest hash mismatch')
    value = json.loads(data)
    if (value['label_definition'] != LABEL_DEFINITION or value['trained_through'] != trained_through
            or value['model_sha256'] != model_digest or type(value['coverage_through']) is not int
            or value['provenance_verified'] is not True or not value['evidence_reference']):
        raise ProvisioningError('Historical evidence definition or provenance is incompatible')
    observed = []
    for row in value['observations']:
        if row['provenance_verified'] is not True or not row['evidence_reference']:
            raise ProvisioningError('Historical observation lineage is unverified')
        record = dict(row, available_at=aware(row['available_at']))
        # Availability cannot precede completion of the claimed observation.
        if date.fromisoformat(row['observation_end']) > record['available_at'].date():
            raise ProvisioningError('Historical observation predates actual availability')
        if type(row['year']) is not int or date.fromisoformat(row['observation_end']).year < row['year']:
            raise ProvisioningError('Historical observation year is incompatible')
        observed.append(record)
    mappings = value['season_year_mappings']
    for row in mappings:
        if (row['verified'] is not True or not row['reference'] or type(row['target_year']) is not int
                or date.fromisoformat(row['planting_start']) > date.fromisoformat(row['planting_end'])):
            raise ProvisioningError('Historical season/year mapping is unverified or invalid')
        row['available_at'] = aware(row['available_at'])
    return value, observed, mappings


def provision():
    alias = os.getenv('CULTIVATION_HISTORICAL_MODEL', '')
    if not alias: return None
    try:
        if alias not in BUNDLES:
            raise ProvisioningError('Unsupported historical model alias')
        folder, trained_through = BUNDLES[alias]
        catalog = json.loads((ROOT / 'models/artifact_catalog.json').read_text(encoding='utf-8'))
        # Verify all executable and metadata bytes before any deserialization.
        model_bytes = verified_bytes(folder + f'/selected_xgboost_through_{trained_through}.joblib', catalog)
        schema = json.loads(verified_bytes(folder + '/feature_schema.json', catalog))
        environment = json.loads(verified_bytes(folder + '/environment.json', catalog))
        if schema['features'] != list(FEATURES):
            raise ProvisioningError('Historical model feature schema is incompatible with the district-season predictor')
        runtime = {'python': platform.python_version(), **{key: version(package) for key, package in
            [('numpy','numpy'), ('pandas','pandas'), ('sklearn','scikit-learn'), ('xgboost','xgboost')]}}
        if any(environment.get(key) != actual for key, actual in runtime.items()):
            raise ProvisioningError('Historical model runtime versions are incompatible')
        path = os.getenv('CULTIVATION_HISTORICAL_EVIDENCE')
        if not path: raise ProvisioningError('Verified historical observations and season/year mapping manifest missing')
        evidence, observations, mappings = evidence_bundle(path, os.getenv('CULTIVATION_HISTORICAL_EVIDENCE_SHA256'), trained_through, hashlib.sha256(model_bytes).hexdigest())
        import joblib
        from sklearn.pipeline import Pipeline
        from xgboost import XGBClassifier
        # Load the exact verified in-memory bytes, eliminating hash/load path races.
        model = joblib.load(io.BytesIO(model_bytes))
        if (not isinstance(model, Pipeline) or not isinstance(model.steps[-1][1], XGBClassifier)
                or list(model.feature_names_in_) != list(FEATURES) or list(model.classes_) != [0,1,2]):
            raise ProvisioningError('Historical pipeline or label encoding is incompatible')
        predictor = HistoricalPredictor(model, observations, 'XGBoost historical district-season proxy',
            aware(evidence['model_available_at']), trained_through, evidence['coverage_through'])
        predictor.season_year_mapping_evidence = dict(verified=True, reference=evidence['evidence_reference'],
            available_at=max((row['available_at'] for row in mappings), default=aware(evidence['model_available_at'])))
        def mapper(plan, season):
            matches = [row for row in mappings if (row['district'],row['crop'],row['season']) ==
                (plan['district'],plan['crop'],season) and row['planting_start'] <= plan['planting_date'] <= row['planting_end']]
            return matches[0]['target_year'] if len(matches)==1 else None
        predictor.season_year_mapper = mapper
        return predictor
    except ProvisioningError as exc:
        return UnavailablePredictor(str(exc))
    except Exception:
        # Optional dependency/configuration/load failure must not block core APIs or
        # expose paths, observations or serialized exception contents.
        return UnavailablePredictor('Historical runtime bundle unavailable or invalid')
