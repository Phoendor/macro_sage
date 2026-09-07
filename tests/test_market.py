from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from macro_sage.market import (
    FredProvider,
    MarketConfig,
    MarketDataError,
    MarketPoint,
    MetricStatus,
    ProviderBatch,
    build_market_snapshot,
    load_market_config,
)


def _points(start: datetime, values: list[str]) -> tuple[MarketPoint, ...]:
    return tuple(
        MarketPoint(start + timedelta(days=index), Decimal(value))
        for index, value in enumerate(values)
    )


def test_market_config_defines_enabled_snapshot_and_explicit_deferred_fx():
    config = load_market_config("config/markets.toml")
    lookup = {instrument.id: instrument for instrument in config.instruments}

    assert config.convention == "latest completed provider observation; never implied live"
    assert lookup["us-2s10s"].operands == ("us-10y", "us-2y")
    assert lookup["sp500"].enabled
    assert not lookup["eur-usd"].enabled
    assert lookup["eur-usd"].unavailable_reason


def test_market_config_rejects_unknown_derived_operand(tmp_path):
    path = tmp_path / "markets.toml"
    path.write_text(
        """
[market]
version = 1
convention = "test"

[[instruments]]
id = "broken"
label = "Broken"
asset_class = "rates"
provider = "calculated"
operation = "difference"
operands = ["missing", "also-missing"]
units = "basis_points"
quote_status = "official_observation"
change_method = "absolute"
source_url = "https://example.com"
""",
        encoding="utf-8",
    )

    try:
        load_market_config(path)
    except MarketDataError as exc:
        assert "unknown operands" in str(exc)
    else:
        raise AssertionError("invalid market config should fail")


def test_snapshot_calculates_changes_and_curve_locally():
    full = load_market_config("config/markets.toml")
    wanted = {"us-2y", "us-10y", "us-2s10s", "sp500"}
    config = MarketConfig(
        full.version,
        full.convention,
        full.lookback_days,
        tuple(item for item in full.instruments if item.id in wanted),
    )
    start = datetime(2026, 8, 3, tzinfo=timezone.utc)
    as_of = start + timedelta(days=21, hours=12)
    twos = [str(Decimal("2.00") + Decimal(index) / 100) for index in range(22)]
    tens = [str(Decimal("3.00") + Decimal(index) / 50) for index in range(22)]
    equities = [str(100 + index) for index in range(22)]
    snapshot = build_market_snapshot(
        config,
        ProviderBatch(
            {
                "us-2y": _points(start, twos),
                "us-10y": _points(start, tens),
                "sp500": _points(start, equities),
            },
            {},
        ),
        as_of=as_of,
    )
    metrics = {metric.instrument_id: metric for metric in snapshot.metrics}

    assert snapshot.market_data_available
    assert metrics["us-10y"].value == Decimal("3.42")
    assert metrics["us-10y"].change_1d == Decimal("2")
    assert metrics["us-10y"].change_5d == Decimal("10")
    assert metrics["us-10y"].change_1m == Decimal("42")
    assert metrics["us-2s10s"].value == Decimal("121")
    assert metrics["us-2s10s"].change_1d == Decimal("1")
    assert metrics["sp500"].change_1d == (Decimal(121) / Decimal(120) - 1) * 100
    assert metrics["sp500"].change_1m == Decimal("21")


def test_snapshot_marks_old_and_failed_series_explicitly():
    full = load_market_config("config/markets.toml")
    config = MarketConfig(
        full.version,
        full.convention,
        full.lookback_days,
        tuple(
            item for item in full.instruments if item.id in {"us-2y", "us-10y"}
        ),
    )
    observed = datetime(2026, 8, 1, tzinfo=timezone.utc)
    snapshot = build_market_snapshot(
        config,
        ProviderBatch(
            {"us-2y": (MarketPoint(observed, Decimal("3.5")),)},
            {"us-10y": "provider request failed with HTTP 503"},
        ),
        as_of=datetime(2026, 8, 10, tzinfo=timezone.utc),
    )
    metrics = {metric.instrument_id: metric for metric in snapshot.metrics}

    assert not snapshot.market_data_available
    assert metrics["us-2y"].status is MetricStatus.STALE
    assert metrics["us-10y"].status is MetricStatus.MISSING
    assert "HTTP 503" in (metrics["us-10y"].detail or "")
    assert len(snapshot.warnings) == 2


class _Response:
    def json(self):
        return {
            "observations": [
                {"date": "2026-08-01", "value": "3.50"},
                {"date": "2026-08-02", "value": "."},
                {"date": "not-a-date", "value": "3.60"},
                {"date": "2026-08-03", "value": "3.75"},
            ]
        }


class _Client:
    def __init__(self):
        self.urls: list[str] = []

    def get(self, url: str):
        self.urls.append(url)
        return _Response()


def test_fred_provider_parses_values_and_skips_missing_rows():
    config = load_market_config("config/markets.toml")
    instrument = next(item for item in config.instruments if item.id == "us-2y")
    client = _Client()

    result = FredProvider(client, "a" * 32).fetch(
        (instrument,),
        as_of=datetime(2026, 8, 3, 12, tzinfo=timezone.utc),
        lookback_days=60,
    )

    assert not result.errors
    assert [point.value for point in result.series["us-2y"]] == [
        Decimal("3.50"),
        Decimal("3.75"),
    ]
    assert "series_id=DGS2" in client.urls[0]
    assert "observation_end=2026-08-03" in client.urls[0]


def test_fred_provider_reports_failure_without_exposing_key():
    config = load_market_config("config/markets.toml")
    instrument = next(item for item in config.instruments if item.id == "us-2y")

    class Response:
        status_code = 403

    class RequestFailure(RuntimeError):
        response = Response()

    class Client:
        def get(self, url: str):
            raise RequestFailure(url)

    secret = "secret-api-key-that-must-not-appear"
    result = FredProvider(Client(), secret).fetch(
        (instrument,),
        as_of=datetime(2026, 8, 3, 12, tzinfo=timezone.utc),
        lookback_days=60,
    )

    assert result.errors == {
        "us-2y": "provider request failed with HTTP 403",
    }
    assert secret not in str(result.errors)
