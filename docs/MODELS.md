# Model and cost policy

## Daily synthesis

The default is `gpt-5.4-mini` through the Responses API with a Pydantic structured
output. It is the best fit here because the task needs competent cross-document
reasoning and citation discipline, but runs every day and does not justify a
premium frontier model.

At OpenAI's published standard pricing on 2026-07-27, `gpt-5.4-mini` costs $0.75
per million input tokens and $4.50 per million output tokens. The configured
350,000-character input ceiling is roughly 90,000 tokens in a worst-case
English-language run, so input is around $0.07 at the ceiling. The 3,000-output-
token ceiling is about $0.014. Typical days are materially smaller.

The model can be changed without code:

```bash
export MACRO_SAGE_MODEL=gpt-5.6-luna
```

`gpt-5.6-luna` tracks the newest GPT-5.6 family but costs more. `gpt-5.4-nano` is
cheaper, but is not the default because this brief requires nuanced synthesis
rather than simple classification or extraction.

- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)
- [GPT-5.4 mini model](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

## Podcast transcription

The opt-in default is `gpt-4o-mini-transcribe`. Published pricing is about
$0.003/minute, or $0.18 for a one-hour episode. This is now reasonable for
selective episodes, while local Whisper remains a poor experience on the target
Intel Mac.

Audio is still constrained by the transcription upload limit. Files over 24 MiB
are re-encoded into 30-minute, mono, 48 kbps segments with `ffmpeg`; the neural
work remains in the API. Podcasts stay off by default and are excluded from live
source validation and paid tests.

- [OpenAI speech-to-text guide](https://developers.openai.com/api/docs/guides/speech-to-text)
- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)
