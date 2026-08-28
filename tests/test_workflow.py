from pathlib import Path

WORKFLOW = Path(".github/workflows/generate-brief.yml")


def test_workflow_selects_models_once_and_never_uploads_private_corpus():
    text = WORKFLOW.read_text(encoding="utf-8")
    upload_section = text.split("- name: Upload report and audit trail", maxsplit=1)[1]

    assert text.count("python -m macro_sage models") == 1
    assert "documents.private.json" not in upload_section
    assert "manifest.json" in upload_section
    assert "cancel-in-progress: false" in text


def test_workflow_uses_shared_date_resolution_and_locked_dependencies():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "python -m macro_sage resolve-date" in text
    assert text.count("--date-resolution output/date-resolution.json") == 2
    assert "--constraint constraints.txt" in text
