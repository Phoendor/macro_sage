from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode


class MarketDataError(RuntimeError):
    pass


class MarketAssetClass(StrEnum):
    RATES = "rates"
    FX = "fx"
    EQUITIES = "equities"
    CREDIT = "credit"
    COMMODITIES = "commodities"
    VOLATILITY = "volatility"
    FINANCIAL_CONDITIONS = "financial_conditions"


class QuoteStatus(StrEnum):
    OFFICIAL_OBSERVATION = "official_observation"
    OFFICIAL_FIXING = "official_fixing"
    COMPLETED_CLOSE = "completed_close"


class ChangeMethod(StrEnum):
    PERCENT = "percent"
    BASIS_POINTS = "basis_points"
    ABSOLUTE = "absolute"


class MetricStatus(StrEnum):
    AVAILABLE = "available"
    STALE = "stale"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class MarketInstrument:
    id: str
    label: str
    asset_class: MarketAssetClass
    provider: str
    units: str
    currency: str | None
    quote_status: QuoteStatus
    change_method: ChangeMethod
    max_age_days: int
    source_url: str
    enabled: bool = True
    series_id: str | None = None
    operation: str | None = None
    operands: tuple[str, ...] = ()
    scale: Decimal = Decimal("1")
    unavailable_reason: str | None = None


@dataclass(frozen=True, slots=True)
class MarketConfig:
    version: int
    convention: str
    lookback_days: int
    instruments: tuple[MarketInstrument, ...]


@dataclass(frozen=True, slots=True)
class MarketPoint:
    observed_at: datetime
    value: Decimal


@dataclass(frozen=True, slots=True)
class ProviderBatch:
    series: dict[str, tuple[MarketPoint, ...]]
    errors: dict[str, str]


@dataclass(frozen=True, slots=True)
class MarketMetric:
    instrument_id: str
    label: str
    asset_class: MarketAssetClass
    status: MetricStatus
    provider: str
    series_id: str | None
    units: str
    currency: str | None
    quote_status: QuoteStatus
    source_url: str
    observed_at: datetime | None
    value: Decimal | None
    change_1d: Decimal | None
    change_5d: Decimal | None
    change_1m: Decimal | None
    change_units: str
    transformation: str
    detail: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id,
            "label": self.label,
            "asset_class": self.asset_class.value,
            "status": self.status.value,
            "provider": self.provider,
            "series_id": self.series_id,
            "units": self.units,
            "currency": self.currency,
            "quote_status": self.quote_status.value,
            "source_url": self.source_url,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "value": _decimal_text(self.value),
            "change_1d": _decimal_text(self.change_1d),
            "change_5d": _decimal_text(self.change_5d),
            "change_1m": _decimal_text(self.change_1m),
            "change_units": self.change_units,
            "transformation": self.transformation,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    schema_version: int
    as_of: datetime
    convention: str
    metrics: tuple[MarketMetric, ...]
    warnings: tuple[str, ...]

    @property
    def market_data_available(self) -> bool:
        return any(metric.status is MetricStatus.AVAILABLE for metric in self.metrics)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "as_of": self.as_of.isoformat(),
            "convention": self.convention,
            "market_data_available": self.market_data_available,
            "available_metrics": sum(
                metric.status is MetricStatus.AVAILABLE for metric in self.metrics
            ),
            "configured_metrics": len(self.metrics),
            "warnings": list(self.warnings),
            "metrics": [metric.as_dict() for metric in self.metrics],
        }


class MarketHttpClient(Protocol):
    def get(self, url: str): ...


def _required(row: dict[str, object], name: str) -> str:
    value = str(row.get(name, "")).strip()
    if not value:
        raise MarketDataError(f"Market instrument is missing {name}")
    return value


