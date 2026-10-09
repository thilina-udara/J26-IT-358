import json
import os
import secrets
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Query
from datetime import date, datetime, timezone
from typing import Literal
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas.cultivation_plan import PlanInput, PlanResponse
from app.services.cultivation_plans import PlanStore

def create_app(database_path=None, farmer_tokens=None, analysis_tokens=None, alternative_evidence=None,
               planning_approvals=None, planning_guideline_dir=None, admin_tokens=None,
               reviewer_tokens=None, reference_database_path=None, historical_predictor=None, production_evidence=None, prospective_predictor=None):
    from app.schemas.production_risk import ProductionRegistry
    production_registry=ProductionRegistry.model_validate(production_evidence or {})
    application = FastAPI(title="Cultivation Concentration Risk Prediction")
    # Lazy initialization keeps health checks/tests from creating the live DB.
    database_path = database_path or os.getenv('CULTIVATION_PLAN_DB', str(Path(__file__).resolve().parents[1]/'storage/cultivation_plans.sqlite3'))
    security = HTTPBearer(auto_error=False)

    def roles():
        try:
            farmers = farmer_tokens if farmer_tokens is not None else json.loads(os.getenv('CULTIVATION_FARMER_TOKENS','{}'))
            analysts = analysis_tokens if analysis_tokens is not None else json.loads(os.getenv('CULTIVATION_ANALYSIS_TOKENS','[]'))
            admins = admin_tokens if admin_tokens is not None else json.loads(os.getenv('CULTIVATION_ADMIN_TOKENS','[]'))
            if not isinstance(farmers,dict) or not isinstance(analysts,list) or not isinstance(admins,list):
                raise ValueError('Invalid registry')
            if any(not isinstance(t,str) or not t for t in [*farmers,*analysts,*admins]):
                raise ValueError('Invalid token')
            if any(not isinstance(v,str) or not v for v in farmers.values()):
                raise ValueError('Invalid identity')
            if set(farmers)&(set(analysts)|set(admins)) or set(analysts)&set(admins):
                raise ValueError('Ambiguous roles')
            experts=reviewer_tokens if reviewer_tokens is not None else json.loads(os.getenv('CULTIVATION_REVIEWER_TOKENS','{}'))
            if not isinstance(experts,dict) or any(not isinstance(k,str) or not k or not isinstance(v,str) or not v for k,v in experts.items()):
                raise ValueError('Invalid reviewer registry')
            if set(experts)&(set(farmers)|set(analysts)|set(admins)):raise ValueError('Ambiguous reviewer role')
            return farmers, analysts, admins
        except (ValueError, TypeError) as exc:
            raise HTTPException(503,'Authentication configuration unavailable') from exc

    def farmer(credentials: HTTPAuthorizationCredentials = Depends(security)):
        tokens, _, _ = roles()
        if not tokens:
            raise HTTPException(503,'Farmer authentication is not configured')
        if credentials and credentials.scheme.lower() == 'bearer':
            for token, identity in tokens.items():
                if secrets.compare_digest(credentials.credentials,token):
                    return identity
        raise HTTPException(401,'Valid farmer credentials required',headers={'WWW-Authenticate':'Bearer'})

    def store():
        return PlanStore(database_path)

    def analyst(credentials: HTTPAuthorizationCredentials = Depends(security)):
        _, tokens, admins = roles()
        if credentials and any(secrets.compare_digest(credentials.credentials,token) for token in [*tokens,*admins]):
            return True
        raise HTTPException(403,'Restricted analysis credentials required')

    def administrator(credentials: HTTPAuthorizationCredentials = Depends(security)):
        from hashlib import sha256
        _, _, admins=roles()
        if credentials and any(secrets.compare_digest(credentials.credentials,t) for t in admins):
            return 'admin-'+sha256(credentials.credentials.encode()).hexdigest()
        raise HTTPException(403,'Admin credentials required')

    def reviewer(credentials: HTTPAuthorizationCredentials = Depends(security)):
        farmers, analysts, admins=roles()
        try:
            tokens=reviewer_tokens if reviewer_tokens is not None else json.loads(os.getenv('CULTIVATION_REVIEWER_TOKENS','{}'))
            if not isinstance(tokens,dict) or any(not isinstance(k,str) or not k or not isinstance(v,str) or not v for k,v in tokens.items()):
                raise ValueError('Invalid registry')
            if set(tokens)&(set(farmers)|set(analysts)|set(admins)):raise ValueError('Ambiguous roles')
        except (ValueError,TypeError) as exc:raise HTTPException(503,'Reviewer authentication unavailable') from exc
        if credentials:
            for token,identity in tokens.items():
                if secrets.compare_digest(credentials.credentials,token):return identity
        raise HTTPException(403,'Reviewer credentials required')

    def reference_store():
        from app.services.reference_governance import ReferenceStore
        path=reference_database_path or os.getenv('CULTIVATION_REFERENCE_DB',str(Path(database_path).with_name('reference_governance.sqlite3')))
        return ReferenceStore(path)

    from app.schemas.reference_governance import ReviewerRegistration, RubricRegistration, CaseRegistration, GovernedReview, Adjudication

    @application.post('/api/expert-validation/reviewers')
    def register_reviewer(value: ReviewerRegistration,actor=Depends(administrator),repository=Depends(reference_store)):
        return repository.record('reviewers',value,actor)

    @application.post('/api/expert-validation/rubrics')
    def register_rubric(value: RubricRegistration,actor=Depends(administrator),repository=Depends(reference_store)):
        return repository.record('rubrics',value,actor)

    @application.post('/api/expert-validation/cases')
    def register_case(value: CaseRegistration,actor=Depends(administrator),repository=Depends(reference_store)):
        return repository.record('cases',value,actor)

    @application.post('/api/expert-validation/cases/{case_id}/assign')
    def assign_review(case_id: str,case_version: int,reviewer_id: str,rubric_version: str,
                      actor=Depends(administrator),repository=Depends(reference_store)):
        return repository.assign(case_id,case_version,reviewer_id,rubric_version,actor)

    @application.get('/api/expert-validation/cases/{case_id}')
    def read_review_case(case_id: str,case_version: int,rubric_version: str,
                          identity=Depends(reviewer),repository=Depends(reference_store)):
        return repository.assigned_case(case_id,case_version,rubric_version,identity)

    @application.post('/api/expert-validation/cases/{case_id}/reviews')
    def submit_review(case_id: str,value: GovernedReview,identity=Depends(reviewer),repository=Depends(reference_store)):
        return repository.review(case_id,value,identity)

    @application.post('/api/expert-validation/cases/{case_id}/adjudicate')
    def adjudicate_case(case_id: str,value: Adjudication,identity=Depends(reviewer),repository=Depends(reference_store)):
        return repository.adjudicate(case_id,value,identity)

    @application.get('/api/expert-validation/cases/{case_id}/status')
    def review_status(case_id: str,case_version: int,rubric_version: str,
                      actor=Depends(administrator),repository=Depends(reference_store)):
        return repository.status(case_id,case_version,rubric_version)

    @application.get('/api/expert-validation/cases/{case_id}/adjudication-packet')
    def adjudication_packet(case_id: str,case_version: int,rubric_version: str,
                              identity=Depends(reviewer),repository=Depends(reference_store)):
        return repository.adjudication_packet(case_id,case_version,rubric_version,identity)

    from app.schemas.alternatives import AlternativeRequest,EvidenceRegistry
    from app.schemas.personalized_planning import PlanningRequest, ClaimApproval

    def planning_configuration():
        try:
            evidence = alternative_evidence
            if evidence is None:
                path = os.getenv('CULTIVATION_ALTERNATIVE_EVIDENCE')
                evidence = json.loads(Path(path).read_text(encoding='utf-8')) if path else {}
            approvals = planning_approvals
            if approvals is None:
                path = os.getenv('CULTIVATION_PLANNING_APPROVALS')
                approvals = json.loads(Path(path).read_text(encoding='utf-8')) if path else []
            return [ClaimApproval.model_validate(a) for a in approvals], EvidenceRegistry.model_validate(evidence)
        except (OSError, ValueError, TypeError) as exc:
            raise HTTPException(503, 'Planning evidence configuration unavailable') from exc

    def run_planning(value, identity, repository, saving=False):
        from app.services.personalized_planning import generate, save_choice, DATA
        approvals, evidence = planning_configuration()
        try:
            return (save_choice if saving else generate)(repository, value, identity, approvals,
                evidence, planning_guideline_dir or DATA)
        except (OSError, ValueError, KeyError) as exc:
            raise HTTPException(503, 'Guideline dataset unavailable or invalid') from exc

    from app.schemas.farmer_workflow import WorkflowPlan, WorkflowAnalysis, WorkflowChoice

    @application.post('/api/farmer-workflow/plans',status_code=201)
    def workflow_submit(value: WorkflowPlan,identity=Depends(farmer),repository=Depends(store)):
        from app.services.farmer_workflow import run
        if value.planting_date<=datetime.now(timezone.utc).date():
            raise HTTPException(422,'Planting must be in the future')
        _,registry=planning_configuration()
        fields=value.model_dump(exclude={'season'})
        saved=repository.save(PlanInput(**fields,farmer_id=identity),identity)
        return dict(plan=saved['plan'],workflow=run(repository,identity,saved['plan'].plan_id,value.season,registry,historical_predictor=historical_predictor,production_registry=production_registry))

    @application.post('/api/farmer-workflow/analyze')
    def workflow_analyze(value: WorkflowAnalysis,identity=Depends(farmer),repository=Depends(store)):
        from app.services.farmer_workflow import run
        _,registry=planning_configuration()
        return run(repository,identity,value.plan_id,value.season,registry,value.as_of,historical_predictor,production_registry)

    @application.post('/api/farmer-workflow/select')
    def workflow_select(value: WorkflowChoice,identity=Depends(farmer),repository=Depends(store)):
        from app.services.farmer_workflow import run
        _,registry=planning_configuration()
        current=repository.read(value.plan_id,identity)['plan']
        if value.final_crop!=current.crop:
            if any(getattr(value,key)!=getattr(current,key) for key in ('district','region','land_size_acres','planting_date')) or (
                value.expected_harvest_date is not None and value.expected_harvest_date!=current.expected_harvest_date):
                raise HTTPException(409,'Update the original plan and reanalyze before selecting an alternative')
            if value.as_of is not None:raise HTTPException(422,'Alternative selection requires current evidence')
            report=run(repository,identity,value.plan_id,value.season,registry,historical_predictor=historical_predictor,production_registry=production_registry)
            if value.final_crop not in {a['crop'] for a in report['recommendations']['alternatives']}:
                raise HTTPException(409,'No defensible High-risk eligible alternative is available')
        request=PlanningRequest.model_validate(value.model_dump(exclude={'save'}))
        return run_planning(request,identity,repository,value.save)

    @application.get('/api/farmer-workflow/plans/{plan_id}')
    def workflow_read(plan_id: str,identity=Depends(farmer),repository=Depends(store)):
        from app.services.personalized_planning import retrieve
        result=repository.read(plan_id,identity)
        try:personalized=retrieve(repository,plan_id,identity)
        except HTTPException as exc:
            if exc.status_code!=404:raise
            personalized=None
        return dict(plan=result['plan'],personalized_plan=personalized)

    @application.post('/api/personalized-cultivation-plans/generate')
    def generate_personalized(value: PlanningRequest, identity=Depends(farmer), repository=Depends(store)):
        return run_planning(value, identity, repository)

    @application.post('/api/personalized-cultivation-plans/save')
    def save_personalized(value: PlanningRequest, identity=Depends(farmer), repository=Depends(store)):
        return run_planning(value, identity, repository, True)

    @application.get('/api/personalized-cultivation-plans/{plan_id}')
    def read_personalized(plan_id: str, identity=Depends(farmer), repository=Depends(store)):
        from app.services.personalized_planning import retrieve
        return retrieve(repository, plan_id, identity)

    @application.post('/api/cultivation-analysis/alternatives')
    def alternatives(value: AlternativeRequest,identity=Depends(farmer),repository=Depends(store)):
        from app.services.alternatives import compare_alternatives
        try:
            evidence=alternative_evidence
            if evidence is None:
                evidence_path=os.getenv('CULTIVATION_ALTERNATIVE_EVIDENCE')
                evidence=json.loads(Path(evidence_path).read_text(encoding='utf-8')) if evidence_path else {}
            registry=EvidenceRegistry.model_validate(evidence)
        except (OSError,ValueError) as exc:
            raise HTTPException(503,'Alternative evidence registry is invalid or unavailable') from exc
        from app.services.privacy import farmer_view
        return farmer_view(compare_alternatives(repository,value,identity,registry))

    @application.get('/api/cultivation-analysis/clusters')
    def clustering(district: Literal['Matara','Hambantota'],
                   as_of: datetime | None = None,
                   k: int = Query(3,ge=1,le=10),
                   eps: float = Query(1.0,gt=0,le=10,allow_inf_nan=False),
                   min_samples: int = Query(3,ge=2,le=100),
                   authorized=Depends(analyst),repository=Depends(store)):
        from app.services.plan_clustering import snapshot, analyze
        now = datetime.now(timezone.utc)
        cutoff = as_of or now
        if cutoff.tzinfo is None or cutoff > now:
            raise HTTPException(422,'as_of must be timezone-aware and no later than now')
        cutoff = cutoff.astimezone(timezone.utc)
        result = analyze(snapshot(repository,cutoff),district,k,eps,min_samples)
        result.update(as_of=cutoff.isoformat(),availability_warning='Pre-versioning updates cannot be reconstructed; initial current versions are available only at updated_at.')
        from app.services.privacy import analyst_view
        return analyst_view(result)

    @application.get('/api/cultivation-plans/{plan_id}/risk-assessment')
    def owned_assessment(plan_id: str, season: Literal['Maha','Yala'], as_of: datetime | None = None,
                         identity=Depends(farmer),repository=Depends(store)):
        from app.services.plan_clustering import snapshot
        from app.services.risk_assessment import assess
        from app.services.privacy import farmer_view
        # Check current ownership before searching historical versions; uniform 404.
        with repository.connection() as db:
            repository.get(db,plan_id,identity)
        cutoff=as_of or datetime.now(timezone.utc)
        if cutoff.tzinfo is None or cutoff>datetime.now(timezone.utc):
            raise HTTPException(422,'Invalid analysis cutoff')
        cutoff=cutoff.astimezone(timezone.utc)
        plan=next((p for p in snapshot(repository,cutoff) if p['plan_id']==plan_id and p['farmer_id']==identity),None)
        if plan is None:
            raise HTTPException(404,'Active available plan not found')
        return farmer_view(assess(repository,cutoff,plan['district'],plan['region'],plan['crop'],season,
                                 date.fromisoformat(plan['expected_harvest_date'])))

    @application.get('/api/cultivation-analysis/risk-indicators')
    def risk_indicators(district: Literal['Matara','Hambantota'],
                        region: str = Query(min_length=1,max_length=100),
                        crop: Literal['Mung Beans','Corn','Bandakka','Brinjal','Pumpkin','Chillies'] = Query(),
                        season: Literal['Maha','Yala'] = Query(),
                        harvest_date: date = Query(),as_of: datetime | None = None,
                        authorized=Depends(analyst),repository=Depends(store)):
        from app.services.risk_indicators import prepare_indicators
        now=datetime.now(timezone.utc)
        cutoff=as_of or now
        if cutoff.tzinfo is None or cutoff>now:
            raise HTTPException(422,'as_of must be timezone-aware and no later than now')
        try:
            return prepare_indicators(repository,cutoff.astimezone(timezone.utc),district,region,crop,season,harvest_date)
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc

    @application.get('/api/cultivation-analysis/risk-assessment')
    def risk_assessment(district: Literal['Matara','Hambantota'],
                        region: str = Query(min_length=1,max_length=100),
                        crop: Literal['Mung Beans','Corn','Bandakka','Brinjal','Pumpkin','Chillies'] = Query(),
                        season: Literal['Maha','Yala'] = Query(),
                        harvest_date: date = Query(),as_of: datetime | None = None,
                        authorized=Depends(analyst),repository=Depends(store)):
        from app.services.risk_assessment import explain
        return explain(risk_indicators(district,region,crop,season,harvest_date,as_of,authorized,repository))

    @application.get('/')
    def root() -> dict[str, str]:
        return {'message': 'Cultivation concentration backend'}

    @application.get('/health')
    def health_check() -> dict[str, str]:
        return {'status': 'healthy'}

    @application.post('/api/cultivation-plans',response_model=PlanResponse,status_code=201)
    def create(value: PlanInput, identity=Depends(farmer), repository=Depends(store)):
        return repository.save(value,identity)

    @application.get('/api/cultivation-plans/{plan_id}',response_model=PlanResponse)
    def read(plan_id: str, identity=Depends(farmer), repository=Depends(store)):
        return repository.read(plan_id,identity)

    @application.put('/api/cultivation-plans/{plan_id}',response_model=PlanResponse)
    def update(plan_id: str,value: PlanInput, identity=Depends(farmer),repository=Depends(store)):
        return repository.save(value,identity,plan_id)

    @application.delete('/api/cultivation-plans/{plan_id}',response_model=PlanResponse)
    def cancel(plan_id: str,identity=Depends(farmer),repository=Depends(store)):
        return repository.cancel(plan_id,identity)

    from app.prospective_routes import router as prospective_router
    application.include_router(prospective_router(farmer,analyst,administrator,store,prospective_predictor))

    return application


app = create_app()
