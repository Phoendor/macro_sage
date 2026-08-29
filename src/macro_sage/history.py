from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError, field_validator

from macro_sage.files import write_json_atomic
from macro_sage.models import Bias, DailyBrief
from macro_sage.scheduling import AcquisitionWindow
from macro_sage.versions import (
    BRIEF_SCHEMA_VERSION,
    HISTORY_RECORD_VERSION,
    HISTORY_STORE_VERSION,
    SYNTHESIS_PROMPT_VERSION,
)


class BaselineStatus(StrEnum):
    AVAILABLE = "available"
    FIRST_RUN = "first_run"
    MISSING = "missing"
    INCOMPATIBLE = "incompatible"
    DEGRADED = "degraded"
    NO_PRIOR = "no_prior"


class ChangeStatus(StrEnum):
    NEW = "new"
    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    UNCHANGED = "unchanged"
    REVERSED = "reversed"
    RETIRED = "retired"


class Freshness(StrEnum):
    CURRENT = "current"
    CARRIED = "carried"


class ViewStatusEvent(BaseModel):
    as_of_date: date
    status: ChangeStatus
    bias: Bias
    confidence: int = Field(ge=1, le=5)
    current_source_document_ids: list[str] = Field(default_factory=list)
    freshness: Freshness


class TrackedAssetView(BaseModel):
    key: str
    family: str
    horizon_key: str
    asset: str
    horizon: str
    bias: Bias
    confidence: int = Field(ge=1, le=5)
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    source_document_ids: list[str]
    first_seen_date: date
    last_updated_date: date
    expected_expiry_date: date
    freshness: Freshness = Freshness.CURRENT
    status_history: list[ViewStatusEvent]


class TrackedTheme(BaseModel):
    key: str
    entity_type: str
    title: str
    implication: str
    source_document_ids: list[str]
    first_seen_date: date
    last_updated_date: date
    expected_expiry_date: date
    freshness: Freshness = Freshness.CURRENT


class AssetViewChange(BaseModel):
    key: str
    status: ChangeStatus
    asset: str
    horizon: str
    previous_bias: Bias | None = None
    current_bias: Bias | None = None
    previous_confidence: int | None = None
    current_confidence: int | None = None
    current_source_document_ids: list[str] = Field(default_factory=list)
    historical_source_document_ids: list[str] = Field(default_factory=list)
    first_seen_date: date
    last_updated_date: date
    expected_expiry_date: date
    resolved_date: date | None = None
    carried_forward: bool = False
    explanation: str


class ThemeChange(BaseModel):
    key: str
    entity_type: str
    status: ChangeStatus
    title: str
    current_source_document_ids: list[str] = Field(default_factory=list)
    historical_source_document_ids: list[str] = Field(default_factory=list)
    first_seen_date: date
    last_updated_date: date
    expected_expiry_date: date
    resolved_date: date | None = None
    carried_forward: bool = False


class BriefComparison(BaseModel):
    baseline_status: BaselineStatus
    baseline_detail: str
    previous_run_id: str | None = None
    previous_date: date | None = None
    week_run_id: str | None = None
    week_date: date | None = None
    asset_view_changes: list[AssetViewChange] = Field(default_factory=list)
    theme_changes: list[ThemeChange] = Field(default_factory=list)
    week_asset_view_changes: list[AssetViewChange] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BriefHistoryRecord(BaseModel):
    record_schema_version: int = HISTORY_RECORD_VERSION
    run_id: str
    target_date: date
    intended_cutoff: datetime
    acquisition_start: datetime
    acquisition_end: datetime
    acquisition_rule: str
    completed_at: datetime
    health: str
    versions: dict[str, object]
    brief_schema_version: str
    synthesis_prompt_version: str
    model: str
    reasoning_effort: str | None = None
    document_ids: list[str]
    cited_document_ids: list[str]
    brief: DailyBrief
    asset_views: list[TrackedAssetView]
    themes: list[TrackedTheme]
    comparison: BriefComparison

    @field_validator(
        "intended_cutoff",
        "acquisition_start",
        "acquisition_end",
        "completed_at",
    )
    @classmethod
    def timestamps_are_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("history timestamps must be timezone-aware")
        return value