def load_market_config(path: str | Path) -> MarketConfig:
    value = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    settings = value.get("market")
    rows = value.get("instruments")
    if not isinstance(settings, dict) or not isinstance(rows, list):
        raise MarketDataError("Market config requires [market] and [[instruments]]")
    instruments: list[MarketInstrument] = []
    identifiers: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            raise MarketDataError("Each market instrument must be a table")
        identifier = _required(raw, "id")
        if identifier in identifiers:
            raise MarketDataError(f"Duplicate market instrument id: {identifier}")
        identifiers.add(identifier)
        try:
            instrument = MarketInstrument(
                id=identifier,
                label=_required(raw, "label"),
                asset_class=MarketAssetClass(_required(raw, "asset_class")),
                provider=_required(raw, "provider"),
                units=_required(raw, "units"),
                currency=(str(raw["currency"]) if raw.get("currency") else None),
                quote_status=QuoteStatus(_required(raw, "quote_status")),
                change_method=ChangeMethod(_required(raw, "change_method")),
                max_age_days=int(raw.get("max_age_days", 4)),
                source_url=_required(raw, "source_url"),
                enabled=bool(raw.get("enabled", True)),
                series_id=(str(raw["series_id"]) if raw.get("series_id") else None),
                operation=(str(raw["operation"]) if raw.get("operation") else None),
                operands=tuple(str(item) for item in raw.get("operands", [])),
                scale=Decimal(str(raw.get("scale", 1))),
                unavailable_reason=(
                    str(raw["unavailable_reason"])
                    if raw.get("unavailable_reason")
                    else None
                ),
            )
        except (TypeError, ValueError, InvalidOperation) as exc:
            raise MarketDataError(f"Invalid market instrument {identifier}: {exc}") from exc
        if instrument.max_age_days < 1:
            raise MarketDataError(f"{identifier} max_age_days must be positive")
        if instrument.operation:
            if instrument.operation != "difference" or len(instrument.operands) != 2:
                raise MarketDataError(
                    f"{identifier} must define a two-operand difference"
                )
        elif not instrument.series_id:
            raise MarketDataError(f"{identifier} requires series_id or operation")
        instruments.append(instrument)
    for instrument in instruments:
        unknown = set(instrument.operands) - identifiers
        if unknown:
            raise MarketDataError(
                f"{instrument.id} references unknown operands: {', '.join(sorted(unknown))}"
            )
    return MarketConfig(
        version=int(settings.get("version", 1)),
        convention=_required(settings, "convention"),
        lookback_days=int(settings.get("lookback_days", 60)),
        instruments=tuple(instruments),
    )


class FredProvider:
    endpoint = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, client: MarketHttpClient, api_key: str):
        if not api_key.strip():
            raise MarketDataError("FRED_API_KEY is required for FRED market data")
        self.client = client
        self.api_key = api_key.strip()

    def fetch(
        self,
        instruments: tuple[MarketInstrument, ...],
        *,
        as_of: datetime,
        lookback_days: int,
    ) -> ProviderBatch:
        series: dict[str, tuple[MarketPoint, ...]] = {}
        errors: dict[str, str] = {}
        start = as_of.date() - timedelta(days=lookback_days)
        for instrument in instruments:
            if instrument.provider != "fred" or not instrument.series_id:
                continue
            query = urlencode(
                {
                    "series_id": instrument.series_id,
                    "api_key": self.api_key,
                    "file_type": "json",
                    "observation_start": start.isoformat(),
                    "observation_end": as_of.date().isoformat(),
                    "sort_order": "asc",
                }
            )
            try:
                response = self.client.get(f"{self.endpoint}?{query}")
                payload = response.json()
                observations = payload.get("observations", [])
                points = tuple(
                    point
                    for row in observations
                    if (point := _fred_point(row)) is not None
                )
                if not points:
                    raise MarketDataError("no usable observations returned")
                series[instrument.id] = points
            except Exception as exc:
                errors[instrument.id] = _safe_provider_error(exc)
        return ProviderBatch(series, errors)


def _fred_point(row: object) -> MarketPoint | None:
    if not isinstance(row, dict) or row.get("value") in {None, "."}:
        return None
    try:
        observed = date.fromisoformat(str(row["date"]))
        value = Decimal(str(row["value"]))
    except (KeyError, ValueError, InvalidOperation):
        return None
    return MarketPoint(
        datetime.combine(observed, datetime.min.time(), tzinfo=timezone.utc),
        value,
    )


def _safe_provider_error(exc: Exception) -> str:
    if hasattr(exc, "response"):
        response = getattr(exc, "response")
        status = getattr(response, "status_code", "unknown")
        return f"provider request failed with HTTP {status}"
    if isinstance(exc, (json.JSONDecodeError, MarketDataError)):
        return str(exc)
    return f"provider request failed: {type(exc).__name__}"


