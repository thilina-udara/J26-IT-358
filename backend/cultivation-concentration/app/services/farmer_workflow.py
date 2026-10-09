"""One farmer journey over existing services; no new risk labels or models."""
from datetime import datetime,timezone,date
from fastapi import HTTPException
from app.services.plan_clustering import snapshot,analyze
from app.services.risk_indicators import prepare_indicators
from app.services.risk_assessment import explain
from app.services.privacy import farmer_view
from app.services.alternatives import compare_alternatives
from app.schemas.alternatives import AlternativeRequest


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
    if owned is None:raise HTTPException(404,'Active available future plan not found')
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
    from app.services.current_plan_risk import evaluate
    from app.schemas.production_risk import ProductionRegistry
    from app.services.production_risk import evaluate as production_evaluate,farmer_response,alternatives as production_alternatives
    production_registry=production_registry or ProductionRegistry()
    production=production_evaluate(records,owned,season,cutoff,production_registry)
    experimental_candidates=production_alternatives(records,owned,season,cutoff,production_registry,evidence,production)
    from app.services.production_reference import evaluate as reference_evaluate, farmer_response as reference_response
    reference_assessment=reference_response(reference_evaluate(records,owned,season,cutoff,production_registry))
    return dict(workflow_version='1',plan_id=plan_id,as_of=cutoff.isoformat(),historical_prediction=historical,
        current_plan_risk=farmer_view(evaluate(indicators)),
        experimental_production_assessment=farmer_response(production),experimental_alternatives=experimental_candidates,
        experimental_reference_assessment=reference_assessment,
        assessment=farmer_view(assessment),clustering=clustering,recommendations=recommendations,
        next_step='keep_original_or_select_eligible_alternative' if recommendations['alternatives'] else 'keep_original_or_collect_missing_evidence',
        planning_status='verified_guideline_gated_partial_planning_available')