@dataclass(frozen=True, slots=True)
class HistoryContext:
    status: BaselineStatus
    detail: str
    previous: BriefHistoryRecord | None
    week_ago: BriefHistoryRecord | None
    warnings: tuple[str, ...] = ()
    collection_predecessor: BriefHistoryRecord | None = None

    @property
    def history_available(self) -> bool:
        return self.status not in {
            BaselineStatus.MISSING,
            BaselineStatus.INCOMPATIBLE,
            BaselineStatus.DEGRADED,
        }

    @property
    def previous_cutoff(self) -> datetime | None:
        predecessor = self.collection_predecessor
        return predecessor.acquisition_end if predecessor else None


class BriefHistoryStore(Protocol):
    def context(
        self,
        target: date,
        intended_cutoff: datetime | None = None,
    ) -> HistoryContext: ...

    def save(self, record: BriefHistoryRecord) -> Path: ...


def _slug(value: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", value.casefold())).strip("-")


_CURRENCY_CODES = {
    "aud",
    "cad",
    "chf",
    "cny",
    "eur",
    "gbp",
    "jpy",
    "nzd",
    "usd",
}


def canonical_asset(value: str) -> tuple[str, str]:
    """Return a deterministic comparison key and broad asset family."""
    compact = "".join(re.findall(r"[a-z]+", value.casefold()))
    if len(compact) == 6 and compact[:3] in _CURRENCY_CODES and compact[3:] in _CURRENCY_CODES:
        return f"fx:{compact[:3]}-{compact[3:]}", "fx"
    aliases = (
        (("dollar index", "dxy", "us dollar"), "fx:usd-basket", "fx"),
        (("treasur", "ust", "us rates"), "rates:us", "rates"),
        (("bund", "euro rates", "euro area rates"), "rates:euro-area", "rates"),
        (("gilt", "uk rates"), "rates:uk", "rates"),
        (("jgb", "japan rates"), "rates:japan", "rates"),
        (("s&p", "sp 500", "s&p 500", "us equities"), "equities:us", "equities"),
        (("stoxx", "european equities", "euro equities"), "equities:europe", "equities"),
        (("credit", "spread"), "credit:global", "credit"),
        (("brent", "wti", "crude", "oil"), "commodities:oil", "commodities"),
        (("gold",), "commodities:gold", "commodities"),
    )
    lowered = value.casefold()
    for labels, key, family in aliases:
        if any(label in lowered for label in labels):
            return key, family
    family = next(
        (
            name
            for name in ("rates", "fx", "equities", "credit", "commodities")
            if name in lowered
        ),
        "other",
    )
    return f"{family}:{_slug(value) or 'unspecified'}", family


def canonical_horizon(value: str) -> str:
    lowered = value.casefold()
    if any(term in lowered for term in ("intraday", "overnight", "one day", "1 day", "24 hour")):
        return "immediate"
    if any(term in lowered for term in ("day", "week", "short", "tactical", "1w", "2w")):
        return "short_term"
    if any(term in lowered for term in ("month", "quarter", "medium", "1m", "3m", "6m")):
        return "medium_term"
    if any(term in lowered for term in ("year", "long", "strategic", "12m")):
        return "long_term"
    return "unspecified"


def _expiry(target: date, horizon_key: str) -> date:
    days = {
        "immediate": 1,
        "short_term": 14,
        "medium_term": 90,
        "long_term": 365,
        "unspecified": 30,
    }[horizon_key]
    return target + timedelta(days=days)


_THEME_STOPWORDS = {"a", "an", "and", "of", "the", "to", "with"}
_EVENT_TERMS = {
    "decision",
    "election",
    "meeting",
    "referendum",
    "release",
    "shock",
    "summit",
}
_REGIME_TERMS = {
    "growth": {"growth", "recession", "activity"},
    "inflation": {"inflation", "disinflation", "prices"},
    "monetary-policy": {"central", "monetary", "policy", "rates"},
    "fiscal-policy": {"fiscal", "budget", "deficit"},
    "liquidity": {"liquidity", "financial", "conditions"},
    "risk-sentiment": {"sentiment", "risk", "volatility"},
}


def canonical_theme(value: str) -> tuple[str, str]:
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in _THEME_STOPWORDS
    ]
    token_set = set(tokens)
    if token_set.intersection(_EVENT_TERMS):
        key = "-".join(tokens) or "unspecified"
        return f"event:{key}", "event"
    matches = [
        name for name, terms in _REGIME_TERMS.items() if token_set.intersection(terms)
    ]
    if len(matches) == 1:
        return f"regime:{matches[0]}", "regime"
    key = "-".join(tokens) or "unspecified"
    return f"thesis:{key}", "thesis"


