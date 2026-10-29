PP1 historical trend-based cultivation concentration implementation

Implemented in the PP1 copy only. Open
http://127.0.0.1:3001/crop-planning/admin/dashboard and use the officer/admin login.
The new section, ?Historical Trend-Based Concentration Analysis?, appears above
all existing dashboard tabs. It has 24 crop/district/season combinations and a
held-out-year selector. Backend and frontend were restarted using PP1_RUN.md and
are running on ports 8001 and 3001.

This is an exploratory chronological historical backtest, not live farmer risk
and not a validated agricultural warning system. The source file has enough
recorded years for temporal testing, but independent source verification and
publication/revision vintages are absent. Calendar-year separation cannot prove
that every record version was actually available at the historical decision date.
The UI states this prominently; neither data authenticity nor prospective skill
is invented.

Data inspection and grouping

Selected file: `data/official/official_historical_2001_2025.csv`, relative to the
cultivation backend. Fields are `district_name`, `crop_name`, `year`, `season`,
`cultivated_extent_hectares`, and `production_metric_tons`. The selection uses
cultivated extent in hectares only. Production in metric tons is inspected but
never mixed with acreage or used in this classifier.

There are 878 source rows: 580 individual seasonal observations and 298 annual
`Total` rows. No column is blank; there are no duplicate district/crop/season/year
keys. Cultivated extent ranges from 1 to 8,044.6 hectares; production ranges from
0 to 16,794.9 metric tons. The 580 seasonal rows have one already aggregated
measurement per district/crop/season/year. They are full recorded seasonal
cumulative totals; do not sum annual Total plus Maha and Yala, or sum multiple
years to obtain a single season. Exact repeat measurements are deduplicated by
the natural key. Conflicting repeats are rejected because revision precedence
is unknown. Seasons are taken exactly as recorded; no planting-month mapping is
assumed. The dataset's complete regional/census coverage is unverified.

Coverage by selected series (missing years refer to 2001?2025):

| District | Crop | Season | Observations | Missing years |
|---|---|---|---:|---|
| Hambantota | Bandakka | Maha | 25 | None |
| Hambantota | Bandakka | Yala | 24 | 2009 |
| Hambantota | Brinjal | Maha | 25 | None |
| Hambantota | Brinjal | Yala | 24 | 2009 |
| Hambantota | Chillies | Maha | 25 | None |
| Hambantota | Chillies | Yala | 24 | 2009 |
| Hambantota | Corn | Maha | 25 | None |
| Hambantota | Corn | Yala | 24 | 2009 |
| Hambantota | Mung Beans | Maha | 25 | None |
| Hambantota | Mung Beans | Yala | 24 | 2009 |
| Hambantota | Pumpkin | Maha | 25 | None |
| Hambantota | Pumpkin | Yala | 24 | 2009 |
| Matara | Bandakka | Maha | 25 | None |
| Matara | Bandakka | Yala | 24 | 2009 |
| Matara | Brinjal | Maha | 25 | None |
| Matara | Brinjal | Yala | 24 | 2009 |
| Matara | Chillies | Maha | 25 | None |
| Matara | Chillies | Yala | 24 | 2009 |
| Matara | Corn | Maha | 23 | 2001, 2002 |
| Matara | Corn | Yala | 21 | 2001, 2002, 2006, 2009 |
| Matara | Mung Beans | Maha | 25 | None |
| Matara | Mung Beans | Yala | 21 | 2001, 2002, 2009, 2019 |
| Matara | Pumpkin | Maha | 25 | None |
| Matara | Pumpkin | Yala | 24 | 2009 |

The legacy file `data/legacy/official_farmer_cultivation_2020_2026.csv` has
15,090 records, unique Record_ID values, no blank fields, six crops, the same two
district names, years 2020?2026, and Maha/Yala labels. Its area is in acres and
expected production in kg (with kg/acre expected yield). There are 1?1,635 records
per crop/district/season/year, requiring aggregation if used as a cohort. Unique
record IDs do not establish unique farmers, complete regional coverage, or
revision availability. Other farmer files contain 1,450 (2020?2025), 422 (2026),
and 1,509 (2020?2026) records. They have overlapping periods, differing date/ID
conventions, and no demonstrated population equivalence, so none are merged into
the selected historical totals.

Live farmer plans store `land_size_acres`, district, free-text region and a
farmer-declared season. They have no directly comparable verified expected
production amount. Their participation, regional coverage and season mapping
are unverified. Unit conversion alone cannot make this small volunteer cohort
comparable with regional historical totals. The new service never reads live
farmer plans, writes a database, or compares those plans with district totals.
The PP1 farmer workflow and its existing rule/evidence/privacy checks are unchanged.

