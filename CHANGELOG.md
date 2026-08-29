# Changelog

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
