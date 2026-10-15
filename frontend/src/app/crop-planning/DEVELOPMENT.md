# Cultiva — Research Component 02

Premium farmer-facing crop-planning frontend built in the existing Next.js 14 App
Router project. React 18, TypeScript, Tailwind 3.4.19, source-owned shadcn/ui
new-york components and Lucide icons are retained. All feature styling, UI helpers,
research views and tests live in `src/app/crop-planning`. Sibling components and
backend algorithms are unchanged.

## Local development (PowerShell)

In `frontend`:

```powershell
npm ci
$env:NEXT_PUBLIC_CULTIVATION_API_URL = 'http://127.0.0.1:8000'
npm run dev
```

Open **http://localhost:3000/crop-planning**. The base URL defaults to
`http://127.0.0.1:8000`. It is a public build-time setting, not a credential;
rebuild a production frontend when changing it.

In `backend/cultivation-concentration`:

```powershell
$env:CULTIVATION_PLAN_DB = 'storage/cultivation_plans.sqlite3'
$env:CULTIVATION_CORS_ORIGINS = '["http://localhost:3000","http://127.0.0.1:3000","http://localhost:3001","http://127.0.0.1:3001"]'
.venv\Scripts\python.exe -B -m app.migrations
.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For the local fictional historical cohort only, set the explicit research cutoff
before starting Next.js:

```powershell
$env:NEXT_PUBLIC_CULTIVATION_RESEARCH_AS_OF = '2025-12-31T23:59:59Z'
```

This causes Risk Analysis and Suggested Crops to forward that `as_of` value.
Leave it unset for ordinary live farmer testing. It does not create data, bypass
ownership, or enable a current Low/Medium/High classification.

Back up an operational database before migration. The migration and application
must use the same database. CORS origins include the exact scheme, hostname and
port. This frontend uses farmer accounts, not analyst/admin/static credentials.
HTTPS is required for deployment.

## Primary page architecture

| Route | Audience and functionality |
| --- | --- |
| `/crop-planning` | Public landing page: research introduction, features, process, farmer benefits |
| `/crop-planning/register` | Public registration, live validation and password confirmation |
| `/crop-planning/login` | Public login, show/hide password, redirect to dashboard |
| `/crop-planning/dashboard` | Private owner summary, recent plans, upcoming dates and quick actions |
| `/crop-planning/risk-analysis` | Private plan selection and descriptive analysis |
| `/crop-planning/suggested-crops` | Private conditional crop comparison |
| `/crop-planning/cultivation-plan` | Private registration, saved-plan selection and personalized activity timeline |

Existing routes remain functional: `/crop-planning/plans`, `/plans/new`,
`/plans/<id>`, `/plans/<id>/analysis`, `/plans/<id>/alternatives`, and
`/plans/<id>/planning`. They reuse the redesigned form and research panels. Record
listing retains pagination and crop/district/status filters. Plan details retain
editing, cancellation, and exposed saved planning revision metadata.

`components/shell.tsx` separates public navigation from the protected farmer
sidebar/mobile menu. The public home is never replaced by an authenticated
dashboard. Login redirects to `/dashboard`. Mobile menus have explicit controls,
expanded state, Escape handling and keyboard focus restoration. Styles and reset
rules are scoped to `.cp-root`; Tailwind's global preflight remains disabled.

`components/plan-selector.tsx` pages only the authenticated owner's records and
retrieves the selected record through the existing workflow-read API before
rendering a research panel. Dashboard date summaries are explicitly scoped to
the six most recently registered active plans; the total active-plan count comes
from the owner's listing response. No collective metrics are used.

## Existing backend integration

| Feature | Existing endpoint |
| --- | --- |
| Register/login/profile/logout | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` |
| Own plans | `GET /api/cultivation-plans` |
| Register with analysis | `POST /api/farmer-workflow/plans` |
| Read owned plan and latest planning | `GET /api/farmer-workflow/plans/<id>` |
| Edit/cancel | `PUT`, `DELETE /api/cultivation-plans/<id>` |
| Run/retry analysis | `POST /api/farmer-workflow/analyze` |
| Conditional comparisons | `POST /api/cultivation-analysis/alternatives` |
| Preview/save planning | `POST /api/farmer-workflow/select`, `save: false/true` |
| Retrieve saved planning | `GET /api/personalized-cultivation-plans/<id>` |

`lib/api.ts` is reused without changing request or response contracts. No raw
farmer-ID selectors, analyst endpoints, or locally generated recommendations are
introduced. Only exposed personalized revision metadata and the latest result
are displayed; the API does not expose older cultivation/personalized payloads
through farmer routes.

## Validation, sessions and write recovery

Registration sends only `login_identifier` and `password`. Usernames are 3–100
ASCII letters, digits, or `. _ @ + -`; they are trimmed/lowercased, not verified
emails. Registration passwords contain 15–128 Unicode code points. Passwords are
never trimmed or normalized. Validation updates as users type; confirmation and
show/hide controls do not alter values.

