# Registered farmer workflow

All examples use fictional accounts. Adjust future dates when necessary. See
`/docs` and `/openapi.json` for complete response schemas and
[authentication.md](authentication.md) for session security and deployment limits.

## Run and verify locally (PowerShell)

```powershell
Set-Location D:\Research\Rese\J26-IT-358\backend\cultivation-concentration
# First setup only, if .venv does not already exist:
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:CULTIVATION_PLAN_DB = "$PWD\storage\cultivation_plans.sqlite3"
$env:CULTIVATION_CORS_ORIGINS = '["http://localhost:5173"]'
.venv\Scripts\python.exe -B -m app.migrations
.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal at the same directory:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_farmer_workflow_e2e.py
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Back up an existing database before migration. This workflow change requires no
new migration. Readiness reports essential dependencies and optional artifacts
separately; it does not certify model validation or agricultural evidence.

## Frontend sequence

Send JSON with `Content-Type: application/json`. After login add
`Authorization: Bearer <returned access_token>` to every request. Keep credentials
out of URLs and logs. Identity comes from the session, without submitted farmer ID.

1. `POST /auth/register` (201), then `POST /auth/login` (200), same JSON:

```json
{"login_identifier":"fictional-workflow-farmer","password":"Fictional demonstration password 02!"}
```

Registration returns `farmer_id`, `login_identifier`, `authentication_method`, `created_at`.
Login returns `access_token`, `token_type`, `expires_in`, `expires_at`, `farmer`.
`GET /auth/me` returns the account profile.

2. `POST /api/farmer-workflow/plans` (201):

```json
{"crop":"Corn","district":"Matara","region":"north","land_size_acres":2,"planting_date":"2030-01-01","expected_harvest_date":"2030-04-01","season":"Maha"}
```

The response contains `plan` (including generated `plan_id`) and `workflow`.
Store `plan.plan_id`. This is a **response excerpt**, not the full response:

```json
{"workflow":{"status":"insufficient_evidence","analysis_status":"completed","assessment":{"status":"risk_level_unvalidated","risk_level":null},"clustering":{"algorithms":["K-Means","DBSCAN"]},"recommendations":{"status":"blocked_unvalidated_risk","alternatives":[]},"planning_status":"verified_guideline_gated_partial_planning_available"}}
```

`missing_evidence` explains validation gaps. Completion is separate from evidence
sufficiency. K-Means/DBSCAN describe similarity and density, not risk; noise is not
High risk. Concentration is in `workflow.assessment.indicators`, with collective
numeric values and peer cluster memberships withheld. Coverage suppression remains
explicit. No other farmer's records appear in this response.

3. `GET /api/cultivation-plans/<plan_id>` returns the saved plan and concentration
contract. `GET /api/farmer-workflow/plans/<plan_id>` returns
`{ "plan": ..., "personalized_plan": null }` until planning is saved.
`GET /api/cultivation-plans?limit=20&offset=0&status=active&crop=Corn&district=Matara`
returns `items`, `total`, `limit`, `offset`, `has_more`, `next_offset` for this owner.

4. `POST /api/farmer-workflow/analyze` (200):

```json
{"plan_id":"<returned plan_id>","season":"Maha"}
```

This reuses existing clustering, concentration and evidence-gated assessment.
`GET /api/cultivation-plans/<plan_id>/risk-assessment?season=Maha` returns owned
risk directly. Raw `/api/cultivation-analysis/clusters`, `/risk-indicators`, and
`/risk-assessment` remain research-role endpoints (403 for farmers); the workflow
is the privacy-filtered farmer integration.

5. `POST /api/cultivation-analysis/alternatives` (200):

```json
{"selected_crop":"Corn","district":"Matara","region":"north","land_size_acres":2,"planting_date":"2030-01-01","expected_harvest_date":"2030-04-01","replacing_plan_id":"<plan_id>"}
```

Inspect `status`, `comparisons` and evidence reasons. Missing approved suitability
or comparable coverage produces no eligible alternatives. Conditional eligibility
does not establish High risk; automatic workflow recommendations remain blocked
until independently verified classification evidence exists.

6. `POST /api/personalized-cultivation-plans/generate` (200):

```json
{"plan_id":"<plan_id>","final_crop":"Corn","district":"Matara","region":"north","land_size_acres":2,"planting_date":"2030-01-01","season":"Maha","planting_method":"direct_sowing"}
```

With insufficient approved guidance, the response has `status: "partial_plan"`,
`warnings`, `missing_categories` and `activities: []` when none are approved.
Unapproved guidance does not become active.

7. Save via `POST /api/farmer-workflow/select` with the planning JSON plus
`"save": true`, or `POST /api/personalized-cultivation-plans/save` with the planning
JSON. A different crop must pass the existing workflow recommendation gate.
Response keys: `personalized_plan`, `revision_id`, `revisions`, `stale`.
Retrieve via `GET /api/personalized-cultivation-plans/<plan_id>` or workflow read.
Concurrent plan changes preserve existing 409 checks.

8. `PUT /api/cultivation-plans/<plan_id>` with this complete ordinary plan body:

```json
{"crop":"Corn","district":"Matara","region":"north","land_size_acres":3,"planting_date":"2030-01-01","expected_harvest_date":"2030-04-01"}
```

The ID/history stay intact; previous personalized results become stale.
`DELETE /api/cultivation-plans/<plan_id>` cancels without deleting history.
Cancelled records remain retrievable/listable. `POST /auth/logout` returns 204
without JSON and revokes the session; further requests get 401.

## Historical records and recoverable writes

Ordinary CRUD intentionally permits historical/started records. Workflow submission
is a pre-planting operation: planting must be strictly after today's UTC date,
otherwise 422 before writing. Owner retrieval/listing preserve historical records.
Analyzing an available active historical version returns `analysis_status:
"not_applicable"`, `status: "insufficient_evidence"`, null risk and an explicit
eligibility reason. Owned risk assessment also returns insufficient evidence.
These records remain excluded from the unchanged future-plan research snapshot;
they are never deleted. A valid `as_of` can analyze a prior eligible version.
Unavailable or cancelled versions retain 404 semantics.

Persistence and analysis are separate operations. Input/configuration failures
before saving create no plan. The plan and initial history version commit
atomically. If later analysis raises or produces an invalid response, submission
still returns **201**, the committed owner plan and a safe report. Response excerpt:

```json
{"workflow":{"status":"analysis_unavailable","analysis_status":"failed","assessment":{"status":"insufficient_evidence","risk_level":null},"recovery":{"plan_saved":true,"retryable":true,"method":"POST","endpoint":"/api/farmer-workflow/analyze","request":{"plan_id":"<saved plan_id>","season":"Maha"}},"next_step":"retry_saved_plan_analysis","planning_status":"not_evaluated"}}
```

Retry that analysis request after dependency recovery; do not resubmit the plan.
Retry creates no cultivation revision. Failure responses contain no exception
text, peer data or invented results. Recovery is returned, not stored as an
analysis job: after restart retrieve/list the plan and request analysis again.
Network loss can still hide a committed response; refresh the owned list before
resubmission. Duplicate active plans return 409.

Unauthorized sessions return 401; cross-owner IDs return uniform 404; invalid
inputs return 422; invalid evidence configuration returns 503. Existing research
roles, privacy suppression, stale-plan checks and approval gates remain intact.

## Evidence limitations

Descriptive clustering/concentration cannot validate Low/Medium/High risk. Missing
classification evidence, verified production/yield, historical baselines, seasonal
coverage, suitability and approved agricultural claims remain explicit. Optional
models are not asserted healthy or validated. No yield, price, profit or demand
claims are fabricated.
## Persistent declared season

The existing workflow submission `season` now persists as
`plan.farmer_declared_season`. A fictional farmer may submit:

```json
{
  "district": "Matara", "region": "north", "crop": "Corn",
  "land_size_acres": 2, "planting_date": "2030-01-01",
  "expected_harvest_date": "2030-04-01", "season": "Maha"
}
```

POST this to `/api/farmer-workflow/plans` with the farmer's bearer session. Retrieval
and listing retain the declaration. POST `{"plan_id":"<owned-plan-id>"}` to
`/api/farmer-workflow/analyze` to use the cutoff-available stored declaration. Add
`"season":"Yala"` to analyze a different context: the response reports a conflict
and leaves the saved Maha declaration unchanged. Explicit season changes belong in
PUT `/api/cultivation-plans/<owned-plan-id>` using `farmer_declared_season` and the
existing required plan fields. This creates a revision and makes earlier saved
personalized results stale.

Personalized planning retains its explicit request `season` and approval matching.
Saving a personalized plan preserves the base declaration rather than replacing it
with planning context. Existing records remain unknown; no dates imply a season.
Neither a stored declaration nor an override verifies a statistical season/year,
enables a model, or approves agricultural guidance. See
[API contract](frontend_api.md) and [migration details](database_migrations.md).
