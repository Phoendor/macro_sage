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
6. A deterministic corpus contract reserves primary evidence, applies only
   explicit reviewed exclusions, interleaves publishers and records every
   inclusion, truncation and omission. It does not impose per-source or
   per-publisher hard caps.
7. Selected documents receive short run-scoped citation keys such as `S001` and
   are serialized as one JSON evidence array; opaque canonical IDs remain
   internal and source text cannot forge document boundaries.
8. The complete request, including its structured-output schema, is checked by
   the OpenAI Responses input-token counter and deterministically reduced only
   when it exceeds the configured model-input budget.
9. The OpenAI Responses API returns the model-authored portion of a
   Pydantic-validated `DailyBriefV2`; operational coverage fields and the final
   source register are calculated in code, and short keys are strictly resolved
   back to canonical document IDs.
10. Each attempt writes atomically to `output/runs/<run-id>/`, with separate
   content and health outcomes.
11. The local private corpus is separated from a body-free audit manifest used
   by PDF rendering and GitHub artifact upload.
12. Successful structured briefs are appended to a versioned history store;
    deterministic one-day and one-week comparisons are rendered from it.
13. JSON, public Markdown/PDF and a deterministic private technical audit are
    rendered from the same run. The optional Telegram adapter sends the content
    PDF to the channel and, when configured, the technical PDF to the owner's
    numeric private chat ID. Each destination has its own idempotency record.

## Main decisions

### One synthesis generation request

Modern context windows make the old token-chunk/map-reduce code unnecessary for
this workload. One request also avoids compounding summary loss and repeated
output-token cost. The complete input is counted against a model-token budget;
article and character limits remain deterministic safety bounds. That is a
failure guard, not a second summarization layer.

### Deterministic corpus admission

Acquisition and synthesis admission are separate. Lawfully acquired documents
remain in the private manifest even when they do not enter the bounded model
context. Corpus version 5 ranks evidence by configured authority and priority,
explicit title preference, macro relevance, freshness and publisher diversity,
and reserves up to one third of the article capacity for available primary
evidence. Every collected document remains eligible until the global article or
model-input boundary; there are no per-product-line or publisher hard caps.
Source-specific title exclusions are declarative, narrow and versioned in
`sources.toml` rather than hidden in model prompts.

Every decision and reason is written to `run.json`. The selected records are a
JSON array, not pseudo-XML assembled around publisher text. JSON escaping keeps
closing tags, quotes and instruction-like source content inside the content
field instead of allowing them to alter citation or document boundaries.

Feed requests keep a short 30-second network bound. The single, richer V2
synthesis request has a separate 180-second read bound so model generation is
not forced through a feed-sized timeout; the hosted job and all development
subprocesses retain their own outer safety limits.

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
when the public configuration exists. The public channel receives only the
content PDF. If `TELEGRAM_ADMIN_CHAT_ID` is configured, the bot also sends the
technical PDF to that numeric private chat. The adapter validates PDF type and
size, uses a destination-aware run/content idempotency key, retries only an
explicit rate-limit response once, and records the returned message ID in
durable history state. Report artifacts remain available when delivery fails.

### Failures are output, not log noise

A source outage must be visible without reading debug logs. The collection
manifest records a structured outcome for every attempted source. The private
technical Markdown/PDF groups every acquired document by source and separately
lists failed extraction, explicit filtering, stale feeds, ordinary same-day
silence and non-participation. The public content file contains only cited
research content, so operational diagnostics do not leak into a public channel.

### Source health is cadence-aware and model-free

Daily collection and the independent `Source Health` workflow append discovery
events to SQLite schema 3. The accumulated snapshot records last check, last
success, last failure, latest publication, expected publication boundary and
consecutive adverse observations. Same-day silence is quiet until the newest
known publication exceeds the source's configured maximum normal gap; the old
weekday-based “expected absent” inference is not used because a broad cadence
description is not an exact release schedule. A source becomes `failing` only
after its configured threshold (three by default), and no source is
automatically disabled. Source-health rule v2 makes the workflow exit non-zero
only on the transition into `failing`; an unresolved source remains visible in
every summary and body-free artifact without generating a duplicate daily
failure notification. A source already proven unavailable may be moved to the
explicit unavailable register, where it remains auditable but is excluded from
routine requests until a bounded review date.

The weekday check performs feed discovery only. A Sunday canary runs full
extraction separately from synthesis and transcription. Both produce body-free
artifacts and need no OpenAI credentials. Critical coverage is calculated from
configured role groups: a role is materially missing only when no active source
in the role supplied content and at least one role source had an adverse
outcome. Quiet role sources alone do not turn a normal empty day into a failure.

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
transcript text. Both public and technical PDFs use only the safe manifest. The
technical file reveals titles, URLs and reason labels, never article or
transcript bodies.
