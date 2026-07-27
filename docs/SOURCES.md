# Source policy

Enabled sources must:

- publish a stable HTTPS RSS or Atom feed;
- expose a publication timestamp and canonical item link;
- allow retrieval of the linked HTML or PDF with a normal research-reader user agent;
- yield meaningful main text through the generic extractor;
- be reputable primary institutions or established research publishers.

Run `macro-sage validate-sources` after changing the list. It fetches the newest
entry from every enabled article feed and requires at least 250 extracted
characters. It intentionally does not run in CI because publisher availability is
external and changes over time.

The maintained inventory, publication cadence, description, links, and rationale
for every configured source live in
[SOURCE_CATALOG.md](SOURCE_CATALOG.md). An offline test prevents that catalog from
drifting away from `config/sources.toml`.

## Verification record

The feeds configured for ING, Saxo articles, BNP Paribas Economic Research, ECB,
Federal Reserve Board, BIS, Bank of Canada, and Liberty Street Economics returned
valid entries in a live feed check on 2026-07-27. The expanded Bank of England,
SNB, Norges Bank, Riksbank, San Francisco Fed, Bank of Japan, Bruegel, and NBER
feeds were also checked through original-text extraction on that date. Bruegel
later began consistently returning HTTP 403 and is now kept as a
configured-but-disabled candidate. The extraction validator is the authoritative
repeatable check.

After the unavailable Bruegel feed was disabled, a complete live pass on
2026-07-27 verified original-text extraction for all 31 enabled article sources
and enclosure discovery for all 16 opt-in podcast feeds.

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

Podcast feeds are preserved as disabled, explicit opt-ins. They are excluded from
routine testing to avoid downloads and paid transcription. Enabling them uses at
most the configured number of same-day episodes per feed and caches completed
transcripts. `macro-sage validate-sources --include-podcasts` verifies feed
discovery and audio enclosures without downloading the media.

Some official publication feeds point to short landing pages. Sources marked
`prefer_pdf` fetch and parse the official linked PDF so the model receives the
actual report rather than its teaser. The BOJ's broad update feed is filtered by
URL before item limits are applied, preventing spreadsheets and routine
statistical tables from entering the text corpus.
