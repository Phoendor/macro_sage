import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "audio_tools",
        "get_data",
        "main_prototype",
        "parcers",
        "summarization",
        "text_tools",
    ],
)
def test_prototype_modules_import_without_side_effects(module_name):
    importlib.import_module(module_name)


def test_entrypoint_is_callable():
    module = importlib.import_module("main_prototype")
    assert callable(module.main)


def test_entrypoint_requires_environment_key(monkeypatch):
    module = importlib.import_module("main_prototype")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="OPENAI_API_KEY is not set"):
        module._required_api_key()


def test_entrypoint_reads_environment_key(monkeypatch):
    module = importlib.import_module("main_prototype")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-value")

    assert module._required_api_key() == "test-only-value"
