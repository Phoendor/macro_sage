import json

from pypdf import PdfReader

from macro_sage.pdf import render


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
