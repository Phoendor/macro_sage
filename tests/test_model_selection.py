import pytest

from scripts.select_openai_model import choose_model


def test_choose_model_uses_first_available_preference():
    selected = choose_model(
        {"gpt-4.1-mini", "gpt-4o-mini"},
        ("gpt-5.6-luna", "gpt-4.1-mini", "gpt-4o-mini"),
    )

    assert selected == "gpt-4.1-mini"


def test_choose_model_fails_when_project_has_no_supported_model():
    with pytest.raises(RuntimeError, match="No supported synthesis model"):
        choose_model({"unrelated-model"}, ("gpt-5.6-luna", "gpt-4.1-mini"))


def test_choose_model_can_select_transcription_fallback():
    selected = choose_model(
        {"whisper-1"},
        ("gpt-4o-mini-transcribe", "whisper-1"),
        purpose="transcription",
    )

    assert selected == "whisper-1"


def test_choose_model_names_transcription_failure():
    with pytest.raises(RuntimeError, match="No supported transcription model"):
        choose_model(
            {"unrelated-model"},
            ("gpt-4o-mini-transcribe", "whisper-1"),
            purpose="transcription",
        )
