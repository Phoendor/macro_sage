from pathlib import Path

WORKFLOW = Path(".github/workflows/generate-brief.yml")
HEALTH_WORKFLOW = Path(".github/workflows/source-health.yml")


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


def test_workflow_uses_a_durable_history_branch_not_actions_cache():
    text = WORKFLOW.read_text(encoding="utf-8")
    cache_sections = "\n".join(
        section
        for section in text.split("- name:")
        if "cache" in section.splitlines()[0].casefold()
    )

    assert "ref: macro-sage-history" in text
    assert "path: .history-store" in text
    assert text.count("--history .history-store") == 2
    assert text.count("--require-history") == 2
    assert "push origin HEAD:macro-sage-history" in text
    assert "jq -r '.history_record // empty'" in text
    assert "python -m macro_sage confirm-history" in text
    assert "contents: write" in text
    assert ".history-store" not in cache_sections


def test_workflow_delivers_optionally_and_persists_idempotency_state():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "secrets.TELEGRAM_BOT_TOKEN" in text
    assert "vars.TELEGRAM_CHAT_ID" in text
    assert "python -m macro_sage deliver" in text
    assert "--state .history-store/delivery/telegram.json" in text
    assert "continue-on-error: true" in text
    assert "git -C .history-store add delivery" in text
    assert "retention-days: 30" in text


def test_source_health_workflow_is_model_free_and_runs_full_canaries_weekly():
    text = HEALTH_WORKFLOW.read_text(encoding="utf-8")

    assert "python -m macro_sage source-health" in text
    assert "python -m macro_sage validate-sources" in text
    assert "30 8 * * 0" in text
    assert "OPENAI_API_KEY" not in text
    assert "documents.private.json" not in text
    assert "--review-bundle" not in text
    assert "retention-days: 30" in text
    assert "macro-sage-data-v3" in text
