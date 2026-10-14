import json
import os
import secrets
import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response
from datetime import date, datetime, timezone
from typing import Literal
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas.cultivation_plan import PlanInput, PlanResponse, PlanSubmission, PlanListResponse, Crop, District
from app.services.cultivation_plans import PlanStore
from app.services.farmer_auth import AuthStore, SESSION_PREFIX, unauthorized
from app.schemas.api_responses import (
    HealthResponse, ReadinessResponse, RiskAssessmentResponse, AlternativeComparisonResponse,
    PersonalizedPlanResponse, SavedPersonalizedPlanResponse, WorkflowReportResponse,
    WorkflowSubmitResponse, WorkflowReadResponse, error_responses,
)

def create_app(database_path=None, farmer_tokens=None, analysis_tokens=None, alternative_evidence=None,
               planning_approvals=None, planning_guideline_dir=None, admin_tokens=None,
               reviewer_tokens=None, reference_database_path=None, historical_predictor=None, production_evidence=None, prospective_predictor=None):
    from app.schemas.production_risk import ProductionRegistry
    production_registry=ProductionRegistry.model_validate(production_evidence or {})
    if historical_predictor is None:
        from app.services.historical_runtime import provision
        historical_predictor = provision()
    application = FastAPI(title="Cultivation Concentration Risk Prediction")
    # Lazy initialization keeps health checks/tests from creating the live DB.
    database_path = database_path or os.getenv('CULTIVATION_PLAN_DB', str(Path(__file__).resolve().parents[1]/'storage/cultivation_plans.sqlite3'))
    operational_path = Path(database_path).resolve()
    if operational_path.name.casefold() == 'research_demo.sqlite3':
        raise ValueError('Synthetic research database cannot serve operational farmer workflows')
    if operational_path.exists():
        with closing(sqlite3.connect(f'{operational_path.as_uri()}?mode=ro', uri=True)) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='research_demo_metadata'").fetchone():
                raise ValueError('Synthetic research database cannot serve operational farmer workflows')
    security = HTTPBearer(auto_error=False)
    from app.cors import allowed_origins
    frontend_origins = allowed_origins()

    # Prevent credentials from appearing in validation responses or intermediary caches.
    from fastapi.exceptions import RequestValidationError
    from fastapi.exception_handlers import request_validation_exception_handler
    from fastapi.responses import JSONResponse

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        if request.url.path.startswith('/auth/'):
            errors = [{key: error[key] for key in ('type', 'loc', 'msg')} for error in exc.errors()]
            return JSONResponse(status_code=422, content={'detail': errors})
        return await request_validation_exception_handler(request, exc)

    @application.middleware('http')
    async def protect_auth_responses(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith('/auth/'):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Pragma'] = 'no-cache'
        return response

    def auth_store():
        return AuthStore(database_path)

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

    def farmer_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
        tokens, _, _ = roles()
        if credentials and credentials.scheme.lower() == 'bearer':
            # Session-looking tokens never fall back to static credentials after expiry/revocation.
            if credentials.credentials.startswith(SESSION_PREFIX):
                return auth_store().authenticate(credentials.credentials)
            legacy = os.getenv('CULTIVATION_LEGACY_FARMER_TOKENS_ENABLED', 'true').lower()
            if legacy not in ('true', 'false'):
                raise HTTPException(503, 'Farmer authentication configuration unavailable')
            if legacy == 'true':
                for token, identity in tokens.items():
                    if secrets.compare_digest(credentials.credentials.encode('utf-8'),token.encode('utf-8')):
                        return dict(farmer_id=identity, login_identifier=None,
                                    authentication_method='legacy_research_token', created_at=None)
        raise unauthorized()

    def farmer(profile=Depends(farmer_profile)):
        return profile['farmer_id']

    def store():
        return PlanStore(database_path)

    from app.auth_routes import router as auth_router
    application.include_router(auth_router(auth_store, farmer_profile, security, roles))

    def verified_plan_input(value, identity):
        if value.farmer_id is not None and value.farmer_id != identity:
            raise HTTPException(403, 'farmer_id must match authenticated farmer')
        return PlanInput(**value.model_dump(exclude={'farmer_id'}), farmer_id=identity)

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

    @application.post('/api/farmer-workflow/plans',status_code=201,response_model=WorkflowSubmitResponse,
                      responses=error_responses(401,403,409,422,503))
    def workflow_submit(value: WorkflowPlan,identity=Depends(farmer),repository=Depends(store)):
        from app.services.farmer_workflow import run, unavailable_report, season_context
        if value.planting_date<=datetime.now(timezone.utc).date():
            raise HTTPException(422,'Planting must be in the future')
        _,registry=planning_configuration()
        fields=value.model_dump(exclude={'season'})
        fields['farmer_declared_season']=value.season
        saved=repository.save(PlanInput(**fields,farmer_id=identity),identity)
        try:
            report=run(repository,identity,saved['plan'].plan_id,value.season,registry,historical_predictor=historical_predictor,production_registry=production_registry)
            # Validate before returning: an invalid analysis response must also leave
            # the committed plan discoverable by its owner.
            WorkflowReportResponse.model_validate(report)
        except Exception as exc:
            logging.getLogger(__name__).warning('Post-save workflow analysis unavailable (%s)', type(exc).__name__)
            report=unavailable_report(saved['plan'].plan_id,
                'Analysis unavailable; the cultivation plan was saved. Retry analysis using the saved plan ID.',
                failed=True, season=value.season, context=season_context(saved['plan'].model_dump(),value.season))
        return dict(plan=saved['plan'],workflow=report)

    @application.post('/api/farmer-workflow/analyze',response_model=WorkflowReportResponse,
                      responses=error_responses(401,404,422,503))
    def workflow_analyze(value: WorkflowAnalysis,identity=Depends(farmer),repository=Depends(store)):
        from app.services.farmer_workflow import run
        _,registry=planning_configuration()
        return run(repository,identity,value.plan_id,value.season,registry,value.as_of,historical_predictor,production_registry)

    @application.post('/api/farmer-workflow/select',
                      response_model=PersonalizedPlanResponse | SavedPersonalizedPlanResponse,
                      response_model_exclude_unset=True,responses=error_responses(401,404,409,422,503))
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

    @application.get('/api/farmer-workflow/plans/{plan_id}',response_model=WorkflowReadResponse,
                     responses=error_responses(401,404,503))
    def workflow_read(plan_id: str,identity=Depends(farmer),repository=Depends(store)):
        from app.services.personalized_planning import retrieve
        result=repository.read(plan_id,identity)
        try:personalized=retrieve(repository,plan_id,identity)
        except HTTPException as exc:
            if exc.status_code!=404:raise
            personalized=None
        return dict(plan=result['plan'],personalized_plan=personalized)

    @application.post('/api/personalized-cultivation-plans/generate',response_model=PersonalizedPlanResponse,
                      response_model_exclude_unset=True,responses=error_responses(401,404,409,422,503))
    def generate_personalized(value: PlanningRequest, identity=Depends(farmer), repository=Depends(store)):
        return run_planning(value, identity, repository)

    @application.post('/api/personalized-cultivation-plans/save',response_model=SavedPersonalizedPlanResponse,
                      response_model_exclude_unset=True,responses=error_responses(401,404,409,422,503))
    def save_personalized(value: PlanningRequest, identity=Depends(farmer), repository=Depends(store)):
        return run_planning(value, identity, repository, True)

    @application.get('/api/personalized-cultivation-plans/{plan_id}',response_model=SavedPersonalizedPlanResponse,
                     responses=error_responses(401,404,503))
    def read_personalized(plan_id: str, identity=Depends(farmer), repository=Depends(store)):
        from app.services.personalized_planning import retrieve
        return retrieve(repository, plan_id, identity)

    @application.post('/api/cultivation-analysis/alternatives',response_model=AlternativeComparisonResponse,
                      responses=error_responses(401,404,422,503))
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

    @application.get('/api/cultivation-analysis/clusters',responses=error_responses(403,422,503))
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

    @application.get('/api/cultivation-plans/{plan_id}/risk-assessment',response_model=RiskAssessmentResponse,
                     responses=error_responses(401,404,422,503))
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
            from app.services.farmer_workflow import run
            from app.schemas.alternatives import EvidenceRegistry
            report=run(repository,identity,plan_id,season,EvidenceRegistry(),cutoff)
            return dict(report['assessment'], indicators={}, explanations={},
                interpretation='Historical records are preserved; current pre-planting risk is not evaluated.')
        return farmer_view(assess(repository,cutoff,plan['district'],plan['region'],plan['crop'],season,
                                 date.fromisoformat(plan['expected_harvest_date'])))

    @application.get('/api/cultivation-analysis/risk-indicators',responses=error_responses(403,422,503))
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

    @application.get('/api/cultivation-analysis/risk-assessment',response_model=RiskAssessmentResponse,
                     responses=error_responses(403,422,503))
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

    @application.get('/health',response_model=HealthResponse,summary='Application liveness')
    def health_check() -> dict[str, str]:
        return {'status': 'healthy'}

    @application.get('/ready',response_model=ReadinessResponse,summary='Core dependency readiness',
                     responses={503: {'model': ReadinessResponse, 'description': 'Required dependency unavailable'}})
    def readiness(response: Response):
        from app.services.readiness import report
        result = report(database_path,roles,
                        os.getenv('CULTIVATION_LEGACY_FARMER_TOKENS_ENABLED','true').lower(),
                        historical_predictor,prospective_predictor,planning_guideline_dir)
        response.headers['Cache-Control'] = 'no-store'
        if result['status'] != 'ready':
            response.status_code = 503
        return result

    @application.get('/api/cultivation-plans',response_model=PlanListResponse,
                     summary='List the authenticated farmer\'s current plans',
                     responses=error_responses(401,422,503))
    def list_plans(request: Request,response: Response,
                   limit: int = Query(20,ge=1,le=100),
                   offset: int = Query(0,ge=0,le=1_000_000),
                   status: Literal['active','cancelled'] | None = Query(None),
                   crop: Crop | None = Query(None),district: District | None = Query(None),
                   identity=Depends(farmer),repository=Depends(store)):
        allowed = {'limit','offset','status','crop','district'}
        if any(key not in allowed for key in request.query_params):
            raise HTTPException(422,'Unsupported plan listing query parameter')
        if any(len(request.query_params.getlist(key)) != 1 for key in request.query_params):
            raise HTTPException(422,'Plan listing query parameters must not be repeated')
        response.headers['Cache-Control'] = 'no-store'
        return repository.list_owned(identity,limit,offset,status,crop,district)

    @application.post('/api/cultivation-plans',response_model=PlanResponse,status_code=201,
                      responses=error_responses(401,403,409,422,503))
    def create(value: PlanSubmission, identity=Depends(farmer), repository=Depends(store)):
        return repository.save(verified_plan_input(value,identity),identity)

    @application.get('/api/cultivation-plans/{plan_id}',response_model=PlanResponse,
                     responses=error_responses(401,404,503))
    def read(plan_id: str, identity=Depends(farmer), repository=Depends(store)):
        return repository.read(plan_id,identity)

    @application.put('/api/cultivation-plans/{plan_id}',response_model=PlanResponse,
                     responses=error_responses(401,403,404,409,422,503))
    def update(plan_id: str,value: PlanSubmission, identity=Depends(farmer),repository=Depends(store)):
        return repository.save(verified_plan_input(value,identity),identity,plan_id)

    @application.delete('/api/cultivation-plans/{plan_id}',response_model=PlanResponse,
                        responses=error_responses(401,404,503))
    def cancel(plan_id: str,identity=Depends(farmer),repository=Depends(store)):
        return repository.cancel(plan_id,identity)

    from app.prospective_routes import router as prospective_router
    application.include_router(prospective_router(farmer,analyst,administrator,store,prospective_predictor))

    from app.research_demo_routes import router as research_demo_router
    application.include_router(research_demo_router())

    # CORS is outside the auth response middleware, so normal error responses also
    # receive allowlist headers. This bearer API does not use credential cookies.
    from fastapi.middleware.cors import CORSMiddleware
    application.add_middleware(CORSMiddleware,allow_origins=frontend_origins,
                               allow_credentials=False,
                               allow_methods=['GET','POST','PUT','DELETE','OPTIONS'],
                               allow_headers=['Authorization','Content-Type','Accept'],
                               expose_headers=['WWW-Authenticate','Retry-After'])

    return application


app = create_app()
