# Historical simulation and disclosure contract

This component retains a private retrospective evaluator and a separate public
scenario-metadata endpoint. Frozen model binaries, training data, labels and
research metrics are not modified or published by this implementation.

## Public research API

`POST /api/research-demo/evaluate` is disabled unless the server explicitly
enables research mode. It validates the caller's crop, district, season, acreage,
planting date, harvest date and optional decision cutoff. The cutoff defaults to
planting, means start of day in Asia/Colombo, must not follow planting, and must
be in the supported research date range. Different planting/cutoff calendar years
are rejected because verified statistical-season mappings are unavailable.

Public responses contain caller inputs, fixed feature-contract metadata and
previously reported frozen evaluation metrics only. They do not open private
historical CSV/model files or evaluate those private populations. All peer
statistics, derived historical features, coverage, isolated flags, proxy
categories, probabilities and alternatives are withheld for all cohort sizes.
An enabled endpoint, authentication or the age of data does not establish a right
to publish it. No request field can approve disclosure.

The response is constructed by `research_disclosure.public_scenario` from the
validated request, using a closed schema. The schema rejects unexpected fields
and non-null protected values. Zero, singleton, sparse and large cohorts receive
the same disclosure statuses. Repeated requests and cutoff/acreage changes have
no private-history dependency; no raw comparison/export endpoint is provided.
Public metrics describe the existing evaluation, not this scenario or current
market risk. No public historical prediction is claimed to have been computed.

## Private retrospective evaluator

`historical_research_evaluator.evaluate_historical_scenario` retains calculations
for authorized offline research. It is not an HTTP serializer or a public data
provider. It matches district/crop/declared season and expected harvest anchors
within an inclusive +/-14-day window. Earlier planting is a retrospective
assumption, not evidence of submission or actual observation availability.

Verified exact-version observations after the cutoff are excluded. Unknown
availability remains an explicit replay assumption; no zero temporal leakage
claim follows. Historical references use earlier recorded Years and expected
harvest before cutoff. Recorded Year is not a planting or availability timestamp,
and its relationship to statistical seasons requires independent evidence.

Production windows sum recorded production rather than borrowing a yield median
from later cohorts. Own production is missing and handled by the frozen pipeline;
no approved yield, profit or activity estimate is invented. Saved feature order
and class encoding are checked. Trusted artifact bytes are hash-verified before
deserialization. Private artifacts require the separately authorized local
bundle and are not included in Git.

Historical labels are experimental acreage-percentile rules, not independently
observed oversupply or financial loss. A model can disagree with direct
application of the rule because target overlap acreage is excluded from its
features. That disagreement does not authorize changing frozen labels/metrics
or promoting a historical proxy into current validated risk.

## Operational and security boundaries

Operational farmer creation retains future-date validation and owner isolation.
Automatic recommendations still require independently validated current High
risk; crop comparison and planning retain suitability, comparable-coverage and
applicable agricultural guideline approvals. K-Means/DBSCAN remain descriptive.

The synthetic seeder is disabled by default, accepts only reserved isolated
research storage, refuses configured operational paths/non-demo records, and
marks synthetic databases. Operational application startup refuses those
databases, including renamed marked files. Public scenarios never read them.

CORS defaults to no origins and uses only the exact server-configured JSON
allowlist, without pytest-dependent behavior or automatic port expansion.
Local Next.js development explicitly configures localhost and 127.0.0.1 port
3000. Credentialed browser CORS and private-network CORS remain disabled.

## Regression coverage and remaining limitations

Regressions cover cutoff/planting independence, known late observations, unknown
availability, synthetic historical feature semantics, future-data mutations,
sparse/zero evidence, class ordering, source-independent public serialization,
repeated/differenced queries, rejected disclosure injections, actual CORS startup
outside pytest, owner privacy and isolated synthetic storage. Model contract
tests require the authorized private bundle without publishing observations.

Observation/model availability, source/publication permission, season/region
compatibility, representative participation, probability calibration, independent
current-risk labels and field/market effectiveness remain unverified. A public
historical-data provider needs independent publication/disclosure review. This
implementation supplies no such approval.
