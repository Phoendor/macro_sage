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

## Verification record

The feeds configured for ING, Saxo articles, BNP Paribas Economic Research, ECB,
Federal Reserve Board, BIS, Bank of Canada, and Liberty Street Economics returned
valid entries in a live feed check on 2026-07-27. The final extraction validator
is the authoritative repeatable check.

RBA feeds were considered but returned HTTP 403 to the application client. Saxo
Trade Views was removed because its newest item was from 2020. A Bank of Canada
working-paper URL was removed because it returned an empty feed. Sources that
cannot be acquired correctly are not kept merely to make the list longer.

The official feed indexes are:

- [ECB RSS feeds](https://www.ecb.europa.eu/home/html/rss.en.html)
- [Federal Reserve RSS feeds](https://www.federalreserve.gov/feeds/feeds.htm)
- [BIS RSS feeds](https://www.bis.org/rss/index.htm)
- [Bank of Canada RSS feeds](https://www.bankofcanada.ca/rss-feeds/)
- [BNP Paribas Economic Research RSS](https://economic-research.bnpparibas.com/RSS/en-US/)
- [Saxo RSS feeds](https://www.home.saxo/insights/content-hub/rss)

## Podcasts

Podcast feeds are preserved as disabled, explicit opt-ins. They are excluded from
routine testing to avoid downloads and paid transcription. Enabling them uses at
most the configured number of same-day episodes per feed and caches completed
transcripts.
