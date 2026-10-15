# Final scientific and code review

The findings below record the earlier review snapshot. See the subsequent
[P0/P1 remediation report](security_privacy_blocker_fixes.md) for fixes, updated
verification and the current disclosure/commit assessment.

Reviewed 2026-10-14 against the current complete working tree on
`feature/dasuni/cultivation-concentration-new`.

**Verdict: the complete working tree is not ready for a safe commit.** The
historical distinction between retrospective concentration and current risk is
substantially correct, but the complete pending changes contain security,
privacy and agricultural presentation regressions that passing tests miss.

No application code was changed during this review. Only this report and ignored
review logs were written. No models, labels or research metrics were changed;
nothing was staged, committed, pushed or rebased. Existing edits were preserved.

## Findings requiring resolution before committing the whole change

### 1. P1: the primary cultivation page bypasses approved agricultural activity rendering

`frontend/src/app/crop-planning/cultivation-plan/page.tsx:78` defines static crop
profiles described as verified Department of Agriculture guidelines, with fixed
dates, quantities and Completed/Current Stage statuses. The default schedule
at line 952 renders those profiles; line 2212 renders their guidance directly.
It only requests the owner's plan listing, not approved planning activities.
It does not use `approvedActivities`, `PlanningPanel` or `PlanningResult`.

Read-only rendering of the current compiled page, without any backend planning
response, confirmed that it shows a personalized schedule, manure quantities in
tons/acre, a Completed stage and recommended practices. This can present invented
or inapplicable instructions even when the approval registry has no entries.
The properly gated nested `/plans/<id>/planning` page does not repair this other
route. Replace the primary route's static schedule with approved returned
activities, or clearly isolate a non-actionable illustrative mockup outside the
operational farmer workflow. Add a route-level regression for absent approvals.

### 2. P1: CORS silently broadens the configured origin allowlist outside pytest

`backend/cultivation-concentration/app/cors.py:10` changes an absent setting from
no allowed origins to localhost defaults. Lines 33 onward expand an explicit
localhost origin to ports 3000-3005. Both behaviors are disabled when
`PYTEST_CURRENT_TEST` exists. `app/main.py:451` also enables private-network CORS
globally. These changes are separate from historical simulation isolation and
weaken the previous explicit deployment allowlist.

A read-only reproduction with only `http://localhost:3000` configured returned
six effective origins in normal execution, but one under pytest. Existing CORS
tests therefore do not exercise the deployed behavior. Preserve the operator's
exact origins in all environments, with separately explicit development options
if needed, and test ordinary execution rather than branching on pytest state.

### 3. P1: research response suppression does not protect singleton history or sparse count side channels

`app/research_demo_routes.py:63` is enabled by a server flag/file but does not
require an authenticated researcher. `historical_research_evaluator.py:286`
returns historical numeric features unconditionally. Only sparse overlap count
is suppressed; prior-window means and previous-year mean plan acreage remain
visible. `concentration_indicators` and observation metadata also return exact
unknown-availability counts when ordinary sparse counts are withheld.

Using only fictional fixtures, a single prior plan of 7.25 acres resulted in
`Past_Window_Count=1` and `Previous_Year_Mean_Plan_Acres=7.25` in the response.
For one peer, displayed peer count was null but `replay_unknown_peer_records=1`.
Thus withholding some fields does not prevent recovery of sensitive values.
The original dataset's individual provenance is unverified, so it cannot safely
be presumed public or synthetic. Protect private-data research access and apply
disclosure policy to the entire response, including derived features and counts,
or use a reviewed non-private demonstration source. No real individual record
was used in the reproduction. The API must not be publicly enabled against the
private historical source in its current form.

## Additional findings

- P2: `risk-analysis/page.tsx:518` states that no peers exist whenever the risk
  category is unvalidated; `suggested-crops/page.tsx:451` similarly asserts zero
  peers. A null risk or withheld aggregate does not establish zero peers. The
  research lab keeps this distinction, but these operational explanations do not.
