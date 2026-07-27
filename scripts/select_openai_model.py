from __future__ import annotations

import os
from collections.abc import Collection

from openai import OpenAI

DEFAULT_PREFERENCES = (
    "gpt-5.6-luna",
    "gpt-5.4-mini",
    "gpt-5-mini",
    "gpt-4.1-mini",
    "gpt-4o-mini",
)
DEFAULT_TRANSCRIPTION_PREFERENCES = (
    "gpt-4o-mini-transcribe",
    "whisper-1",
)


def choose_model(
    available: Collection[str],
    preferences: tuple[str, ...] = DEFAULT_PREFERENCES,
    *,
    purpose: str = "synthesis",
) -> str:
    for model in preferences:
        if model in available:
            return model
    raise RuntimeError(
        f"No supported {purpose} model is available to this OpenAI project. "
        f"Tried: {', '.join(preferences)}"
    )


def main() -> None:
    available = {model.id for model in OpenAI().models.list()}
    configured = tuple(
        value.strip()
        for value in os.getenv("MACRO_SAGE_MODEL_PREFERENCES", "").split(",")
        if value.strip()
    )
    transcription_configured = tuple(
        value.strip()
        for value in os.getenv(
            "MACRO_SAGE_TRANSCRIPTION_MODEL_PREFERENCES", ""
        ).split(",")
        if value.strip()
    )
    selected = choose_model(available, configured or DEFAULT_PREFERENCES)
    transcription_selected = choose_model(
        available,
        transcription_configured or DEFAULT_TRANSCRIPTION_PREFERENCES,
        purpose="transcription",
    )
    print(f"Selected synthesis model: {selected}")
    print(f"Selected transcription model: {transcription_selected}")

    github_env = os.getenv("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as handle:
            handle.write(f"MACRO_SAGE_MODEL={selected}\n")
            handle.write(
                f"MACRO_SAGE_TRANSCRIPTION_MODEL={transcription_selected}\n"
            )
    else:
        print(f"MACRO_SAGE_MODEL={selected}")
        print(f"MACRO_SAGE_TRANSCRIPTION_MODEL={transcription_selected}")


if __name__ == "__main__":
    main()
