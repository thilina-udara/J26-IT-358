"""One farmer journey over existing services; no new risk labels or models."""
from datetime import datetime,timezone,date
from fastapi import HTTPException
from app.services.plan_clustering import snapshot,analyze
from app.services.risk_indicators import prepare_indicators
from app.services.risk_assessment import explain
from app.services.privacy import farmer_view
from app.services.alternatives import compare_alternatives
from app.schemas.alternatives import AlternativeRequest
import json


def season_context(owned, requested):
    declared = owned.get('farmer_declared_season')
    return dict(farmer_declared_season=declared, requested_season=requested,
        effective_analysis_season=requested if requested is not None else declared,
        source='analysis_request' if requested is not None else 'farmer_declaration' if declared else 'unknown',
        conflict=requested is not None and declared is not None and requested != declared,
        independently_verified_statistical_season=None,
        interpretation='Analysis context only; independent statistical-season/year mapping and evidence approvals remain required')


def unavailable_report(plan_id, reason, *, failed=False, season=None, cutoff=None, context=None):
    """Preserve the workflow envelope without claiming analysis was performed."""
    cutoff = cutoff or datetime.now(timezone.utc)
    missing = [reason]
    empty = dict(status='insufficient_evidence', risk_level=None, missing_evidence=missing,
                 reason_codes=['analysis_not_evaluated'])
    return dict(workflow_version='1', plan_id=plan_id, as_of=cutoff.isoformat(),
        season_context=context or season_context({}, season),
        status='analysis_unavailable' if failed else 'insufficient_evidence',
        analysis_status='failed' if failed else 'not_applicable', missing_evidence=missing,
        reason_codes=['analysis_unavailable' if failed else 'analysis_not_applicable'],
        historical_prediction=dict(empty), current_plan_risk=farmer_view(empty),
        experimental_production_assessment=dict(empty), experimental_alternatives=[],
        experimental_reference_assessment=dict(empty), assessment=farmer_view(empty),
        clustering=dict(status='not_evaluated', algorithms=['K-Means','DBSCAN'],
            explanation='Descriptive cultivation patterns only; no risk classification.'),
        recommendations=dict(status='blocked_unvalidated_risk', alternatives=[]),
        next_step='retry_saved_plan_analysis' if failed else 'retain_historical_record',
        planning_status='not_evaluated',
        recovery=dict(plan_saved=True, retryable=failed, method='POST',
            endpoint='/api/farmer-workflow/analyze', request=dict(plan_id=plan_id, season=season)))


def defensible_high(assessment,cutoff):
    # No existing assessor satisfies this gate. Future integration must supply
    # independently verified classification evidence; caller fields cannot do so.
    evidence=assessment.get('classification_evidence',{})
    try:
        available=datetime.fromisoformat(evidence['available_at'])
        return (assessment.get('risk_level')=='High' and assessment.get('status')=='risk_level_validated'
            and evidence.get('verified') is True and bool(evidence.get('reference'))
            and available.tzinfo is not None and available<=cutoff)
    except (KeyError,TypeError,ValueError):return False


