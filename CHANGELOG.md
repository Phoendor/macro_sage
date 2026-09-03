# Changelog

## 0.7.3 - 2026-09-03

### Model-aware input budgeting

- Added an exact Responses input-token preflight covering the complete model
  request, including developer instructions, history context, evidence JSON and
  the structured-output schema.
- Replaced the primary 350,000-character corpus boundary with a 250,000-token
  default model-input budget and retained a larger serialization-only safety
  boundary.
- When an exact count is over budget, reduce long-document allowances across
  the whole selected corpus before considering lower-ranked omissions, then
  verify the rebuilt request again.
- If exact counting is unavailable, fall back to a conservative UTF-8 estimate
  and the former 350,000-character boundary instead of failing the daily run.
- Record the planned input, budget and exact/estimated method in `run.json`, the
  GitHub summary and both private technical report formats.
- Added a manual-workflow delivery switch so hosted validation can exercise the
  complete report pipeline without posting a duplicate PDF to Telegram;
  scheduled runs continue to publish normally.

## 0.7.2 - 2026-09-03

### Evidence identity and speech deduplication

- Changed confidence calibration to normalize evidence-family labels, connect
  them to the exact cited documents and count distinct underlying releases.
  Several publisher write-ups of one release can no longer raise
  confidence as though they were independent evidence.
- Added source-owner context to the synthesis records and made the prompt use
  one stable family label for claims derived from the same release or event.
- Added a narrow BIS speech duplicate rule that prefers an originating central
  bank copy only when publication dates are close, speech titles agree and the
  extracted bodies have at least 82% seven-word-sequence overlap. A title match
  by itself never removes a document.
- Kept every removed BIS copy in the private technical funnel under the explicit
  `duplicate_underlying_speech` reason and added true-match, false-positive and
  cross-publisher family regression tests.

## 0.7.1 - 2026-09-02

### Actionable source-health alerts

- Changed the discovery-only health command to fail the GitHub job only when a
  source newly crosses into the failing state. Persistently failing sources
  remain explicit in the Markdown and JSON evidence without generating the
  same workflow-failure email every weekday.
- Added separate new-alert and persistent-failure counts plus machine-readable
  alert source IDs to the body-free health artifact.
- Moved the known-broken BIS Research Hub RSS source to configured-unavailable
  participation after the endpoint continued returning HTTP 404 through ten
  consecutive adverse observations. It remains visible in the catalog and is
  eligible for bounded replacement review, but daily runs no longer request it.
- Versioned the revised source-health rule as v2 and added transition,
  persistence, catalog and configuration regression tests.

## 0.7.0 - 2026-09-01

### Transparent material funnel

- Removed per-source and per-publisher synthesis caps. Collected documents now
  remain eligible until the overall article or character boundary; publisher
  diversity affects ordering, not arbitrary rejection.
- Made configured inclusion keywords a soft ordering preference while retaining
  narrow explicit exclusions for known off-topic or single-security material.
- Added a deterministic, body-free technical Markdown/PDF that groups every
  collected document by source, labels cited, available-but-uncited, truncated
  and rejected material, lists every discovered item not added separately, and
  separates acquisition failure, stale publication, normal silence and
  non-participation. This audit makes no additional OpenAI request.
- Stopped inferring “expected absent” from a broad weekday/cadence setting.
  Same-day silence stays quiet until the source exceeds its configured maximum
  normal publication gap.

### Public/private delivery split

- Removed source-health, model, token and acquisition diagnostics from the
  public content PDF; its source register now contains only documents cited in
  the report.
- Added a separately dated technical PDF to local outputs and GitHub artifacts.
- Added optional `TELEGRAM_ADMIN_CHAT_ID` routing: the public channel receives
  only the content PDF, while the owner's numeric private bot chat receives the
  technical PDF.
- Made duplicate protection destination-aware so public and private delivery of
  the same run cannot suppress one another.
- Expanded the offline regression suite to 148 tests and made the development
  check verify the active installation before adding the source directory to
  subprocess paths.

## 0.6.1 - 2026-09-01

### Public Telegram presentation

- Replaced the operator-oriented Telegram caption with a public-facing report
  title and human-readable publication date.
- Removed run health, source-failure counts and GitHub workflow links from PDF,
  no-data and delayed Telegram messages; those diagnostics remain in the report
  and audit trail.
- Send the Telegram document as `Macro-Sage-YYYY-MM-DD.pdf` instead of the
  internal per-run filename `report.pdf`.
- Expanded the bounded offline suite to 143 tests with a regression contract
  that rejects operational terms from public Telegram copy.

## 0.6.0 - 2026-08-30

### Trustworthy daily corpus

- Replaced recency-only publisher round-robin with deterministic evidence-tier,
  configured-priority, macro-title-relevance, freshness and diversity ranking.