- P2: `components/session.tsx:28` restores a bearer session from sessionStorage,
  and line 45 writes it there. `DEVELOPMENT.md:117` and the login notice still
  claim memory-only credentials and no sessionStorage. Resolve that contract
  mismatch and verify restoration/expiry/revocation behavior. No bearer secret
  was embedded in the files scanned.
- The pending change includes an entire frontend, root portal, 18 JPEG assets,
  UI components and dependency changes beyond the historical fixes. The portal
  claims verified alternatives, risk categories including Critical, and realized
  benefits that the scientific audit does not establish. The dashboard has fixed
  activity reminders and a fixed two-plan insight. These require separate scope
  and scientific presentation review before blanket staging.
- Only the terrace photograph's provenance/license is documented locally. No
  EXIF headers were detected in the 18 JPEGs, but that does not prove their
  licensing, consent or provenance. No claim is made that all images are cleared.
- The lockfile adds 318 package entries and changes 76 existing entries. Some
  inherited resolved URLs use an alternate npm mirror. This is not evidence of
  a vulnerability, but reinforces that the full diff exceeds a minimal research
  fix and needs an intentional dependency/scope review.

## Temporal and scientific assessment

The date cutoff is independent of selected planting date and means start of day
in Asia/Colombo. The API constrains it to the research date range and on/before
planting; the replay rejects differing planting/cutoff calendar years.

Verified observation-version timestamps after cutoff are excluded from both
peers and prior features. Earlier-planted peers also require expected harvest
on/after cutoff and an inclusive +/-14-day harvest match. Prior references
require earlier recorded Years and expected harvest strictly before cutoff.
The old whole-cohort yield median is gone. Historical production sums use
recorded production; own production is missing and handled by the frozen model.
Targets, target acreage and target percentile thresholds are absent from inputs.

**An unconditional claim that future observations cannot leak is unsupported.**
Unknown availability remains explicitly included in the retrospective replay.
An unverified late timestamp is classified unknown, not independently trusted.
Unknown publication/version lags can therefore retain later information. The
data and model availability at historical decisions are not established. The
verified-availability view excludes unknown records; the current API/UI never
calls those unknown records verified. Existing regression tests check known
late observations and mutations of future records; they do not prove missing
historical observability.

`Year` is not read as a submission/observation timestamp. Actual Planting_Date
and Expected_Harvest_Date drive calendar membership. There are 6,241 records
whose Year differs from planting calendar year. Historical grouping still uses
recorded Year, while reference selection and model metadata use the scenario's
calendar year. That alignment remains an explicit unverified replay assumption,
not a verified statistical-season mapping. The `is_out_of_time_holdout` field
must be read with its metadata caveat; it does not establish an untouched or
available-at-the-time operational holdout.

Historical `historical_proxy_label` and its compatibility alias remain inside
the research envelope. Operational status stays unvalidated, alternatives are
empty, and automatic recommendations stay blocked. The existing backend
`defensible_high`, suitability/comparable-coverage gates and guideline approvals
are unchanged. The backend operational 8-input predictor still rejects the
incompatible 15-input artifact rather than inventing missing inputs. The primary
frontend schedule issue above prevents confirming those approvals are respected
through every user-facing route.

### XGBoost High versus direct acreage-rule Medium

Read-only reproduction confirms Scenario A has 83 peers/218.5 peer acres and
222 scenario-inclusive acres; Scenario B has 214 peers/549 peer acres and
552.5 inclusive acres. XGBoost predicts Low/High. The unchanged historical
linear P33/P67 references are 320.81/737.97 acres, so direct application of that
rule gives Low/Medium. Target overlap acreage is excluded from XGBoost's inputs;
the learned approximation can disagree with the underlying rule.

This is a hypothetical-scenario approximation discrepancy, not verified market
oversupply or an independent ground-truth outcome. It is already documented in
`historical_simulation_audit.md` and is retained here without changing labels,
models, thresholds or research metrics. A shared explicit cutoff gives identical
inputs for the two June planting dates. No comparison validates current risk.

## Fresh verification results

