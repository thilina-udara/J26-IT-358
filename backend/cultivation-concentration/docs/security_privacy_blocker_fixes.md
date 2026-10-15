# P0/P1 security, privacy and scientific-integrity remediation

Branch: `feature/dasuni/cultivation-concentration-new`. Reviewed and fixed on
2026-10-14. The earlier final review is retained as a historical snapshot.

## Root causes and fixes

### P0: private historical response reconstruction

The public research route serialized internal statistics, including historical
means that exposed singleton acreage, unknown-availability counts that defeated
sparse suppression, and scenario-inclusive totals. Class predictions and
probabilities also depend on the hidden history, so merely hiding counts would
leave a repeated-query side channel. Authentication or historical age alone
does not establish a right to publish the original private source.

The route now calls `research_disclosure.public_scenario`, which accepts only
validated caller inputs. It never reads historical CSV/model files or calls the
internal evaluator. It emits a closed, server-validated response containing
caller inputs, fixed feature names and previously reported frozen benchmarks.
Every history-dependent feature, count, acre total, coverage state, isolated
flag, proxy class and probability is null/withheld for every population size.
The same policy covers available-window and dataset-window values, prior means,
complementary counts, alternatives and scenario comparisons. Neutral disclosure
statuses/reason codes do not distinguish zero, sparse or large cohorts.

Typed nested response models reject extra/private fields, non-null protected
values, unauthorized alternative arrays and unlisted benchmark statistics. The
feature validator permits only exact caller inputs; derived history cannot be
serialized as another feature. There are no raw comparison/export endpoints.
The same schema controls JSON/export serialization. The frontend independently
ignores injected private fields; it compares caller dates only.

This resolves the reported response/differencing attacks by removing the HTTP
response's private-data dependency. It does not claim differential privacy for
other services. Public historical inference is unavailable until independently
reviewed publication permissions and a safe disclosure policy exist; no request,
enable flag or authentication setting can grant them. This task introduces no
public-data provider or illustrative farmer fixture.

The internal offline evaluator and its original feature calculations remain
unchanged for authorized private research. It must not be connected to a new
HTTP/export route without the same disclosure review. No public prediction is
claimed to have been computed when it was withheld.

### P0: deployed CORS differed from tested CORS

The origin parser silently defaulted to localhost and expanded configured
localhost ports only outside pytest. Global private-network CORS was enabled.
Tests therefore passed against a stricter policy than normal application startup.

The parser now uses only the exact explicit `CULTIVATION_CORS_ORIGINS` JSON
allowlist in every environment; missing configuration means an empty list. Port
expansion and pytest branching are gone. Wildcards/credentialed origin URLs
remain rejected, `allow_credentials` remains false, and private-network CORS is
disabled. The parser is now identical to its safe HEAD implementation.

Local development is explicitly documented in README and `.env.example`:

