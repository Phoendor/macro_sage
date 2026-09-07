# Market-data contract

Status: foundation implemented in version 0.8.0; daily-report integration is
deliberately not enabled yet.

## Decision

The first market snapshot uses **the latest completed observation published by
the provider; it is never represented as live**. This preserves the existing
19:30 Amsterdam publication schedule without mixing an incomplete US trading
session with completed European closes. Each metric carries its own observation
time and quote status, so a prior US close remains visibly a prior close.

If a later provider can deliver and license the current completed US close
reliably, the scheduled report should move to 22:30 Amsterdam. Until then,
moving the schedule would imply freshness the current providers do not promise.

Changes are deterministic and use available observations rather than calendar
days:

- `1d`: change from the previous observation;
- `5d`: change from five observations earlier;
- `1m`: change from 21 observations earlier;
- yields and percentage-point spreads change in basis points;
- prices, indices and exchange rates change in percent;
- already-normalized spreads and condition indices change in their displayed
  units.

## Providers

### FRED — implemented foundation

The Federal Reserve Bank of St. Louis FRED API is the initial adapter for US
rates, broad US equity closes, credit spreads, energy prices, volatility and
financial conditions. It has a documented HTTPS observations API and requires a
free `FRED_API_KEY`.

FRED is sometimes a distributor rather than the originating publisher. Every
configured series therefore keeps both the FRED series identifier and source
page. Series-specific notes, attribution and redistribution conditions must be
reviewed before a metric enters the public PDF; implementing an API adapter is
not itself publication approval.

- API documentation: <https://fred.stlouisfed.org/docs/api/fred/series_observations.html>
- API-key terms: <https://fred.stlouisfed.org/docs/api/api_key.html>
- Terms of use: <https://fred.stlouisfed.org/docs/api/terms_of_use.html>

### ECB Data Portal — selected, adapter pending

The official ECB SDMX service is selected for daily euro reference rates. The
initial EUR/USD, EUR/JPY, EUR/GBP and EUR/CHF definitions are present in
`config/markets.toml` but disabled until the response schema, publication time,
cross-rate rules and three representative live samples are tested.

- API overview: <https://data.ecb.europa.eu/help/api/overview>
- Data examples: <https://data.ecb.europa.eu/help/api/data-examples>

### Still unresolved

The foundation is intentionally incomplete outside the US. Before public
enablement, the project still needs appropriately licensed and sufficiently
timely coverage for European and Asian equity indices, broader commodities and
any market positioning data. It will not use `yfinance`, scrape consumer quote
pages, or disguise delayed values as live data to fill those gaps.

## Snapshot contract

`config/markets.toml` is the authoritative registry. Every enabled instrument
declares:

- canonical instrument ID and human label;
- asset class, provider and provider series ID;
- level units and currency where applicable;
- official observation, official fixing or completed-close status;
- change method and maximum acceptable age;
- source URL;
- any deterministic formula and its operands.

The snapshot records the requested as-of timestamp, convention, exact metric
observation time, current/stale/missing state, level, 1/5/21-observation changes,
provider attribution, transformation and a plain warning for every unavailable
or stale metric. Calculated curve slopes are built locally from date-aligned
component observations.

Missing market data is non-fatal. The existing qualitative report continues to
state that market data is unavailable until the snapshot is integrated and the
public-use gate has passed.

## Manual foundation check

After obtaining a FRED API key:

```bash
export FRED_API_KEY=replace-with-your-key
macro-sage market-snapshot \
  --as-of 2026-09-07T19:30:00+02:00 \
  --output output/market-data/2026-09-07.json
```

This command makes no OpenAI request and does not alter or publish the daily
brief.