def _asset_status(previous: TrackedAssetView, current_bias: Bias, confidence: int) -> ChangeStatus:
    if {previous.bias, current_bias} == {Bias.BULLISH, Bias.BEARISH}:
        return ChangeStatus.REVERSED
    if previous.bias == current_bias:
        if confidence > previous.confidence:
            return ChangeStatus.STRENGTHENED
        if confidence < previous.confidence:
            return ChangeStatus.WEAKENED
        return ChangeStatus.UNCHANGED
    directional = {Bias.BULLISH, Bias.BEARISH}
    if previous.bias not in directional and current_bias in directional:
        return ChangeStatus.STRENGTHENED
    return ChangeStatus.WEAKENED


def _explanation(
    status: ChangeStatus,
    previous: TrackedAssetView | None,
    current_bias: Bias | None,
    current_confidence: int | None,
) -> str:
    if previous is None:
        return "No comparable view appeared in the previous successful brief."
    if status is ChangeStatus.RETIRED:
        return "The prior view reached its deterministic horizon expiry without current renewal."
    if current_bias is None:
        return "No current evidence renewed the view; it is retained only as historical context."
    return (
        f"Bias moved from {previous.bias.value}/{previous.confidence} to "
        f"{current_bias.value}/{current_confidence}."
    )


