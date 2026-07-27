# Architecture

Macro Sage is intentionally a small batch application, not a framework.

## Data flow

1. `config/sources.toml` defines stable publisher feeds.
2. Feed entries are normalized and tracking parameters are removed.
3. The original linked HTML or PDF is fetched; RSS body text is only a fallback.
4. Documents are cached by a stable URL hash in SQLite.
5. Documents for one configured local date are placed into one bounded corpus.
6. the OpenAI Responses API returns a Pydantic-validated `DailyBrief`.
7. JSON, Markdown, source documents, token usage, and omissions are saved together.

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
lets a failed model call reuse already fetched documents.

### Podcasts are opt-in and cloud-first

Local Whisper was removed. On a 2019 Intel Mac, neural transcription is the wrong
place to spend wall-clock time. `gpt-4o-mini-transcribe` is used only with
`--include-podcasts`; oversized audio is split with low-bitrate `ffmpeg` encoding
to satisfy the upload limit. Podcast feeds are not part of CI or normal live
source validation.
