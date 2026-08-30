# Macro Sage

[![Generate Macro Brief](https://github.com/Phoendor/macro_sage/actions/workflows/generate-brief.yml/badge.svg)](https://github.com/Phoendor/macro_sage/actions/workflows/generate-brief.yml)
[![Source Health](https://github.com/Phoendor/macro_sage/actions/workflows/source-health.yml/badge.svg)](https://github.com/Phoendor/macro_sage/actions/workflows/source-health.yml)

Macro Sage collects a structured, curated set of macro and central-bank feeds,
verifies and versions the original article or PDF text, deduplicates it in
SQLite, and creates a source-attributed daily macro decision brief.

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

Successful local briefs are also appended to `data/brief-history/`. Each new
report states whether a trustworthy previous baseline exists and shows
deterministic one-day and one-week view changes. Historical model output is
labelled as context and cannot replace current cited evidence.

## Commands

```bash
# Verify every default feed and extract representative original content.
macro-sage validate-sources

# Also probe every optional podcast enclosure without transcription.
macro-sage validate-sources --include-podcasts

# Create private excerpts for an explicit human/Codex contract review.
macro-sage validate-sources --include-podcasts \
  --review-bundle output/source-review.private.json

# After inspection, apply a complete fingerprint-bound decision file.
macro-sage review-source-contracts \
  --validation validation/source-validation-YYYY-MM-DD.json \
  --decisions validation/source-review-YYYY-MM-DD.json

# Run today's article pipeline.
macro-sage run

# Opt in to cloud podcast transcription. Disabled by default.
macro-sage run --include-podcasts

# Collect now and synthesize later from the saved corpus.
macro-sage collect --include-podcasts
macro-sage synthesize

# See configured sources without network access.
macro-sage list-sources --all

# Check feed discovery and accumulated cadence health without OpenAI or extraction.
macro-sage source-health

# Check a saved brief against the deterministic grounding contract.
macro-sage evaluate --brief output/runs/RUN_ID/brief.json \
  --manifest output/runs/RUN_ID/manifest.json

# Print the latest local PDF path, or open it in the default viewer.
macro-sage latest-report
macro-sage latest-report --open
```

DailyBriefV2 separates observed facts, source forecasts, source opinions and
Macro Sage inference. It ranks material changes, shows six macro regimes,
cross-asset transmission, scenarios, disagreement, catalysts, invalidations and
at most three conditional research expressions. Without timestamped market
data, the brief says so prominently and cannot label an expression ready for
review.

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
still selects the intended Amsterdam publication day. Scheduled collection uses
the half-open interval from the last successful scheduled cutoff to the current
intended cutoff, so Monday includes Friday-evening and weekend publications.
Explicit dates remain deterministic calendar-day replays. The workflow persists
the SQLite document/transcript cache between runs, synthesizes the brief, renders
a PDF, and uploads the PDF plus a sanitized audit trail for 30 days. Raw article
bodies and transcripts are never included in the uploaded artifact. Standard
GitHub-hosted runners are free for this public repository; OpenAI API
transcription and synthesis remain paid usage.

Brief history does not use the evictable Actions cache. The same body-free,
append-only history directory is committed to the dedicated
`macro-sage-history` branch, and a hosted run is not marked complete until that
push succeeds. The workflow token therefore has repository-contents write
permission limited to this persistence step.

The separate `Source Health` workflow runs a model-free discovery check on
weekday mornings and a full extraction canary each Sunday. It records latest
publication, last success/failure and consecutive adverse observations in the
same migrated SQLite store. One transient failure is a warning; the configured
threshold must be reached before the source is labelled failing. This workflow
does not need an OpenAI key and never downloads podcast audio.

Every run writes `source-status.md` and lists failed or partially acquired
sources in terminal output, GitHub's run summary, Markdown, JSON, and the PDF.
Sources with no same-day publication are listed separately and are not treated
as failures. A healthy no-data day completes successfully without making a
synthesis request; collection health is recorded separately as healthy,
degraded, or failed.

Optional Telegram delivery uses the same application locally and on GitHub.
When `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured, scheduled
GitHub runs send the completed PDF automatically, or a short status message on
a normal no-data day. Local runs send only with `--deliver`. Delivery state is
durable and suppresses duplicate rerun posts; use the explicit `deliver
--force` command for intentional redelivery. A delivery outage does not remove
the PDF or fail report generation. See [Telegram delivery](docs/TELEGRAM.md).

The input budget is intentionally bounded by article count and characters. This
controls cost without splitting the corpus into many model calls. Corpus
selection reserves capacity for primary evidence, ranks by evidence tier,
configured priority, title relevance and freshness, balances publishers, and
enforces per-source and per-publisher caps. Explicit title filters keep known
single-security or off-topic material out of synthesis without deleting it from
the private collection manifest. Every inclusion, truncation and omission is
saved in `run.json`. The model receives a JSON evidence array, so source text
cannot forge document boundaries or citation headers.

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

Automated validation never labels its own output as manually reviewed. It emits
pending contract samples and can optionally write a private, ignored review
bundle containing bounded source excerpts. An explicit decision file must cover
every sample and match its fingerprint before review status can become complete.

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
source-health` for routine discovery checks and `macro-sage validate-sources`
when full live extraction needs checking.

## Security

Never place credentials in source code, tests, notebooks, or examples. Use
`OPENAI_API_KEY` from the environment. If a credential is accidentally committed,
revoke it before cleaning Git history. `documents.private.json` is local run
material for synthesis and must never be added to a hosted artifact; the safe
`manifest.json` contains metadata, hashes, provenance, and source outcomes but
no source bodies.

See [the architecture notes](docs/ARCHITECTURE.md),
[model and cost policy](docs/MODELS.md),
[history and collection-window contract](docs/HISTORY.md),
[Telegram delivery](docs/TELEGRAM.md), and
[source policy](docs/SOURCES.md) for the main design decisions. The full
[source catalog](docs/SOURCE_CATALOG.md) records cadence, links, descriptions,
and why each source belongs. The current implementation sequence and acceptance
criteria are maintained in the [action plan](docs/ROADMAP.md); released changes
are summarized in the [changelog](CHANGELOG.md).
