# main_prototype.py
import os

from audio_tools import process_audio_source
from parcers import parse_ING
from summarization import summarize_corpus
from text_tools import process_text_source


def _required_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and load it "
            "into your shell before running Macro Sage."
        )
    return api_key


def main():
    # --------------- USER SETTINGS ----------------#
    # ---- OpenAI ----
    openai_api_key = _required_api_key()

    # ---- Audio transcription (Whisper) ----
    use_local_whisper = True  # local = faster + $0
    local_whisper_model = "base"
    local_whisper_device = "cpu"
    compression_bitrate = "64k"  # mp3 re-encode before ASR

    # ---- Corpus summarisation ----
    gpt_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    temperature = 0.10  # deterministic/factual
    max_tokens_output = 4_000  # ≈ 3 000-word daily wrap

    # ------------------------------------------------
    # Simulated RSS / podcast feed
    # (Replace with real feedparser + scheduler later)
    # ------------------------------------------------
    sources = [
        {
            "url": "https://think.ing.com/articles/the-commodities-feed-gas-rallies-on-supply-risks120424/",
            "source": "ING",
            "type": "web article",
        },
        {
            "url": (
                "https://dcs-spotify.megaphone.fm/"
                "ALFINVESTMENTSTRATEGYBV4832558841.mp3?"
                "key=f0aae9f5e6eae7e655274c61eb2744b5"
            ),
            "source": "Bloomberg Surveillance",
            "type": "podcast",
        },
    ]

    # ----------------------------------------------------------------------
    # STEP 1 – harvest EVERY document first; keep meta in `corpus` list
    # ----------------------------------------------------------------------
    corpus = []  # list of dicts {id, meta, text}
    for idx, src in enumerate(sources, start=1):
        print(f"\n--- Harvesting {idx}/{len(sources)} | {src['type']} ---")
        try:
            if src["type"].lower() == "web article":
                text = (
                    parse_ING(src["url"])
                    if src["source"].lower() == "ing"
                    else process_text_source(src["url"])
                )
            elif src["type"].lower() == "podcast":
                text = process_audio_source(
                    url=src["url"],
                    openai_api_key=openai_api_key,
                    use_local_whisper=use_local_whisper,
                    local_whisper_model=local_whisper_model,
                    local_whisper_device=local_whisper_device,
                    compression_bitrate=compression_bitrate,
                )
            else:
                raise ValueError(f"Unknown source type: {src['type']}")

            corpus.append(
                {
                    "id": idx,
                    "meta": {
                        "url": src["url"],
                        "source": src["source"],
                        "type": src["type"],
                    },
                    "text": text,
                }
            )
            print(f"✓ Harvested Source {idx}")

        except Exception as exc:
            print(f"✗ Error harvesting Source {idx}: {exc}")

    if not corpus:
        print("No documents harvested – aborting.")
        return

    # ----------------------------------------------------------------------
    # STEP 2 – build the mega-prompt that the model will receive
    # ----------------------------------------------------------------------
    mega_prompt_parts = [
        (
            f"### DOC {doc['id']} | Source: {doc['meta']['source']} "
            f"| Type: {doc['meta']['type']}\n{doc['text']}"
        )
        for doc in corpus
    ]
    mega_prompt = "\n\n".join(mega_prompt_parts)

    # ----------------------------------------------------------------------
    # STEP 3 – call the configured model once on the full corpus
    # ----------------------------------------------------------------------
    print(f"\n=== Sending full corpus to {gpt_model} ===")
    final_summary = summarize_corpus(
        mega_prompt,
        api_key=openai_api_key,
        model=gpt_model,
        temperature=temperature,
        max_tokens=max_tokens_output,
    )

    # ----------------------------------------------------------------------
    # STEP 4 – print / persist results
    # ----------------------------------------------------------------------
    print("\n##########  DAILY MACRO WRAP ##########\n")
    print(final_summary)
    print("\n######################################\n")


if __name__ == "__main__":
    main()