- Reserved corpus capacity for primary evidence and enforced configured
  per-source product-line and per-publisher caps before the global article and
  character budgets.
- Added explicit synthesis title filters for known single-security/off-topic ING
  and Saxo material and for NBER's broad weekly batch; acquisition still retains
  omitted documents privately.
- Recorded the reason for every inclusion, truncation and omission in
  `run.json`.
- Replaced breakable pseudo-XML prompt framing with a JSON evidence array and
  regression-tested closing tags, quotes and forged citation keys as inert
  source content.

### Coverage and source health

- Added deterministic critical-role coverage rule v1. A role is materially
  missing only when none of its active sources supplied content and at least one
  role source had an adverse outcome; quiet event-driven sources alone do not
  create a gap.
- Migrated SQLite to schema 3 and accumulated last check, last success/failure,
  latest publication, expected publication boundary and consecutive adverse
  observations without rewriting prior health events.
- Added `macro-sage source-health` plus a model-free weekday GitHub check and a
  weekly full extraction canary. One transient failure remains a warning until
  the configured threshold is reached; sources are never disabled silently.
- Kept configured timestamp-derivation notes informational so valid ING, NBER
  and similar feeds are not mislabeled as degraded by expected source policy.
- Made default, optional-skipped and configured-unavailable participation states
  explicit in the safe run manifest and fixed podcast item outcomes so they are
  no longer dropped when article and audio reports are combined.
- Expanded the bounded offline suite from 130 to 142 tests.

## 0.5.0 - 2026-08-30

### Decision brief v2

- Replaced the summary-first schema with a versioned decision brief that
  separates fact, source forecast, source opinion and synthesis inference.
- Added ranked changes and developments, six macro-regime assessments,
  evidence/counterevidence, cross-asset transmission, candidate research
  expressions, scenarios, disagreements, catalysts, invalidations and blind
  spots.
- Added a hard market-data limitation: unsupported current-price or “priced
  in” language is rejected, market confirmation remains unavailable, and an
  expression cannot be marked ready for review without verified market data.
- Recalibrated confidence in code from source tiers, independent evidence
  families, freshness, disagreement and missing market context; confidence is
  evidence strength, not probability of profit or a position-size signal.
- Kept V1 history records readable while all new synthesis writes schema 2.
- Separated the V2 synthesis request's 180-second bound from the 30-second feed
  timeout after the first hosted canary proved that the richer structured
  response can legitimately exceed the old feed-sized limit.

### Evaluation and reporting

- Froze a body-free 15-case evaluation inventory, V1 defect log, quality rubric
  and deterministic schema, citation, source-register, coverage, duplication
  and unsupported-language graders.
- Redesigned Markdown and PDF from the same V2 object. The first page now
  foregrounds limitations, changes, regimes and at most three conditional
  expressions, while model/token metadata and the complete source register move
  to a technical appendix.
- Added source links beside regime evidence, disagreement sides, catalysts and
  risks, plus cross-format parity and rendered-PDF regression tests.

### Delivery and daily usability

- Added optional Telegram PDF/no-data delivery with strict configuration,
  content-based duplicate suppression, explicit force resend, one bounded 429
  retry, sanitized errors and durable message state.
- Kept delivery separate from report success so Telegram failure cannot destroy
  or hide an otherwise valid artifact.
- Increased GitHub artifact retention from 14 to 30 days, added a workflow badge
  and clearer artifact instructions, and added `evaluate` and `latest-report`
  CLI commands.
- Passed final hosted canary `33319046110` on commit `12ae26b`: 20 documents,
  nine explicit coverage limitations, schema 2, a 10-page PDF, 27 material
  claims, 12 cited documents and zero deterministic evaluation defects.

## 0.4.7 - 2026-08-29

### Durable history and comparison

- Added one versioned, append-only brief-history format used locally under
  `data/brief-history/` and on the dedicated `macro-sage-history` Git branch.
- Persisted structured briefs, exact acquisition intervals, transformation
  versions, document references, normalized views and comparison provenance
  without source bodies or transcripts.
- Added deterministic regime, thesis, event and asset-view keys, standard asset
  families/horizons, first/updated/expiry/resolution dates and status history.
- Added one-day and one-week comparison output with new, strengthened,
  weakened, unchanged, reversed and retired asset-view states; missing current
  evidence is carried explicitly and never treated as a reversal.
- Marked historical model output as non-evidence in the synthesis contract and
  kept all current theme/view citations bound to current documents.

### Gap-free scheduling and hosted integrity

- Replaced scheduled calendar-day filtering with persisted half-open intervals
  from the prior successful scheduled cutoff to the current intended cutoff.
- Preserved explicit-date calendar replays and prevented them from advancing
  the scheduled cutoff chain; per-source limits now apply per publication day
  in multi-day windows.