def _compare_assets(
    brief: DailyBrief,
    target: date,
    baseline: BriefHistoryRecord | None,
) -> tuple[list[TrackedAssetView], list[AssetViewChange]]:
    prior = {view.key: view for view in baseline.asset_views} if baseline else {}
    current: list[TrackedAssetView] = []
    changes: list[AssetViewChange] = []
    seen: set[str] = set()
    for view in brief.asset_views:
        asset_key, family = canonical_asset(view.asset)
        horizon_key = canonical_horizon(view.horizon)
        key = f"asset-view:{asset_key}:{horizon_key}"
        previous = prior.get(key)
        status = (
            _asset_status(previous, view.bias, view.confidence)
            if previous
            else ChangeStatus.NEW
        )
        status_event = ViewStatusEvent(
            as_of_date=target,
            status=status,
            bias=view.bias,
            confidence=view.confidence,
            current_source_document_ids=view.source_ids,
            freshness=Freshness.CURRENT,
        )
        snapshot = TrackedAssetView(
            key=key,
            family=family,
            horizon_key=horizon_key,
            asset=view.asset,
            horizon=view.horizon,
            bias=view.bias,
            confidence=view.confidence,
            supporting_evidence=view.drivers,
            contradicting_evidence=view.risks,
            source_document_ids=view.source_ids,
            first_seen_date=previous.first_seen_date if previous else target,
            last_updated_date=target,
            expected_expiry_date=_expiry(target, horizon_key),
            status_history=[*(previous.status_history if previous else []), status_event],
        )
        current.append(snapshot)
        changes.append(
            AssetViewChange(
                key=key,
                status=status,
                asset=view.asset,
                horizon=view.horizon,
                previous_bias=previous.bias if previous else None,
                current_bias=view.bias,
                previous_confidence=previous.confidence if previous else None,
                current_confidence=view.confidence,
                current_source_document_ids=view.source_ids,
                historical_source_document_ids=(
                    previous.source_document_ids if previous else []
                ),
                first_seen_date=snapshot.first_seen_date,
                last_updated_date=target,
                expected_expiry_date=snapshot.expected_expiry_date,
                explanation=_explanation(status, previous, view.bias, view.confidence),
            )
        )
        seen.add(key)

    for key, previous in prior.items():
        if key in seen:
            continue
        expired = target >= previous.expected_expiry_date
        status = ChangeStatus.RETIRED if expired else ChangeStatus.UNCHANGED
        if not expired:
            carry_event = ViewStatusEvent(
                as_of_date=target,
                status=ChangeStatus.UNCHANGED,
                bias=previous.bias,
                confidence=previous.confidence,
                current_source_document_ids=[],
                freshness=Freshness.CARRIED,
            )
            current.append(
                previous.model_copy(
                    update={
                        "freshness": Freshness.CARRIED,
                        "status_history": [*previous.status_history, carry_event],
                    }
                )
            )
        changes.append(
            AssetViewChange(
                key=key,
                status=status,
                asset=previous.asset,
                horizon=previous.horizon,
                previous_bias=previous.bias,
                current_bias=None if expired else previous.bias,
                previous_confidence=previous.confidence,
                current_confidence=None if expired else previous.confidence,
                historical_source_document_ids=previous.source_document_ids,
                first_seen_date=previous.first_seen_date,
                last_updated_date=previous.last_updated_date,
                expected_expiry_date=previous.expected_expiry_date,
                resolved_date=target if expired else None,
                carried_forward=not expired,
                explanation=_explanation(status, previous, None, None),
            )
        )
    return current, sorted(changes, key=lambda change: change.key)


def _compare_themes(
    brief: DailyBrief,
    target: date,
    baseline: BriefHistoryRecord | None,
) -> tuple[list[TrackedTheme], list[ThemeChange]]:
    prior = {theme.key: theme for theme in baseline.themes} if baseline else {}
    current: list[TrackedTheme] = []
    changes: list[ThemeChange] = []
    seen: set[str] = set()
    for theme in brief.macro_themes:
        key, entity_type = canonical_theme(theme.theme)
        previous = prior.get(key)
        snapshot = TrackedTheme(
            key=key,
            entity_type=entity_type,
            title=theme.theme,
            implication=theme.market_implication,
            source_document_ids=theme.source_ids,
            first_seen_date=previous.first_seen_date if previous else target,
            last_updated_date=target,
            expected_expiry_date=target + timedelta(days=14),
        )
        current.append(snapshot)
        changes.append(
            ThemeChange(
                key=key,
                entity_type=entity_type,
                status=ChangeStatus.UNCHANGED if previous else ChangeStatus.NEW,
                title=theme.theme,
                current_source_document_ids=theme.source_ids,
                historical_source_document_ids=(
                    previous.source_document_ids if previous else []
                ),
                first_seen_date=snapshot.first_seen_date,
                last_updated_date=target,
                expected_expiry_date=snapshot.expected_expiry_date,
            )
        )
        seen.add(key)
    for key, previous in prior.items():
        if key in seen:
            continue
        expired = target >= previous.expected_expiry_date
        if not expired:
            current.append(previous.model_copy(update={"freshness": Freshness.CARRIED}))
        changes.append(
            ThemeChange(
                key=key,
                entity_type=previous.entity_type,
                status=ChangeStatus.RETIRED if expired else ChangeStatus.UNCHANGED,
                title=previous.title,
                historical_source_document_ids=previous.source_document_ids,
                first_seen_date=previous.first_seen_date,
                last_updated_date=previous.last_updated_date,
                expected_expiry_date=previous.expected_expiry_date,
                resolved_date=target if expired else None,
                carried_forward=not expired,
            )
        )
    return current, sorted(changes, key=lambda change: change.key)


