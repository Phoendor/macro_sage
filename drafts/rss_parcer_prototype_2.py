#!/usr/bin/env python3
"""
market_feeds_on_dates.py
────────────────────────
Poll a curated list of macro/markets research feeds and report every item
whose calendar date matches one of the hard-wired DATES tuples.

• 100 % self-contained: change FEEDS or DATES inside this file only.
• Prints   ### <feed-name> (N)   blocks with bullet-list URLs.
• Appends a summary of feeds that delivered no matching items, with reason.

Requires:  requests  feedparser      →  pip install requests feedparser
"""

from __future__ import annotations
import datetime as dt, ssl, textwrap, requests, feedparser, re, time, sys

# ──────────────────────────────────────────────────────────────────
# EDIT THESE TWO CONSTANTS WHENEVER YOU LIKE
# ──────────────────────────────────────────────────────────────────
DATES: list[tuple[int, int, int]] = [        # (YYYY, MM, DD)
    (2024, 4, 8),
    (2025, 4, 28),
    (2025, 5, 1),
    (2025, 5, 2),
    (2025, 5, 3),
    (2025, 5, 4),
    (2025, 5, 5),
    (2025, 5, 6),
    (2025, 5, 7),
    (2025, 5, 8),
    (2025, 5, 9),
    (2025, 5, 10),
    (2025, 5, 11),
    (2025, 5, 12),
    (2025, 5, 13),
    (2025, 5, 14),
    (2025, 5, 15),
    (2025, 5, 16),
    (2025, 5, 17),
    (2025, 5, 18),
    (2025, 5, 19),
    (2025, 5, 20),
    (2025, 5, 21),
    (2025, 5, 22),
    (2025, 5, 29),
]

FEEDS: dict[str, str] = {
    # ---------- ARTICLES ----------
    "Saxo – Articles":   "https://www.home.saxo/insights/content-hub/rss/articles",
    "Saxo - Trade views": "https://www.home.saxo/insights/content-hub/rss/trade-views",
    "ING Think":         "https://think.ing.com/rss/",
    "BNP Paribas – Eco-Week": "https://economic-research.bnpparibas.com/RSS/en-US/Eco-Week",
    "BNP Paribas – Eco-Flash": "https://economic-research.bnpparibas.com/RSS/en-US/Eco-Flash",
    "BNP Paribas – Eco-Perspectives": "https://economic-research.bnpparibas.com/RSS/en-US/Eco-Perspectives",
    "BNP Paribas – Eco-Insight": "https://economic-research.bnpparibas.com/RSS/en-US/Eco-Insight",
    "Bank of China – FX":    "https://pics.bankofchina.com/fimarkets/foreignx/rss.xml",
    "BIS – Statistics": "https://data.bis.org/feed.xml",
    # ---------- PODCASTS ----------
    "Saxo – Market Call":                           "https://feed.podbean.com/saxostrats/feed.xml",
    "J.P. Morgan – At Any Rate":                    "https://feed.podbean.com/atanyrate/feed.xml",
    "J.P. Morgan – Global Data Pod":                "https://feed.podbean.com/globaldatapod/feed.xml",
    "J.P. Morgan - Making Sense":                   "https://feed.podbean.com/marketmatters/feed.xml",
    "J.P. Morgan - Notes on the week ahead":        "https://feed.podbean.com/notesontheweekahead/feed.xml",
    "Deutsche Bank - Weekly Investment Outlook":    "https://feeds.captivate.fm/cio-weekly-investment-o/",
    "Morgan Stanley – Thoughts on the Market":      "https://rss.art19.com/thoughts-on-the-market",
    "Goldman Sachs The Markets":                    "https://feeds.megaphone.fm/GLD9322922848",
    "HSBC – Macro Brief":                           "https://feeds.acast.com/public/shows/6476e27317ed970011e62580",
    "HSBC Global Viewpoint – Banking and Markets":  "https://feeds.acast.com/public/shows/5fb7d2326b6552292cd3e847",
    "Standard Chartered – Money Insights":          "https://feeds.buzzsprout.com/1662247.rss",
    "NatWest – Currency exchange":                  "https://feeds.buzzsprout.com/2109661.rss",
    "NatWest – Bondcast":                           "https://feeds.buzzsprout.com/1842617.rss",
    "Steno research - Macro Mondays":               "https://feeds.buzzsprout.com/2206288.rss",
    "Nordea Markets Insights":                      "https://feeds.soundcloud.com/users/soundcloud:users:180369357/sounds.rss",
    "Nordea DK – Insights":                         "https://feeds.soundcloud.com/users/soundcloud:users:417538800/sounds.rss",
    "SocGen – Ideas Daily":                         "https://sg-zertifikate.podcaster.de/ideas-boersennews-podcast.rss",
    "Macro Trading Floor":                          "https://feeds.megaphone.fm/ALFINVESTMENTSTRATEGYBV2974145286",
    "Macro Voices":                                 "https://feed.podbean.com/macrovoices/feed.xml",
    "Moody's – Inside Economics":                   "https://feeds.simplecast.com/4LZRim3c",
    "ideas Börsennews":                             "https://sg-zertifikate.podcaster.de/ideas-boersennews-podcast.rss",
    "Eurodollar University":                        "https://feeds.transistor.fm/making-sense",
    "Rosenberg Round-Up":                           "https://anchor.fm/s/ee8c6e5c/podcast/rss",
    "LPL Financial - Market Signals":               "https://feeds.soundcloud.com/users/soundcloud:users:355827665/sounds.rss",
    "Bank of America Global Research Unlocked":     "https://feed.podbean.com/bofaglobalresearch/feed.xml"

}
# Missing articles RSS: JP Morgan, Bank of China
# Missing podcasts:
# ──────────────────────────────────────────────────────────────────

