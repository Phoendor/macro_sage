import json

import requests
from bs4 import BeautifulSoup


def parse_ING(url: str):
    """
    Fetches an ING Think article from the given URL and parses out:
      - Title
      - Publish date
      - Authors
      - Intro text
      - A list of sections (each with 'heading' and 'paragraphs')
      - Meta description

    Returns a dictionary with the extracted data.
    """
    # 1) Fetch the HTML from the URL
    response = requests.get(url)
    html_source = response.text

    soup = BeautifulSoup(html_source, "html.parser")

    # ---------------------------------------------------------
    # 1) GET ARTICLE TITLE
    # ---------------------------------------------------------
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else None

    # Fallback to og:title if needed
    og_title = soup.find("meta", property="og:title")
    og_title = og_title.get("content") if og_title else None
    final_title = og_title or page_title

    # ---------------------------------------------------------
    # 2) GET META DESCRIPTION
    # ---------------------------------------------------------
    meta_desc = soup.find("meta", attrs={"name": "description"})
    description = meta_desc.get("content") if meta_desc else None

    # ---------------------------------------------------------
    # 3) GET PUBLISH DATE
    # ---------------------------------------------------------
    meta_date_published = soup.find("meta", attrs={"name": "date_published"})
    date_published = meta_date_published.get("content") if meta_date_published else None

    # ---------------------------------------------------------
    # 4) PARSE JSON-LD STRUCTURED DATA
    # ---------------------------------------------------------
    article_json_data = {}
    json_ld_scripts = soup.find_all("script", {"type": "application/ld+json"})
    for script_tag in json_ld_scripts:
        try:
            data = json.loads(script_tag.string)
            # The data can be a dict or a list of dicts
            if isinstance(data, dict) and data.get("@type") == "Article":
                article_json_data = data
                break
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Article":
                        article_json_data = item
                        break
        except (json.JSONDecodeError, TypeError):
            pass

    ld_title = article_json_data.get("headline")
    ld_description = article_json_data.get("description")
    ld_date_published = article_json_data.get("datePublished")
    ld_author = article_json_data.get("author")
    # The "author" field can be dict or list. Grab the name(s).
    if isinstance(ld_author, dict):
        ld_author = ld_author.get("name")
    elif isinstance(ld_author, list):
        ld_author = [a.get("name") for a in ld_author if "name" in a]

    # ---------------------------------------------------------
    # 5) AUTHORS FROM HTML
    # ---------------------------------------------------------
    author_cards = soup.find_all("a", class_="card_author")
    authors = []
    for card in author_cards:
        title_div = card.find("div", class_="card-title")
        if title_div:
            authors.append(title_div.get_text(strip=True))

    # Fallback to JSON-LD if not found in HTML
    if not authors and ld_author:
        if isinstance(ld_author, str):
            # Could be multiple authors in one string, separated by commas
            if "," in ld_author:
                authors = [a.strip() for a in ld_author.split(",")]
            else:
                authors = [ld_author.strip()]
        elif isinstance(ld_author, list):
            authors = ld_author

    # ---------------------------------------------------------
    # 6) INTRO TEXT (FS-LARGER)
    # ---------------------------------------------------------
    intro_div = soup.find("div", class_="fs-larger")
    intro_text = intro_div.get_text(strip=True) if intro_div else ""

    # ---------------------------------------------------------
    # 7) PARAGRAPH TITLES + CONTENT
    # ---------------------------------------------------------
    sections_data = []
    content_wrappers = soup.find_all("div", class_="content_wrapper")

    for wrapper in content_wrappers:
        # Get the heading
        heading_tag = wrapper.find("h4")
        heading = heading_tag.get_text(strip=True) if heading_tag else None

        # Get the paragraphs
        paragraphs = []
        for p in wrapper.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)

        if heading or paragraphs:
            sections_data.append({
                "heading": heading,
                "paragraphs": paragraphs
            })

    # ---------------------------------------------------------
    # BUILD A SINGLE STRING WITH ALL INFO
    # ---------------------------------------------------------
    # Fallback values if the JSON-LD or meta tags were missing
    merged_title = final_title or ld_title or ""
    merged_date = date_published or ld_date_published or ""
    merged_desc = description or ld_description or ""

    # Combine authors into a textual representation
    authors_str = ", ".join(authors) if authors else ""

    # Now build the textual output, similar to your original console print.
    text_chunks = []
    text_chunks.append(f"TITLE: {merged_title}")
    text_chunks.append(f"PUBLISHED DATE: {merged_date}")
    text_chunks.append(f"AUTHORS: {authors_str}")
    text_chunks.append(f"META DESCRIPTION: {merged_desc}")
    text_chunks.append("--- INTRO TEXT ---")
    text_chunks.append(intro_text)
    text_chunks.append("--- SECTIONS ---")

    for section in sections_data:
        heading = section["heading"] or ""
        paragraphs = section["paragraphs"]
        text_chunks.append(f"HEADING: {heading}")
        text_chunks.append("PARAGRAPHS:")
        for paragraph in paragraphs:
            text_chunks.append(f"  - {paragraph}")
        text_chunks.append("")  # blank line between sections

    # Join them all with newlines
    text_output = "\n".join(text_chunks)

    return text_output
