from __future__ import annotations

from macro_sage.models import DailyBrief, Document


def _citations(source_ids: list[str], documents: dict[str, Document]) -> str:
    links = []
    for source_id in dict.fromkeys(source_ids):
        document = documents.get(source_id)
        if document:
            links.append(f"[{document.source_name}: {document.title}]({document.url})")
    return "; ".join(links)


def render_markdown(brief: DailyBrief, documents: list[Document]) -> str:
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
    return "\n".join(lines).rstrip() + "\n"
