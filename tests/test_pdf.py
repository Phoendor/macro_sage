import json

from pypdf import PdfReader

from macro_sage.pdf import render, render_technical
from tests.helpers import v2_brief


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _render(tmp_path, brief, documents, *, run_extra=None):
    brief_path = tmp_path / "brief.json"
    documents_path = tmp_path / "documents.json"
    run_path = tmp_path / "run.json"
    output_path = tmp_path / "brief.pdf"
    _write_json(brief_path, brief)
    _write_json(documents_path, {"documents": documents, "errors": [], "skipped": []})
    run = {
        "model": "gpt-5.6-luna",
        "input_tokens": 100,
        "output_tokens": 50,
    }
    run.update(run_extra or {})
    _write_json(run_path, run)
    render(brief_path, documents_path, run_path, output_path)
    return [page.extract_text() for page in PdfReader(output_path).pages]


def _render_technical(tmp_path, brief, manifest, *, run_extra=None):
    brief_path = tmp_path / "technical-brief.json"
    documents_path = tmp_path / "technical-documents.json"
    run_path = tmp_path / "technical-run.json"
    output_path = tmp_path / "technical.pdf"
    _write_json(brief_path, brief)
    _write_json(documents_path, manifest)
    run = {
        "run_id": "fixture-run",
        "model": "gpt-5.6-luna",
        "input_tokens": 100,
        "output_tokens": 50,
    }
    run.update(run_extra or {})
    _write_json(run_path, run)
    render_technical(brief_path, documents_path, run_path, output_path)
    return [page.extract_text() for page in PdfReader(output_path).pages]


def _view(number):
    return {
        "asset": f"Asset {number}",
        "bias": "mixed",
        "horizon": "days to weeks",
        "confidence": 3,
        "drivers": [f"Driver {number}-{index}" for index in range(3)],
        "risks": [f"View risk {number}-{index}" for index in range(4)],
        "source_ids": [],
    }


def test_top_risks_stay_with_their_heading(tmp_path):
    risks = [f"Top risk marker {index}" for index in range(8)]
    pages = _render(
        tmp_path,
        {
            "as_of_date": "2026-07-27",
            "executive_summary": [],
            "macro_themes": [],
            "asset_views": [_view(index) for index in range(10)],
            "top_risks": risks,
            "source_ids_used": [],
        },
        [],
    )

    matching_pages = {
        index
        for index, text in enumerate(pages)
        if "Top risks" in text or any(risk in text for risk in risks)
    }
    assert len(matching_pages) == 1


def test_pdf_explicitly_reports_when_no_sources_failed(tmp_path):
    pages = _render(
        tmp_path,
        {
            "as_of_date": "2026-07-27",
            "executive_summary": [],
            "macro_themes": [],
            "asset_views": [],
            "top_risks": [],
            "source_ids_used": [],
        },
        [],
    )

    text = "\n".join(pages)
    assert "Failed or partial sources" in text
    assert "None." in text


def test_source_register_entries_do_not_split_across_pages(tmp_path):
    documents = [
        {
            "id": f"source-{index}",
            "publisher": f"Publisher {index}",
            "title": f"Unique title marker {index}",
            "url": f"https://example.com/research/{index}/a-deliberately-long-path",
            "media_type": "text/html",
        }
        for index in range(18)
    ]
    pages = _render(
        tmp_path,
        {
            "as_of_date": "2026-07-27",
            "executive_summary": [],
            "macro_themes": [],
            "asset_views": [],
            "top_risks": [],
            "source_ids_used": [document["id"] for document in documents],
        },
        documents,
    )

    for index in range(18):
        title = f"Unique title marker {index}"
        url = f"https://example.com/research/{index}/a-deliberately-long-path"
        assert any(title in text and url in text for text in pages)


def test_pdf_renders_comparison_baseline_and_carried_history(tmp_path):
    pages = _render(
        tmp_path,
        {
            "as_of_date": "2026-07-27",
            "executive_summary": [],
            "macro_themes": [],
            "asset_views": [],
            "top_risks": [],
            "source_ids_used": [],
        },
        [],
        run_extra={
            "comparison": {
                "baseline_status": "available",
                "previous_date": "2026-07-24",
                "asset_view_changes": [
                    {
                        "status": "unchanged",
                        "asset": "EUR/USD",
                        "previous_bias": "bullish",
                        "current_bias": "bullish",
                        "carried_forward": True,
                    }
                ],
            }
        },
    )

    text = "\n".join(pages)
    assert "Previous successful brief: 2026-07-24" in text
    assert "historical carry, no current evidence" in text