def _derived_points(
    instrument: MarketInstrument,
    series: dict[str, tuple[MarketPoint, ...]],
) -> tuple[MarketPoint, ...]:
    if instrument.operation != "difference":
        return ()
    left_id, right_id = instrument.operands
    left = {point.observed_at: point.value for point in series.get(left_id, ())}
    right = {point.observed_at: point.value for point in series.get(right_id, ())}
    return tuple(
        MarketPoint(observed_at, (left[observed_at] - right[observed_at]) * instrument.scale)
        for observed_at in sorted(left.keys() & right.keys())
    )


def _change(
    points: tuple[MarketPoint, ...],
    lookback: int,
    method: ChangeMethod,
) -> Decimal | None:
    if len(points) <= lookback:
        return None
    latest = points[-1].value
    previous = points[-(lookback + 1)].value
    if method is ChangeMethod.PERCENT:
        if previous == 0:
            return None
        return ((latest / previous) - 1) * 100
    if method is ChangeMethod.BASIS_POINTS:
        return (latest - previous) * 100
    return latest - previous


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value.quantize(Decimal("0.0001")), "f")


def build_market_snapshot(
    config: MarketConfig,
    batch: ProviderBatch,
    *,
    as_of: datetime,
) -> MarketSnapshot:
    if as_of.tzinfo is None:
        raise MarketDataError("Market snapshot as_of must include a timezone")
    series = dict(batch.series)
    for instrument in config.instruments:
        if instrument.enabled and instrument.operation:
            series[instrument.id] = _derived_points(instrument, series)

    metrics: list[MarketMetric] = []
    warnings: list[str] = []
    for instrument in config.instruments:
        if not instrument.enabled:
            continue
        points = tuple(
            point for point in series.get(instrument.id, ()) if point.observed_at <= as_of
        )
        change_units = {
            ChangeMethod.PERCENT: "percent",
            ChangeMethod.BASIS_POINTS: "basis_points",
            ChangeMethod.ABSOLUTE: instrument.units,
        }[instrument.change_method]
        transformation = (
            f"difference({instrument.operands[0]}, {instrument.operands[1]})"
            f" * {instrument.scale}"
            if instrument.operation
            else f"{instrument.change_method.value} change across 1, 5 and 21 observations"
        )
        if not points:
            detail = batch.errors.get(
                instrument.id,
                "required observations were unavailable or operands did not overlap",
            )
            warnings.append(f"{instrument.id}: {detail}")
            metrics.append(
                MarketMetric(
                    instrument.id,
                    instrument.label,
                    instrument.asset_class,
                    MetricStatus.MISSING,
                    instrument.provider,
                    instrument.series_id,
                    instrument.units,
                    instrument.currency,
                    instrument.quote_status,
                    instrument.source_url,
                    None,
                    None,
                    None,
                    None,
                    None,
                    change_units,
                    transformation,
                    detail,
                )
            )
            continue
        latest = points[-1]
        age_days = (as_of.date() - latest.observed_at.date()).days
        status = (
            MetricStatus.STALE
            if age_days > instrument.max_age_days
            else MetricStatus.AVAILABLE
        )
        detail = None
        if status is MetricStatus.STALE:
            detail = (
                f"latest observation is {age_days} calendar days old; "
                f"maximum is {instrument.max_age_days}"
            )
            warnings.append(f"{instrument.id}: {detail}")
        metrics.append(
            MarketMetric(
                instrument.id,
                instrument.label,
                instrument.asset_class,
                status,
                instrument.provider,
                instrument.series_id,
                instrument.units,
                instrument.currency,
                instrument.quote_status,
                instrument.source_url,
                latest.observed_at,
                latest.value,
                _change(points, 1, instrument.change_method),
                _change(points, 5, instrument.change_method),
                _change(points, 21, instrument.change_method),
                change_units,
                transformation,
                detail,
            )
        )
    return MarketSnapshot(
        schema_version=config.version,
        as_of=as_of,
        convention=config.convention,
        metrics=tuple(metrics),
        warnings=tuple(warnings),
    )