```dotenv
CULTIVATION_CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

Real operator environment files were not changed. Other ports require explicit
server configuration. New subprocess tests construct the actual FastAPI app and
exercise middleware with `PYTEST_CURRENT_TEST` removed, checking both permitted
and rejected origins, empty configuration and private-network denial.

### P1: operational pages bypassed agricultural approval

The primary cultivation route used static crop profiles containing agricultural
instructions, quantities, fixed dates and Completed/Current Stage flags, without
requesting approved planning activities. Dashboard reminders also invented
activities/dates. These outputs bypassed the otherwise correct backend gates.

Static profiles/instructions were removed rather than relabeled as approved.
The primary route now selects an owned saved record through `PlanSelector` and
uses the same `PlanningPanel`/`PlanningResult` as the nested planning route.
Owner details remain visible. Empty/missing approvals yield a polished partial
planning state with no synthesized activities, quantities or timeline. A saved
activity needs the backend's envelope approval, explicit planning verification
and nonblank approval evidence. Stale revisions are withheld until regenerated
for the current cultivation context. Approved returned dates remain unchanged.

Dashboard static activity reminders and the fixed two-plan insight were removed.
Operational explanations no longer infer zero peers from unvalidated risk or
promise approved guidance for all crops. No illustrative schedule or demo fixture
was added to operational pages. Registration/partial-success state remains
preserved when switching workspaces. Backend crop suitability, comparison,
ownership, date-validation and guideline approval services were not weakened.

## Regression coverage

- Research: identical responses for zero/singleton/small/large fictional
  populations; no private loader/model/evaluator invocation; repeated identical
  requests; changing cutoff/acreage; all five model contracts; injected disclosure
  permission fields; absence of comparison/export routes; strict schema/JSON
  rejection of counts, totals, singleton means, classes, probabilities, isolated
  flags, extra records and hidden statistics in benchmark metadata.
- CORS: real startup in a child process without pytest flags, exact explicit
  localhost/127.0.0.1 port 3000 acceptance, other ports/origins rejected, empty and
  absent configurations deny origins, no credential or private-network allowance.
- Planning: primary operational route with an owned plan and absent, missing,
  unverified, blank, stale and valid approvals. Only valid returned activities
  and dates render; saved details and partial state remain visible. Former
  quantities, pesticide/fertilizer advice, completion flags and static schedules
  are absent. Existing registration recovery, privacy and approval tests remain.
- Scientific: existing internal cutoff, future-record exclusion, unknown
  availability, original model contracts, scenario reproduction and validated-risk
  separation tests continue to run without retraining research artifacts.

## Scientific integrity and limitations

All 63 catalogued historical files remain hash-identical, including 31 joblib
model/preprocessing binaries. The original source CSV remains at SHA-256
`4397ddae6a3fabde06f1b9dc6fd42d40b3f0cc5a5275754621011e4cfcbb2bab`.
No training labels, frozen classifier settings, thresholds or reported metrics
were changed. Tests fitting small fictional classifiers do not retrain or
overwrite research artifacts.

The prior XGBoost High/direct acreage-rule Medium disagreement remains documented
in the scientific audit. It remains an internal hypothetical-scenario
approximation discrepancy, not validated oversupply or an independent outcome.
The dataset's Year is not an observation timestamp; statistical-season/calendar
alignment and observation/model availability remain unverified. Unknown versions
can still carry later information in private retrospective research. No zero
temporal leakage claim is justified. Probability calibration, independent current
risk, representative coverage and agronomic effectiveness are not established.

These limitations do not authorize releasing private values or bypassing
guidelines. Historical proxy results remain separate from current validated risk;
automatic recommendations remain blocked and alternatives require their
existing independent suitability/coverage approvals. Synthetic storage remains
isolated and is never consumed by public responses or operational workflows.

## Scope and commit assessment

At task start there were 8 modified tracked files and 85 untracked files.
Baseline hashes captured the complete pending inventory before edits. The root
portal, unrelated component pages/assets, package files, shared configuration,
all JPEG assets and frozen/private research inputs were preserved. No unrelated
file was deleted or overwritten. `_test-build`, `.next`, Python caches and review
logs are generated/ignored outputs and are excluded from the pending inventory.

The three reported P0/P1 blockers are resolved. The remediation is suitable for
a carefully scoped commit review after the checks below; do not blanket-stage
the entire working tree. Existing root-portal scientific claims, image provenance,
session-storage documentation and broader dependency changes remain separate
review matters. Include required Crop Planning feature dependencies when scoping
the eventual commit. This is not approval to publish a private-data inference API
or deploy every unrelated pending frontend change.

Nothing was staged, committed, pushed or rebased. Exact changed files, the final
classified inventory and verification results follow.

## Exact files edited in this task

- `backend/cultivation-concentration/README.md` (modified tracked)
- `backend/cultivation-concentration/app/cors.py` (restored to HEAD; no remaining diff)
- `backend/cultivation-concentration/app/main.py` (modified tracked)
- `backend/cultivation-concentration/app/research_demo_routes.py` (edited pre-existing untracked)
- `backend/cultivation-concentration/app/schemas/research_demo.py` (edited pre-existing untracked)
- `backend/cultivation-concentration/docs/historical_simulation_audit.md` (edited pre-existing untracked)
- `backend/cultivation-concentration/docs/historical_simulation_final_review.md` (edited pre-existing untracked)
- `backend/cultivation-concentration/tests/test_research_demo.py` (edited pre-existing untracked)
- `frontend/src/app/crop-planning/components/planning-panel.tsx` (edited pre-existing untracked)
- `frontend/src/app/crop-planning/components/research-result.tsx` (edited pre-existing untracked)
- `frontend/src/app/crop-planning/components/ui.tsx` (edited pre-existing untracked)
- `frontend/src/app/crop-planning/cultivation-plan/page.tsx` (edited pre-existing untracked)
- `frontend/src/app/crop-planning/dashboard/page.tsx` (edited pre-existing untracked)
- `frontend/src/app/crop-planning/lib/contracts.ts` (edited pre-existing untracked)
- `frontend/src/app/crop-planning/lib/evidence.ts` (edited pre-existing untracked)
- `frontend/src/app/crop-planning/research-demo/page.tsx` (edited pre-existing untracked)
- `frontend/src/app/crop-planning/risk-analysis/page.tsx` (edited pre-existing untracked)
- `frontend/src/app/crop-planning/suggested-crops/page.tsx` (edited pre-existing untracked)
- `frontend/src/app/crop-planning/tests/frontend.test.tsx` (edited pre-existing untracked)
- `backend/cultivation-concentration/.env.example` (modified tracked)
- `backend/cultivation-concentration/app/services/research_disclosure.py` (new untracked)
- `backend/cultivation-concentration/docs/security_privacy_blocker_fixes.md` (new untracked)
- `backend/cultivation-concentration/tests/test_cors_startup.py` (new untracked)
- `backend/cultivation-concentration/tests/test_research_disclosure.py` (new untracked)

## Final verification

- Full backend: **472 passed**, one dependency deprecation warning, 208.28 seconds.
- Frontend: **38 passed**; TypeScript, ESLint and production build passed. Existing image/hook warnings remain.
- `git diff --check`: passed; only LF/CRLF normalization notices.
- All **63** catalogued research files present/hash-identical; source CSV hash unchanged.
- No staging/history changes; no private data, model binaries, databases or real environment files in the pending inventory.
- Logs: ignored `logs/blocker-fix-*`; generated frontend/test/cache outputs remain ignored.

## Complete classified pending inventory

8 modified tracked files and 89 untracked files (97 total), including this remediation report. The restored CORS file is listed as a task edit above but has no remaining Git diff.

| State | Exact path | Scope |
| --- | --- | --- |
| Modified | `backend/cultivation-concentration/.env.example` | Crop Planning backend/docs/tests |
| Modified | `backend/cultivation-concentration/README.md` | Crop Planning backend/docs/tests |
| Modified | `backend/cultivation-concentration/app/main.py` | Crop Planning backend/docs/tests |
| Modified | `backend/cultivation-concentration/docs/historical_inference.md` | Crop Planning backend/docs/tests |
| Modified | `frontend/package-lock.json` | Existing shared frontend configuration/dependencies (preserved) |
| Modified | `frontend/package.json` | Existing shared frontend configuration/dependencies (preserved) |
| Modified | `frontend/tailwind.config.ts` | Existing shared frontend configuration/dependencies (preserved) |
| Modified | `frontend/tsconfig.json` | Existing shared frontend configuration/dependencies (preserved) |
| Untracked | `backend/cultivation-concentration/app/research_demo_routes.py` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/app/schemas/research_demo.py` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/app/seed_demo_data.py` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/app/services/historical_research_evaluator.py` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/app/services/research_disclosure.py` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/docs/historical_simulation_audit.md` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/docs/historical_simulation_final_review.md` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/docs/security_privacy_blocker_fixes.md` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/tests/test_cors_startup.py` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/tests/test_research_demo.py` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/tests/test_research_disclosure.py` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/tests/test_research_temporal_correctness.py` | Crop Planning backend/docs/tests |
| Untracked | `backend/cultivation-concentration/tests/test_seed_demo_data.py` | Crop Planning backend/docs/tests |
| Untracked | `frontend/.env.example` | Existing shared frontend configuration/dependencies (preserved) |
| Untracked | `frontend/.eslintrc.json` | Existing shared frontend configuration/dependencies (preserved) |
| Untracked | `frontend/.gitignore` | Existing shared frontend configuration/dependencies (preserved) |
| Untracked | `frontend/components.json` | Existing shared frontend configuration/dependencies (preserved) |
| Untracked | `frontend/public/crop-planning/agfarm_aerial.jpg` | Existing decorative Crop Planning assets (preserved) |
| Untracked | `frontend/public/crop-planning/agfarm_hero.jpg` | Existing decorative Crop Planning assets (preserved) |
| Untracked | `frontend/public/crop-planning/terraces.jpg` | Existing decorative Crop Planning assets (preserved) |
| Untracked | `frontend/public/images/about_farmer.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/component1_market.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/component2_planning.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/component3_waste.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/component4_climate.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/crop_brinjal_detail.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/crop_chili_detail.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/crop_corn_detail.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/crop_mungbean_detail.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/crop_okra_detail.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/crop_pumpkin_detail.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/crop_tomato_detail.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/dashboard_banner_landscape.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/field_furrows_detail.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/public/images/hero_farmer.jpg` | Existing shared/generated images, including other components (preserved) |
| Untracked | `frontend/src/app/crop-planning/.gitignore` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/DEVELOPMENT.md` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/analysis-panel.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/auth-form.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/brand.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/comparison-panel.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/plan-form.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/plan-selector.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/plan-workspace.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/planning-panel.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/research-result.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/session.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/shell.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/ui.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/ui/LICENSE.txt` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/ui/SOURCE.md` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/ui/alert.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/ui/badge.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/ui/button.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/ui/card.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/ui/input.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/ui/label.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/ui/native-select.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/components/ui/table.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/crop-planning.css` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/cultivation-plan/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/dashboard/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/layout.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/lib/api.ts` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/lib/contracts.ts` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/lib/dates.ts` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/lib/evidence.ts` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/lib/navigation.ts` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/lib/utils.ts` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/lib/validation.ts` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/login/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/plans/[planId]/alternatives/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/plans/[planId]/analysis/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/plans/[planId]/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/plans/[planId]/planning/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/plans/new/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/plans/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/register/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/research-demo/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/risk-analysis/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/suggested-crops/page.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/tests/frontend.test.tsx` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/tests/live-api-smoke.mjs` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/tests/run.mjs` | Crop Planning frontend |
| Untracked | `frontend/src/app/crop-planning/tests/tsconfig.json` | Crop Planning frontend |
| Untracked | `frontend/src/app/layout.tsx` | Existing root portal/shared other-component presentation (preserved) |
| Untracked | `frontend/src/app/page.tsx` | Existing root portal/shared other-component presentation (preserved) |
| Untracked | `frontend/src/app/portal.css` | Existing root portal/shared other-component presentation (preserved) |
