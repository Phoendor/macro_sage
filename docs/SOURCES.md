# Source policy

Default sources must:

- publish a stable HTTPS RSS or Atom feed;
- expose a publication timestamp and canonical item link, or have a documented
  explicit timestamp policy;
- allow retrieval of the linked HTML or PDF with a normal research-reader user agent;
- yield meaningful main text through the generic extractor;
- be reputable primary institutions or established research publishers.

Run `macro-sage validate-sources --include-podcasts` after changing the list. It
records feed HTTP/redirect behavior, timestamp quality, parse counts and up to
three representative extraction attempts for every default text and optional
audio source. Podcast media is probed without transcription or a complete
download. Live validation intentionally does not run in CI because publisher
availability is external and changes over time.

Routine health is lighter: `macro-sage source-health` checks discovery and
publication cadence without extraction, audio download or OpenAI. GitHub runs
that check on weekday mornings and runs the complete extraction canary weekly.
The event log retains last success/failure, latest publication and consecutive
adverse observations; a source is labelled failing at its configured threshold
but is never silently disabled.

`config/sources.toml` is authoritative. It generates
[SOURCE_CATALOG.md](SOURCE_CATALOG.md) and
[SOURCE_COVERAGE.md](SOURCE_COVERAGE.md); offline checks compare the complete
generated documents rather than only checking that IDs appear.
The same inventory controls synthesis admission separately from acquisition:
evidence tier, priority and explicit title include/exclude patterns determine
ordering and narrowly defined exclusions. There is no per-source or
per-publisher synthesis cap. Every collected document remains visible in the
private technical report, including documents omitted by the overall context
boundary or explicit keyword policy.

Automated validation and manual review are separate operations. Validation
always writes `pending_review` contract samples. Supplying `--review-bundle`
writes bounded excerpts under ignored `output/` storage for inspection; those
excerpts must never be committed or uploaded. After inspection, `macro-sage
review-source-contracts` accepts a complete decision file only when every
decision matches the exact contract fingerprint and baseline Git commit.

## Verification record

The current baseline is
[`validation/source-validation-2026-08-29.json`](../validation/source-validation-2026-08-29.json).
It checked all 31 default text sources and all 16 optional podcast feeds under
application version 0.4.6 and extractor version 3: 45 passed, Norges Regional
Network was degraded, and BIS Research Hub failed. The official BIS Research
Hub RSS endpoint returned HTTP 404 on two bounded checks. The Norges report's
prose extracted completely, while its charts lost tabular structure. All 47
body-free contract records were explicitly reviewed: 44 approved, two approved
with limitations, and the BIS failure rejected. Decisions are retained in
`validation/source-review-2026-08-29.json` and exact samples under
`validation/contracts/`.

That pass made Norges Monetary Policy Report follow its complete official PDF,
excluded multimedia summaries from the Bank of Canada speech contract,
corrected UTF-8 decoding, accepted Acast's generic range-probe response only
because the HSBC feed explicitly declares `audio/mpeg`, and documented explicit
timestamp policies for feeds that do not
publish a conventional item publication field. A malformed 2035 BIS date and a
future Bank of Canada event entry are retained as warnings but are not eligible
for daily collection.

The BIS Research Hub endpoint continued returning HTTP 404 through the live
2026-09-02 source-health run and reached ten consecutive adverse observations.
Version 0.7.1 therefore moved this one rejected contract from default to
configured-unavailable participation. It remains listed with its exact failure
and rationale, but daily collection and health checks no longer request the
known-broken endpoint.

RBA and RBNZ feeds were considered but returned HTTP 403 to the application
client. IMF Blog and CEPR/VoxEU feeds were rejected by their edge services. Saxo
Trade Views was removed because its newest item was from 2020. A Bank of Canada
working-paper URL was removed because it returned an empty feed. Sources that
cannot be acquired correctly are not kept merely to make the list longer. They
are recorded in the "Would be good to have, but these don't work" catalog
section so they can be revisited deliberately.

The official feed indexes are:

- [ECB RSS feeds](https://www.ecb.europa.eu/home/html/rss.en.html)
- [Federal Reserve RSS feeds](https://www.federalreserve.gov/feeds/feeds.htm)
- [BIS RSS feeds](https://www.bis.org/rss/index.htm)
- [Bank of Canada RSS feeds](https://www.bankofcanada.ca/rss-feeds/)
- [BNP Paribas Economic Research RSS](https://economic-research.bnpparibas.com/RSS/en-US/)
- [Saxo RSS feeds](https://www.home.saxo/insights/content-hub/rss)
- [Bank of England RSS feeds](https://www.bankofengland.co.uk/rss)
- [SNB RSS feeds](https://www.snb.ch/en/services-events/digital-services/rss-calendar-feeds)
- [Norges Bank RSS feeds](https://www.norges-bank.no/en/rss-feeds/)
- [Riksbank RSS feeds](https://www.riksbank.se/en-gb/press-and-published/subscribe-via-rss/)

## Podcasts

Podcast feeds have explicit `optional` participation, distinct from unavailable
sources. They are excluded from routine offline tests to avoid downloads and
paid transcription. Enabling them uses at
most the configured number of same-day episodes per feed and caches completed
transcripts. `macro-sage validate-sources --include-podcasts` verifies feed
discovery and audio enclosures without downloading the media.

Some official publication feeds point to short landing pages. Sources with a
`full_pdf` acquisition contract use a tested declarative PDF-link pattern so the
model receives the report rather than a teaser or unrelated appendix. The BOJ's
broad update feed is filtered by URL before daily selection, preventing
spreadsheets and routine statistical tables from entering the text corpus.
