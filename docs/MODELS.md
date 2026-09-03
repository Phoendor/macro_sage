# Model and cost policy

## Daily synthesis

The primary model is `gpt-5.6-luna` through the Responses API with a Pydantic
structured output and low reasoning effort. This is a daily, cost-sensitive
synthesis workload rather than a frontier-quality coding or agent task. OpenAI
describes Luna as the cost-sensitive, high-volume member of the GPT-5.6 family.

Synthesis prompt version 4 targets `DailyBriefV2`. The model supplies decision
content while code supplies cutoffs, source counts, market-data availability,
schema version and the complete resolved source register. The prompt explicitly
separates facts, source forecasts, source opinions and synthesis inference;
forbids invented prices, calendars, consensus and unsupported precision; and
allows no material change or zero candidate expressions. Displayed confidence
is recalibrated in code from evidence authority, independent evidence families,
freshness, contradiction and missing market context rather than trusting a raw
model score.

The default compatibility preference order after the requested model is
`gpt-5.6-terra`, then `gpt-4.1-mini`. Before any
paid model-backed run, Macro Sage calls the Models API once and selects the first
configured model visible to the exact OpenAI project. The immutable selection is
then shared by collection and synthesis. A compatibility choice is never
silent: it is printed and recorded in `model-selection.json` and `run.json`.
This is preflight selection, not a request-time retry. Plain text-only
collection and source validation do not require model discovery or an OpenAI
key.

Set policy without changing code:

```bash
export MACRO_SAGE_MODEL=gpt-5.6-luna
export MACRO_SAGE_MODEL_FALLBACKS=gpt-5.6-terra,gpt-4.1-mini
export MACRO_SAGE_REASONING_EFFORT=low
```

Before synthesis, Macro Sage sends the completed request shape—including the
structured-output schema—to the Responses input-token counter. The default
model-input budget is 250,000 tokens. A normal run therefore makes one exact
count and one synthesis request. If the count is too large, the application
reduces the per-document ceiling across the corpus, counts again, and keeps the
ranking and every decision deterministic. It does not run a hidden summarizer.

The 1,250,000-character setting is now only a serialization safety boundary,
not the primary context rule. If exact counting is unavailable, the application
uses a conservative UTF-8 estimate and the prior 350,000-character fallback
boundary instead of failing or silently trusting an oversized request. The
private report and `run.json` record the planned count, budget, method, omitted
IDs and truncated IDs.

```bash
export MACRO_SAGE_MAX_INPUT_TOKENS=250000
export MACRO_SAGE_MAX_CORPUS_CHARS=1250000
```

- [OpenAI GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [Responses input-token counting](https://developers.openai.com/api/reference/cli/resources/responses/subresources/input_tokens/methods/count)
- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)

## Podcast transcription

The opt-in primary is `gpt-4o-mini-transcribe`; cloud-hosted `whisper-1` is the
next preflight compatibility choice. Local Whisper is never run.

New audio is limited to six episodes and 240 combined minutes per run by
default. The limits can be lowered through CLI flags or environment variables.
Completed transcripts are stored in SQLite locally and in the GitHub Actions
cache remotely. New audio is re-encoded into 15-minute, mono, 48 kbps segments
when it exceeds either that duration or the upload-size limit. The duration cap
also keeps long, highly compressed files below the model's audio-token limit.

```bash
export MACRO_SAGE_MAX_PODCAST_EPISODES=6
export MACRO_SAGE_MAX_PODCAST_MINUTES=240
```

- [GPT-4o mini Transcribe](https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe)
- [Speech-to-text guide](https://developers.openai.com/api/docs/guides/speech-to-text)
