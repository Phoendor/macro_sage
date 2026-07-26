#!/usr/bin/env python3
"""crawl_jpm_markets.py – dump all JPM markets/outlook articles to a CSV"""
import datetime as dt, gzip, io, sqlite3, sys, xml.etree.ElementTree as ET
from pathlib import Path

import requests, pandas as pd
from bs4 import BeautifulSoup

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# -- TWO root sitemaps: corporate + private-bank --------------------
ROOT_SITEMAPS = (
    "https://www.jpmorgan.com/sitemap.xml",
    "https://privatebank.jpmorgan.com/sitemap.xml",
)

DB_FILE = Path(__file__).with_suffix(".sqlite")

# -- 1. Requests session with browser-ish headers -------------------
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml, application/rss+xml;q=0.9, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8",
})

# -- 2.  Fetch & transparently decompress every sitemap -------------
def _fetch_sitemap_text(url: str) -> str:
    r = SESSION.get(url, timeout=30, allow_redirects=True)
    r.raise_for_status()
    raw = r.content

    # gzip if (a) file name ends with .gz  OR  (b) server sets gzip encoding
    if url.endswith(".gz") or r.headers.get("content-encoding", "") == "gzip":
        raw = gzip.decompress(raw)

    return raw.decode("utf-8", errors="replace")

def iter_sitemap_urls(url: str):
    """Recursively yield every <loc> entry from *all* sitemap levels."""
    xml = _fetch_sitemap_text(url)
    root = ET.fromstring(xml)

    if root.tag.endswith("sitemapindex"):
        for loc in root.findall(".//sm:loc", NS):
            yield from iter_sitemap_urls(loc.text.strip())
    else:  # <urlset>
        for loc in root.findall(".//sm:loc", NS):
            yield loc.text.strip()

# -- 3.  Article filter covers BOTH markets paths -------------------
ARTICLE_PATTERNS = (
    "/insights/outlook/market-outlook/",
    "/insights/markets-and-investing/",
)

def iter_market_articles():
    seen = set()
    for root in ROOT_SITEMAPS:
        for url in iter_sitemap_urls(root):
            # normalise double slashes after the domain
            url = url.replace("://", "://").replace("//insights", "/insights")
            if not any(p in url for p in ARTICLE_PATTERNS):
                continue
            # skip section landing pages
            if any(url.rstrip("/").endswith(p.rstrip("/")) for p in ARTICLE_PATTERNS):
                continue
            if url not in seen:
                seen.add(url)
                yield url

# -- 4.  Everything below is unchanged ------------------------------
def fetch_title(url):
    html = SESSION.get(url, timeout=30).text
    h1 = BeautifulSoup(html, "lxml").find("h1")
    return h1.get_text(strip=True) if h1 else "N/A"

def ensure_schema(cx):
    cx.execute("""CREATE TABLE IF NOT EXISTS articles(
                     url TEXT PRIMARY KEY,
                     title TEXT,
                     first_seen TEXT
                 )""")

def main():
    cx = sqlite3.connect(DB_FILE)
    ensure_schema(cx)
    cur = cx.cursor()
    new_rows = []

    for url in iter_market_articles():
        if cur.execute("SELECT 1 FROM articles WHERE url=?", (url,)).fetchone():
            continue
        title = fetch_title(url)
        cur.execute("INSERT INTO articles VALUES (?,?,?)",
                    (url, title, dt.datetime.utcnow().isoformat()))
        new_rows.append((title, url))

    cx.commit()
    if new_rows:
        print(f"Added {len(new_rows)} new rows:")
        for t, u in new_rows:
            print(f"  • {t[:70]:70}  {u}")
    else:
        print("No new articles found.")

if __name__ == "__main__":
    sys.exit(main())
