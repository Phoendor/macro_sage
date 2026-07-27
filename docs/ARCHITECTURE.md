# Architecture

Macro Sage is intentionally a small batch application, not a framework.

## Data flow

1. `config/sources.toml` defines stable publisher feeds.
2. Feed entries are normalized and tracking parameters are removed.
3. The original linked HTML or PDF is fetched; RSS body text is only a fallback.
4. Documents are cached by a stable URL hash in SQLite.
5. Every configured source receives an explicit collected, no-items, partial,
   failed, or policy-skipped outcome.
6. Documents for one configured local date are placed into one bounded corpus.
7. The OpenAI Responses API returns a Pydantic-validated `DailyBrief`.
8. JSON, Markdown, PDF, source documents, model selection, token usage, failures,
   truncations, and omissions are saved together.

## Main decisions

### One synthesis request

Modern context windows make the old token-chunk/map-reduce code unnecessary for
this workload. One request also avoids compounding summary loss and repeated
output-token cost. Inputs still have deterministic article-count, per-article,
and total-character caps. That is a cost and failure guard, not a second
summarization layer.

### Structured output with enforced citations

The model emits a schema rather than free-form prose. Every theme and asset view
must contain source IDs, and unknown IDs make the run fail. Markdown is rendered
locally from that validated object.

### Generic extraction before source-specific code

RSS is used for discovery, Trafilatura for HTML, and pypdf for PDF. This covers
the verified sources without fragile per-publisher CSS selectors. A
publisher-specific adapter should only be introduced when a live validation
proves generic extraction inadequate.

### SQLite as the local boundary

SQLite provides idempotency without introducing an external database. It also
lets a failed model call reuse already fetched documents. Local runs reuse it
directly; GitHub Actions restores and saves the same data directory through the
repository cache so reruns do not normally pay to transcribe the same episode.

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
upload. It does not contain separate collection or model-selection logic.

### Failures are output, not log noise

A source outage must be visible without reading debug logs. The collection
manifest records a structured outcome for every attempted source. Failed and
partial sources are repeated in the terminal, `source-status.md`, the brief,
the PDF, and the GitHub job summary. A source with no same-day item is reported
separately because absence is normal for lower-frequency publishers.
