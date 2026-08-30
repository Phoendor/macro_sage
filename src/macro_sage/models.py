from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


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


# DailyBrief remains the version-1 history type. New synthesis uses the version-2
# contract below, while history deliberately keeps reading version-1 records.
DailyBriefV1 = DailyBrief


class ClaimType(StrEnum):
    OBSERVED_FACT = "observed_fact"
    SOURCE_FORECAST = "source_forecast"
    SOURCE_OPINION = "source_opinion"
    SYNTHESIS_INFERENCE = "synthesis_inference"


class StandardHorizon(StrEnum):
    IMMEDIATE = "immediate"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class Urgency(StrEnum):
    ROUTINE = "routine"
    WATCH = "watch"
    IMMEDIATE = "immediate"


class RegimeDimension(StrEnum):
    GROWTH = "growth"
    INFLATION = "inflation"
    MONETARY_POLICY = "monetary_policy"
    FISCAL_POLICY = "fiscal_policy"
    LIQUIDITY = "liquidity_financial_conditions"
    RISK_SENTIMENT = "risk_sentiment"


class RegimeDirection(StrEnum):
    IMPROVING = "improving"
    DETERIORATING = "deteriorating"
    STABLE = "stable"
    MIXED = "mixed"
    UNCLEAR = "unclear"


class MarketConfirmation(StrEnum):
    UNAVAILABLE = "unavailable"
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    CONTRADICTED = "contradicted"


class Actionability(StrEnum):
    BACKGROUND = "background"
    MONITOR = "monitor"
    CONDITIONAL = "conditional"
    READY_FOR_REVIEW = "ready_for_review"


class ScenarioKind(StrEnum):
    BASE = "base"
    UPSIDE = "upside"
    DOWNSIDE = "downside"


class QualitativeLikelihood(StrEnum):
    LEADING = "leading"
    PLAUSIBLE = "plausible"
    TAIL = "tail"
    UNRANKED = "unranked"


class EvidenceClaim(BaseModel):
    text: str
    claim_type: ClaimType
    source_ids: list[str] = Field(min_length=1, max_length=8)
    evidence_family: str
    carried_forward: bool = False


class CoverageSummary(BaseModel):
    data_cutoff: datetime
    comparison_date: date | None = None
    documents_collected: int = Field(ge=0)
    sources_collected: int = Field(ge=0)
    sources_failed_or_partial: int = Field(ge=0)
    sources_without_items: int = Field(ge=0)
    important_missing_coverage: list[str] = Field(max_length=12)
    market_data_available: bool = False
    market_data_note: str


class MaterialChange(BaseModel):
    headline: str
    significance: str
    affected_assets: list[str] = Field(max_length=6)
    transmission: str
    horizon: StandardHorizon
    source_ids: list[str] = Field(min_length=1, max_length=8)


class RankedDevelopment(BaseModel):
    rank: int = Field(ge=1, le=5)
    development: str
    why_it_matters: str
    transmission: str
    urgency: Urgency
    horizon: StandardHorizon
    source_ids: list[str] = Field(min_length=1, max_length=8)


class RegimeAssessment(BaseModel):
    dimension: RegimeDimension
    state: str
    direction: RegimeDirection
    horizon: StandardHorizon
    confidence: int = Field(ge=1, le=5)
    confidence_rationale: str
    evidence: list[EvidenceClaim] = Field(max_length=4)
    counterevidence: list[EvidenceClaim] = Field(max_length=3)
    source_ids: list[str] = Field(min_length=1, max_length=10)


class AssetTransmission(BaseModel):
    asset_class: Literal["rates", "fx", "equities", "credit", "commodities"]
    implication: str


class MacroThemeV2(BaseModel):
    theme: str
    thesis: str
    market_implication: str
    observed_facts: list[EvidenceClaim] = Field(max_length=5)
    inferences: list[EvidenceClaim] = Field(max_length=4)
    conflicting_evidence: list[EvidenceClaim] = Field(max_length=4)
    unresolved_questions: list[str] = Field(max_length=4)
    transmission: list[AssetTransmission] = Field(max_length=5)
    horizon: StandardHorizon
    catalysts: list[str] = Field(max_length=4)
    invalidation_conditions: list[str] = Field(min_length=1, max_length=4)
    source_ids: list[str] = Field(min_length=1, max_length=12)


