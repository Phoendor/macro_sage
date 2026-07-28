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
