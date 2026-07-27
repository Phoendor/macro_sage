from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SourceKind(StrEnum):
    ARTICLE = "article"
    PODCAST = "podcast"


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


@dataclass(frozen=True, slots=True)
class FeedItem:
    source: SourceDefinition
    title: str
    url: str
    published_at: datetime | None
    author: str | None = None
    feed_text: str = ""
    media_url: str | None = None

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


@dataclass(slots=True)
class CollectionReport:
    documents: list[Document] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


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
