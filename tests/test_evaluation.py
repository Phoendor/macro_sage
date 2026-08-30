from macro_sage.evaluation import evaluate_brief
from tests.helpers import v2_brief


def manifest(*, errors=None):
    return {
        "documents": [{"id": "doc:one", "title": "Document"}],
        "errors": errors or [],
    }


def test_v2_evaluation_passes_complete_grounded_contract():
    result = evaluate_brief(v2_brief(), manifest())

    assert result.passed is True
    assert result.material_claim_count > 0
    assert result.cited_document_count == 1
    assert result.candidate_expression_count == 1


def test_v2_evaluation_rejects_source_register_drift():
    brief = v2_brief()
    brief["source_ids_used"] = []

    result = evaluate_brief(brief, manifest())

    assert result.passed is False
    assert "source_register_drift" in {issue.code for issue in result.issues}


def test_v2_evaluation_rejects_unsupported_market_language():
    brief = v2_brief()
    brief["macro_themes"][0]["thesis"] = "The move is already priced in."

    result = evaluate_brief(brief, manifest())

    assert result.passed is False
    assert "unsupported_market_language" in {issue.code for issue in result.issues}


def test_v2_evaluation_requires_manifest_coverage_parity():
    result = evaluate_brief(v2_brief(failed=0), manifest(errors=["source failed"]))

    assert result.passed is False
    assert "coverage_count_drift" in {issue.code for issue in result.issues}
