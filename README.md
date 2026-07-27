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
- optional: `ffmpeg` only when explicitly enabling oversized podcast transcription

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

To collect and inspect documents without making a paid model call:

```bash
macro-sage run --date 2026-07-27 --no-ai
```

Outputs are written to `output/<date>/`; fetched documents are cached in
`data/macro_sage.sqlite3`.

## Commands

```bash
# Verify every enabled feed and extract one real item from each.
macro-sage validate-sources

# Run today's article pipeline.
macro-sage run

# Opt in to cloud podcast transcription. Disabled by default.
macro-sage run --include-podcasts

# See configured sources without network access.
macro-sage list-sources --all
```

`gpt-5.4-mini` is the default synthesis model because this is a daily,
high-volume-style task. Override it with `MACRO_SAGE_MODEL`. Podcast transcription
uses `gpt-4o-mini-transcribe`, never local Whisper, and processes oversized files
through lightweight `ffmpeg` segments before upload.

The input budget is intentionally bounded by article count and characters. This
controls cost without splitting the corpus into many model calls. The selected
documents and any omissions are saved alongside every brief.

## Repository layout

```text
.
├── config/sources.toml     # curated article and opt-in podcast feeds
├── src/macro_sage/         # application package
├── tests/                  # offline fixtures and boundary tests
├── scripts/                # bounded operational checks
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
[source policy](docs/SOURCES.md) for the main design decisions.
