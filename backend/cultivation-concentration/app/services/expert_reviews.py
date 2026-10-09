"""Exclusive JSON exports/import validation; never assigns or verifies labels."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from app.schemas.expert_review import ExpertCase,ExpertReview


def digest(case):
    return hashlib.sha256(json.dumps(case.model_dump(mode='json'),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def create_case(assessment):
    values=assessment['indicators']
    if values['status']!='available':
        raise ValueError('Private/insufficient cases cannot enter review export')
    indicators={key:values[key] for key in ('overlapping_farmer_count','overlapping_plan_count','total_planned_acreage',
            'harvest_overlap_intensity','estimated_production_kg','historical_concentration_baseline')}
    for algorithm in ('kmeans','dbscan'):
        indicators['district_'+algorithm+'_groups']=[{key:group[key] for key in ('farmer_count','plan_count','planned_acreage')}
            for group in values.get('cluster_context',{}).get(algorithm,[]) if group.get('status')=='available']
    from datetime import date,timedelta
    anchor=date.fromisoformat(values['harvest_window_start'])+timedelta(days=14)
    return ExpertCase(case_id=str(uuid4()),forecast_cutoff=values['as_of'],
        scenario=dict(district=values['district'],crop=values['crop'],season=values['season'],harvest_month=anchor.isoformat()[:7]),
        indicators=indicators,
        missing_evidence=list(assessment['missing_evidence']))


def template(case):
    return dict(case_id=case.case_id,case_digest=digest(case),label_kind='expert_reference',reference_label=None,
                reason='',reviewer_id='',reviewer_role='',reviewer_organization='',reviewed_at=None,rubric_version='')


def export_cases(assessments,path):
    cases=[create_case(assessment) for assessment in assessments]
    if not cases:
        raise ValueError('No releasable cases')
    content=dict(schema_version='phase3b-v1',cases=[c.model_dump(mode='json') for c in cases],
                 review_templates=[template(c) for c in cases])
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(content,stream,indent=2)
    return cases


def validate_reviews(cases,submitted,now=None):
    """Atomic batch validation. Acceptance is structural, not reviewer verification."""
    now=now or datetime.now(timezone.utc)
    lookup={case.case_id:case for case in cases}
    if len(lookup)!=len(cases):
        raise ValueError('Duplicate case IDs')
    accepted=[];seen=set()
    for item in submitted:
        review=ExpertReview.model_validate(item)
        case=lookup.get(review.case_id)
        if case is None or review.case_digest!=digest(case):
            raise ValueError('Unknown or altered review case')
        key=(review.case_id,review.reviewer_id,review.rubric_version)
        if key in seen:
            raise ValueError('Duplicate reviewer/case/rubric submission')
        seen.add(key)
        if not case.forecast_cutoff<=review.reviewed_at<=now:
            raise ValueError('Review timestamp outside permitted chronology')
        accepted.append(dict(review=review.model_dump(mode='json'),reviewer_identity_verified=False,
                             adjudication_status='pending',training_eligible=False))
    return accepted


def import_reviews(case_path,review_path,output_path):
    """Keep imports in a separate review artifact; original cases remain unlabeled."""
    content=json.loads(Path(case_path).read_text(encoding='utf-8'))
    cases=[ExpertCase.model_validate(c) for c in content['cases']]
    reviews=json.loads(Path(review_path).read_text(encoding='utf-8'))
    accepted=validate_reviews(cases,reviews)
    with Path(output_path).open('x',encoding='utf-8') as stream:
        json.dump(dict(expert_reviews=accepted,provisional_rule_reviews=[]),stream,indent=2)
    return accepted
