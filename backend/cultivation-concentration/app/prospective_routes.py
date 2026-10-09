"""Authenticated routes; reuse existing role dependencies and plan repository."""
from fastapi import APIRouter,Depends
from app.schemas.prospective import AssessmentRequest,Protocol,Outcome
from app.services import prospective as service

def router(farmer,analyst,administrator,store,predictor=None):
    routes=APIRouter(prefix='/api/prospective',tags=['prospective research evaluation'])
    @routes.post('/protocols',status_code=201)
    def protocol(value:Protocol,actor=Depends(administrator),repository=Depends(store)):
        return service.register_protocol(repository,value,actor)
    @routes.post('/assessments',status_code=201)
    def assess(value:AssessmentRequest,identity=Depends(farmer),repository=Depends(store)):
        return service.assess(repository,identity,value,predictor)
    @routes.get('/assessments/{assessment_id}')
    def read(assessment_id:str,identity=Depends(farmer),repository=Depends(store)):
        return service.get_assessment(repository,identity,assessment_id)
    @routes.get('/audit/assessments/{assessment_id}')
    def audit(assessment_id:str,authorized=Depends(analyst),repository=Depends(store)):
        return service.get_assessment(repository,None,assessment_id,restricted=True)
    @routes.post('/outcomes',status_code=201)
    def outcome(value:Outcome,actor=Depends(administrator),repository=Depends(store)):
        return service.record_outcome(repository,value,actor)
    return routes
