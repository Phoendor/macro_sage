from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
DEFAULT_MAX_ARTICLES = 30
DEFAULT_MAX_ARTICLE_CHARS = 40_000
DEFAULT_MAX_CORPUS_CHARS = 350_000


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = int(raw)
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    model: str = DEFAULT_MODEL
    transcription_model: str = DEFAULT_TRANSCRIPTION_MODEL
    max_articles: int = DEFAULT_MAX_ARTICLES
    max_article_chars: int = DEFAULT_MAX_ARTICLE_CHARS
    max_corpus_chars: int = DEFAULT_MAX_CORPUS_CHARS
    request_timeout_seconds: int = 30
    user_agent: str = "MacroSage/0.2 (personal research reader)"
    timezone_name: str = "Europe/Amsterdam"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            model=os.getenv("MACRO_SAGE_MODEL", DEFAULT_MODEL),
            transcription_model=os.getenv(
                "MACRO_SAGE_TRANSCRIPTION_MODEL", DEFAULT_TRANSCRIPTION_MODEL
            ),
            max_articles=_positive_int("MACRO_SAGE_MAX_ARTICLES", DEFAULT_MAX_ARTICLES),
            max_article_chars=_positive_int(
                "MACRO_SAGE_MAX_ARTICLE_CHARS", DEFAULT_MAX_ARTICLE_CHARS
            ),
            max_corpus_chars=_positive_int(
                "MACRO_SAGE_MAX_CORPUS_CHARS", DEFAULT_MAX_CORPUS_CHARS
            ),
            timezone_name=os.getenv("MACRO_SAGE_TIMEZONE", "Europe/Amsterdam"),
        )
