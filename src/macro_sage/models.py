from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SourceKind(StrEnum):
    ARTICLE = "article"
    PODCAST = "podcast"


class Participation(StrEnum):
    DEFAULT = "default"
    OPTIONAL = "optional"
    UNAVAILABLE = "unavailable"
    CANDIDATE = "candidate"


class EvidenceTier(StrEnum):
    PRIMARY = "primary"
    INSTITUTIONAL_ANALYSIS = "institutional_analysis"
    MARKET_INTERPRETATION = "market_interpretation"
    INFORMED_VIEWPOINT = "informed_viewpoint"


class CadenceBasis(StrEnum):
    OBSERVED = "observed"
    IMPLICIT = "implicit"
    EXPECTED = "expected"


class AcquisitionMode(StrEnum):
    FULL_HTML = "full_html"
    FULL_PDF = "full_pdf"
    FEED_BODY = "feed_body"
    PUBLISHER_TRANSCRIPT = "publisher_transcript"
    MACHINE_TRANSCRIPT = "machine_transcript"


class ValidationStatus(StrEnum):
    VALIDATED = "validated"
    DEGRADED = "degraded"
    NEEDS_VALIDATION = "needs_validation"
    FAILED = "failed"


class SourceState(StrEnum):
    COLLECTED = "collected"
    NO_ITEMS = "no_items"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"
    QUIET_EXPECTED = "quiet_expected"
    EXPECTED_ABSENT = "expected_absent"
    STALE = "stale"
    FILTERED = "filtered"
    INVALID_DATES = "invalid_dates"
    DUPLICATE = "duplicate"
    DEGRADED = "degraded"


class ContentResult(StrEnum):
    REPORT = "report"
    NO_DATA = "no_data"
    NOT_PRODUCED = "not_produced"


class RunHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class ItemState(StrEnum):
    COLLECTED = "collected"
    CACHED = "cached"
    FAILED = "failed"
    SKIPPED = "skipped"
    FILTERED = "filtered"
    INVALID_DATE = "invalid_date"
    DUPLICATE = "duplicate"
    DEGRADED = "degraded"


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    id: str
    name: str
    publisher: str
    feed_url: str
    category: str
    kind: SourceKind = SourceKind.ARTICLE
    participation: Participation = Participation.DEFAULT
    homepage_url: str = ""
    description: str = ""
    rationale: str = ""
    evidence_tier: EvidenceTier = EvidenceTier.INSTITUTIONAL_ANALYSIS
    geographies: tuple[str, ...] = ("global",)
    topics: tuple[str, ...] = ("macro",)
    asset_classes: tuple[str, ...] = ("rates", "fx", "equities")
    language: str = "en"
    cadence: str = "event-driven"
    cadence_basis: CadenceBasis = CadenceBasis.EXPECTED
    max_gap_days: int = 31
    active_weekdays: tuple[int, ...] = (0, 1, 2, 3, 4)
    event_driven: bool = True
    acquisition_mode: AcquisitionMode = AcquisitionMode.FULL_HTML
    priority: int = 50
    critical_coverage_role: str | None = None
    scan_depth: int = 50
    daily_limit: int = 3
    publisher_cap: int = 5
    validation_status: ValidationStatus = ValidationStatus.NEEDS_VALIDATION
    last_validation_date: date | None = None
    validation_note: str | None = None
    owner: str = ""
    include_url_pattern: str | None = None
    exclude_title_pattern: str | None = None
    pdf_link_pattern: str | None = None
    published_from_updated: bool = False
    published_from_feed_last_modified: bool = False
    max_future_days: int = 1
    unavailable_reason: str | None = None

    @property
    def enabled(self) -> bool:
        return self.participation is Participation.DEFAULT

    @property
    def max_items(self) -> int:
        """Compatibility alias; discovery and daily selection are now separate."""
        return self.daily_limit

    @property
    def prefer_pdf(self) -> bool:
        return self.acquisition_mode is AcquisitionMode.FULL_PDF

    @property
    def disabled_reason(self) -> str | None:
        return self.unavailable_reason


