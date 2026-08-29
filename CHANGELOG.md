# Changelog

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
