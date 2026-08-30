# Architecture

Macro Sage is intentionally a small batch application, not a framework.

## Data flow

1. `config/sources.toml` is the versioned source, catalog and acquisition
   inventory.
2. All feed entries are normalized, deduplicated and sorted before scan and
   daily-selection limits; publication and update times remain separate.
3. The original linked HTML or configured PDF is fetched and quality checked;
   feed body text is an explicitly degraded fallback.
4. Canonical URLs and content hashes establish source-independent document
   identity in a migrated, revision-preserving SQLite schema.
5. Every discovery origin, content revision, source-health event, invalid date,
   filter, duplicate, quiet period and failure remains auditable.
6. Documents selected for synthesis receive short run-scoped citation keys such
   as `S001`; opaque canonical IDs remain internal.
7. The OpenAI Responses API returns the model-authored portion of a
   Pydantic-validated `DailyBriefV2`; operational coverage fields and the final
   source register are calculated in code, and short keys are strictly resolved
   back to canonical document IDs.
8. Each attempt writes atomically to `output/runs/<run-id>/`, with separate
   content and health outcomes.
9. The local private corpus is separated from a body-free audit manifest used
   by PDF rendering and GitHub artifact upload.
10. Successful structured briefs are appended to a versioned history store;
    deterministic one-day and one-week comparisons are rendered from it.
11. JSON, Markdown and PDF are rendered from the same final brief object. An
    optional Telegram adapter sends the PDF after rendering and records its
    idempotency key separately from report success.

## Main decisions

### One synthesis request

Modern context windows make the old token-chunk/map-reduce code unnecessary for
this workload. One request also avoids compounding summary loss and repeated
output-token cost. Inputs still have deterministic article-count, per-article,
and total-character caps. That is a cost and failure guard, not a second
summarization layer.

### Structured output with enforced citations

The model emits a schema rather than free-form prose. Every theme and asset view
must contain supplied short citation keys, and unknown or missing keys make the
run fail. The application resolves them to canonical document IDs before JSON,
Markdown, or PDF output, avoiding fragile reproduction of opaque hashes.

DailyBriefV2 makes evidence type explicit, calculates confidence from source
tier, independent evidence families, freshness, contradiction and market-data
availability, and permits zero research expressions. It cannot claim that an
idea is confirmed by markets or ready for review while timestamped market data
is absent. The old V1 model remains readable only for history compatibility.

### Generic extraction before source-specific code

RSS is used for discovery, Trafilatura for HTML, and pypdf for PDF. This covers
the verified sources without fragile per-publisher CSS selectors. A
publisher-specific adapter should only be introduced when a live validation
proves generic extraction inadequate.

The generic path rejects access-control/error pages, checks title and expected
language plausibility, removes repeated text, preserves tables, validates PDF
type/page/text density, and retains both the landing and resolved content URLs.
PDF sources use declarative link patterns in the inventory. A fallback to feed
text is never represented as full publisher content.

### Publication time is a source contract

An RSS/Atom `updated` value is not silently treated as publication time. Feeds
that use it as their publication contract opt in explicitly; NBER's undated
weekly batch explicitly uses the official feed `Last-Modified` header. Raw,
parsed publication and update values are retained separately. Missing,
malformed and implausibly future values produce explicit outcomes.

### SQLite as the local boundary

SQLite provides idempotency without introducing an external database. Schema 2
migrates the legacy table in place into canonical documents, immutable content
revisions, many-to-many discovery origins, source-health events and review-only
similar-title duplicate candidates. Canonical URL and exact-content matches may
deduplicate; title similarity alone never merges evidence. ETag and
Last-Modified validators are used only while the extractor version and quality
contract still match. Local runs reuse the database directly; GitHub Actions
restores the same data directory as a performance cache.

### Durable brief history is not a cache

The append-only history format has one implementation used from a local
directory and from the dedicated `macro-sage-history` Git branch. It contains
structured briefs, acquisition intervals, comparison state and document IDs,
but no source bodies. Manual calendar replays never advance the scheduled
cutoff chain. A hosted run remains pending until its history commit is pushed;
cache eviction therefore cannot silently erase comparison state. See
[the history contract](HISTORY.md).

### Podcasts are opt-in and cloud-first

Local Whisper was removed. On a 2019 Intel Mac, neural transcription is the wrong
place to spend wall-clock time. `gpt-4o-mini-transcribe` is used only with
`--include-podcasts`; cloud `whisper-1` is the explicit fallback. New audio is
bounded by attempted episode count and total duration. Audio longer than 15
minutes, or larger than the upload limit, is split with low-bitrate `ffmpeg`
encoding to satisfy both audio-token and upload limits. Podcast feeds are not
part of CI or normal live source validation.

### One application, two execution environments

Local runs and GitHub Actions call the same CLI. `run` performs the complete
pipeline; `collect` and `synthesize` are first-class recovery and inspection
stages. GitHub adds only scheduling, secrets, cache persistence, and artifact
upload. The workflow resolves the target date and selects accessible models once,
then passes those immutable records to collection and synthesis.

### Delivery is a separate stage

Telegram configuration is optional. Local delivery requires `--deliver` or an
explicit `macro-sage deliver` command; GitHub sends after a successful render
when both configuration values exist. The adapter validates PDF type and size,
uses a run/content idempotency key, retries only an explicit rate-limit response
once, and records the returned message ID in durable history state. Ambiguous
network failures are not automatically retried because the first request may
already have posted. Report artifacts remain available when delivery fails.

### Failures are output, not log noise

A source outage must be visible without reading debug logs. The collection
manifest records a structured outcome for every attempted source. Failed and
partial sources are repeated in the terminal, `source-status.md`, the brief,
the PDF, and the GitHub job summary. A source with no same-day item is reported
separately because absence is normal for lower-frequency publishers.

### Content and health are separate outcomes

`content_result` is `report`, `no_data`, or `not_produced`; `health` is
`healthy`, `degraded`, or `failed`. This makes a normal quiet day successful
without allowing a systemic acquisition failure to masquerade as normal
silence. Every attempt receives its own run directory and writes diagnostics
before synthesis begins.

### Private corpus, safe artifact

`documents.private.json` contains the bodies required for local synthesis and
is permission-restricted. `manifest.json` contains document metadata, body
lengths, content hashes, item/source outcomes, and provenance without article or
transcript text. PDF rendering and hosted artifact upload use the safe manifest.