class AssetViewV2(BaseModel):
    asset: str
    bias: Bias
    horizon: StandardHorizon
    confidence: int = Field(ge=1, le=5)
    confidence_rationale: str
    market_confirmation: MarketConfirmation
    thesis: str
    transmission: str
    drivers: list[str] = Field(max_length=5)
    risks: list[str] = Field(min_length=1, max_length=5)
    catalyst: str
    invalidation_condition: str
    evidence: list[EvidenceClaim] = Field(max_length=5)
    counterevidence: list[EvidenceClaim] = Field(max_length=4)
    source_ids: list[str] = Field(min_length=1, max_length=12)


class CandidateExpression(BaseModel):
    thesis: str
    expression: str
    framing: Literal["directional", "relative_value"]
    why_now: str
    catalyst: str
    expected_path: str
    horizon: StandardHorizon
    invalidation_condition: str
    countercase: str
    implementation_risks: list[str] = Field(min_length=1, max_length=5)
    alternative_expression: str
    evidence_quality: str
    thesis_confidence: int = Field(ge=1, le=5)
    expression_confidence: int = Field(ge=1, le=5)
    confidence_rationale: str
    source_ids: list[str] = Field(min_length=1, max_length=12)
    market_data_required: bool = True
    actionability: Actionability

    @model_validator(mode="after")
    def ready_requires_market_context(self) -> CandidateExpression:
        if self.market_data_required and self.actionability is Actionability.READY_FOR_REVIEW:
            raise ValueError("ready_for_review requires verified market context")
        return self


class Scenario(BaseModel):
    kind: ScenarioKind
    qualitative_likelihood: QualitativeLikelihood
    description: str
    signposts: list[str] = Field(min_length=1, max_length=5)
    cross_asset_consequences: list[AssetTransmission] = Field(max_length=5)
    assumptions: list[EvidenceClaim] = Field(min_length=1, max_length=5)
    source_ids: list[str] = Field(min_length=1, max_length=10)


class DisagreementSide(BaseModel):
    position: str
    evidence: list[EvidenceClaim] = Field(min_length=1, max_length=5)
    source_ids: list[str] = Field(min_length=1, max_length=8)


class Disagreement(BaseModel):
    issue: str
    sides: list[DisagreementSide] = Field(min_length=2, max_length=3)
    resolution_signal: str


class Catalyst(BaseModel):
    event_or_signpost: str
    timing: str
    what_matters: str
    affected_views: list[str] = Field(max_length=6)
    source_ids: list[str] = Field(min_length=1, max_length=8)


class BriefRisk(BaseModel):
    risk: str
    why_it_matters: str
    monitor: str
    source_ids: list[str] = Field(min_length=1, max_length=8)


class DecisionBriefContent(BaseModel):
    what_changed: list[MaterialChange] = Field(max_length=5)
    executive_decisions: list[RankedDevelopment] = Field(max_length=5)
    regime_dashboard: list[RegimeAssessment] = Field(min_length=6, max_length=6)
    macro_themes: list[MacroThemeV2] = Field(max_length=6)
    asset_views: list[AssetViewV2] = Field(max_length=8)
    candidate_expressions: list[CandidateExpression] = Field(max_length=3)
    scenarios: list[Scenario] = Field(min_length=3, max_length=3)
    disagreements: list[Disagreement] = Field(max_length=4)
    catalysts: list[Catalyst] = Field(max_length=8)
    top_risks: list[BriefRisk] = Field(max_length=8)

    @model_validator(mode="after")
    def require_complete_dashboards(self) -> DecisionBriefContent:
        dimensions = [item.dimension for item in self.regime_dashboard]
        if len(set(dimensions)) != len(RegimeDimension):
            raise ValueError("regime dashboard must contain each dimension exactly once")
        scenarios = [item.kind for item in self.scenarios]
        if len(set(scenarios)) != len(ScenarioKind):
            raise ValueError("scenario map must contain base, upside, and downside")
        ranks = [item.rank for item in self.executive_decisions]
        if len(ranks) != len(set(ranks)):
            raise ValueError("executive decision ranks must be unique")
        return self


class DailyBriefV2Draft(DecisionBriefContent):
    """The model-authored part of V2; operational fields are injected by code."""


class DailyBriefV2(DecisionBriefContent):
    schema_version: Literal["2"] = "2"
    as_of_date: str
    coverage: CoverageSummary
    source_ids_used: list[str] = Field(max_length=60)
