# Changelog

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
