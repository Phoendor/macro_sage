from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
DEFAULT_MODEL_FALLBACKS = ("gpt-5.6-terra", "gpt-4.1-mini")
DEFAULT_TRANSCRIPTION_FALLBACKS = ("whisper-1",)
DEFAULT_MAX_ARTICLES = 30
DEFAULT_MAX_ARTICLE_CHARS = 40_000
DEFAULT_MAX_CORPUS_CHARS = 350_000
DEFAULT_MAX_PODCAST_EPISODES = 6
DEFAULT_MAX_PODCAST_MINUTES = 240


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = int(raw)
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _preferences(
    primary_name: str,
    fallback_name: str,
    default_primary: str,
    default_fallbacks: tuple[str, ...],
) -> tuple[str, ...]:
    primary = os.getenv(primary_name, default_primary).strip()
    configured = tuple(
        value.strip()
        for value in os.getenv(fallback_name, "").split(",")
        if value.strip()
    )
    return tuple(dict.fromkeys((primary, *(configured or default_fallbacks))))


@dataclass(frozen=True, slots=True)
class Settings:
    model: str = DEFAULT_MODEL
    transcription_model: str = DEFAULT_TRANSCRIPTION_MODEL
    model_preferences: tuple[str, ...] = (DEFAULT_MODEL, *DEFAULT_MODEL_FALLBACKS)
    transcription_model_preferences: tuple[str, ...] = (
        DEFAULT_TRANSCRIPTION_MODEL,
        *DEFAULT_TRANSCRIPTION_FALLBACKS,
    )
    reasoning_effort: str = "low"
    max_articles: int = DEFAULT_MAX_ARTICLES
    max_article_chars: int = DEFAULT_MAX_ARTICLE_CHARS
    max_corpus_chars: int = DEFAULT_MAX_CORPUS_CHARS
    max_podcast_episodes: int = DEFAULT_MAX_PODCAST_EPISODES
    max_podcast_minutes: int = DEFAULT_MAX_PODCAST_MINUTES
    request_timeout_seconds: int = 30
    user_agent: str = "MacroSage/0.2 (personal research reader)"
    timezone_name: str = "Europe/Amsterdam"

    @classmethod
    def from_env(cls) -> Settings:
        model_preferences = _preferences(
            "MACRO_SAGE_MODEL",
            "MACRO_SAGE_MODEL_FALLBACKS",
            DEFAULT_MODEL,
            DEFAULT_MODEL_FALLBACKS,
        )
        transcription_preferences = _preferences(
            "MACRO_SAGE_TRANSCRIPTION_MODEL",
            "MACRO_SAGE_TRANSCRIPTION_MODEL_FALLBACKS",
            DEFAULT_TRANSCRIPTION_MODEL,
            DEFAULT_TRANSCRIPTION_FALLBACKS,
        )
        return cls(
            model=model_preferences[0],
            transcription_model=transcription_preferences[0],
            model_preferences=model_preferences,
            transcription_model_preferences=transcription_preferences,
            reasoning_effort=os.getenv("MACRO_SAGE_REASONING_EFFORT", "low"),
            max_articles=_positive_int("MACRO_SAGE_MAX_ARTICLES", DEFAULT_MAX_ARTICLES),
            max_article_chars=_positive_int(
                "MACRO_SAGE_MAX_ARTICLE_CHARS", DEFAULT_MAX_ARTICLE_CHARS
            ),
            max_corpus_chars=_positive_int(
                "MACRO_SAGE_MAX_CORPUS_CHARS", DEFAULT_MAX_CORPUS_CHARS
            ),
            max_podcast_episodes=_positive_int(
                "MACRO_SAGE_MAX_PODCAST_EPISODES",
                DEFAULT_MAX_PODCAST_EPISODES,
            ),
            max_podcast_minutes=_positive_int(
                "MACRO_SAGE_MAX_PODCAST_MINUTES",
                DEFAULT_MAX_PODCAST_MINUTES,
            ),
            timezone_name=os.getenv("MACRO_SAGE_TIMEZONE", "Europe/Amsterdam"),
        )
