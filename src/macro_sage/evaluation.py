from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from macro_sage.models import DailyBriefV1, DailyBriefV2


@dataclass(frozen=True, slots=True)
class EvaluationIssue:
    severity: str
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class BriefEvaluation:
    schema_version: str
    passed: bool
    material_claim_count: int
    cited_document_count: int
    candidate_expression_count: int
    issues: list[EvaluationIssue]

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["issues"] = [asdict(issue) for issue in self.issues]
        return value


def _walk(value: object) -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.append((key, child))
            found.extend(_walk(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk(child))
    return found


def _citations(value: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for key, child in _walk(value):
        if key == "source_ids" and isinstance(child, list):
            result.extend(str(item) for item in child)
    return list(dict.fromkeys(result))


def _claim_count(value: dict[str, Any]) -> int:
    return sum(
        1
        for key, child in _walk(value)
        if key == "claim_type" and isinstance(child, str)
    )


def evaluate_brief(
    brief_value: dict[str, Any],
    manifest_value: dict[str, Any],
) -> BriefEvaluation:
    issues: list[EvaluationIssue] = []
    schema_version = str(brief_value.get("schema_version", "1"))
    model_type = DailyBriefV2 if schema_version == "2" else DailyBriefV1
    try:
        model_type.model_validate(brief_value)
    except ValidationError as exc:
        issues.append(
            EvaluationIssue("critical", "schema_validation", str(exc))
        )

    known_ids = {
        str(document["id"])
        for document in manifest_value.get("documents", [])
        if isinstance(document, dict) and document.get("id")
    }
    citations = _citations(brief_value)
    source_register = [str(value) for value in brief_value.get("source_ids_used", [])]
    unknown = sorted(set([*citations, *source_register]) - known_ids)
    if unknown:
        issues.append(
            EvaluationIssue(
                "critical",
                "unknown_citations",
                f"Unknown document IDs: {unknown}",
            )
        )
    if schema_version == "2" and set(citations) != set(source_register):
        issues.append(
            EvaluationIssue(
                "critical",
                "source_register_drift",
                "The code-derived source register does not equal nested citations.",
            )
        )

    text = json.dumps(brief_value, ensure_ascii=False)
    unsupported_market = re.search(
        r"\b(priced[ -]in|crowded trade|current (?:market )?price|"
        r"markets? confirm(?:s|ed)?|spot (?:is|at))\b",
        text,
        re.IGNORECASE,
    )
    if unsupported_market:
        issues.append(
            EvaluationIssue(
                "critical",
                "unsupported_market_language",
                f"Found {unsupported_market.group(0)!r} without a market-data layer.",
            )
        )

    if schema_version == "2":
        themes = [
            " ".join(re.findall(r"[a-z0-9]+", str(value.get("theme", "")).casefold()))
            for value in brief_value.get("macro_themes", [])
            if isinstance(value, dict)
        ]
        if len(themes) != len(set(themes)):
            issues.append(
                EvaluationIssue("critical", "duplicate_themes", "Duplicate normalized themes.")
            )
        expressions = [
            value
            for value in brief_value.get("candidate_expressions", [])
            if isinstance(value, dict)
        ]
        for expression in expressions:
            missing = [
                key
                for key in (
                    "thesis",
                    "expression",
                    "why_now",
                    "catalyst",
                    "invalidation_condition",
                    "countercase",
                    "alternative_expression",
                )
                if not str(expression.get(key, "")).strip()
            ]
            if missing:
                issues.append(
                    EvaluationIssue(
                        "critical",
                        "incomplete_expression",
                        f"{expression.get('expression', 'expression')} lacks {missing}",
                    )
                )
            if expression.get("actionability") == "ready_for_review" and bool(
                expression.get("market_data_required", True)
            ):
                issues.append(
                    EvaluationIssue(
                        "critical",
                        "unsafe_actionability",
                        "ready_for_review was used without verified market data.",
                    )
                )

        coverage = brief_value.get("coverage", {})
        expected_failures = len(manifest_value.get("errors", []))
        if isinstance(coverage, dict) and int(
            coverage.get("sources_failed_or_partial", -1)
        ) != expected_failures:
            issues.append(
                EvaluationIssue(
                    "critical",
                    "coverage_count_drift",
                    "Brief and manifest failed-source counts differ.",
                )
            )

    critical = [issue for issue in issues if issue.severity == "critical"]
    return BriefEvaluation(
        schema_version=schema_version,
        passed=not critical,
        material_claim_count=_claim_count(brief_value),
        cited_document_count=len(set(citations)),
        candidate_expression_count=len(brief_value.get("candidate_expressions", [])),
        issues=issues,
    )


def evaluate_files(
    brief_path: Path,
    manifest_path: Path,
) -> BriefEvaluation:
    brief_value = json.loads(brief_path.read_text(encoding="utf-8"))
    manifest_value = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(brief_value, dict) or not isinstance(manifest_value, dict):
        raise ValueError("brief and manifest must be JSON objects")
    return evaluate_brief(brief_value, manifest_value)
