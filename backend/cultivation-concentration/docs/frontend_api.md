# Frontend API integration

The frontend uses existing Component 02 endpoints and bearer sessions. No research
service is duplicated or automatically promoted to validated risk prediction.
OpenAPI and Swagger UI are available at `/openapi.json` and `/docs`.

## Existing routes reused

| Capability | Existing method and path |
| --- | --- |
| Accounts | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` |
| Create a plan | `POST /api/cultivation-plans` |
| Read, update, cancel an owned plan | `GET`, `PUT`, `DELETE /api/cultivation-plans/{plan_id}` |
| Owned descriptive risk assessment | `GET /api/cultivation-plans/{plan_id}/risk-assessment` |
| Submit a plan with analysis | `POST /api/farmer-workflow/plans` |
| Analyze an owned plan | `POST /api/farmer-workflow/analyze` |
| Preview or save a selection | `POST /api/farmer-workflow/select` |
| Read plan and saved personalized result | `GET /api/farmer-workflow/plans/{plan_id}` |
| Conditional crop comparison | `POST /api/cultivation-analysis/alternatives` |
| Generate/save/read personalized plans | `POST /api/personalized-cultivation-plans/generate`, `POST /api/personalized-cultivation-plans/save`, `GET /api/personalized-cultivation-plans/{plan_id}` |
| Restricted analyst/admin analysis | `GET /api/cultivation-analysis/clusters`, `/risk-indicators`, `/risk-assessment` |
| Liveness | `GET /health` |

Expert-validation and prospective-evaluation routes retain their existing role
requirements. Farmer account sessions never grant analyst, administrator or reviewer access.

## New farmer listing

`GET /api/cultivation-plans` requires `Authorization: Bearer <session>` and lists
only current records owned by the verified farmer. It accepts no farmer-ID selector.

| Query | Default | Allowed values |
| --- | --- | --- |
| `limit` | 20 | Integer 1-100 |
| `offset` | 0 | Integer 0-1,000,000 |
| `status` | Unfiltered | `active`, `cancelled` |
| `crop` | Unfiltered | `Mung Beans`, `Corn`, `Bandakka`, `Brinjal`, `Pumpkin`, `Chillies` |
| `district` | Unfiltered | `Matara`, `Hambantota` |

Filters combine with AND. Values are case-sensitive. Unknown or repeated query
parameters return 422, including submitted `farmer_id` selectors. SQL uses
parameterized values, an owner predicate, database-level count/filter/LIMIT/OFFSET,
and owner-specific indexes. Count and page share a single read transaction.

Order is `submitted_at DESC, plan_id DESC`, giving a deterministic tie-breaker.
Updates do not change original submission order. Default listing includes cancelled
plans; use `status=active` for a current cultivation dashboard. Cancellation never
deletes records or historical versions. Listing does not expose the version history
or other farmers' plans and does not compute collective concentration totals.

The 200 response contract is:

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0,
  "has_more": false,
  "next_offset": null
}
```

Each nonempty `items` element has the existing `Plan` shape: `plan_id`, verified
`farmer_id`, `district`, `region`, `crop`, `land_size_acres`, planting and expected
harvest dates, submission/update timestamps, and status. It is the same plan object
found inside existing CRUD responses, without their separate `concentration` wrapper.
`total` counts the authenticated farmer's filtered current records. Offsets at or
beyond total return an empty page with the same total. Follow `next_offset` while
`has_more` is true. Responses use `Cache-Control: no-store`.

Pagination is stable within each request. New registrations or status/filter changes
between requests can shift offset pages; this is not a frozen multi-request snapshot.

## Browser authentication and requests

The following example uses a fictional account and future sample dates. It assumes
the frontend origin has been allowed by deployment configuration. Keep the returned
credential in memory; do not put it in URLs, source control or analytics.