Trend and threshold protocol

The protocol is fixed for this exploratory demonstration, not selected to obtain
a desired held-out category:

1. Select one crop, district and recorded season (Maha or Yala). Reject missing,
   negative, non-finite or conflicting selected-period measurements and explicit
   non-hectare units. Missing calendar years are reported, never imputed.
2. Hold out evaluation year E. Fit only recorded years less than E. Exclude future
   measurement values and units before validation. E must have an observation and
   the immediately previous year must be present, so the final horizon is one year.
3. Estimate a centered OLS line: baseline(y) = a + b ? (y ? mean_training_year),
   where a = mean(training hectares), and b = sum[(year?mean_year) ? (hectares?a)]
   divided by sum[(year?mean_year)^2]. Actual calendar-year spacing is retained.
4. Starting after five initial observations, refit on an expanding prefix and
   forecast the next observation only when it is the next calendar year. Compute
   signed one-year percentage errors = 100 ? (actual / earlier-fit forecast ? 1).
   Both the calibration observation itself and every later observation are
   excluded from that calibration fit. Zero/negative forecasts cannot calibrate
   a percentage. The evaluation year never enters the error distribution.
5. Require at least eight valid earlier errors. Set lower/upper boundaries to
   empirical quantiles at 1/3 and 2/3. Use Type-7 linear interpolation: sort n
   errors; h=(n?1)p; Q(p)=x[floor(h)] + fraction(h) ? (x[ceil(h)]?x[floor(h)]
   with zero-based indexing. These central quantiles do not assume Gaussian
   errors and are less sensitive to a single extreme error than a variance-based
   rule. Their numeric values are derived independently for each group/year.
6. Deviation(E) = 100 ? (observed(E) / baseline(E) ? 1). Low means below the lower
   error tercile, Medium includes both boundaries, High means above the upper
   tercile. Amount boundaries are baseline(E) ? (1 + Q/100). Classification uses
   unrounded numbers; the UI rounds display values only.

Terciles are an explicit equal-frequency descriptive convention, not empirically
validated agronomic severity boundaries. Five fit observations and eight errors
are conservative minimum demonstration guards, not a proof of statistical power.
No arbitrary ?10% amount cutoff is used. The bands are neither confidence nor
prediction intervals and do not assign calibrated probabilities. Their signed
percentages can vary by series; a Low label does not universally mean below
zero deviation. Residual dependence, trend breaks and sampling uncertainty remain
limitations. No model selection, significance test or causality claim is made.

Insufficient history, a missing held-out/preceding year, invalid values/units,
non-positive baseline, non-finite arithmetic, fewer than eight calibration errors,
or tied terciles returns `Insufficient Data` with category null. The UI never
renders a category for that status. Zero observed cultivation is valid when the
baseline is positive. Finite extreme values are preserved; OLS sensitivity is
explicitly disclosed. Prior fitted residuals outside the usual Q1/Q3 ?1.5 IQR
fences are flagged for review but never trimmed or used as category thresholds.

Method references: expanding-origin evaluation is described by the authors of
[Forecasting: Principles and Practice](https://otexts.com/fpp3/toolbox.html#time-series-cross-validation).
Its [time series regression chapter](https://otexts.com/fpp3/regression.html)
explains trend regression and limitations. The [NIST percentile guide](https://www.itl.nist.gov/div898/handbook/prc/section2/prc262.htm)
explains empirical order statistics and interpolation conventions. These references
support the calculation principles; they do not validate these PP1 category cutoffs.

Recorded worked example (not synthetic and not live)

Hambantota / Bandakka / Maha, held-out recorded year 2025:

- Training: 2001?2024, 24 seasonal observations.
- Trend: 289.987500000 + 2.023434783 ? (year ? 2012.5), hectares.
- Forecast baseline: 315.280435 ha.
- Recorded 2025 seasonal cumulative extent: 329.900000 ha.
- Deviation: 4.637004%.
- Calibration: 19 one-year errors, evaluated in 2006?2024; each fit stops earlier.
- Lower tercile: -2.657215% ? 306.902757 ha.
- Upper tercile: 32.642487% ? 418.195810 ha.
- Result: **Medium relative historical concentration**.

The observation comes directly from the repository's historical CSV. Independent
verification of its claimed official origin remains outstanding. This recorded
chronological exercise cannot establish what a real officer knew in 2025.

Dashboard, API and verification

Protected API: `GET /api/admin/analytics/historical-trend/options` and
`GET /api/admin/analytics/historical-trend?district=Hambantota&crop=Bandakka&season=Maha&evaluation_year=2025`.
The default endpoint uses the latest recorded year. Inputs are limited to supported
crop/district/season values; invalid selections return HTTP 422, missing/invalid
admin authentication returns HTTP 401. Authentication uses the existing officer/admin
session mechanism. No public fake-data or authentication-bypass endpoint was added.

The dashboard chart shows recorded observations, the earlier-year fitted trend,
and the held-out observation. It shows baseline, cumulative extent, deviation,
percent/ha boundaries, category or insufficiency reason, training/calibration
years, source/units/grain/coverage and limitations. Source-model roles are stated:
XGBoost is the separate offline historical research classifier; this service is
OLS; K-Means/DBSCAN are descriptive clustering; live farmer risk remains rule-based.

Passed checks:

- Backend: 29 tests across `test_historical_trend.py`, `test_health.py`, and
  `test_admin_model_validation.py`. Coverage includes exact trend, actual calendar
  gaps, chronological calibration and held-out/future leakage invariance, quantile
  derivation, boundary classification, zero/missing/extreme data, wrong units,
  insufficient/tied history, duplicate/conflicting rows and excluded annual totals,
  all 24 real historical groups, protected API validation and no farmer-record writes.
  One existing Starlette/httpx deprecation warning remains.
- Frontend: TypeScript no-emit check passed; all 53 component/API tests passed,
  including the new historical result/category/insufficiency/chart tests.
- Real authenticated PP1 API: 24 options; HTTP 200 valid analysis; HTTP 401
  unauthenticated; early historical year has no category; /ready is ready.
- Real headless Edge browser: chart, baseline, observation and Medium band render;
  changing to 2005 suppresses category; selecting Matara/Corn/Yala updates the
  result; only port 8001 is used for API requests; zero runtime exceptions.
- Screenshot: `scratch/pp1-isolation/trend/admin-trend-dashboard.png`.
- Git whitespace check passed. No commit or push.

Restart used the PP1 scripts. A small existing stop-helper race was fixed: a
parent process may exit while its child is stopped; an already-exited parent is
now tolerated while genuine stop failures still propagate. The repaired stop/start
sequence was exercised successfully. No backend automatic reload is used.

Safety verification: all 3,255 fingerprinted original files, 55 model-directory
files (including frozen binaries), and 26 dataset files remain unchanged. No
XGBoost training or artifact rewrite occurred. PP1 farmer account and plan counts
remain zero. The live API/browser check used the app's existing development
officer login; its existing AdminStore automatically provisions two system admin/
officer accounts on first login and normal session metadata was written. The test
session was logged out. No SQLite file was overwritten, and no fake farmer was
inserted. No shared PostgreSQL/Redis connection or Docker invocation was used.
Only PP1 service processes were restarted; other components were not edited.

Exact files created or modified for this implementation (isolation work from the
previous task is separate):

- `backend/cultivation-concentration/app/services/historical_trend.py`
- `backend/cultivation-concentration/app/admin_routes.py`
- `backend/cultivation-concentration/tests/test_historical_trend.py`
- `frontend/src/app/crop-planning/components/historical-trend-analysis.tsx`
- `frontend/src/app/crop-planning/lib/historical-trend.ts`
- `frontend/src/app/crop-planning/admin/dashboard/page.tsx`
- `frontend/src/app/crop-planning/tests/historical-trend.test.tsx`
- `frontend/src/app/crop-planning/tests/run.mjs`
- `scripts/stop-pp1.ps1`
- `backend/cultivation-concentration/docs/pp1_historical_trend.md`

Generated test/browser evidence is confined to `scratch/pp1-isolation/trend`,
pytest temp directories under `scratch`, and the ignored frontend `_test-build`
and development caches. See `data-audit.json`, `worked-example.json`,
`live-verification.json` and `integrity-results.json` there for numeric evidence.

30-second PP1 explanation

?We fit a simple trend to earlier seasonal cultivation totals for each crop and
district. We then predict a held-out year and compare its observed cultivated
area with that baseline. Low, Medium and High bands come from earlier forecast
errors, rather than fixed percentages or harvest overlap alone. This is a clearly
labeled exploratory historical demonstration, separate from XGBoost and live farmer
risk, and it does not prove market oversupply.?
