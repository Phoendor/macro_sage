from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#102A43")
TEAL = colors.HexColor("#167D7F")
PALE_TEAL = colors.HexColor("#E8F4F3")
PALE_BLUE = colors.HexColor("#EEF4F8")
PALE_RED = colors.HexColor("#FDECEC")
RED = colors.HexColor("#B42318")
SLATE = colors.HexColor("#486581")
MID_GREY = colors.HexColor("#829AB1")
LIGHT_GREY = colors.HexColor("#D9E2EC")
INK = colors.HexColor("#243B53")
WHITE = colors.white


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=27,
            leading=31,
            textColor=NAVY,
            spaceAfter=5 * mm,
        ),
        "kicker": ParagraphStyle(
            "Kicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            tracking=1.2,
            textColor=TEAL,
            spaceAfter=3 * mm,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=SLATE,
            spaceAfter=7 * mm,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=NAVY,
            spaceBefore=7 * mm,
            spaceAfter=4 * mm,
            keepWithNext=True,
        ),
        "section_compact": ParagraphStyle(
            "SectionCompact",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=NAVY,
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
            keepWithNext=True,
        ),
        "card_title": ParagraphStyle(
            "CardTitle",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=NAVY,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=INK,
            spaceAfter=2 * mm,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=SLATE,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=SLATE,
        ),
        "source": ParagraphStyle(
            "Source",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.2,
            leading=9.5,
            textColor=SLATE,
            leftIndent=2 * mm,
        ),
        "center": ParagraphStyle(
            "Center",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
    }


def _paragraph(text: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def _bullets(values: list[str], style: ParagraphStyle) -> Any:
    if not values:
        return _paragraph("None.", style)
    items = [
        ListItem(_paragraph(value, style), leftIndent=3 * mm, value="circle")
        for value in values
    ]
    return ListFlowable(
        items,
        bulletType="bullet",
        start="circle",
        leftIndent=5 * mm,
        bulletFontName="Helvetica",
        bulletFontSize=6,
        bulletColor=TEAL,
        spaceAfter=2 * mm,
    )


def _source_labels(
    source_ids: list[str],
    documents: dict[str, dict[str, Any]],
) -> str:
    labels = []
    for source_id in dict.fromkeys(source_ids):
        document = documents.get(source_id)
        if not document:
            continue
        publisher = escape(str(document.get("publisher") or document.get("source_name")))
        title = escape(str(document.get("title") or "Untitled"))
        url = escape(str(document.get("url") or ""), quote=True)
        labels.append(f'<link href="{url}" color="#167D7F">{publisher}: {title}</link>')
    return "<br/>".join(labels) or "No source link available"


def _footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(LIGHT_GREY)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MID_GREY)
    canvas.drawString(18 * mm, 9 * mm, "MACRO SAGE - SOURCE-ATTRIBUTED RESEARCH")
    page = str(document.page)
    canvas.drawRightString(width - 18 * mm, 9 * mm, page)
    canvas.restoreState()


def _confidence_bar(confidence: int) -> Table:
    cells = ["" for _ in range(5)]
    table = Table([cells], colWidths=[6 * mm] * 5, rowHeights=[2.3 * mm])
    commands: list[tuple[Any, ...]] = [
        ("BOX", (0, 0), (-1, -1), 0.3, LIGHT_GREY),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, WHITE),
    ]
    for index in range(5):
        commands.append(
            (
                "BACKGROUND",
                (index, 0),
                (index, 0),
                TEAL if index < confidence else LIGHT_GREY,
            )
        )
    table.setStyle(TableStyle(commands))
    return table


def _card(content: list[Any], background: colors.Color = PALE_TEAL) -> Table:
    card = Table([[content]], colWidths=[165 * mm])
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GREY),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )
    return card


def _source_paragraph(
    source_ids: list[str],
    documents: dict[str, dict[str, Any]],
    style: ParagraphStyle,
) -> Paragraph:
    return Paragraph(_source_labels(source_ids, documents), style)