```javascript
const baseUrl = "http://127.0.0.1:8000";
let accessToken;

async function api(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(baseUrl + path, {
    method,
    headers,
    credentials: "omit",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    if (response.status === 401) accessToken = undefined;
    const error = await response.json();
    throw new Error(`${response.status}: ${JSON.stringify(error.detail)}`);
  }
  return response.status === 204 ? null : response.json();
}

const fictionalCredentials = {
  login_identifier: "fictional-frontend-demo",
  password: "A fictional frontend demo passphrase!",
};
await api("/auth/register", { method: "POST", body: fictionalCredentials });
const session = await api("/auth/login", { method: "POST", body: fictionalCredentials });
accessToken = session.access_token;
const me = await api("/auth/me");

const input = {
  district: "Matara",
  region: "fictional-demo-region",
  crop: "Corn",
  land_size_acres: 2,
  planting_date: "2030-01-01",
  expected_harvest_date: "2030-04-01",
};
const created = await api("/api/cultivation-plans", { method: "POST", body: input });
const id = created.plan.plan_id;

const filters = new URLSearchParams({
  limit: "20", offset: "0", status: "active", crop: "Corn", district: "Matara",
});
const page = await api(`/api/cultivation-plans?${filters}`);
const detail = await api(`/api/cultivation-plans/${id}`);
await api(`/api/cultivation-plans/${id}`, {
  method: "PUT", body: { ...input, land_size_acres: 3 },
});

const workflow = await api("/api/farmer-workflow/analyze", {
  method: "POST", body: { plan_id: id, season: "Maha" },
});
// Display status, missing evidence and warnings. null risk_level is not Low risk.
console.log(workflow.assessment.status, workflow.assessment.missing_evidence);

await api(`/api/cultivation-plans/${id}`, { method: "DELETE" });
await api("/auth/logout", { method: "POST" });
accessToken = undefined;
```

Registration duplicates return 409; log in rather than registering again. Sessions
expire and must be renewed through login. CRUD bodies may omit `farmer_id`; a supplied
value must match the verified identity or the server returns 403. Cross-farmer
detail access remains 404. See [account security](authentication.md) for lifecycle,
research-token compatibility, limits and production requirements.

## CORS allowlist

Set `CULTIVATION_CORS_ORIGINS` to a JSON array before starting the application:

```powershell
$env:CULTIVATION_CORS_ORIGINS = '["http://localhost:5173","http://127.0.0.1:5173"]'
```

Unset means `[]`: no cross-origin browser access. List exact scheme/host/port origins,
without paths or trailing slashes. Wildcards, origin regexes, userinfo, invalid ports
and malformed configuration are rejected at startup. HTTP and HTTPS origins are
supported; public deployments should use HTTPS. Restart to apply changes.

The allowlist permits GET, POST, PUT, DELETE and OPTIONS; request headers include
Authorization, Content-Type and Accept. Retry-After and WWW-Authenticate are exposed
to browser clients. Cookies are not enabled (`allow_credentials=False`); the API
uses an explicitly supplied Authorization header with `credentials: "omit"`.
Allowed preflights return 200. Disallowed origins, methods or request headers return
400. Ordinary requests from disallowed origins receive no allow-origin header,
so browsers cannot expose their responses. CORS does not deny access to non-browser
HTTP clients and does not replace authentication.