- Added explicit first-run, missing, incompatible and degraded history states,
  plus a visible seven-day recovery window when expected history is unavailable.
- Kept hosted runs in `history_sync_pending` until their body-free history commit
  reaches GitHub, while retaining Actions cache only for documents/transcripts.
- Passed hosted canary `33274205799`: 20 documents, nine explicit limitations,
  a 10-page PDF, matching artifact hashes and body-free history commit `8735886`.
- Expanded the bounded offline suite from 90 to 110 tests.

## 0.4.6 - 2026-08-29

### Validation audit integrity

- Separated automated source checks from manual contract review; generated
  samples now remain pending until explicit decisions are applied.
- Bound every review decision to the exact source-contract fingerprint,
  validation timestamp and committed code revision.
- Added an ignored private review bundle for inspecting bounded article
  excerpts without committing or uploading source bodies.
- Corrected UTF-8 HTML decoding, removed ephemeral media query parameters from
  review evidence, made Norges Bank monetary-policy reports follow the complete
  PDF, and excluded multimedia summaries from the Bank of Canada speech feed.
- Recorded a committed-code live baseline with 45 automated passes, one
  degradation and one failure, followed by 44 explicit approvals, two approvals
  with limitations and one rejection across all 47 contracts.
- Expanded the bounded offline suite to 90 tests.
- Closed the Milestone 2 audit with green Python 3.11/3.12 CI and a successful
  hosted end-to-end run that collected 26 documents, transcribed six podcast
  episodes, rendered an 11-page PDF and retained all nine coverage limitations.

## 0.4.5 - 2026-08-29

### Source contracts

- Replaced the overloaded enabled flag with default, optional and unavailable
  participation in one versioned structured inventory.
- Added evidence, coverage, cadence, acquisition, priority, health and
  selection metadata and generated the source catalog and coverage matrix from
  that inventory.
- Added a structured non-working candidate registry with exact failure and
  review information.
- Recorded a fresh 47-source live baseline: 45 passed, BIS Research Hub was
  degraded by two explicit third-party timeouts, and Norges Regional Network
  was degraded because chart data lost tabular structure; no source contract
  failed completely.

### Acquisition and provenance

- Separated publication/update/raw timestamps, added explicit source timestamp
  policies, sorted before selection, and exposed missing, future, stale,
  filtered and duplicate outcomes.
- Added access-page, title, language, density, repeated-text and PDF quality
  validation, declarative PDF selection, and explicit feed-body degradation.
- Made document identity independent of discovery source and retained original,
  canonical, landing/resolved, extraction and quality provenance.

### Storage and reproducibility

- Added a backward-compatible SQLite schema-2 migration with immutable content
  revisions, many-to-many discovery origins, source-health events and
  review-only similar-title candidates.
- Added safe conditional cache revalidation and deterministic invalidation for
  updates, extractor changes and quality warnings.
- Versioned every transformation contract in `run.json` and increased the
  offline suite to 86 tests, including generated-catalog drift checks.

### Deferred

- Durable brief history and comparison remain Milestone 3.
- Publisher transcripts, advertisement handling and transcript provenance
  remain in the later podcast milestone.
- Ongoing cadence monitoring, corpus balancing and source expansion remain G6
  through G9.

## 0.4.0 - 2026-08-28

### Reliability

- Replaced model-facing document hashes with deterministic run-scoped citation
  keys and strict local resolution back to canonical IDs.
- Added separate content (`report`, `no_data`, `not_produced`) and health
  (`healthy`, `degraded`, `failed`) outcomes.
- Made a healthy no-data day successful without sending a synthesis request.
- Added tested Amsterdam date resolution for delayed scheduled runners,
  weekends, explicit dates, and daylight-saving boundaries.
- Added per-attempt run IDs, stage diagnostics, atomic output replacement,
  sanitized errors, and item-level acquisition outcomes.

### GitHub Actions

- Added non-cancelling concurrency control and distinct date, model, collection,
  synthesis/rendering, summary, and artifact stages.
- Reduced OpenAI model discovery from three calls to one immutable preflight
  selection per hosted run.
- Added run-page/artifact links and safe diagnostic upload after application
  failures.

### Security and reproducibility

- Split the local `documents.private.json` synthesis corpus from the body-free
  `manifest.json` uploaded to GitHub.
- Added secret redaction tests and prohibited raw article/transcript bodies from
  hosted artifacts.
- Added exact dependency constraints and a bounded offline check command.
- Rebuilt the local virtual environment so it imports the current checkout.

### Deferred

- The synthesis-v2 redesign, source-foundation work, podcast-model migration,
  market data, and Telegram delivery remain in later roadmap milestones.
- Milestone 1 remains under observation until five consecutive scheduled runs
  pass its operational exit gate.