def _v2_story(
    brief: dict[str, Any],
    manifest: dict[str, Any],
    run: dict[str, Any],
    documents: dict[str, dict[str, Any]],
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    story: list[Any] = []
    coverage = brief.get("coverage", {})
    errors = manifest.get("errors", [])
    skipped = manifest.get("skipped", [])

    story.extend(
        [
            _paragraph("DAILY MACRO DECISION BRIEF", styles["kicker"]),
            _paragraph("Macro Sage", styles["title"]),
            _paragraph(
                f"{brief.get('as_of_date', 'unknown date')} | Data cutoff "
                f"{coverage.get('data_cutoff', 'unknown')} | Previous brief "
                f"{coverage.get('comparison_date') or 'none'} | Outcome "
                f"{run.get('content_result', 'report')}/{run.get('health', 'unknown')}",
                styles["subtitle"],
            ),
        ]
    )
    coverage_rows = [
        [
            _paragraph("DOCUMENTS", styles["small"]),
            _paragraph("SOURCES", styles["small"]),
            _paragraph("FAILED / PARTIAL", styles["small"]),
            _paragraph("NO ITEM", styles["small"]),
        ],
        [
            _paragraph(coverage.get("documents_collected", 0), styles["center"]),
            _paragraph(coverage.get("sources_collected", 0), styles["center"]),
            _paragraph(coverage.get("sources_failed_or_partial", 0), styles["center"]),
            _paragraph(coverage.get("sources_without_items", 0), styles["center"]),
        ],
    ]
    coverage_table = Table(coverage_rows, colWidths=[41.25 * mm] * 4)
    coverage_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, WHITE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ]
        )
    )
    story.extend([coverage_table, Spacer(1, 3 * mm)])
    warnings = [str(value) for value in coverage.get("important_missing_coverage", [])]
    warning_text = str(coverage.get("market_data_note", "Market data unavailable."))
    if errors:
        warning_text += f" {len(errors)} source(s) failed or were partial."
    if warnings:
        warning_text += " Important gaps: " + "; ".join(warnings)
    story.extend(
        [
            _card(
                [
                    _paragraph("DECISION LIMITATIONS", styles["card_title"]),
                    _paragraph(warning_text, styles["small"]),
                ],
                PALE_RED if errors or warnings else PALE_BLUE,
            ),
            Spacer(1, 2 * mm),
        ]
    )

    story.append(_paragraph("What changed", styles["section_compact"]))
    changes = brief.get("what_changed", [])
    if changes:
        for change in changes[:5]:
            content = [
                _paragraph(change.get("headline", "Change"), styles["card_title"]),
                _paragraph(
                    f"{change.get('significance', '')} Transmission: "
                    f"{change.get('transmission', '')}",
                    styles["body"],
                ),
                _source_paragraph(change.get("source_ids", []), documents, styles["source"]),
            ]
            story.extend([KeepTogether(_card(content, PALE_BLUE)), Spacer(1, 1.5 * mm)])
    else:
        story.append(_paragraph("No material evidence-backed change was identified.", styles["body"]))

    story.append(_paragraph("Regime dashboard", styles["section_compact"]))
    regime_rows: list[list[Any]] = [
        [
            _paragraph("DIMENSION", styles["small"]),
            _paragraph("STATE / DIRECTION", styles["small"]),
            _paragraph("HORIZON", styles["small"]),
            _paragraph("EVIDENCE", styles["small"]),
        ]
    ]
    for regime in brief.get("regime_dashboard", []):
        regime_rows.append(
            [
                _paragraph(str(regime.get("dimension", "")).replace("_", " ").upper(), styles["small"]),
                _paragraph(
                    f"{regime.get('state', '')} / {regime.get('direction', '')}",
                    styles["small"],
                ),
                _paragraph(str(regime.get("horizon", "")).replace("_", " "), styles["small"]),
                _paragraph(f"{regime.get('confidence', 1)}/5", styles["center"]),
            ]
        )
    regime_table = Table(regime_rows, colWidths=[38 * mm, 70 * mm, 32 * mm, 25 * mm])
    regime_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE_BLUE]),
                ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, LIGHT_GREY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ]
        )
    )
    story.append(regime_table)

    story.append(
        _paragraph("Highest-priority research expressions", styles["section_compact"])
    )
    expressions = brief.get("candidate_expressions", [])
    if not expressions:
        story.append(_paragraph("No sufficiently supported setup today.", styles["body"]))
    for expression in expressions[:3]:
        story.extend(
            [
                KeepTogether(
                    _card(
                        [
                            _paragraph(expression.get("expression", "Expression"), styles["card_title"]),
                            _paragraph(
                                f"{str(expression.get('actionability', '')).upper()} | "
                                f"{str(expression.get('horizon', '')).replace('_', ' ')} | "
                                f"Thesis {expression.get('thesis_confidence', 1)}/5, "
                                f"expression {expression.get('expression_confidence', 1)}/5",
                                styles["meta"],
                            ),
                            _paragraph(expression.get("thesis", ""), styles["body"]),
                            _paragraph(
                                f"Invalidation: {expression.get('invalidation_condition', '')}",
                                styles["small"],
                            ),
                            _source_paragraph(
                                expression.get("source_ids", []), documents, styles["source"]
                            ),
                        ],
                        PALE_TEAL,
                    )
                ),
                Spacer(1, 1.5 * mm),
            ]
        )

    story.append(_paragraph("Next event risks", styles["section_compact"]))
    catalysts = brief.get("catalysts", [])
    if not catalysts:
        story.append(_paragraph("No sourced event risk was identified.", styles["body"]))
    for item in catalysts[:3]:
        story.extend(
            [
                KeepTogether(
                    [
                        _paragraph(
                            f"{item.get('event_or_signpost', '')} "
                            f"({item.get('timing', '')}): {item.get('what_matters', '')}",
                            styles["small"],
                        ),
                        _source_paragraph(
                            item.get("source_ids", []), documents, styles["source"]
                        ),
                    ]
                ),
                Spacer(1, 1.5 * mm),
            ]
        )

    story.append(PageBreak())
    story.append(_paragraph("Executive decision summary", styles["section"]))
    for item in sorted(brief.get("executive_decisions", []), key=lambda value: value.get("rank", 99)):
        story.extend(
            [
                KeepTogether(
                    _card(
                        [
                            _paragraph(
                                f"{item.get('rank', '')}. {item.get('development', '')}",
                                styles["card_title"],
                            ),
                            _paragraph(
                                f"{item.get('why_it_matters', '')} {item.get('transmission', '')}",
                                styles["body"],
                            ),
                            _paragraph(
                                f"Urgency: {item.get('urgency', '')} | Horizon: "
                                f"{str(item.get('horizon', '')).replace('_', ' ')}",
                                styles["meta"],
                            ),
                            _source_paragraph(item.get("source_ids", []), documents, styles["source"]),
                        ],
                        PALE_BLUE,
                    )
                ),
                Spacer(1, 2 * mm),
            ]
        )

    story.append(_paragraph("Regime evidence", styles["section"]))
    for regime in brief.get("regime_dashboard", []):
        evidence_lines = [
            f"{str(claim.get('claim_type', '')).replace('_', ' ').upper()}: "
            f"{claim.get('text', '')}"
            for claim in regime.get("evidence", [])
        ]
        counter_lines = [
            f"COUNTEREVIDENCE: {claim.get('text', '')}"
            for claim in regime.get("counterevidence", [])
        ]
        story.extend(
            [
                _card(
                    [
                        _paragraph(
                            str(regime.get("dimension", "")).replace("_", " ").title(),
                            styles["card_title"],
                        ),
                        _paragraph(
                            f"{regime.get('state', '')} / {regime.get('direction', '')} | "
                            f"Evidence {regime.get('confidence', 1)}/5",
                            styles["meta"],
                        ),
                        _paragraph(regime.get("confidence_rationale", ""), styles["small"]),
                        _bullets([*evidence_lines, *counter_lines], styles["small"]),
                        _source_paragraph(
                            regime.get("source_ids", []), documents, styles["source"]
                        ),
                    ],
                    PALE_BLUE,
                ),
                Spacer(1, 2 * mm),
            ]
        )

    story.append(_paragraph("Theme analysis", styles["section"]))
    for theme in brief.get("macro_themes", []):
        facts = [
            f"FACT ({claim.get('evidence_family', '')}): {claim.get('text', '')}"
            for claim in theme.get("observed_facts", [])
        ]
        inferences = [
            f"INFERENCE: {claim.get('text', '')}" for claim in theme.get("inferences", [])
        ]
        conflicts = [
            f"COUNTEREVIDENCE: {claim.get('text', '')}"
            for claim in theme.get("conflicting_evidence", [])
        ]
        content = [
            _paragraph(theme.get("theme", "Theme"), styles["card_title"]),
            _paragraph(theme.get("thesis", ""), styles["body"]),
            _paragraph(f"Implication: {theme.get('market_implication', '')}", styles["body"]),
            _bullets([*facts, *inferences, *conflicts], styles["small"]),
            _paragraph(
                "Invalidation: " + "; ".join(theme.get("invalidation_conditions", [])),
                styles["small"],
            ),
            _source_paragraph(theme.get("source_ids", []), documents, styles["source"]),
        ]
        story.extend([_card(content), Spacer(1, 3 * mm)])

    story.append(_paragraph("Cross-asset map", styles["section"]))
    for view in brief.get("asset_views", []):
        confidence = max(1, min(5, int(view.get("confidence", 1))))
        content = [
            _paragraph(
                f"{view.get('asset', 'Asset')} - {str(view.get('bias', '')).upper()}",
                styles["card_title"],
            ),
            _paragraph(
                f"Horizon: {str(view.get('horizon', '')).replace('_', ' ')} | "
                f"Evidence: {confidence}/5 | Market confirmation: "
                f"{view.get('market_confirmation', 'unavailable')}",
                styles["meta"],
            ),
            _paragraph(f"{view.get('thesis', '')} {view.get('transmission', '')}", styles["body"]),
            _paragraph("Drivers: " + "; ".join(view.get("drivers", [])), styles["small"]),
            _paragraph("Countercase: " + "; ".join(view.get("risks", [])), styles["small"]),
            _paragraph(f"Catalyst: {view.get('catalyst', '')}", styles["small"]),
            _paragraph(
                f"Invalidation: {view.get('invalidation_condition', '')}", styles["small"]
            ),
            _source_paragraph(view.get("source_ids", []), documents, styles["source"]),
        ]
        story.extend([_card(content, PALE_BLUE), Spacer(1, 3 * mm)])

    story.append(PageBreak())
    story.append(_paragraph("Scenario map", styles["section"]))
    for scenario in brief.get("scenarios", []):
        consequences = "; ".join(
            f"{item.get('asset_class', '')}: {item.get('implication', '')}"
            for item in scenario.get("cross_asset_consequences", [])
        )
        story.extend(
            [
                _card(
                    [
                        _paragraph(
                            f"{str(scenario.get('kind', '')).upper()} - "
                            f"{scenario.get('qualitative_likelihood', '')}",
                            styles["card_title"],
                        ),
                        _paragraph(scenario.get("description", ""), styles["body"]),
                        _paragraph("Signposts: " + "; ".join(scenario.get("signposts", [])), styles["small"]),
                        _paragraph("Consequences: " + consequences, styles["small"]),
                        _source_paragraph(scenario.get("source_ids", []), documents, styles["source"]),
                    ]
                ),
                Spacer(1, 3 * mm),
            ]
        )

    story.append(_paragraph("Disagreement map", styles["section"]))
    disagreements = brief.get("disagreements", [])
    if not disagreements:
        story.append(_paragraph("No material source disagreement was identified.", styles["body"]))
    for disagreement in disagreements:
        side_content: list[Any] = []
        for side in disagreement.get("sides", []):
            side_content.extend(
                [
                    _paragraph(f"Position: {side.get('position', '')}", styles["body"]),
                    _source_paragraph(
                        side.get("source_ids", []), documents, styles["source"]
                    ),
                ]
            )
        story.extend(
            [
                _card(
                    [
                        _paragraph(disagreement.get("issue", "Issue"), styles["card_title"]),
                        *side_content,
                        _paragraph(
                            f"Resolution signal: {disagreement.get('resolution_signal', '')}",
                            styles["small"],
                        ),
                    ],
                    PALE_BLUE,
                ),
                Spacer(1, 3 * mm),
            ]
        )

    story.append(_paragraph("Catalysts and monitoring", styles["section"]))
    catalysts = brief.get("catalysts", [])
    if not catalysts:
        story.append(_paragraph("No sourced catalyst or signpost was identified.", styles["body"]))
    for item in catalysts:
        story.extend(
            [
                KeepTogether(
                    [
                        _paragraph(
                            f"{item.get('event_or_signpost', '')} ({item.get('timing', '')}): "
                            f"{item.get('what_matters', '')}",
                            styles["body"],
                        ),
                        _source_paragraph(
                            item.get("source_ids", []), documents, styles["source"]
                        ),
                    ]
                ),
                Spacer(1, 2 * mm),
            ]
        )

    story.append(_paragraph("Top risks and blind spots", styles["section"]))
    for item in brief.get("top_risks", []):
        story.extend(
            [
                KeepTogether(
                    [
                        _paragraph(
                            f"{item.get('risk', '')}: {item.get('why_it_matters', '')} "
                            f"Monitor: {item.get('monitor', '')}",
                            styles["body"],
                        ),
                        _source_paragraph(
                            item.get("source_ids", []), documents, styles["source"]
                        ),
                    ]
                ),
                Spacer(1, 2 * mm),
            ]
        )

    story.append(PageBreak())
    story.append(_paragraph("Technical audit", styles["section"]))
    story.append(Spacer(1, 3 * mm))
    story.append(
        _paragraph(
            f"Model: {run.get('model', 'unknown')} | Input tokens: "
            f"{run.get('input_tokens', 'n/a')} | Output tokens: "
            f"{run.get('output_tokens', 'n/a')} | Brief schema: "
            f"{brief.get('schema_version', 'unknown')}",
            styles["meta"],
        )
    )
    story.append(_paragraph("Source register", styles["section"]))
    used_ids = list(dict.fromkeys(brief.get("source_ids_used", [])))
    used_documents = [documents[source_id] for source_id in used_ids if source_id in documents]
    used_documents.sort(
        key=lambda document: (
            str(document.get("publisher", "")),
            str(document.get("title", "")),
        )
    )
    for index, document in enumerate(used_documents, start=1):
        publisher = escape(str(document.get("publisher", "Unknown publisher")))
        title = escape(str(document.get("title", "Untitled")))
        url = escape(str(document.get("url", "")), quote=True)
        story.append(
            KeepTogether(
                [
                    Paragraph(
                        f"<b>{index}. {publisher}</b><br/>{title}<br/>"
                        f'<link href="{url}" color="#167D7F">{url}</link>',
                        styles["body"],
                    ),
                    Spacer(1, 1.5 * mm),
                ]
            )
        )
    story.append(_paragraph("Failed or partial sources", styles["section"]))
    story.append(_bullets([str(value) for value in errors], styles["small"]))
    if skipped:
        story.append(_paragraph("Sources without dated items", styles["card_title"]))
        story.append(_bullets([str(value) for value in skipped], styles["small"]))
    return story