| Check | Current result |
| --- | --- |
| Full backend `python -m pytest tests -q` | 440 passed in 192.77 seconds; one Starlette/httpx deprecation warning |
| Frontend `npm run test:crop-planning` | 32 passed, zero failures |
| Frontend `npm run typecheck` | Passed |
| Frontend `npm run lint` | Passed with image/hook warnings |
| Frontend `npm run build` | Passed with the same warnings |
| `git diff --check` | Passed; Git also notes LF/CRLF normalization |
| Artifact integrity | All 63 catalogued files present and hash-identical; 31 are joblib model/preprocessing binaries |
| Original historical CSV | SHA-256 unchanged: `4397ddae6a3fabde06f1b9dc6fd42d40b3f0cc5a5275754621011e4cfcbb2bab` |
| Staging area | Empty |

All backend test files are in Component 02. Tests fitting small fictional
classifiers do not retrain or overwrite research artifacts. Logs are under the
ignored `backend/cultivation-concentration/logs/final-review-*` paths. The normal
test commands were rerun; the additional reproductions were read-only and used
fictional fixtures or aggregate historical calculations. No live-write smoke
script was run against an operational database.

The complete pending-file inventory contains no raw CSV exports, model binaries,
databases, archives, private key files or real environment files. A redacted
high-confidence credential scan found no embedded secret; remaining literals
were fictional test credentials or validation messages. Real .env files, private
historical/model storage and review logs remain ignored. This checks the current
pending changes, not a guarantee that future blanket staging or force-add is safe.

Remaining scientific limitations: source and version provenance; actual
observation/model availability; regional and season/reporting-year mapping;
dependent overlapping windows; incomplete or nonrepresentative participation;
global missing-input treatment; uncalibrated class probabilities; previously
examined development/evaluation years; independent current-risk labels and
prospective field/market outcomes; applicable guideline/suitability approvals.

## Commit recommendation

Do not commit the entire current working tree yet. Resolve the three P1 findings,
correct evidence explanations, and separate the unrelated frontend/dependency
scope before a commit review. The historical isolation, frozen model integrity
and passing tests are useful evidence, but do not override the reproduced
security/privacy/approval defects. No staging or history changes were made by this review.

## Exact changed-file inventory

At review start: 8 tracked modifications, 84 untracked files, zero staged files.
The only new visible file created by this review is this report. Final inventory:
8 tracked modifications and 85 untracked files (93 total). No application source
file changed during this review.

### Modified tracked files (8)

