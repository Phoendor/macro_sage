# Source catalog

This is the human-readable catalog for every source in `config/sources.toml`.
Article sources are enabled. Podcast sources are opt-in because transcription has
a direct cost. The catalog is checked by the test suite so a configured source
cannot be added or removed without updating this file.

Frequency labels use three kinds of evidence:

- **O (observed):** cadence visible in the feed history checked on 2026-07-27.
- **I (implicit):** cadence stated by the series name or publisher schedule.
- **E (expected):** event-driven cadence where a fixed schedule would be misleading.

These are practical monitoring expectations, not publisher guarantees.

## Enabled text sources

| ID | Source | Publication frequency | Links | What it is | Why I need it |
|---|---|---|---|---|---|
| `ing-think` | ING Think | O: most weekdays | [Feed](https://think.ing.com/rss/) · [Home](https://think.ing.com/) | Global bank economics, rates, FX and sector research. | Fast, tradable interpretation across Europe and global markets. |
| `saxo-articles` | Saxo Market Insights | O: most weekdays | [Feed](https://www.home.saxo/insights/content-hub/rss/articles) · [Home](https://www.home.saxo/insights/) | Market strategy and cross-asset commentary. | Adds concise investor framing and market implications. |
| `bnp-eco-week` | BNP Paribas EcoWeek | I: weekly | [Feed](https://economic-research.bnpparibas.com/RSS/en-US/Eco-Week) · [Home](https://economic-research.bnpparibas.com/) | Weekly macroeconomic review from BNP Paribas economists. | A regular European bank baseline for the global cycle. |
| `bnp-eco-flash` | BNP Paribas EcoFlash | E: around important data and events | [Feed](https://economic-research.bnpparibas.com/RSS/en-US/Eco-Flash) · [Home](https://economic-research.bnpparibas.com/) | Short, event-led economic analysis. | Captures quick interpretation when data or policy changes. |
| `bnp-eco-perspectives` | BNP Paribas EcoPerspectives | I: quarterly | [Feed](https://economic-research.bnpparibas.com/RSS/en-US/Eco-Perspectives) · [Home](https://economic-research.bnpparibas.com/) | Country outlooks and medium-term forecasts. | Anchors daily news in a slower-moving country outlook. |
| `bnp-eco-insight` | BNP Paribas EcoInsight | E: irregular | [Feed](https://economic-research.bnpparibas.com/RSS/en-US/Eco-Insight) · [Home](https://economic-research.bnpparibas.com/) | Deeper thematic macro research. | Supplies structural context that daily market notes often omit. |
| `ecb-blog` | ECB Blog | O: several per month | [Feed](https://www.ecb.europa.eu/rss/blog.html) · [Home](https://www.ecb.europa.eu/press/blog/html/index.en.html) | Accessible analysis by ECB officials and staff. | Explains euro-area policy priorities in the institution’s own words. |
| `ecb-press` | ECB Press, Speeches and Interviews | O: several per week | [Feed](https://www.ecb.europa.eu/rss/press.html) · [RSS index](https://www.ecb.europa.eu/home/html/rss.en.html) | Official ECB decisions, speeches and interviews. | Primary evidence for euro rates, guidance and policy reaction functions. |
| `fed-press` | Federal Reserve Press Releases | O: several per week | [Feed](https://www.federalreserve.gov/feeds/press_all.xml) · [RSS index](https://www.federalreserve.gov/feeds/feeds.htm) | Official Board decisions, statements and regulatory releases. | The authoritative source for changes affecting US monetary policy. |
| `fed-speeches` | Federal Reserve Speeches | O: several per week | [Feed](https://www.federalreserve.gov/feeds/speeches.xml) · [Home](https://www.federalreserve.gov/newsevents/speeches.htm) | Speeches and testimony by Federal Reserve governors. | Reveals policy reasoning, disagreement and changes in emphasis. |
| `fed-notes` | FEDS Notes | O: roughly 1–3 per week | [Feed](https://www.federalreserve.gov/feeds/feds_notes.xml) · [Home](https://www.federalreserve.gov/econres/notes/feds-notes/default.htm) | Timely applied research by Federal Reserve staff. | Adds evidence behind US macro and financial-stability debates. |
| `bis-research` | BIS Research Hub | O: several per week | [Feed](https://www.bis.org/doclist/reshub_papers.rss) · [Home](https://www.bis.org/topic/research.htm) | Cross-country monetary, banking and market research. | Provides international comparisons and system-level risk analysis. |
| `bis-speeches` | BIS Central Bank Speeches | O: most weekdays | [Feed](https://www.bis.org/doclist/cbspeeches.rss) · [RSS index](https://www.bis.org/rss/index.htm) | Aggregated speeches from central banks worldwide. | Broadens policy coverage beyond the individually configured G10 banks. |
| `boc-news` | Bank of Canada News | O: several per week | [Feed](https://www.bankofcanada.ca/utility/news/feed/) · [RSS index](https://www.bankofcanada.ca/rss-feeds/) | Official Bank of Canada announcements and publications. | Covers CAD-sensitive policy and Canadian financial conditions. |
| `boc-speeches` | Bank of Canada Speeches | E: several per month | [Feed](https://www.bankofcanada.ca/content_type/speeches/feed/) · [Home](https://www.bankofcanada.ca/press/speeches/) | Speeches by Bank of Canada leaders. | Adds the reasoning and risks behind Canadian policy decisions. |
| `boc-sparks` | Sparks at the Bank | E: irregular | [Feed](https://www.bankofcanada.ca/content_type/sparks-at-bank-article/feed/) · [Home](https://www.bankofcanada.ca/) | Accessible research stories from Bank of Canada staff. | Surfaces useful empirical work without requiring a full working paper. |
| `nyfed-liberty-street` | Liberty Street Economics | O: roughly 2–4 per week | [Feed](https://libertystreeteconomics.newyorkfed.org/feed/) · [Home](https://libertystreeteconomics.newyorkfed.org/) | NY Fed research on markets, banking and the real economy. | Particularly useful for market plumbing, credit and inflation detail. |
| `boe-speeches` | Bank of England Speeches | O: roughly 1–3 per week | [Feed](https://www.bankofengland.co.uk/rss/speeches) · [RSS index](https://www.bankofengland.co.uk/rss) | Speeches by MPC, FPC and Bank leaders. | Primary evidence for UK rates, sterling and financial-stability views. |
| `boe-bank-insights` | Bank Insights | O: roughly 1–3 per week | [Feed](https://www.bankofengland.co.uk/rss/bank-insights) · [Home](https://www.bankofengland.co.uk/bank-overground) | Short analytical pieces using Bank of England data and research. | Adds timely UK evidence between formal policy publications. |
| `boe-publications` | Bank of England Publications | O: several per week | [Feed](https://www.bankofengland.co.uk/rss/publications) · [Latest](https://www.bankofengland.co.uk/news/latest-and-upcoming) | Working papers and flagship policy or stability publications. | Supplies full official reports; the collector follows the publication PDF. |
| `snb-monetary-policy` | SNB Monetary Policy Publications | I: quarterly plus policy decisions | [Feed](https://www.snb.ch/public/rss/en/mopo) · [RSS index](https://www.snb.ch/en/services-events/digital-services/rss-calendar-feeds) | Quarterly Bulletins and monetary-policy material. | Covers CHF policy, inflation and the SNB’s distinctive FX considerations. |
| `snb-speeches` | Swiss National Bank Speeches | O: roughly 1–3 per month | [Feed](https://www.snb.ch/public/rss/en/speeches) · [Home](https://www.snb.ch/en/publications/communication/speeches) | Speeches by SNB Governing Board members. | Adds nuance around Swiss policy and financial-system risks. |
| `norges-speeches` | Norges Bank Speeches | E: several per month | [Feed](https://www.norges-bank.no/en/rss-feeds/Speeches---Norges-Bank/) · [RSS index](https://www.norges-bank.no/en/rss-feeds/) | Speeches and policy remarks from Norway’s central bank. | Covers NOK rates and oil-sensitive Nordic macro conditions. |
| `norges-monetary-policy` | Norges Bank Monetary Policy Report | I: quarterly | [Feed](https://www.norges-bank.no/en/rss-feeds/Norges-Bank-Monetary-Policy-Report-with-financial-stability-assessment/) · [Home](https://www.norges-bank.no/en/topics/Monetary-policy/Monetary-Policy-Report-with-financial-stability-assessment/) | Forecasts, rate path and financial-stability assessment. | Gives the complete Norwegian reaction function and forecast baseline. |
| `norges-regional-network` | Norges Bank Regional Network Reports | I: quarterly | [Feed](https://www.norges-bank.no/en/rss-feeds/Regional-network-reports---Norges-Bank/) · [Home](https://www.norges-bank.no/en/topics/Research/Regional-network/) | Survey-based intelligence from Norwegian businesses. | Adds current activity and capacity signals before hard data arrive. |
| `riksbank-speeches` | Sveriges Riksbank Speeches | E: several per month | [Feed](https://www.riksbank.se/en-gb/rss/speeches/) · [RSS index](https://www.riksbank.se/en-gb/press-and-published/subscribe-via-rss/) | English-language speeches and presentations by Riksbank officials. | Covers SEK policy and another important European inflation regime. |
| `riksbank-minutes` | Riksbank Monetary Policy Minutes | E: after monetary-policy meetings | [Feed](https://www.riksbank.se/en-gb/rss/minutes-of-the-executive-boards-monetary-policy-meetings/) · [Home](https://www.riksbank.se/en-gb/press-and-published/minutes-of-the-executive-boards-monetary-policy-meetings/) | Full English minutes of Executive Board policy meetings. | Shows vote-level reasoning and disagreement not visible in headlines. |
| `sf-fed-economic-letter` | FRBSF Economic Letter | O: roughly 2–4 per month | [Feed](https://www.frbsf.org/economic-research/economic-letter-rss-feed/) · [Home](https://www.frbsf.org/research-and-insights/publications/economic-letter/) | Concise, policy-relevant Federal Reserve research. | Adds rigorous work on inflation, labor and the US cycle. |
| `sf-fed-fedviews` | SF FedViews | I: approximately monthly | [Feed](https://www.frbsf.org/economic-research/fedviews-rss-feed/) · [Home](https://www.frbsf.org/research-and-insights/publications/fedviews/) | Staff assessment of current US economic conditions. | Provides a recurring, comparable US outlook snapshot. |
| `boj-policy-research` | Bank of Japan Policy and Research Updates | E: irregular, several per month | [Feed](https://www.boj.or.jp/en/rss/whatsnew.xml) · [Home](https://www.boj.or.jp/en/) | BOJ policy, regional outlook and research items selected from its broad feed. | Adds JPY and Japan coverage while filtering spreadsheets and routine statistics. |
| `bruegel-analysis` | Bruegel Analysis and Events | O: several per week | [Feed](https://www.bruegel.org/rss.xml) · [Home](https://www.bruegel.org/) | Independent European economic-policy research and expert discussions. | Adds non-central-bank analysis on EU fiscal, trade and structural policy. |
| `nber-working-papers` | New NBER Working Papers | I: weekly Monday batch | [Feed](https://www.nber.org/rss/new.xml) · [Home](https://www.nber.org/papers) | Abstracts for newly released economics working papers. | Surfaces new empirical results; the feed provides abstracts rather than paywalled PDFs. |

## Opt-in audio sources

Audio feeds are cataloged and feed-validated, but remain disabled by default.
`macro-sage validate-sources --include-podcasts` checks their RSS enclosures
without downloading audio or paying for transcription.

| ID | Source | Publication frequency | Links | What it is | Why I need it |
|---|---|---|---|---|---|
| `pod-jpm-at-any-rate` | J.P. Morgan At Any Rate | O: roughly weekly | [Feed](https://feed.podbean.com/atanyrate/feed.xml) · [J.P. Morgan podcasts](https://www.jpmorgan.com/insights/podcast-hub) | Markets and macro conversations with J.P. Morgan researchers. | Adds desk-level rates, FX and macro interpretation. |
| `pod-jpm-global-data` | J.P. Morgan Global Data Pod | O: one or more per week | [Feed](https://feed.podbean.com/globaldatapod/feed.xml) · [J.P. Morgan podcasts](https://www.jpmorgan.com/insights/podcast-hub) | Global economics discussions from J.P. Morgan Research. | A direct audio counterpart to a global bank economics team. |
| `pod-morgan-stanley` | Morgan Stanley Thoughts on the Market | O: most weekdays | [Feed](https://rss.art19.com/thoughts-on-the-market) · [Home](https://www.morganstanley.com/insights/podcasts/thoughts-on-the-market) | Short daily market and economics commentary. | Useful for timely consensus, disagreement and asset implications. |
| `pod-goldman-markets` | Goldman Sachs The Markets | O: roughly weekly | [Feed](https://feeds.megaphone.fm/GLD9322922848) · [Home](https://www.goldmansachs.com/insights/goldman-sachs-exchanges) | Conversations on major market moves and investor questions. | Adds institutional market color across asset classes. |
| `pod-hsbc-macro` | HSBC Macro Brief | O: roughly 1–2 per week | [Feed](https://feeds.acast.com/public/shows/6476e27317ed970011e62580) · [HSBC podcasts](https://www.gbm.hsbc.com/en-gb/insights/global-viewpoint) | Short global and regional macro briefings. | Adds strong UK, Europe and Asia-oriented bank research. |
| `pod-macro-voices` | Macro Voices | I: weekly | [Feed](https://feed.podbean.com/macrovoices/feed.xml) · [Home](https://www.macrovoices.com/) | Long-form interviews with macro investors and specialists. | Captures investable theses and informed non-consensus views. |
| `pod-moodys-economics` | Moody’s Inside Economics | O: roughly weekly | [Feed](https://feeds.simplecast.com/4LZRim3c) · [Home](https://www.economy.com/economicview) | Economist panel on current US and global data. | Adds a data-heavy forecasting perspective and explicit debate. |
| `pod-bofa-research` | BofA Global Research Unlocked | O: roughly weekly | [Feed](https://feed.podbean.com/bofaglobalresearch/feed.xml) · [Home](https://business.bofa.com/en-us/content/global-research-podcasts.html) | Public conversations with Bank of America research strategists. | Broadens bank research coverage without relying on client-only notes. |
| `pod-saxo-market-call` | Saxo Market Call | O: weekdays while in season | [Feed](https://feed.podbean.com/saxostrats/feed.xml) · [Home](https://www.home.saxo/insights/podcasts) | Short cross-asset morning market calls. | Provides fast daily positioning and catalyst context. |
| `pod-jpm-making-sense` | J.P. Morgan Making Sense | O: roughly weekly | [Feed](https://feed.podbean.com/marketmatters/feed.xml) · [Home](https://www.jpmorgan.com/insights/podcast-hub/making-sense) | Markets, research and geopolitical conversations. | Adds specialist coverage where macro, commodities and geopolitics meet. |
| `pod-jpm-week-ahead` | Notes on the Week Ahead | I: weekly, usually Monday | [Feed](https://feed.podbean.com/notesontheweekahead/feed.xml) · [Home](https://am.jpmorgan.com/us/en/asset-management/adv/insights/market-insights/market-updates/notes-on-the-week-ahead/) | David Kelly’s weekly economic and market outlook. | Gives a stable weekly baseline for US growth and asset allocation. |
| `pod-deutsche-weekly` | Deutsche Bank PERSPECTIVES Weekly | I: weekly, usually Monday | [Feed](https://feeds.captivate.fm/cio-weekly-investment-o/) · [Home](https://www.deutsche-bank.com/what-we-do/wealth-management/cio-special) | CIO discussion of the week’s data, policy and markets. | Adds a European global-investment-house perspective. |
| `pod-macro-trading-floor` | The Macro Trading Floor | O: roughly 1–2 per month | [Feed](https://feeds.megaphone.fm/ALFINVESTMENTSTRATEGYBV2974145286) · [Home](https://www.realvision.com/podcast/the-macro-trading-floor) | Practitioner discussion of macro regimes and trades. | Adds explicit portfolio construction and trade-expression thinking. |
| `pod-imf` | IMF Podcasts | O: roughly 2–4 per month | [Feed](https://imfpodcast.libsyn.com/rss) · [Home](https://www.imf.org/en/news/podcasts) | Interviews on IMF research and global economic policy. | Adds authoritative global and emerging-market context in accessible form. |
| `pod-macro-musings` | Macro Musings | I: weekly, usually Monday | [Feed](https://macromusings.libsyn.com/rss) · [Home](https://www.mercatus.org/macro-musings) | Long-form monetary economics interviews hosted by David Beckworth. | Deepens understanding of central banking, money and financial plumbing. |
| `pod-bloomberg-odd-lots` | Bloomberg Odd Lots | O: roughly 3–5 per week | [Feed](https://www.omnycontent.com/d/playlist/e73c998e-6e60-432f-8610-ae210140c5b1/8a94442e-5a74-4fa2-8b8d-ae27003a8d6b/982f5071-765c-403d-969d-ae27003a8d83/podcast.rss) · [Home](https://www.bloomberg.com/originals/series/odd-lots) | Deep dives into market structure, economics and unusual price signals. | Adds specialist explanations of mechanisms that headline research can miss; sponsored episodes are filtered. |

## Known gaps

The Reserve Bank of Australia and Reserve Bank of New Zealand are reputable and
would fit editorially, but their feeds returned HTTP 403 to the application client
on 2026-07-27. IMF Blog and CEPR/VoxEU feeds were also rejected by their edge
services, and the FT Unhedged feed returned HTTP 410. They are intentionally not
configured until they can be acquired reliably. The broad BOJ feed is retained
with a URL allow-list so routine statistics and spreadsheet releases never enter
the text pipeline.