def run(repository,identity,plan_id,season,evidence,as_of=None,historical_predictor=None,production_registry=None):
    with repository.connection() as db:repository.get(db,plan_id,identity)
    now=datetime.now(timezone.utc);cutoff=as_of or now
    if cutoff.tzinfo is None or cutoff>now:raise HTTPException(422,'Invalid analysis cutoff')
    cutoff=cutoff.astimezone(timezone.utc)
    records=snapshot(repository,cutoff)
    owned=next((p for p in records if p['plan_id']==plan_id and p['farmer_id']==identity),None)
    if owned is None:
        # Inspect this owner's version at the cutoff, without changing the research
        # snapshot's pre-planting eligibility or exposing any other farmer's records.
        with repository.connection() as db:
            rows=db.execute('SELECT recorded_at,payload FROM cultivation_plan_versions WHERE plan_id=? ORDER BY version_id DESC', (plan_id,)).fetchall()
        version=next((json.loads(row['payload']) for row in rows
            if datetime.fromisoformat(row['recorded_at'])<=cutoff
            and datetime.fromisoformat(json.loads(row['payload'])['submitted_at'])<=cutoff), None)
        if version and version['farmer_id']==identity and version['status']=='active' and (
                date.fromisoformat(version['planting_date'])<=cutoff.date()
                or date.fromisoformat(version['expected_harvest_date'])<=cutoff.date()):
            return unavailable_report(plan_id, 'Historical or already-started cultivation is not eligible for current pre-planting analysis; the record is preserved.', season=season, cutoff=cutoff, context=season_context(version,season))
        raise HTTPException(404,'Active available future plan not found')
    context_season=season_context(owned,season)
    season=context_season['effective_analysis_season']
    indicators=prepare_indicators(repository,cutoff,owned['district'],owned['region'],owned['crop'],
        season or 'unspecified',date.fromisoformat(owned['expected_harvest_date']),prepared_snapshot=records)
    assessment=explain(indicators)
    context=indicators.get('cluster_context')
    # Clustering also runs when the queried crop/window has insufficient coverage.
    clusters=context if context is not None else analyze(records,owned['district'])
    clustering=dict(algorithms=['K-Means','DBSCAN'],scope='district future-plan snapshot; not target membership',
        status='available_context' if context else clusters.get('status','insufficient_or_private'),
        explanation='Similarity and density patterns are descriptive; DBSCAN noise is not High risk.',
        privacy='Cluster memberships and collective numeric values withheld from farmer')
    recommendations=dict(status='blocked_unvalidated_risk',alternatives=[],
        explanation='No defensible High-risk classification is available; alternatives are not recommended automatically.')
    if defensible_high(assessment,cutoff):
        compared=compare_alternatives(repository,AlternativeRequest(selected_crop=owned['crop'],district=owned['district'],
            region=owned['region'],land_size_acres=owned['land_size_acres'],planting_date=owned['planting_date'],
            expected_harvest_date=owned['expected_harvest_date'],as_of=cutoff,replacing_plan_id=plan_id),identity,evidence)
        # Rank internally on the already evidence-gated acreage criterion.
        alternatives=sorted(compared['alternatives'],key=lambda a:(a['planned_concentration']['scenario_inclusive_acreage'],a['crop']))[:3]
        recommendations=dict(status=compared['status'],alternatives=farmer_view(alternatives),
            explanation='At most three Phase 4 eligible crops; risk validation does not itself establish suitability.')
    if season is None:assessment['missing_evidence'].append('Season not supplied; no season was inferred')
    from app.services.historical_prediction import predict_context
    historical=predict_context(historical_predictor,owned,season,cutoff)
    historical=dict(historical,reason_codes=['historical_proxy_only'] if historical['status']=='historical_proxy_prediction'
                    else ['historical_prediction_unavailable'])
    from app.services.current_plan_risk import evaluate
    from app.schemas.production_risk import ProductionRegistry
    from app.services.production_risk import evaluate as production_evaluate,farmer_response,alternatives as production_alternatives
    production_registry=production_registry or ProductionRegistry()
    production=production_evaluate(records,owned,season,cutoff,production_registry)
    experimental_candidates=production_alternatives(records,owned,season,cutoff,production_registry,evidence,production)
    from app.services.production_reference import evaluate as reference_evaluate, farmer_response as reference_response
    reference_assessment=reference_response(reference_evaluate(records,owned,season,cutoff,production_registry))
    return dict(workflow_version='1',plan_id=plan_id,as_of=cutoff.isoformat(),historical_prediction=historical,
        season_context=context_season,
        status='insufficient_evidence' if assessment.get('risk_level') is None else assessment['status'],
        analysis_status='completed', missing_evidence=assessment['missing_evidence'],
        current_plan_risk=farmer_view(evaluate(indicators)),
        experimental_production_assessment=farmer_response(production),experimental_alternatives=experimental_candidates,
        experimental_reference_assessment=reference_assessment,
        assessment=farmer_view(assessment),clustering=clustering,recommendations=recommendations,
        next_step='keep_original_or_select_eligible_alternative' if recommendations['alternatives'] else 'keep_original_or_collect_missing_evidence',
        planning_status='verified_guideline_gated_partial_planning_available')