Configuration follows [FastAPI's explicit-origin CORS guidance](https://fastapi.tiangolo.com/tutorial/cors/).

## Response contracts and errors

Existing CRUD response wrappers and status codes are retained. Explicit response
models now describe workflow submit/analyze/read/select, personalized generation/
saved results, conditional alternatives and risk assessment responses. Variable
research/evidence dictionaries and extra privacy annotations remain intact; response
models do not introduce categories, thresholds, defaults or agricultural evidence.
Risk status, warnings and missing-evidence fields remain the source of frontend state.
Some restricted research responses remain dynamic dictionaries.

OpenAPI documents successful schemas and relevant error responses for frontend routes.
HTTPException responses retain `{"detail": "message"}`. Validation errors retain
`{"detail": [...]}`; auth validation omits submitted field values. The readiness
503 response uses its readiness report, not an HTTPException detail wrapper.

| Status | Frontend handling |
| --- | --- |
| 200/201 | Use the documented result; 201 means a plan/account was created |
| 204 | Logout succeeded; no JSON body |
| 401 | Missing, invalid, expired or revoked credentials; prompt for login |
| 403 | Identity assertion mismatch or insufficient role/permission |
| 404 | Owned resource unavailable; do not infer another farmer's ownership |
| 409 | Duplicate, cancelled or changed plan, or selection not eligible; refresh/review |
| 422 | Invalid fields, pagination, filter or cutoff; show validation errors |
| 429 | Authentication limit; honor Retry-After |
| 503 | Required dependency/configuration unavailable; do not invent successful analysis |

Preflight rejection is a plain-text CORS 400. Browser CORS failures may surface as
network errors rather than readable API responses. Workflow submission returns 201
with the saved plan and `workflow.analysis_status: "failed"` if analysis fails after
commit. Follow `workflow.recovery` to retry analysis rather than resubmitting.
Network loss can still hide a committed response; refresh the owned list first.
See [the complete farmer journey](farmer_workflow.md) for requests, date policy,
evidence states and recovery examples.

## Liveness and readiness

`GET /health` keeps its existing 200 `{"status":"healthy"}` response. It indicates
application liveness and does not check the database or validate research.

`GET /ready` returns a Pydantic report with `status`, `checks` and
`research_validation: "not_asserted"`, using HTTP 200 when essential dependencies
are ready and HTTP 503 otherwise. Both outcomes disable caching. Public reports
omit filesystem paths, credentials, farmer counts and database exception details.

Required checks cover:

- Cultivation/account tables and required columns, the account migration ledger,
  and SQLite write access through a rolled-back transaction.
- Valid research role registries, account-session lifetime/compatibility settings,
  and availability of the scrypt hashing API.
- Successful import of the existing clustering runtime dependencies.

Readiness never creates databases, applies migrations, loads model binaries or
trains models. Initialize before starting traffic:

```powershell
Set-Location D:\Research\Rese\J26-IT-358\backend\cultivation-concentration
$env:CULTIVATION_PLAN_DB = 'storage/cultivation_plans.sqlite3'
$env:CULTIVATION_CORS_ORIGINS = '["http://localhost:5173"]'
.venv\Scripts\python.exe -B -m app.migrations
.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The migration CLI reuses existing plan initialization, including owner-listing
indexes and existing pre-versioning backfill semantics. A missing database or
schema yields not-ready; a busy/read-only/unavailable database also yields 503.
Readiness checks connection, schema and write access, not comprehensive integrity,
load capacity, free disk space, or encrypted storage.

Optional checks report guidelines, catalogued model file presence, and injected
historical/prospective predictors. Possible statuses include `missing`, `unavailable`,
`not_configured`, `present_not_validated`, `available_not_approved` and
`configured_not_validated`. Optional absence does not block account/plan operations.
File presence is not hash verification, predictor configuration is not inference
readiness, and readable guidelines are not approved applicable agricultural claims.
Readiness does not check all historical sources, evidence overlays or research outcomes.

## Verification and remaining limitations

```powershell
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_frontend_api.py
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Tests use fictional accounts/plans, temporary databases and synthetic optional
artifact metadata. The full existing suite requires authorized private research
inputs. These changes do not activate a validated risk classifier, automatic
High-risk recommendations, or unapproved guideline activities. Offset pagination
has a bounded but growing cost for deep pages. SQLite concurrency and deployment
abuse controls still require operational review.
## Farmer-declared season

Existing cultivation-plan POST and PUT bodies accept the optional field
`"farmer_declared_season": "Maha"` (or `"Yala"`, or `null`). Plan responses,
owned list items, and workflow retrieval include it. Existing clients may omit it:
creation remains unknown, and updates preserve the current declaration. Explicit
`null` clears it. Unsupported values return 422. Ownership/session errors retain
their existing 401/403/404 behavior.

Workflow submission continues accepting the existing `season` field and now stores
it as `farmer_declared_season`. Analysis requests still accept `season`. A supplied
analysis season takes precedence for that analysis only; otherwise the declaration
from the plan version available at `as_of` is used. Neither operation infers a
season from dates or writes an analysis override to plan history.

Workflow reports add `season_context`, for example:

```json
{
  "farmer_declared_season": "Maha",
  "requested_season": "Yala",
  "effective_analysis_season": "Yala",
  "source": "analysis_request",
  "conflict": true,
  "independently_verified_statistical_season": null,
  "interpretation": "Analysis context only; independent statistical-season/year mapping and evidence approvals remain required"
}
```

The verified statistical-season field remains null in this context: independent
mapping evidence is managed separately, and no declaration is promoted to verified
evidence. Current concentration analysis still makes no season-specific population
filtering claim. Risk, historical model compatibility, coverage, and guideline
approval gates remain unchanged.
