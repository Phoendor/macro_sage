import get_data
from bs4 import BeautifulSoup
import json


def parse_ing_think_article(html_source: str):
    """
    Parses an ING Think article HTML string, extracting:
      - Title
      - Publish date
      - Authors
      - Overall introduction text
      - An ordered list of sub-sections, each with a heading and paragraphs
      - Meta description
    Returns a dict of results.
    """
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
        ld_author = [a["name"] for a in ld_author if "name" in a]

    # ---------------------------------------------------------
    # 5) AUTHORS FROM HTML
    # ---------------------------------------------------------
    # Grab authors from the "card_author" blocks
    author_cards = soup.find_all("a", class_="card_author")
    authors = []
    for card in author_cards:
        title_div = card.find("div", class_="card-title")
        if title_div:
            authors.append(title_div.get_text(strip=True))

    # Fallback to JSON-LD if not found in HTML
    if not authors and ld_author:
        # ld_author might be a string or list
        if isinstance(ld_author, str):
            # Could be multiple authors in one string, separated by commas:
            if "," in ld_author:
                authors = [a.strip() for a in ld_author.split(",")]
            else:
                authors = [ld_author.strip()]
        elif isinstance(ld_author, list):
            authors = ld_author

    # ---------------------------------------------------------
    # 6) INTRO TEXT (FS-LARGER)
    # ---------------------------------------------------------
    # Often there's a short summary/intro in <div class="fs-larger">
    intro_div = soup.find("div", class_="fs-larger")
    intro_text = intro_div.get_text(strip=True) if intro_div else ""

    # ---------------------------------------------------------
    # 7) PARAGRAPH TITLES + CONTENT
    # ---------------------------------------------------------
    # The main article sections appear in <div class="row content_wrapper"> blocks.
    # Inside each, we have:
    #   <h4 class="mt-1">Subheading</h4>
    #   <span class="fs-large"><p>Paragraph 1...</p> <p>Paragraph 2...</p></span>
    # We’ll parse them into a list of {"heading": ..., "paragraphs": [...]}
    sections_data = []
    content_wrappers = soup.find_all("div", class_="content_wrapper")

    for wrapper in content_wrappers:
        # Get the heading
        heading_tag = wrapper.find("h4")
        heading = heading_tag.get_text(strip=True) if heading_tag else None

        # Get the paragraphs. They might be in <span class="fs-large"> or directly under this div, so we’ll
        # do a broad approach: find all <p> in the wrapper.
        paragraphs = []
        for p in wrapper.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)

        # Store them if we found a heading or paragraphs
        if heading or paragraphs:
            sections_data.append({
                "heading": heading,
                "paragraphs": paragraphs
            })

    # ---------------------------------------------------------
    # BUILD THE FINAL DICTIONARY
    # ---------------------------------------------------------
    return {
        "title": final_title or ld_title,
        "description": description or ld_description,
        "date_published": date_published or ld_date_published,
        "authors": authors,
        "intro_text": intro_text,
        "sections": sections_data
    }


if __name__ == "__main__":
    # Either load a local HTML file...
    # with open("example.html", "r", encoding="utf-8") as f:
    #     html_content = f.read()

    # ...or fetch from the live URL
    url = "https://think.ing.com/articles/the-commodities-feed-cpi-data-weighs-on-parts-of-the-complex110424/"
    response = requests.get(url)
    html_content = response.text

    data = parse_ing_think_article(html_content)

    print("TITLE:", data["title"])
    print("PUBLISHED DATE:", data["date_published"])
    print("AUTHORS:", data["authors"])
    print("META DESCRIPTION:", data["description"])
    print("--- INTRO TEXT ---")
    print(data["intro_text"])
    print("--- SECTIONS ---")
    for section in data["sections"]:
        print("HEADING:", section["heading"])
        print("PARAGRAPHS:")
        for para in section["paragraphs"]:
            print("  -", para)
        print()
