from __future__ import annotations

from macro_sage.history import BriefComparison, ChangeStatus
from macro_sage.models import DailyBrief, Document, SourceOutcome, SourceState


def _citations(source_ids: list[str], documents: dict[str, Document]) -> str:
    links = []
    for source_id in dict.fromkeys(source_ids):
        document = documents.get(source_id)
        if document:
            links.append(f"[{document.source_name}: {document.title}]({document.url})")
    return "; ".join(links)


def render_markdown(
    brief: DailyBrief,
    documents: list[Document],
    outcomes: list[SourceOutcome] | None = None,
    comparison: BriefComparison | None = None,
) -> str:
    lookup = {document.id: document for document in documents}
    lines = [f"# Macro Sage — {brief.as_of_date}", "", "## Executive summary", ""]
    lines.extend(f"- {item}" for item in brief.executive_summary)
    if comparison is not None:
        lines.extend(
            [
                "",
                "## What changed",
                "",
                f"**Comparison baseline:** {comparison.baseline_status.value}. "
                f"{comparison.baseline_detail}",
                "",
            ]
        )
        material = [
            change
            for change in comparison.asset_view_changes
            if change.status is not ChangeStatus.UNCHANGED or change.carried_forward
        ]
        if material:
            for change in material:
                transition = (
                    f"{change.previous_bias.value if change.previous_bias else 'none'}"
                    f" → {change.current_bias.value if change.current_bias else 'none'}"
                )
                carried = " (historical carry; no current evidence)" if change.carried_forward else ""
                lines.extend(
                    [
                        f"- **{change.status.value}: {change.asset}** — {transition}{carried}. "
                        f"{change.explanation}",
                    ]
                )
                current_sources = _citations(
                    change.current_source_document_ids,
                    lookup,
                )
                if current_sources:
                    lines.append(f"  Current evidence: {current_sources}")
        else:
            lines.append("- No material asset-view change was identified.")
        new_themes = [
            change
            for change in comparison.theme_changes
            if change.status in {ChangeStatus.NEW, ChangeStatus.RETIRED}
        ]
        for change in new_themes:
            lines.append(
                f"- **{change.status.value} {change.entity_type}:** {change.title}"
            )
        if comparison.week_date:
            week_material = sum(
                change.status is not ChangeStatus.UNCHANGED
                for change in comparison.week_asset_view_changes
            )
            lines.extend(
                [
                    "",
                    f"One-week baseline: {comparison.week_date.isoformat()} "
                    f"({week_material} material asset-view changes).",
                ]
            )
    lines.extend(["", "## Macro themes", ""])
    for theme in brief.macro_themes:
        lines.extend(
            [
                f"### {theme.theme}",
                "",
                theme.market_implication,
                "",
                f"Sources: {_citations(theme.source_ids, lookup)}",
                "",
            ]
        )
    lines.extend(["## Asset views", ""])
    for view in brief.asset_views:
        lines.extend(
            [
                f"### {view.asset}: {view.bias.value}",
                "",
                f"**Horizon:** {view.horizon} · **Confidence:** {view.confidence}/5",
                "",
                f"Drivers: {'; '.join(view.drivers)}",
                "",
                f"Risks: {'; '.join(view.risks)}",
                "",
                f"Sources: {_citations(view.source_ids, lookup)}",
                "",
            ]
        )
    lines.extend(["## Top risks", ""])
    lines.extend(f"- {risk}" for risk in brief.top_risks)
    if outcomes is not None:
        failures = [outcome for outcome in outcomes if outcome.is_failure]
        skipped = [
            outcome
            for outcome in outcomes
            if outcome.state is SourceState.SKIPPED
        ]
        lines.extend(["", "## Source acquisition status", ""])
        lines.append(
            f"**Failed or partial sources: {len(failures)}.** "
            "These sources were not silently omitted."
        )
        lines.extend(["", "### Failed or partial sources", ""])
        if failures:
            lines.extend(f"- {outcome.summary()}" for outcome in failures)
        else:
            lines.append("- None.")
        if skipped:
            lines.extend(["", "### Skipped by run limits", ""])
            lines.extend(f"- {outcome.summary()}" for outcome in skipped)
    return "\n".join(lines).rstrip() + "\n"