def build_history_record(
    *,
    run_id: str,
    target: date,
    intended_cutoff: datetime,
    acquisition_window: AcquisitionWindow,
    health: str,
    versions: dict[str, object],
    model: str,
    reasoning_effort: str | None,
    document_ids: list[str],
    brief: DailyBrief,
    context: HistoryContext,
) -> BriefHistoryRecord:
    asset_views, asset_changes = _compare_assets(brief, target, context.previous)
    themes, theme_changes = _compare_themes(brief, target, context.previous)
    _, week_changes = _compare_assets(brief, target, context.week_ago)
    comparison = BriefComparison(
        baseline_status=context.status,
        baseline_detail=context.detail,
        previous_run_id=context.previous.run_id if context.previous else None,
        previous_date=context.previous.target_date if context.previous else None,
        week_run_id=context.week_ago.run_id if context.week_ago else None,
        week_date=context.week_ago.target_date if context.week_ago else None,
        asset_view_changes=asset_changes,
        theme_changes=theme_changes,
        week_asset_view_changes=week_changes if context.week_ago else [],
        warnings=list(context.warnings),
    )
    return BriefHistoryRecord(
        run_id=run_id,
        target_date=target,
        intended_cutoff=intended_cutoff,
        acquisition_start=acquisition_window.start,
        acquisition_end=acquisition_window.end,
        acquisition_rule=acquisition_window.rule,
        completed_at=datetime.now(timezone.utc),
        health=health,
        versions=versions,
        brief_schema_version=BRIEF_SCHEMA_VERSION,
        synthesis_prompt_version=SYNTHESIS_PROMPT_VERSION,
        model=model,
        reasoning_effort=reasoning_effort,
        document_ids=list(dict.fromkeys(document_ids)),
        cited_document_ids=list(dict.fromkeys(brief.source_ids_used)),
        brief=brief,
        asset_views=asset_views,
        themes=themes,
        comparison=comparison,
    )


def historical_prompt_context(context: HistoryContext) -> str:
    if context.previous is None:
        return (
            "Historical comparison context (prior model output; never current evidence): "
            "none. "
            f"Status: {context.status.value}. {context.detail}"
        )
    lines = [
        "Historical comparison context (prior model output; never current evidence):",
        f"Previous successful brief: {context.previous.target_date.isoformat()}.",
    ]
    for view in context.previous.asset_views:
        lines.append(
            f"- {view.key}: {view.bias.value}, confidence {view.confidence}/5; "
            f"last updated {view.last_updated_date.isoformat()}"
        )
    if context.week_ago:
        lines.append(
            f"One-week comparison brief: {context.week_ago.target_date.isoformat()}."
        )
    return "\n".join(lines)


