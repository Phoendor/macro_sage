from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SourceKind(StrEnum):
    ARTICLE = "article"
    PODCAST = "podcast"


class SourceState(StrEnum):
    COLLECTED = "collected"
    NO_ITEMS = "no_items"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    id: str
    name: str
    publisher: str
    feed_url: str
    category: str
    kind: SourceKind = SourceKind.ARTICLE
    enabled: bool = True
    max_items: int = 3
    include_url_pattern: str | None = None
    exclude_title_pattern: str | None = None
    prefer_pdf: bool = False
    disabled_reason: str | None = None


@dataclass(frozen=True, slots=True)
class FeedItem:
    source: SourceDefinition
    title: str
    url: str
    published_at: datetime | None
    author: str | None = None
    feed_text: str = ""
    media_url: str | None = None
    duration_seconds: int | None = None

    @property
    def document_id(self) -> str:
        digest = hashlib.sha256(self.url.encode("utf-8")).hexdigest()[:16]
        return f"{self.source.id}:{digest}"


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    source_id: str
    source_name: str
    publisher: str
    category: str
    title: str
    url: str
    published_at: datetime | None
    body: str
    author: str | None = None
    media_type: str = "text/html"


@dataclass(frozen=True, slots=True)
class SourceOutcome:
    source_id: str
    source_name: str
    kind: SourceKind
    state: SourceState
    document_count: int = 0
    stage: str | None = None
    detail: str | None = None

    @property
    def is_failure(self) -> bool:
        return self.state in {SourceState.FAILED, SourceState.PARTIAL}

    def summary(self) -> str:
        stage = f" during {self.stage}" if self.stage else ""
        detail = f": {self.detail}" if self.detail else ""
        return f"{self.source_id} ({self.source_name}){stage}{detail}"


@dataclass(slots=True)
class CollectionReport:
    documents: list[Document] = field(default_factory=list)
    outcomes: list[SourceOutcome] = field(default_factory=list)

    @property
    def failures(self) -> list[SourceOutcome]:
        return [outcome for outcome in self.outcomes if outcome.is_failure]

    @property
    def without_items(self) -> list[SourceOutcome]:
        return [
            outcome
            for outcome in self.outcomes
            if outcome.state is SourceState.NO_ITEMS
        ]


class Bias(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class AssetView(BaseModel):
    asset: str
    bias: Bias
    horizon: str
    confidence: int = Field(ge=1, le=5)
    drivers: list[str]
    risks: list[str]
    source_ids: list[str]


class MacroTheme(BaseModel):
    theme: str
    market_implication: str
    source_ids: list[str]


class DailyBrief(BaseModel):
    as_of_date: str
    executive_summary: list[str]
    macro_themes: list[MacroTheme]
    asset_views: list[AssetView]
    top_risks: list[str]
    source_ids_used: list[str]