def render(
    brief_path: Path,
    documents_path: Path,
    run_path: Path,
    output_path: Path,
) -> None:
    brief = _load(brief_path)
    manifest = _load(documents_path)
    run = _load(run_path)
    documents = {
        str(document["id"]): document for document in manifest.get("documents", [])
    }
    styles = _styles()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=19 * mm,
        title=f"Macro Sage - {brief.get('as_of_date', '')}",
        author="Macro Sage",
        subject="Source-attributed daily macro research brief",
    )
    story: list[Any] = []

    if str(brief.get("schema_version", "1")) == "2":
        story.extend(_v2_story(brief, manifest, run, documents, styles))
        pdf.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return

    story.append(_paragraph("DAILY MACRO RESEARCH", styles["kicker"]))
    story.append(_paragraph("Macro Sage", styles["title"]))
    story.append(
        _paragraph(
            f"Source-attributed market brief for {brief.get('as_of_date', 'unknown date')}",
            styles["subtitle"],
        )
    )
    collected = len(manifest.get("documents", []))
    errors = manifest.get("errors", [])
    model = run.get("model", "unknown")
    input_tokens = run.get("input_tokens")
    output_tokens = run.get("output_tokens")
    metadata = [
        [_paragraph("DOCUMENTS", styles["small"]), _paragraph("MODEL", styles["small"])],
        [_paragraph(collected, styles["center"]), _paragraph(model, styles["center"])],
        [
            _paragraph("INPUT TOKENS", styles["small"]),
            _paragraph("OUTPUT TOKENS", styles["small"]),
        ],
        [
            _paragraph(input_tokens if input_tokens is not None else "n/a", styles["center"]),
            _paragraph(
                output_tokens if output_tokens is not None else "n/a",
                styles["center"],
            ),
        ],
    ]
    meta_table = Table(metadata, colWidths=[42 * mm, 42 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, WHITE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ]
        )
    )
    story.extend([meta_table, Spacer(1, 6 * mm), HRFlowable(color=TEAL, thickness=1)])
    if errors:
        failure_notice = Table(
            [
                [
                    _paragraph(
                        f"SOURCE ACQUISITION WARNING - {len(errors)} failed or "
                        "partial source(s). See Run notes for the exact list.",
                        styles["body"],
                    )
                ]
            ],
            colWidths=[165 * mm],
        )
        failure_notice.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PALE_RED),
                    ("BOX", (0, 0), (-1, -1), 0.7, RED),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
                ]
            )
        )
        story.extend([Spacer(1, 4 * mm), failure_notice])

    story.append(_paragraph("Executive summary", styles["section"]))
    story.append(_bullets(brief.get("executive_summary", []), styles["body"]))

    comparison = run.get("comparison")
    if isinstance(comparison, dict):
        baseline = str(comparison.get("baseline_status", "unknown"))
        previous_date = comparison.get("previous_date") or "none"
        story.append(_paragraph("What changed", styles["section"]))
        story.append(
            _paragraph(
                f"Baseline: {baseline}. Previous successful brief: {previous_date}.",
                styles["meta"],
            )
        )
        material_changes = [
            change
            for change in comparison.get("asset_view_changes", [])
            if change.get("status") != "unchanged" or change.get("carried_forward")
        ]
        change_lines = []
        for change in material_changes:
            previous = change.get("previous_bias") or "none"
            current = change.get("current_bias") or "none"
            carried = "; historical carry, no current evidence" if change.get("carried_forward") else ""
            change_lines.append(
                f"{str(change.get('status', 'changed')).upper()}: "
                f"{change.get('asset', 'Asset')} — {previous} to {current}{carried}."
            )
        story.append(
            _bullets(
                change_lines or ["No material asset-view change was identified."],
                styles["body"],
            )
        )

    story.append(_paragraph("Macro themes", styles["section"]))
    for theme in brief.get("macro_themes", []):
        content = [
            _paragraph(theme.get("theme", "Untitled theme"), styles["card_title"]),
            _paragraph(theme.get("market_implication", ""), styles["body"]),
            Paragraph(
                _source_labels(theme.get("source_ids", []), documents),
                styles["source"],
            ),
        ]
        card = Table([[content]], colWidths=[165 * mm])
        card.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PALE_TEAL),
                    ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GREY),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
                ]
            )
        )
        story.extend([KeepTogether(card), Spacer(1, 3 * mm)])

    story.append(PageBreak())
    story.append(_paragraph("Asset views", styles["section"]))
    for view in brief.get("asset_views", []):
        bias = str(view.get("bias", "neutral")).upper()
        confidence = max(1, min(5, int(view.get("confidence", 1))))
        heading = Table(
            [
                [
                    _paragraph(view.get("asset", "Asset"), styles["card_title"]),
                    _paragraph(bias, styles["center"]),
                ]
            ],
            colWidths=[125 * mm, 40 * mm],
        )
        heading.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), PALE_BLUE),
                    ("BACKGROUND", (1, 0), (1, 0), PALE_TEAL),
                    ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GREY),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ]
            )
        )
        details: list[Any] = [
            heading,
            Spacer(1, 2.5 * mm),
            _paragraph(f"Horizon: {view.get('horizon', 'n/a')}", styles["meta"]),
            _paragraph(f"Confidence: {confidence}/5", styles["meta"]),
            _confidence_bar(confidence),
            Spacer(1, 2.5 * mm),
            _paragraph("Drivers", styles["card_title"]),
            _bullets(view.get("drivers", []), styles["body"]),
            _paragraph("Risks to the view", styles["card_title"]),
            _bullets(view.get("risks", []), styles["body"]),
            Paragraph(
                _source_labels(view.get("source_ids", []), documents),
                styles["source"],
            ),
        ]
        story.extend([KeepTogether(details), Spacer(1, 5 * mm)])

    story.append(
        KeepTogether(
            [
                _paragraph("Top risks", styles["section"]),
                _bullets(brief.get("top_risks", []), styles["body"]),
            ]
        )
    )

    story.append(PageBreak())
    story.append(_paragraph("Source register", styles["section"]))
    used_ids = list(dict.fromkeys(brief.get("source_ids_used", [])))
    used_documents = [documents[source_id] for source_id in used_ids if source_id in documents]
    used_documents.sort(
        key=lambda document: (
            str(document.get("publisher", "")),
            str(document.get("title", "")),
        )
    )
    for index, document in enumerate(used_documents, start=1):
        publisher = escape(str(document.get("publisher", "Unknown publisher")))
        title = escape(str(document.get("title", "Untitled")))
        url = escape(str(document.get("url", "")), quote=True)
        media = escape(str(document.get("media_type", "")))
        line = (
            f"<b>{index}. {publisher}</b><br/>{title}<br/>"
            f'<link href="{url}" color="#167D7F">{url}</link><br/>'
            f"<font color=\"#829AB1\">{media}</font>"
        )
        story.append(
            KeepTogether(
                [
                    Paragraph(line, styles["body"]),
                    Spacer(1, 2 * mm),
                ]
            )
        )

    skipped = manifest.get("skipped", [])
    story.append(_paragraph("Run notes", styles["section"]))
    story.append(_paragraph("Failed or partial sources", styles["card_title"]))
    if errors:
        story.append(_bullets([str(value) for value in errors], styles["small"]))
    else:
        story.append(_paragraph("None.", styles["small"]))
    if skipped:
        story.append(_paragraph("Sources without dated items", styles["card_title"]))
        story.append(_bullets([str(value) for value in skipped], styles["small"]))

    pdf.build(story, onFirstPage=_footer, onLaterPages=_footer)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a Macro Sage brief as PDF")
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--documents", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    arguments = _parser().parse_args()
    render(arguments.brief, arguments.documents, arguments.run, arguments.output)


if __name__ == "__main__":
    main()