def test_v2_pdf_contains_only_decision_content_and_cited_documents(tmp_path):
    brief = v2_brief()
    brief["what_changed"] = [
        {
            **brief["what_changed"][0],
            "headline": f"Policy signal changed in market {index}",
            "significance": (
                "The expected path is less certain and requires careful confirmation "
                "from the next complete evidence cycle."
            ),
        }
        for index in range(1, 6)
    ]
    brief["coverage"]["important_missing_coverage"] = [
        "Policy speeches are delayed or absent in several monitored jurisdictions.",
        "No timestamped price, positioning, or complete event-calendar data exists.",
    ]
    documents = [
        {
            "id": "doc:one",
            "publisher": "Fixture Publisher",
            "source_name": "Fixture Source",
            "title": "Fixture evidence",
            "url": "https://example.com/evidence",
            "media_type": "text/html",
        }
    ]

    pages = _render(tmp_path, brief, documents)

    assert "What changed" in pages[0]
    assert "Regime dashboard" in pages[0]
    assert "Highest-priority research expressions" in pages[0]
    assert "Next event risks" in "\n".join(pages[:2])
    assert "Next policy communication" in "\n".join(pages[:2])
    assert "Policy signal changed in market 4" not in pages[0]
    assert "report/unknown" not in pages[0]
    assert "Technical audit" not in pages[0]
    full_text = "\n".join(pages)
    for heading in (
        "Executive decision summary",
        "Additional material changes",
        "Candidate research expressions",
        "Theme analysis",
        "Cross-asset map",
        "Scenario map",
        "Disagreement map",
        "Catalysts and monitoring",
        "Top risks and blind spots",
        "Documents cited in this report",
    ):
        assert heading in full_text
    assert "Technical audit" not in full_text
    assert "Failed or partial sources" not in full_text
    assert "Important gaps" not in full_text
    assert "Policy signal changed in market 5" in full_text
    assert "Fixture Publisher: Fixture evidence" in full_text


def test_technical_pdf_lists_funnel_documents_and_source_failures(tmp_path):
    brief = v2_brief()
    brief["source_ids_used"] = ["doc:used"]
    document = {
        "id": "doc:used",
        "source_id": "source-a",
        "source_name": "Source A",
        "publisher": "Publisher A",
        "title": "Used evidence",
        "url": "https://example.com/used",
        "published_at": "2026-08-31T12:00:00+00:00",
    }
    manifest = {
        "documents": [document],
        "item_statuses": [
            {
                "source_id": "broken",
                "title": "Unextractable item",
                "url": "https://example.com/broken",
                "state": "failed",
                "detail": "body was unavailable",
                "document_id": None,
            },
            {
                "source_id": "source-a",
                "title": "Duplicate discovery",
                "url": "https://example.com/duplicate",
                "state": "duplicate",
                "detail": "canonical document already collected",
                "document_id": "doc:used",
            }
        ],
        "source_statuses": [
            {
                "source_id": "source-a",
                "source_name": "Source A",
                "state": "collected",
                "document_count": 1,
            },
            {
                "source_id": "stale",
                "source_name": "Stale Source",
                "state": "stale",
                "document_count": 0,
                "detail": "newest publication exceeds configured gap",
            },
        ],
        "source_health": [],
    }
    pages = _render_technical(
        tmp_path,
        brief,
        manifest,
        run_extra={
            "corpus_selection": [
                {
                    "document_id": "doc:used",
                    "outcome": "included",
                    "reason_label": "included_full",
                    "reason": "fit within bounded corpus",
                }
            ]
        },
    )

    text = "\n".join(pages)
    for marker in (
        "Technical report",
        "Collected documents by source",
        "[CITED]",
        "Discovered materials not added as separate documents",
        "Unextractable item",
        "Duplicate discovery",
        "Sources with no collected documents",
        "Stale Source",
    ):
        assert marker in text
