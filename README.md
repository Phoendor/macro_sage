# Macro Sage

Macro Sage is an early-stage Python pipeline for turning macro-market articles and
podcasts into a concise, asset-level daily wrap. The current prototype can fetch
articles, parse ING research, download and transcribe podcast audio, and send a
combined corpus to an OpenAI model for synthesis.

> **Status:** recovery and foundation work. The pipeline is a useful prototype,
> but it is not yet production-ready. See the
> [resumption plan](docs/RESUMPTION_PLAN.md) for the repository assessment and
> ordered backlog.

## Quick start

Prerequisites:

- Python 3.11 or newer
- `ffmpeg` for audio compression
- the `whisper` CLI when using local transcription
- an OpenAI API key for final summarization

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
set -a
source .env
set +a
python main_prototype.py
```

Install local Whisper support with:

```bash
python -m pip install -e ".[local-whisper]"
```

The prototype currently uses example sources declared in `main_prototype.py`.
Downloaded audio and generated transcripts are written under `audio_sources/`
and are intentionally ignored by Git.

## Current capabilities

- generic HTTP article retrieval
- structured ING article parsing
- RSS and podcast feed discovery prototypes
- local Whisper or OpenAI-hosted audio transcription
- token-aware chunking and corpus-level market summarization
- an experimental J.P. Morgan sitemap crawler

## Repository layout

```text
.
├── main_prototype.py       # current end-to-end prototype
├── audio_tools.py          # download, compress, and transcribe audio
├── get_data.py             # HTTP retrieval helpers
├── parcers.py              # source-specific article parser (legacy spelling)
├── summarization.py        # OpenAI summarization calls
├── text_tools.py           # generic text retrieval and chunking
├── drafts/                 # experiments awaiting review or retirement
├── tests/                  # offline baseline tests
└── docs/                   # recovery notes and delivery roadmap
```

## Development

```bash
python -m pytest
python -m compileall -q \
  audio_tools.py get_data.py main_prototype.py parcers.py summarization.py text_tools.py
```

Tests must be deterministic and must not call live feeds or paid APIs. Use
fixtures and mocked HTTP responses for integration boundaries.

## Security

Never place credentials in source code, tests, notebooks, or examples. Use
`OPENAI_API_KEY` from the environment. If a credential is accidentally committed,
revoke it before cleaning Git history.

## Project direction

The first target is a reproducible CLI that ingests a configured set of feeds for
one date, stores normalized documents, optionally transcribes audio, and emits
both JSON and Markdown daily wraps with source attribution. Architecture and
acceptance criteria are tracked in [docs/RESUMPTION_PLAN.md](docs/RESUMPTION_PLAN.md).
