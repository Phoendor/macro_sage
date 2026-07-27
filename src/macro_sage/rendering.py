from __future__ import annotations

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
) -> str:
    lookup = {document.id: document for document in documents}
    lines = [f"# Macro Sage — {brief.as_of_date}", "", "## Executive summary", ""]
    lines.extend(f"- {item}" for item in brief.executive_summary)
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