@dataclass(frozen=True, slots=True)
class CandidateDefinition:
    id: str
    name: str
    homepage_url: str
    expected_cadence: str
    cadence_basis: CadenceBasis
    description: str
    rationale: str
    attempted_endpoints: tuple[str, ...]
    precise_failure: str
    last_attempt_date: date
    lawful_alternative: str | None
    constraint: str
    next_review_date: date


@dataclass(frozen=True, slots=True)
class SourceInventory:
    version: int
    sources: tuple[SourceDefinition, ...]
    candidates: tuple[CandidateDefinition, ...]


@dataclass(frozen=True, slots=True)
class FeedItem:
    source: SourceDefinition
    title: str
    url: str
    published_at: datetime | None
    author: str | None = None
    feed_text: str = ""
    media_url: str | None = None
    media_type: str | None = None
    duration_seconds: int | None = None
    updated_at: datetime | None = None
    raw_published: str | None = None
    raw_updated: str | None = None
    guid: str | None = None
    publisher_id: str | None = None
    original_url: str | None = None
    timestamp_warning: str | None = None

    @property
    def document_id(self) -> str:
        digest = hashlib.sha256(self.url.encode("utf-8")).hexdigest()[:16]
        return f"doc:{digest}"


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
    original_url: str | None = None
    canonical_url: str | None = None
    resolved_content_url: str | None = None
    updated_at: datetime | None = None
    raw_published: str | None = None
    raw_updated: str | None = None
    fetched_at: datetime | None = None
    language: str = "en"
    content_sha256: str = ""
    extractor_version: str = ""
    acquisition_method: AcquisitionMode = AcquisitionMode.FULL_HTML
    quality_flags: tuple[str, ...] = ()
    revision_id: str = ""
    etag: str | None = None
    last_modified: str | None = None
    page_count: int | None = None
    discovery_source_ids: tuple[str, ...] = ()


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
        return self.state in {
            SourceState.FAILED,
            SourceState.PARTIAL,
            SourceState.EXPECTED_ABSENT,
            SourceState.STALE,
            SourceState.INVALID_DATES,
            SourceState.DEGRADED,
        }

    def summary(self) -> str:
        stage = f" during {self.stage}" if self.stage else ""
        detail = f": {self.detail}" if self.detail else ""
        return f"{self.source_id} ({self.source_name}){stage}{detail}"


@dataclass(frozen=True, slots=True)
class ItemOutcome:
    source_id: str
    title: str
    url: str
    state: ItemState
    stage: str | None = None
    detail: str | None = None
    document_id: str | None = None


@dataclass(slots=True)
class CollectionReport:
    documents: list[Document] = field(default_factory=list)
    outcomes: list[SourceOutcome] = field(default_factory=list)
    item_outcomes: list[ItemOutcome] = field(default_factory=list)

    @property
    def failures(self) -> list[SourceOutcome]:
        return [outcome for outcome in self.outcomes if outcome.is_failure]

    @property
    def without_items(self) -> list[SourceOutcome]:
        return [
            outcome
            for outcome in self.outcomes
            if outcome.state in {SourceState.NO_ITEMS, SourceState.QUIET_EXPECTED}
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
    drivers: list[str] = Field(max_length=5)
    risks: list[str] = Field(max_length=5)
    source_ids: list[str] = Field(min_length=1, max_length=10)


class MacroTheme(BaseModel):
    theme: str
    market_implication: str
    source_ids: list[str] = Field(min_length=1, max_length=10)


class DailyBrief(BaseModel):
    as_of_date: str
    executive_summary: list[str] = Field(max_length=7)
    macro_themes: list[MacroTheme] = Field(max_length=8)
    asset_views: list[AssetView] = Field(max_length=10)
    top_risks: list[str] = Field(max_length=8)
    source_ids_used: list[str] = Field(max_length=30)
