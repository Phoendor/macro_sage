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


def choose_model(
    available: Collection[str],
    preferences: tuple[str, ...] = DEFAULT_PREFERENCES,
) -> str:
    for model in preferences:
        if model in available:
            return model
    raise RuntimeError(
        "No supported synthesis model is available to this OpenAI project. "
        f"Tried: {', '.join(preferences)}"
    )


def main() -> None:
    available = {model.id for model in OpenAI().models.list()}
    configured = tuple(
        value.strip()
        for value in os.getenv("MACRO_SAGE_MODEL_PREFERENCES", "").split(",")
        if value.strip()
    )
    selected = choose_model(available, configured or DEFAULT_PREFERENCES)
    print(f"Selected synthesis model: {selected}")

    github_env = os.getenv("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as handle:
            handle.write(f"MACRO_SAGE_MODEL={selected}\n")
    else:
        print(f"MACRO_SAGE_MODEL={selected}")


if __name__ == "__main__":
    main()
