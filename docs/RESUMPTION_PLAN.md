# Macro Sage resumption plan

Assessment date: 2026-07-27

## Executive summary

Macro Sage has a credible proof of concept, but the work exists only in a local
prototype history. The connected GitHub repository contains a single initial
commit with a one-line README, while the local `main` branch is three commits
ahead and includes ingestion, parsing, transcription, summarization, and feed
discovery experiments.

Do not push the current local branch. A live-looking OpenAI credential is present
in the local commit history and working tree. Revoke it first, then reconstruct a
sanitized history from the remote `main` commit.

The recommended first product milestone is intentionally narrow:

> Given a date and a configured source list, collect supported articles and
> podcast episodes, normalize their metadata, optionally transcribe audio, and
> write an attributed daily macro wrap in both JSON and Markdown.

## Evidence-backed current state

### GitHub

- Repository: `Phoendor/macro_sage`
- Default and only branch: `main`
- Remote tip: `d1d3fbb` (`Initial commit`, 2025-01-25)
- Remote content at assessment: `README.md` containing only the project heading
- Pull requests for this repository: none
- No Macro Sage item appeared among the 100 most recent accessible issue results;
  a repository issue workflow has not yet been established

### Local checkout

- Branch: `main`
- Local tip: `7b0c264` (2025-05-28)
- Relationship: three commits ahead of `origin/main`
- Tracked implementation: 15 files and roughly 1,800 added lines beyond the
  remote commit
- Uncommitted work: expanded RSS feed configuration in
  `drafts/rss_parcer_prototype_2.py`
- Untracked/generated material: IDE metadata, Python caches, approximately 69 MB
  of audio/transcript artifacts, and a crawler SQLite database

### Implemented prototype behavior

- `main_prototype.py`: sequential orchestration over hard-coded article and
  podcast sources, followed by one corpus summarization call
- `parcers.py`: ING-specific HTML and JSON-LD extraction
- `get_data.py`: basic HTTP retrieval
- `audio_tools.py`: download, MP3 compression, local Whisper or hosted
  transcription
- `text_tools.py`: generic retrieval and token-aware chunking
- `summarization.py`: chunk and corpus summarization through the Chat Completions
  HTTP API
- `drafts/rss_parcer_prototype_2.py`: curated article and podcast feeds with
  date filtering
- `drafts/jpmorgan_crawler.py`: sitemap-based discovery persisted in SQLite

## Restart gates

### Gate 0 — credential and history safety

1. Revoke the exposed OpenAI credential.
2. Preserve the current checkout as a local-only reference or patch.
3. Fetch `origin/main`.
4. Create a new recovery branch from `origin/main`.
5. Apply the sanitized working tree as one or more intentional commits; do not
   merge or push the existing three local commits.
6. Scan the new branch and its history for secrets.
7. Push only the clean recovery branch and open a pull request.

The exact Git history operation should be chosen only after the credential is
revoked and the uncommitted RSS changes are backed up.

### Gate 1 — reproducible baseline

- land this README, ignore rules, environment example, package metadata, CI, and
  offline smoke tests
- make all runtime configuration environment- or file-driven
- add request timeouts, status checks, and actionable exceptions
- establish a normalized `SourceDocument` model with identifiers, timestamps,
  source attribution, content type, URL, and text

### Gate 2 — ingestion foundation

- promote RSS discovery from `drafts/` into the application
- move the feed catalog into validated configuration
- separate discovery, fetching, parsing, and persistence interfaces
- add fixtures for RSS, Atom, ING HTML, malformed XML, redirects, and duplicates
- define deduplication using canonical URL plus source item ID

### Gate 3 — audio workflow

- stream downloads to bounded temporary files
- validate content type and maximum size
- make compression optional and isolate `ffmpeg` checks
- define transcription provider interfaces for local and hosted execution
- persist transcript metadata and allow safe resume after interruption

### Gate 4 — synthesis and outputs

- replace prompt concatenation with explicit document boundaries and citations
- define a structured summary schema before rendering Markdown
- handle context limits using map/reduce only when necessary
- store model, prompt version, source IDs, and generation timestamp
- make failures retryable and preserve partial results

### Gate 5 — operational CLI

- commands: `discover`, `ingest`, `transcribe`, `summarize`, and `run`
- date range, source selection, output directory, and dry-run options
- SQLite state for idempotency and resumability
- structured logs and a final run report
- scheduler/deployment choice only after the local CLI is reliable

## Proposed target architecture

```text
src/macro_sage/
├── cli.py
├── config.py
├── models.py
├── pipeline.py
├── discovery/
│   ├── rss.py
│   └── sitemap.py
├── ingestion/
│   ├── http.py
│   └── parsers/
├── transcription/
│   ├── base.py
│   ├── local_whisper.py
│   └── openai.py
├── synthesis/
│   ├── prompts.py
│   ├── schemas.py
│   └── openai.py
├── storage/
│   └── sqlite.py
└── rendering/
    ├── json.py
    └── markdown.py
```

Do not perform this move in one large refactor. Introduce interfaces and migrate
one working path at a time while keeping the prototype executable.

## First milestone acceptance criteria

- a fresh environment can install the project from `pyproject.toml`
- no credential or runtime artifact is tracked
- CI runs deterministic tests on supported Python versions
- a checked-in fixture feed can be discovered and ingested without network access
- a live run can select sources and a date without editing Python files
- repeated runs do not redownload or retranscribe completed items
- a failed item does not abort all remaining sources
- output JSON validates against a defined schema
- Markdown output cites every contributing source URL
- paid model calls require explicit configuration and report estimated usage

## Ordered starter backlog

1. Revoke the credential and construct a clean recovery branch.
2. Land the repository baseline files and secret-safe prototype entry point.
3. Add `Source`, `FeedItem`, `SourceDocument`, and `RunResult` data models.
4. Extract HTTP behavior behind a session with timeouts and retry policy.
5. Promote RSS discovery with configuration and fixtures.
6. Add a document store and idempotency keys.
7. Refactor ING parsing into a tested parser interface.
8. Refactor transcription behind provider interfaces.
9. Produce structured summary JSON and deterministic Markdown rendering.
10. Add CLI orchestration, dry-run behavior, and end-to-end fixture tests.

## Decisions to make before deployment

- Is the primary output a personal daily briefing, a team research artifact, or
  an API product?
- Which sources are licensed or permitted for automated retrieval and storage?
- Is local transcription a requirement or only a cost-saving option?
- What retention policy applies to downloaded audio, transcripts, and summaries?
- Where should scheduled execution and secrets live?

These decisions affect deployment and retention, but they do not block the
foundation and fixture-driven ingestion work.
