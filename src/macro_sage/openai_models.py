from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from openai import OpenAI

from macro_sage.settings import Settings


@dataclass(frozen=True, slots=True)
class SelectedModel:
    purpose: str
    requested: str
    selected: str
    preferences: tuple[str, ...]

    @property
    def used_fallback(self) -> bool:
        return self.selected != self.requested


@dataclass(frozen=True, slots=True)
class ModelSelection:
    synthesis: SelectedModel | None = None
    transcription: SelectedModel | None = None

    def apply(self, settings: Settings) -> Settings:
        return replace(
            settings,
            model=self.synthesis.selected if self.synthesis else settings.model,
            transcription_model=(
                self.transcription.selected
                if self.transcription
                else settings.transcription_model
            ),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "synthesis": asdict(self.synthesis) if self.synthesis else None,
            "transcription": (
                asdict(self.transcription) if self.transcription else None
            ),
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> ModelSelection:
        def selected(raw: object) -> SelectedModel | None:
            if not isinstance(raw, dict):
                return None
            preferences = raw.get("preferences", ())
            if not isinstance(preferences, (list, tuple)):
                raise ValueError("model preferences must be a list")
            return SelectedModel(
                purpose=str(raw["purpose"]),
                requested=str(raw["requested"]),
                selected=str(raw["selected"]),
                preferences=tuple(str(item) for item in preferences),
            )

        return cls(
            synthesis=selected(value.get("synthesis")),
            transcription=selected(value.get("transcription")),
        )


def choose_model(
    available: set[str],
    preferences: tuple[str, ...],
    *,
    purpose: str,
) -> SelectedModel:
    for model in preferences:
        if model in available:
            return SelectedModel(
                purpose=purpose,
                requested=preferences[0],
                selected=model,
                preferences=preferences,
            )
    raise RuntimeError(
        f"No supported {purpose} model is available to this OpenAI project. "
        f"Tried: {', '.join(preferences)}"
    )


def select_models(
    settings: Settings,
    *,
    require_synthesis: bool,
    require_transcription: bool,
    client: OpenAI | None = None,
) -> ModelSelection:
    if not require_synthesis and not require_transcription:
        return ModelSelection()
    api = client or OpenAI(timeout=settings.request_timeout_seconds)
    available = {model.id for model in api.models.list()}
    synthesis = (
        choose_model(
            available,
            settings.model_preferences,
            purpose="synthesis",
        )
        if require_synthesis
        else None
    )
    transcription = (
        choose_model(
            available,
            settings.transcription_model_preferences,
            purpose="transcription",
        )
        if require_transcription
        else None
    )
    return ModelSelection(synthesis=synthesis, transcription=transcription)


def describe_selection(selection: ModelSelection) -> list[str]:
    lines: list[str] = []
    for selected in (selection.synthesis, selection.transcription):
        if selected is None:
            continue
        suffix = (
            f" (preflight compatibility choice; requested {selected.requested})"
            if selected.used_fallback
            else " (requested model)"
        )
        lines.append(f"{selected.purpose.capitalize()}: {selected.selected}{suffix}")
    return lines


def write_github_env(selection: ModelSelection, path: Path) -> None:
    values = []
    if selection.synthesis:
        values.append(f"MACRO_SAGE_MODEL={selection.synthesis.selected}")
    if selection.transcription:
        values.append(
            "MACRO_SAGE_TRANSCRIPTION_MODEL="
            f"{selection.transcription.selected}"
        )
    with path.open("a", encoding="utf-8") as handle:
        for value in values:
            handle.write(f"{value}\n")


def load_model_selection(path: Path) -> ModelSelection:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Invalid model-selection object in {path}")
    return ModelSelection.from_dict(value)
