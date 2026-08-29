from datetime import datetime, timezone

from macro_sage.history import (
    AssetViewChange,
    BaselineStatus,
    BriefComparison,
    ChangeStatus,
)
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


def test_markdown_distinguishes_current_change_evidence_from_history():
    document = Document(
        id="source:one",
        source_id="source",
        source_name="Source",
        publisher="Publisher",
        category="research",
        title="Current note",
        url="https://example.com/current",
        published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
        body="Body",
    )
    brief = DailyBrief(
        as_of_date="2026-07-27",
        executive_summary=[],
        macro_themes=[],
        asset_views=[],
        top_risks=[],
        source_ids_used=["source:one"],
    )
    comparison = BriefComparison(
        baseline_status=BaselineStatus.AVAILABLE,
        baseline_detail="Compared with yesterday.",
        previous_run_id="previous",
        previous_date="2026-07-24",
        asset_view_changes=[
            AssetViewChange(
                key="asset-view:fx:eur-usd:short_term",
                status=ChangeStatus.REVERSED,
                asset="EUR/USD",
                horizon="one week",
                previous_bias="bullish",
                current_bias="bearish",
                previous_confidence=3,
                current_confidence=4,
                current_source_document_ids=["source:one"],
                historical_source_document_ids=["historical:one"],
                first_seen_date="2026-07-20",
                last_updated_date="2026-07-27",
                expected_expiry_date="2026-08-10",
                explanation="Bias reversed on current evidence.",
            )
        ],
    )

    output = render_markdown(brief, [document], comparison=comparison)

    assert "**reversed: EUR/USD**" in output
    assert "Current evidence: [Source: Current note]" in output
    assert "historical:one" not in output
