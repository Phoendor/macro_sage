# Macro Sage

Macro Sage collects a curated set of macro and central-bank feeds, extracts the
original article or PDF text, deduplicates it in SQLite, and creates a
source-attributed daily market brief.

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
python -m pip install -e ".[dev]"
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

Outputs are written to `output/<date>/`; fetched documents are cached in
`data/macro_sage.sqlite3`. A full run also writes
`output/pdf/macro-sage-<date>.pdf`.

## Commands

```bash
# Verify every enabled feed and extract one real item from each.
macro-sage validate-sources

# Also verify podcast feeds without downloading or transcribing audio.
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

Every model-backed command checks the models available to the OpenAI project
before doing paid work. Daily synthesis prefers `gpt-5.6-luna`, with explicit
fallbacks configured through `MACRO_SAGE_MODEL_FALLBACKS`. Podcast transcription
prefers `gpt-4o-mini-transcribe` and falls back to cloud-hosted `whisper-1`.
Selected models and any fallback are printed and saved with the run.

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

The workflow also runs automatically at 19:30 Amsterdam time on weekdays. It
persists the SQLite document/transcript cache between runs, synthesizes the
brief, renders a PDF, and uploads the PDF plus the complete audit trail for 14
days. Standard GitHub-hosted runners are free for this public repository; OpenAI
API transcription and synthesis remain paid usage.

Every run writes `source-status.md` and lists failed or partially acquired
sources in terminal output, GitHub's run summary, Markdown, JSON, and the PDF.
Sources with no same-day publication are listed separately and are not treated
as failures.

The input budget is intentionally bounded by article count and characters. This
controls cost without splitting the corpus into many model calls. Sources are
round-robined by publisher before the article limit is applied, so one prolific
feed cannot crowd out the rest. The selected documents and any omissions are
saved alongside every brief.

## Repository layout

```text
.
├── config/sources.toml     # curated article and opt-in podcast feeds
├── src/macro_sage/         # application package
├── tests/                  # offline fixtures and boundary tests
└── docs/                   # architecture and source policy
```

## Development

```bash
ruff check .
python -m pytest
python -m compileall -q src tests
```

Tests must be deterministic and must not call live feeds or paid APIs. Use
`macro-sage validate-sources` separately when feed health needs checking.

## Security

Never place credentials in source code, tests, notebooks, or examples. Use
`OPENAI_API_KEY` from the environment. If a credential is accidentally committed,
revoke it before cleaning Git history.

See [the architecture notes](docs/ARCHITECTURE.md),
[model and cost policy](docs/MODELS.md), and
[source policy](docs/SOURCES.md) for the main design decisions. The full
[source catalog](docs/SOURCE_CATALOG.md) records cadence, links, descriptions,
and why each source belongs.
