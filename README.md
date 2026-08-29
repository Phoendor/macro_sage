# Macro Sage

Macro Sage collects a structured, curated set of macro and central-bank feeds,
verifies and versions the original article or PDF text, deduplicates it in
SQLite, and creates a source-attributed daily market brief.

The old collection of one-off scripts has been replaced by an installable `src/`
package and a deterministic CLI. Article synthesis is one structured OpenAI
Responses API request: there is no recursive chunk-summary pipeline.

## Quick start

Prerequisites:

- Python 3.11 or newer
- an OpenAI API key for final summarization
- `ffmpeg`/`ffprobe` only when enabling podcast transcription

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --constraint constraints.txt -e ".[dev]"
cp .env.example .env
set -a
source .env
set +a
macro-sage validate-sources
macro-sage run --date 2026-07-27
```

To collect and inspect text documents without making a paid model call:

```bash
macro-sage collect --date 2026-07-27
```

Each full run receives an immutable attempt ID and writes to
`output/runs/<run-id>/`; fetched documents are cached in
`data/macro_sage.sqlite3`. The latest successful PDF is copied atomically to
`output/pdf/macro-sage-<date>.pdf`. Staged `collect`/`synthesize` commands without
a run ID retain the convenient `output/<date>/` directory.

## Commands

```bash
# Verify every default feed and extract representative original content.
macro-sage validate-sources

# Also probe every optional podcast enclosure without transcription.
macro-sage validate-sources --include-podcasts

# Run today's article pipeline.
macro-sage run

# Opt in to cloud podcast transcription. Disabled by default.
macro-sage run --include-podcasts

# Collect now and synthesize later from the saved corpus.
macro-sage collect --include-podcasts
macro-sage synthesize

# See configured sources without network access.
macro-sage list-sources --all
```

Every model-backed run checks the models available to the OpenAI project once
before doing paid work, then passes that immutable selection through later
stages. Daily synthesis prefers `gpt-5.6-luna`, with additional compatibility
preferences configured through the legacy-named `MACRO_SAGE_MODEL_FALLBACKS`
variable. Podcast transcription prefers `gpt-4o-mini-transcribe`, with
cloud-hosted `whisper-1` as the next preflight choice. Model selection is not a
request-time retry: the selected model and any compatibility choice are printed
and saved with the run.

Podcasts never use local Whisper. New transcription is limited to six episodes
and four hours by default, and completed transcripts are cached. Oversized audio
is split with `ffmpeg` only to satisfy the API upload limit.

## Remote report run

The `Generate Macro Brief` GitHub Actions workflow runs the same `collect` and
`synthesize` commands without access to the development machine. Add an encrypted
repository Actions secret named `OPENAI_API_KEY` under
**Settings → Secrets and variables → Actions**, then run the workflow from the
**Actions** tab. Leave its date blank to use the current date in Amsterdam.
Podcast inclusion and the audio-duration ceiling are explicit inputs.

The workflow also runs automatically at 19:30 Amsterdam time on weekdays. Date
resolution is handled in tested Python code, so a runner delayed past midnight
still selects the intended Amsterdam publication day. It persists the SQLite
document/transcript cache between runs, synthesizes the brief, renders a PDF,
and uploads the PDF plus a sanitized audit trail for 14 days. Raw article bodies
and transcripts are never included in the uploaded artifact. Standard
GitHub-hosted runners are free for this public repository; OpenAI API
transcription and synthesis remain paid usage.

Every run writes `source-status.md` and lists failed or partially acquired
sources in terminal output, GitHub's run summary, Markdown, JSON, and the PDF.
Sources with no same-day publication are listed separately and are not treated
as failures. A healthy no-data day completes successfully without making a
synthesis request; collection health is recorded separately as healthy,
degraded, or failed.

The input budget is intentionally bounded by article count and characters. This
controls cost without splitting the corpus into many model calls. Sources are
round-robined by publisher before the article limit is applied, so one prolific
feed cannot crowd out the rest. The selected documents and any omissions are
saved alongside every brief.

## Source and cache contracts

`config/sources.toml` is the single source inventory. It distinguishes default,
optional and unavailable participation and records evidence tier, coverage,
cadence, expected gaps, acquisition mode, validation state and selection limits.
The source catalog and coverage matrix are generated from it; `python
scripts/check.py` fails if either generated document drifts.

Feed publication and update timestamps remain separate. A small set of feeds
that publish only an update field or a feed-level `Last-Modified` value have an
explicit per-source publication policy; implausible future dates are rejected.
Missing dates and every acquisition failure remain visible rather than becoming
a false quiet day.

SQLite schema migrations preserve existing cached material. Documents use a
source-independent canonical identity, retain every discovery origin and keep
immutable content revisions. See [cache and provenance](docs/CACHE.md) before
changing extraction, source, or transcription contracts.

## Repository layout

```text
.
├── config/sources.toml     # curated article and opt-in podcast feeds
├── validation/             # dated live baseline and reviewed contract metadata
├── src/macro_sage/         # application package
├── tests/                  # offline fixtures and boundary tests
└── docs/                   # architecture and source policy
```

## Development

```bash
python scripts/check.py
```

The check command verifies that the active environment imports this checkout,
checks the generated catalog and coverage matrix, then runs compilation, Ruff,
and the offline test suite with a two-minute limit per subprocess. Tests must be
deterministic and must not call live feeds or paid APIs. Use `macro-sage
validate-sources` separately when feed health needs checking.

## Security

Never place credentials in source code, tests, notebooks, or examples. Use
`OPENAI_API_KEY` from the environment. If a credential is accidentally committed,
revoke it before cleaning Git history. `documents.private.json` is local run
material for synthesis and must never be added to a hosted artifact; the safe
`manifest.json` contains metadata, hashes, provenance, and source outcomes but
no source bodies.

See [the architecture notes](docs/ARCHITECTURE.md),
[model and cost policy](docs/MODELS.md), and
[source policy](docs/SOURCES.md) for the main design decisions. The full
[source catalog](docs/SOURCE_CATALOG.md) records cadence, links, descriptions,
and why each source belongs. The current implementation sequence and acceptance
criteria are maintained in the [action plan](docs/ROADMAP.md); released changes
are summarized in the [changelog](CHANGELOG.md).
