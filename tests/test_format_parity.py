import json
from datetime import datetime, timezone

from pypdf import PdfReader

from macro_sage.models import (
    DailyBriefV2,
    Document,
    SourceKind,
    SourceOutcome,
    SourceState,
)
from macro_sage.pdf import render
from macro_sage.rendering import render_markdown
from tests.helpers import v2_brief


def test_v2_json_markdown_and_pdf_preserve_decision_and_audit_content(tmp_path):
    brief = DailyBriefV2.model_validate(v2_brief(failed=1))
    document = Document(
        id="doc:one",
        source_id="fixture",
        source_name="Fixture Source",
        publisher="Fixture Publisher",
        category="research",
        title="Fixture evidence",
        url="https://example.com/evidence",
        published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
        body="Private fixture body.",
    )
    failure = SourceOutcome(
        "broken",
        "Broken Source",
        SourceKind.ARTICLE,
        SourceState.FAILED,
        detail="HTTP 404",
    )
    brief_path = tmp_path / "brief.json"
    manifest_path = tmp_path / "manifest.json"
    run_path = tmp_path / "run.json"
    pdf_path = tmp_path / "brief.pdf"
    brief_path.write_text(brief.model_dump_json(indent=2), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "id": document.id,
                        "source_name": document.source_name,
                        "publisher": document.publisher,
                        "title": document.title,
                        "url": document.url,
                        "media_type": document.media_type,
                    }
                ],
                "errors": [failure.summary()],
                "skipped": [],
            }
        ),
        encoding="utf-8",
    )
    run_path.write_text(
        json.dumps({"model": "gpt-5.6-luna", "health": "degraded"}),
        encoding="utf-8",
    )

    markdown = render_markdown(brief, [document], [failure])
    render(brief_path, manifest_path, run_path, pdf_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(pdf_path).pages)
    json_value = json.loads(brief_path.read_text(encoding="utf-8"))
    manifest_value = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert json_value["what_changed"][0]["headline"] == "Policy signal changed"
    assert json_value["asset_views"][0]["asset"] == "EUR/USD"
    assert json_value["source_ids_used"] == ["doc:one"]
    assert manifest_value["errors"] == [failure.summary()]
    for output in (markdown, pdf_text):
        assert "Policy signal changed" in output
        assert "EUR/USD" in output
        assert "No timestamped market data" in output
        assert "Fixture Publisher: Fixture evidence" in output
        assert "Broken Source" in output