class DirectoryBriefHistory:
    """Atomic, append-only JSON history used locally and on the hosted branch."""

    def __init__(self, root: Path, *, expect_initialized: bool = False):
        self.root = root
        self.expect_initialized = expect_initialized
        self.metadata_path = root / "store.json"
        self.records_path = root / "records"

    def _metadata_status(self) -> tuple[BaselineStatus, str]:
        if not self.metadata_path.exists():
            if self.expect_initialized:
                return BaselineStatus.MISSING, (
                    "The expected durable history marker is absent; comparison is unavailable."
                )
            return BaselineStatus.FIRST_RUN, "No local history store existed before this run."
        try:
            value = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            version = int(value["store_schema_version"])
            record_version = int(value["record_schema_version"])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return BaselineStatus.DEGRADED, "The durable history marker is unreadable."
        if version != HISTORY_STORE_VERSION:
            return BaselineStatus.INCOMPATIBLE, (
                f"History store schema {version} is not supported by schema "
                f"{HISTORY_STORE_VERSION}."
            )
        if record_version != HISTORY_RECORD_VERSION:
            return BaselineStatus.INCOMPATIBLE, (
                f"History record schema {record_version} is not supported by schema "
                f"{HISTORY_RECORD_VERSION}."
            )
        return BaselineStatus.AVAILABLE, "Durable history store loaded."

    def _records(self) -> tuple[list[BriefHistoryRecord], list[str]]:
        records: list[BriefHistoryRecord] = []
        warnings: list[str] = []
        if not self.records_path.exists():
            return records, warnings
        for path in sorted(self.records_path.rglob("*.json")):
            try:
                value = BriefHistoryRecord.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
                if value.record_schema_version != HISTORY_RECORD_VERSION:
                    warnings.append(
                        f"Ignored {path.name}: record schema "
                        f"{value.record_schema_version} is incompatible."
                    )
                    continue
                records.append(value)
            except (OSError, ValidationError, json.JSONDecodeError) as exc:
                warnings.append(f"Ignored unreadable history record {path.name}: {type(exc).__name__}")
        return records, warnings

    def context(
        self,
        target: date,
        intended_cutoff: datetime | None = None,
    ) -> HistoryContext:
        status, detail = self._metadata_status()
        if status in {
            BaselineStatus.MISSING,
            BaselineStatus.INCOMPATIBLE,
            BaselineStatus.DEGRADED,
        }:
            return HistoryContext(status, detail, None, None)
        records, warnings = self._records()
        compatible = [
            record
            for record in records
            if record.target_date < target
            and record.brief_schema_version == BRIEF_SCHEMA_VERSION
        ]
        compatible.sort(key=lambda record: (record.intended_cutoff, record.completed_at))
        previous = compatible[-1] if compatible else None
        week_candidates = [
            record for record in compatible if record.target_date <= target - timedelta(days=7)
        ]
        week_ago = week_candidates[-1] if week_candidates else None
        collection_candidates = [
            record
            for record in records
            if record.acquisition_rule != "explicit_calendar_day"
            and (
                intended_cutoff is None
                or record.acquisition_end < intended_cutoff
            )
        ]
        collection_candidates.sort(
            key=lambda record: (record.acquisition_end, record.completed_at)
        )
        collection_predecessor = (
            collection_candidates[-1] if collection_candidates else None
        )
        if warnings:
            status = BaselineStatus.DEGRADED if previous is None else BaselineStatus.AVAILABLE
            detail = (
                "A valid comparison baseline loaded, with history warnings."
                if previous
                else "History records exist but no trustworthy baseline could be loaded."
            )
        elif previous:
            status = BaselineStatus.AVAILABLE
            detail = f"Compared with successful brief {previous.run_id}."
        elif records and not any(
            record.brief_schema_version == BRIEF_SCHEMA_VERSION for record in records
        ):
            status = BaselineStatus.INCOMPATIBLE
            detail = "History exists, but no earlier brief has a compatible schema."
        elif records:
            status = BaselineStatus.NO_PRIOR
            detail = "History is healthy, but it contains no earlier comparable brief."
        else:
            status = BaselineStatus.FIRST_RUN
            detail = "The durable history store is initialized but contains no earlier brief."
        return HistoryContext(
            status,
            detail,
            previous,
            week_ago,
            tuple(warnings),
            collection_predecessor,
        )

    def _initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if self.metadata_path.exists():
            status, detail = self._metadata_status()
            if status not in {BaselineStatus.AVAILABLE, BaselineStatus.FIRST_RUN}:
                raise RuntimeError(detail)
            return
        write_json_atomic(
            self.metadata_path,
            {
                "store_schema_version": HISTORY_STORE_VERSION,
                "record_schema_version": HISTORY_RECORD_VERSION,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "format": "append-only-json-directory",
            },
        )

    def save(self, record: BriefHistoryRecord) -> Path:
        self._initialize()
        year = record.target_date.strftime("%Y")
        safe_run_id = _slug(record.run_id) or "run"
        path = self.records_path / year / (
            f"{record.target_date.isoformat()}--{safe_run_id}.json"
        )
        value = record.model_dump(mode="json")
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing != value:
                raise RuntimeError(f"history record already exists with different content: {path}")
            return path
        write_json_atomic(path, value)
        return path