UA   = {"User-Agent": "markets-rss-bot/4.0 (+https://example.com)"}
TLS  = ssl.create_default_context(); TLS.check_hostname = False; TLS.verify_mode = ssl.CERT_NONE
BAD  = re.compile(rb"[\x00-\x08\x0B\x0C\x0E-\x1F]")      # illegal XML chars
TARGETS: set[tuple[int, int, int]] = set(DATES)

def _get_clean_xml(url: str) -> bytes | None:
    try:
        r = requests.get(url, headers=UA, timeout=15)
        r.raise_for_status()
        if "xml" not in r.headers.get("content-type", ""):        # HTML or JSON → ignore
            return None
        return BAD.sub(b" ", r.content)
    except Exception:
        return None


def _matches(entry) -> bool:
    for fld in ("published_parsed", "updated_parsed", "created_parsed"):
        st = entry.get(fld)
        if st and (st.tm_year, st.tm_mon, st.tm_mday) in TARGETS:
            return True
    return False

def _best_link(e) -> str:
    # 1) prefer explicit HTML alternate links
    for ln in e.get("links", []):
        if ln.get("href") and ln.get("type", "").startswith("text/html"):
            return ln["href"]

    # 2) built-in .link, but skip obvious images
    ln = e.get("link")
    if ln and not ln.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp")):
        return ln

    # 3) first enclosure that ISN'T an image
    for enc in e.get("enclosures", []):
        if enc.get("href") and not enc.get("type", "").startswith("image"):
            return enc["href"]

    # 4) last-ditch fallback
    return str(e.get("id", "(no link)"))


def main():
    delivered, missing = {}, []

    for name, url in FEEDS.items():
        raw = _get_clean_xml(url)
        if not raw:
            missing.append((name, "feed unreachable or not XML"))
            continue

        feed = feedparser.parse(raw)
        items = [e for e in feed.entries if _matches(e)]

        if items:
            out = []
            for e in items:
                link = _best_link(e)
                out.append(f"- {textwrap.shorten(e.get('title', '(no title)'), 120, placeholder='…')}"
                               f"\n  {link}")
            if out:
                delivered[name] = out
        else:
            missing.append((name, "no entry with requested date(s)"))

    # -------- output --------
    for name, lines in delivered.items():
        print(f"\n### {name} ({len(lines)})")
        print("\n".join(lines))

    if missing:
        print("\n\n## Feeds with no data on the requested dates")
        for name, reason in missing:
            print(f"- {name} → {reason}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
