from macro_sage.models import (
    CollectionReport,
    ContentResult,
    Document,
    RunHealth,
    SourceKind,
    SourceOutcome,
    SourceState,
)
from macro_sage.run_state import classify_collection, normalize_run_id, sanitized_error


def outcome(state):
    return SourceOutcome("source", "Source", SourceKind.ARTICLE, state)


def test_healthy_empty_collection_is_not_a_failure():
    report = CollectionReport(outcomes=[outcome(SourceState.NO_ITEMS)])

    assert classify_collection(report) == (ContentResult.NO_DATA, RunHealth.HEALTHY)


def test_partially_failed_empty_collection_is_degraded():
    report = CollectionReport(
        outcomes=[outcome(SourceState.NO_ITEMS), outcome(SourceState.FAILED)]
    )

    assert classify_collection(report) == (ContentResult.NO_DATA, RunHealth.DEGRADED)


def test_systemically_failed_empty_collection_is_failed():
    report = CollectionReport(outcomes=[outcome(SourceState.FAILED)])

    assert classify_collection(report) == (ContentResult.NO_DATA, RunHealth.FAILED)


def test_report_with_source_failure_is_degraded():
    report = CollectionReport(
        documents=[
            Document(
                id="document",
                source_id="source",
                source_name="Source",
                publisher="Publisher",
                category="research",
                title="Title",
                url="https://example.com",
                published_at=None,
                body="Body",
            )
        ],
        outcomes=[outcome(SourceState.FAILED)],
    )

    assert classify_collection(report) == (ContentResult.REPORT, RunHealth.DEGRADED)


def test_run_id_is_safely_normalized():
    assert normalize_run_id("github/123 attempt 2") == "github-123-attempt-2"


def test_diagnostics_redact_environment_secrets(monkeypatch):
    monkeypatch.setenv("EXAMPLE_API_KEY", "top-secret-value")

    assert "top-secret-value" not in sanitized_error(
        RuntimeError("request rejected for top-secret-value")
    )