New planting dates must be strictly after the backend's UTC calendar date. The
UI says “Please choose a future planting date”; the input's earliest date and the
validator use the same UTC cutoff. Calendar values remain ISO dates in API bodies,
with a readable day/month/year preview. Expected harvest may equal planting,
matching the actual backend contract. Historical dates remain allowed on ordinary
edits. Acreage must be finite and greater than zero; district/crop/season selections
must match backend values. A declared Maha/Yala season is not independently
verified statistical-season evidence.

Bearer credentials stay only in memory. The existing provider verifies `/auth/me`,
clears expired/401 sessions, and clears local state on logout even when remote
revocation fails. There are no cookies, localStorage, sessionStorage, credential
URLs or sensitive logging. Refreshing/closing the tab requires login again. Memory
storage reduces persistent exposure but cannot protect against JavaScript already
executing in the page; use HTTPS and an appropriate CSP. The backend remains the
ownership/security boundary.

No write is automatically retried. HTTP 201 preserves the returned plan ID even
if subsequent analysis failed. Both creation surfaces replace the form with the
saved result and offer an analysis retry for that ID. Switching workspace modes
does not restore a creation form for an already saved record. Registering another
record requires an explicit action. Network failure can conceal a committed
write; the UI directs users to their owned list before resubmission.

## Research presentation and imagery

The frontend renders an allowlist of owned plan fields and safe categorical
metadata, never raw response JSON. Protected peer counts, collective acreage,
crop shares and clustering details remain hidden even if unexpectedly returned.
It does not fabricate charts, risk scores, crop suitability, yield, profit,
demand, or activity dates.

Analysis execution, descriptive evidence, disclosure, conditional eligibility,
approval, partial schedules and staleness stay distinct. Detailed reasons sit in
accessible disclosure sections. Unknown metadata never grants approval; unknown
reason codes retain neutral text. The timeline displays only returned activities
with both explicit planning verification/approval evidence and the required
envelope approval status. Activity dates and quantities come from those returned
activities. Empty and unrecorded-approval states never synthesize a schedule.

The photograph at `public/crop-planning/terraces.jpg` is by **Andreas Felske**:
[source photograph](https://unsplash.com/photos/YnDuU2vTCY4), used under the
[Unsplash License](https://unsplash.com/license). It depicts rice terraces in Bali
and is decorative agricultural imagery, not a farmer record, local district
photograph, or research dataset. It is served locally through Next Image with
responsive sizes. Attribution appears in the public footer. Component source
and upstream MIT licensing are documented in `components/ui/SOURCE.md`.

## Checks

```powershell
npm run lint
npm run typecheck
npm run test:crop-planning
npm run build
```

The test runner uses Node's built-in framework, TypeScript and React's test
renderer, compiling into ignored `_test-build/`. Tests cover registration/login,
dashboard redirect, public/private navigation, live validation, exact UTC/date
boundaries, Unicode password length, ownership-safe plan selection, privacy,
approval filtering, partial/stale timelines, API errors and 201 recovery on both
creation surfaces. Fixtures are explicitly fictional and never served by the app.

`tests/live-api-smoke.mjs` is a write test intended only for a disposable loopback
backend database. Production HTTP smoke checks verify the seven main pages and
all six retained routes. Full visual browser QA is unavailable in this environment.

The existing transitive ESLint visitor-keys dependency declares Node
`^20.19.0 || ^22.13.0 || >=24`; npm warns on this workspace's Node 22.12.0.
The existing Next 14-compatible lint tooling is retained. No dependency update
was required for the redesign.

## Verification and source structure

The redesigned implementation passed lint, TypeScript, **27 frontend tests**, and
the production build. HTTP checks passed for all 13 crop-planning routes and local
image optimization. The actual frontend API client passed a live check against
FastAPI with a temporary SQLite database: authentication, owned plan CRUD/listing,
analysis, conditional comparison, partial planning, stale revisions, CORS,
cancellation, and logout. Both temporary servers were stopped after verification.
No operational farmer database was used.

Primary pages are `page.tsx`, `register/page.tsx`, `login/page.tsx`,
`dashboard/page.tsx`, `risk-analysis/page.tsx`, `suggested-crops/page.tsx`, and
`cultivation-plan/page.tsx`. Reusable presentation lives in `components/brand.tsx`,
`shell.tsx`, `auth-form.tsx`, `plan-form.tsx`, `plan-selector.tsx`,
`analysis-panel.tsx`, `comparison-panel.tsx`, `planning-panel.tsx`, and `ui.tsx`.
`lib/navigation.ts` and `lib/dates.ts` provide routing/date helpers;
`lib/validation.ts` aligns user-friendly validation with existing backend rules.
`lib/api.ts`, `lib/contracts.ts`, `lib/evidence.ts`, and the in-memory session
provider's authentication logic remain intact. Existing nested `plans/` pages
reuse these components. The only asset outside the feature source folder is the
scoped public photograph. No staging, commit, or push was performed.
