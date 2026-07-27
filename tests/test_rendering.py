from datetime import datetime, timezone

from macro_sage.models import DailyBrief, Document
from macro_sage.rendering import render_markdown


def test_markdown_contains_linked_attribution():
    document = Document(
        id="source:one",
        source_id="source",
        source_name="Source",
        publisher="Publisher",
        category="research",
        title="Research note",
        url="https://example.com/note",
        published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
        body="Body",
    )
    brief = DailyBrief(
        as_of_date="2026-07-27",
        executive_summary=["Summary"],
        macro_themes=[
            {
                "theme": "Growth",
                "market_implication": "A soft landing remains possible.",
                "source_ids": ["source:one"],
            }
        ],
        asset_views=[],
        top_risks=["Inflation"],
        source_ids_used=["source:one"],
    )

    output = render_markdown(brief, [document])

    assert "[Source: Research note](https://example.com/note)" in output
    assert "# Macro Sage — 2026-07-27" in output
