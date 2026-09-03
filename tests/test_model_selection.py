import json

import pytest

from macro_sage.openai_models import (
    ModelSelection,
    choose_model,
    load_model_selection,
    select_models,
)
from macro_sage.settings import DEFAULT_MODEL, Settings


def test_choose_model_uses_first_available_preference():
    selected = choose_model(
        {"gpt-4.1-mini", "gpt-4o-mini"},
        ("gpt-5.6-luna", "gpt-4.1-mini", "gpt-4o-mini"),
        purpose="synthesis",
    )

    assert selected.selected == "gpt-4.1-mini"
    assert selected.used_fallback


def test_choose_model_fails_when_project_has_no_supported_model():
    with pytest.raises(RuntimeError, match="No supported synthesis model"):
        choose_model(
            {"unrelated-model"},
            ("gpt-5.6-luna", "gpt-4.1-mini"),
            purpose="synthesis",
        )


def test_choose_model_can_select_transcription_fallback():
    selected = choose_model(
        {"whisper-1"},
        ("gpt-4o-mini-transcribe", "whisper-1"),
        purpose="transcription",
    )

    assert selected.selected == "whisper-1"


def test_choose_model_names_transcription_failure():
    with pytest.raises(RuntimeError, match="No supported transcription model"):
        choose_model(
            {"unrelated-model"},
            ("gpt-4o-mini-transcribe", "whisper-1"),
            purpose="transcription",
        )


def test_selection_applies_accessible_models_to_settings():
    class Model:
        def __init__(self, identifier):
            self.id = identifier

    class Models:
        def list(self):
            return [Model("gpt-5.6-luna"), Model("gpt-4o-mini-transcribe")]

    class Client:
        models = Models()

    settings = Settings()
    selection = select_models(
        settings,
        require_synthesis=True,
        require_transcription=True,
        client=Client(),
    )

    selected_settings = selection.apply(settings)

    assert selected_settings.model == "gpt-5.6-luna"
    assert selected_settings.transcription_model == "gpt-4o-mini-transcribe"
    assert not selection.synthesis.used_fallback


def test_selection_round_trip_preserves_immutable_choices(tmp_path):
    value = {
        "synthesis": {
            "purpose": "synthesis",
            "requested": "requested-model",
            "selected": "selected-model",
            "preferences": ["requested-model", "selected-model"],
        },
        "transcription": None,
    }
    path = tmp_path / "models.json"
    path.write_text(json.dumps(value), encoding="utf-8")

    selection = load_model_selection(path)

    assert isinstance(selection, ModelSelection)
    assert selection.synthesis.selected == "selected-model"
    assert selection.synthesis.preferences == ("requested-model", "selected-model")


def test_empty_environment_override_uses_committed_default(monkeypatch):
    monkeypatch.setenv("MACRO_SAGE_MODEL", "")
    monkeypatch.setenv("MACRO_SAGE_MODEL_FALLBACKS", "")

    settings = Settings.from_env()

    assert settings.model == DEFAULT_MODEL
    assert settings.model_preferences[0] == DEFAULT_MODEL


def test_synthesis_timeout_has_a_separate_bounded_override(monkeypatch):
    monkeypatch.setenv("MACRO_SAGE_SYNTHESIS_TIMEOUT_SECONDS", "240")

    settings = Settings.from_env()

    assert settings.request_timeout_seconds == 30
    assert settings.synthesis_timeout_seconds == 240


def test_input_token_budget_has_a_bounded_override(monkeypatch):
    monkeypatch.setenv("MACRO_SAGE_MAX_INPUT_TOKENS", "175000")

    settings = Settings.from_env()

    assert settings.max_input_tokens == 175_000