- `backend/cultivation-concentration/README.md`
- `backend/cultivation-concentration/app/cors.py`
- `backend/cultivation-concentration/app/main.py`
- `backend/cultivation-concentration/docs/historical_inference.md`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/tailwind.config.ts`
- `frontend/tsconfig.json`

### Untracked files (85)

- `backend/cultivation-concentration/app/research_demo_routes.py`
- `backend/cultivation-concentration/app/schemas/research_demo.py`
- `backend/cultivation-concentration/app/seed_demo_data.py`
- `backend/cultivation-concentration/app/services/historical_research_evaluator.py`
- `backend/cultivation-concentration/docs/historical_simulation_audit.md`
- `backend/cultivation-concentration/docs/historical_simulation_final_review.md`
- `backend/cultivation-concentration/tests/test_research_demo.py`
- `backend/cultivation-concentration/tests/test_research_temporal_correctness.py`
- `backend/cultivation-concentration/tests/test_seed_demo_data.py`
- `frontend/.env.example`
- `frontend/.eslintrc.json`
- `frontend/.gitignore`
- `frontend/components.json`
- `frontend/public/crop-planning/agfarm_aerial.jpg`
- `frontend/public/crop-planning/agfarm_hero.jpg`
- `frontend/public/crop-planning/terraces.jpg`
- `frontend/public/images/about_farmer.jpg`
- `frontend/public/images/component1_market.jpg`
- `frontend/public/images/component2_planning.jpg`
- `frontend/public/images/component3_waste.jpg`
- `frontend/public/images/component4_climate.jpg`
- `frontend/public/images/crop_brinjal_detail.jpg`
- `frontend/public/images/crop_chili_detail.jpg`
- `frontend/public/images/crop_corn_detail.jpg`
- `frontend/public/images/crop_mungbean_detail.jpg`
- `frontend/public/images/crop_okra_detail.jpg`
- `frontend/public/images/crop_pumpkin_detail.jpg`
- `frontend/public/images/crop_tomato_detail.jpg`
- `frontend/public/images/dashboard_banner_landscape.jpg`
- `frontend/public/images/field_furrows_detail.jpg`
- `frontend/public/images/hero_farmer.jpg`
- `frontend/src/app/crop-planning/.gitignore`
- `frontend/src/app/crop-planning/DEVELOPMENT.md`
- `frontend/src/app/crop-planning/components/analysis-panel.tsx`
- `frontend/src/app/crop-planning/components/auth-form.tsx`
- `frontend/src/app/crop-planning/components/brand.tsx`
- `frontend/src/app/crop-planning/components/comparison-panel.tsx`
- `frontend/src/app/crop-planning/components/plan-form.tsx`
- `frontend/src/app/crop-planning/components/plan-selector.tsx`
- `frontend/src/app/crop-planning/components/plan-workspace.tsx`
- `frontend/src/app/crop-planning/components/planning-panel.tsx`
- `frontend/src/app/crop-planning/components/research-result.tsx`
- `frontend/src/app/crop-planning/components/session.tsx`
- `frontend/src/app/crop-planning/components/shell.tsx`
- `frontend/src/app/crop-planning/components/ui.tsx`
- `frontend/src/app/crop-planning/components/ui/LICENSE.txt`
- `frontend/src/app/crop-planning/components/ui/SOURCE.md`
- `frontend/src/app/crop-planning/components/ui/alert.tsx`
- `frontend/src/app/crop-planning/components/ui/badge.tsx`
- `frontend/src/app/crop-planning/components/ui/button.tsx`
- `frontend/src/app/crop-planning/components/ui/card.tsx`
- `frontend/src/app/crop-planning/components/ui/input.tsx`
- `frontend/src/app/crop-planning/components/ui/label.tsx`
- `frontend/src/app/crop-planning/components/ui/native-select.tsx`
- `frontend/src/app/crop-planning/components/ui/table.tsx`
- `frontend/src/app/crop-planning/crop-planning.css`
- `frontend/src/app/crop-planning/cultivation-plan/page.tsx`
- `frontend/src/app/crop-planning/dashboard/page.tsx`
- `frontend/src/app/crop-planning/layout.tsx`
- `frontend/src/app/crop-planning/lib/api.ts`
- `frontend/src/app/crop-planning/lib/contracts.ts`
- `frontend/src/app/crop-planning/lib/dates.ts`
- `frontend/src/app/crop-planning/lib/evidence.ts`
- `frontend/src/app/crop-planning/lib/navigation.ts`
- `frontend/src/app/crop-planning/lib/utils.ts`
- `frontend/src/app/crop-planning/lib/validation.ts`
- `frontend/src/app/crop-planning/login/page.tsx`
- `frontend/src/app/crop-planning/page.tsx`
- `frontend/src/app/crop-planning/plans/[planId]/alternatives/page.tsx`
- `frontend/src/app/crop-planning/plans/[planId]/analysis/page.tsx`
- `frontend/src/app/crop-planning/plans/[planId]/page.tsx`
- `frontend/src/app/crop-planning/plans/[planId]/planning/page.tsx`
- `frontend/src/app/crop-planning/plans/new/page.tsx`
- `frontend/src/app/crop-planning/plans/page.tsx`
- `frontend/src/app/crop-planning/register/page.tsx`
- `frontend/src/app/crop-planning/research-demo/page.tsx`
- `frontend/src/app/crop-planning/risk-analysis/page.tsx`
- `frontend/src/app/crop-planning/suggested-crops/page.tsx`
- `frontend/src/app/crop-planning/tests/frontend.test.tsx`
- `frontend/src/app/crop-planning/tests/live-api-smoke.mjs`
- `frontend/src/app/crop-planning/tests/run.mjs`
- `frontend/src/app/crop-planning/tests/tsconfig.json`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/app/portal.css`
