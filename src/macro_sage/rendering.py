from __future__ import annotations

from macro_sage.history import BriefComparison, ChangeStatus
from macro_sage.models import (
    DailyBriefV1,
    DailyBriefV2,
    Document,
    EvidenceClaim,
    SourceOutcome,
    SourceState,
)


def _citations(source_ids: list[str], documents: dict[str, Document]) -> str:
    links = []
    for source_id in dict.fromkeys(source_ids):
        document = documents.get(source_id)
        if document:
            links.append(f"[{document.source_name}: {document.title}]({document.url})")
    return "; ".join(links)


def _render_v1_markdown(
    brief: DailyBriefV1,
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


def _claim_line(claim: EvidenceClaim, documents: dict[str, Document]) -> str:
    return (
        f"{claim.text} _[{claim.claim_type.value}; {claim.evidence_family}]_ "
        f"({_citations(claim.source_ids, documents)})"
    )


def _source_status_lines(outcomes: list[SourceOutcome] | None) -> list[str]:
    if outcomes is None:
        return []
    failures = [outcome for outcome in outcomes if outcome.is_failure]
    skipped = [outcome for outcome in outcomes if outcome.state is SourceState.SKIPPED]
    lines = [
        "## Source acquisition status",
        "",
        f"**Failed or partial sources: {len(failures)}.** These sources were not silently omitted.",
        "",
        "### Failed or partial sources",
        "",
    ]
    lines.extend(f"- {outcome.summary()}" for outcome in failures)
    if not failures:
        lines.append("- None.")
    if skipped:
        lines.extend(["", "### Skipped by run limits", ""])
        lines.extend(f"- {outcome.summary()}" for outcome in skipped)
    return lines


def _render_v2_markdown(
    brief: DailyBriefV2,
    documents: list[Document],
    outcomes: list[SourceOutcome] | None,
    comparison: BriefComparison | None,
) -> str:
    lookup = {document.id: document for document in documents}
    coverage = brief.coverage
    lines = [
        f"# Macro Sage - {brief.as_of_date}",
        "",
        f"**Data cutoff:** {coverage.data_cutoff.isoformat()}  ",
        f"**Previous comparable brief:** {coverage.comparison_date or 'none'}  ",
        f"**Coverage:** {coverage.documents_collected} documents from "
        f"{coverage.sources_collected} sources; "
        f"{coverage.sources_failed_or_partial} failed or partial; "
        f"{coverage.sources_without_items} without items.",
        "",
        f"> **Market-data limitation:** {coverage.market_data_note}",
    ]
    if coverage.important_missing_coverage:
        lines.extend(["", "> **Important missing coverage:**"])
        lines.extend(f"> - {item}" for item in coverage.important_missing_coverage)

    lines.extend(["", "## What changed", ""])
    if brief.what_changed:
        for item in brief.what_changed:
            lines.extend(
                [
                    f"- **{item.headline}** - {item.significance}",
                    f"  Transmission: {item.transmission} | Horizon: {item.horizon.value}",
                    f"  Sources: {_citations(item.source_ids, lookup)}",
                ]
            )
    else:
        lines.append("- No material evidence-backed change was identified.")
    if comparison is not None:
        lines.extend(
            [
                "",
                f"Deterministic history status: **{comparison.baseline_status.value}** - "
                f"{comparison.baseline_detail}",
            ]
        )

    lines.extend(["", "## Executive decision summary", ""])
    for item in sorted(brief.executive_decisions, key=lambda value: value.rank):
        lines.extend(
            [
                f"### {item.rank}. {item.development}",
                "",
                f"{item.why_it_matters} {item.transmission}",
                "",
                f"**Urgency:** {item.urgency.value} | **Horizon:** {item.horizon.value}",
                "",
                f"Sources: {_citations(item.source_ids, lookup)}",
                "",
            ]
        )

    lines.extend(
        [
            "## Macro regime dashboard",
            "",
            "| Dimension | State | Direction | Horizon | Confidence |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for regime in brief.regime_dashboard:
        lines.append(
            f"| {regime.dimension.value} | {regime.state} | {regime.direction.value} | "
            f"{regime.horizon.value} | {regime.confidence}/5 |"
        )
        lines.append(f"\n{regime.confidence_rationale}\n")
        for claim in regime.evidence:
            lines.append(f"- Evidence: {_claim_line(claim, lookup)}")
        for claim in regime.counterevidence:
            lines.append(f"- Counterevidence: {_claim_line(claim, lookup)}")

    lines.extend(["", "## Candidate research expressions", ""])
    if not brief.candidate_expressions:
        lines.append("No sufficiently supported setup today.")
    for item in brief.candidate_expressions:
        lines.extend(
            [
                f"### {item.expression}",
                "",
                f"**State:** {item.actionability.value} | **Framing:** {item.framing} | "
                f"**Horizon:** {item.horizon.value}",
                "",
                f"**Thesis:** {item.thesis}",
                "",
                f"**Why now / path:** {item.why_now} {item.expected_path}",
                "",
                f"**Catalyst:** {item.catalyst}",
                "",
                f"**Invalidation:** {item.invalidation_condition}",
                "",
                f"**Countercase:** {item.countercase}",
                "",
                f"**Implementation risks:** {'; '.join(item.implementation_risks)}",
                "",
                f"**Alternative:** {item.alternative_expression}",
                "",
                f"**Evidence confidence:** thesis {item.thesis_confidence}/5; "
                f"expression {item.expression_confidence}/5. {item.confidence_rationale}",
                "",
                f"Sources: {_citations(item.source_ids, lookup)}",
                "",
            ]
        )

    lines.extend(["## Theme analysis", ""])
    for theme in brief.macro_themes:
        lines.extend(
            [
                f"### {theme.theme}",
                "",
                f"**Thesis:** {theme.thesis}",
                "",
                f"**Market implication:** {theme.market_implication}",
                "",
            ]
        )
        for claim in theme.observed_facts:
            lines.append(f"- Source fact: {_claim_line(claim, lookup)}")
        for claim in theme.inferences:
            lines.append(f"- Macro Sage inference: {_claim_line(claim, lookup)}")
        for claim in theme.conflicting_evidence:
            lines.append(f"- Conflicting evidence: {_claim_line(claim, lookup)}")
        lines.extend(
            [
                f"- Transmission: {'; '.join(f'{item.asset_class}: {item.implication}' for item in theme.transmission)}",
                f"- Catalysts: {'; '.join(theme.catalysts) or 'None identified'}",
                f"- Invalidation: {'; '.join(theme.invalidation_conditions)}",
                f"- Sources: {_citations(theme.source_ids, lookup)}",
                "",
            ]
        )

    lines.extend(["## Cross-asset map", ""])
    for view in brief.asset_views:
        lines.extend(
            [
                f"### {view.asset}: {view.bias.value}",
                "",
                f"**Horizon:** {view.horizon.value} | **Evidence confidence:** "
                f"{view.confidence}/5 | **Market confirmation:** {view.market_confirmation.value}",
                "",
                f"{view.thesis} {view.transmission}",
                "",
                f"Drivers: {'; '.join(view.drivers)}",
                "",
                f"Counterarguments: {'; '.join(view.risks)}",
                "",
                f"Catalyst: {view.catalyst}",
                "",
                f"Invalidation: {view.invalidation_condition}",
                "",
                f"{view.confidence_rationale}",
                "",
                f"Sources: {_citations(view.source_ids, lookup)}",
                "",
            ]
        )

    lines.extend(["## Scenario map", ""])
    for scenario in brief.scenarios:
        lines.extend(
            [
                f"### {scenario.kind.value}: {scenario.qualitative_likelihood.value}",
                "",
                scenario.description,
                "",
                f"Signposts: {'; '.join(scenario.signposts)}",
                "",
                "Consequences: "
                + "; ".join(
                    f"{item.asset_class}: {item.implication}"
                    for item in scenario.cross_asset_consequences
                ),
                "",
                f"Sources: {_citations(scenario.source_ids, lookup)}",
                "",
            ]
        )

    lines.extend(["## Disagreement map", ""])
    if not brief.disagreements:
        lines.append("- No material source disagreement was identified.")
    for disagreement in brief.disagreements:
        lines.extend([f"### {disagreement.issue}", ""])
        for side in disagreement.sides:
            lines.append(f"- **Position:** {side.position}")
            for claim in side.evidence:
                lines.append(f"  - {_claim_line(claim, lookup)}")
        lines.extend(["", f"Resolution signal: {disagreement.resolution_signal}", ""])

    lines.extend(["## Catalysts and monitoring", ""])
    if not brief.catalysts:
        lines.append("- No sourced catalyst or signpost was identified.")
    for catalyst in brief.catalysts:
        lines.append(
            f"- **{catalyst.event_or_signpost} ({catalyst.timing})** - "
            f"{catalyst.what_matters} Affects: {', '.join(catalyst.affected_views)}. "
            f"Sources: {_citations(catalyst.source_ids, lookup)}"
        )

    lines.extend(["", "## Top risks and blind spots", ""])
    for risk in brief.top_risks:
        lines.append(
            f"- **{risk.risk}** - {risk.why_it_matters} Monitor: {risk.monitor}. "
            f"Sources: {_citations(risk.source_ids, lookup)}"
        )

    lines.extend(["", *_source_status_lines(outcomes)])
    lines.extend(["", "## Source register", ""])
    used = [lookup[source_id] for source_id in brief.source_ids_used if source_id in lookup]
    used.sort(key=lambda document: (document.publisher, document.title))
    for document in used:
        lines.append(f"- [{document.publisher}: {document.title}]({document.url})")
    return "\n".join(lines).rstrip() + "\n"


def render_markdown(
    brief: DailyBriefV1 | DailyBriefV2,
    documents: list[Document],
    outcomes: list[SourceOutcome] | None = None,
    comparison: BriefComparison | None = None,
) -> str:
    if isinstance(brief, DailyBriefV2):
        return _render_v2_markdown(brief, documents, outcomes, comparison)
    return _render_v1_markdown(brief, documents, outcomes, comparison)
