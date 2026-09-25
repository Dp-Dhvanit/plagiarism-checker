"""
PDF report generation (Feature 4).

No PDF generation exists anywhere in this project yet, so this module
introduces ReportLab (platypus) — the standard choice for structured
multi-section reports with tables, page numbers, and a footer.

Consumes exactly the shape stored in analysis_history.result_json (see
app/main.py's _build_result_json) plus the row's top-level columns — it
does not recompute anything, only lays out already-produced results.
"""
from __future__ import annotations

import io
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

DISCLAIMER = (
    "AI-generated content detection and similarity analysis are probabilistic tools "
    "and should not be treated as definitive proof of plagiarism or AI generation."
)

_ACCENT = colors.HexColor("#0d6e6e")
_INK = colors.HexColor("#1a1f2e")
_MUTED = colors.HexColor("#6b7280")

_styles = getSampleStyleSheet()
_title_style = ParagraphStyle("ReportTitle", parent=_styles["Title"], textColor=_ACCENT, spaceAfter=4)
_h2 = ParagraphStyle("H2", parent=_styles["Heading2"], textColor=_ACCENT, spaceBefore=14, spaceAfter=6)
_body = ParagraphStyle("Body", parent=_styles["BodyText"], textColor=_INK, leading=14)
_muted = ParagraphStyle("Muted", parent=_styles["BodyText"], textColor=_MUTED, fontSize=9)
_disclaimer_style = ParagraphStyle(
    "Disclaimer", parent=_styles["BodyText"], textColor=_MUTED, fontSize=8.5,
    borderColor=_MUTED, borderWidth=0.5, borderPadding=8, backColor=colors.HexColor("#f9fafb"),
)


_cell = ParagraphStyle("Cell", parent=_styles["BodyText"], textColor=_INK, fontSize=8, leading=10)


def _source_cell(m: dict) -> Paragraph:
    """Where a matched passage came from: its name, then its URL (external
    pages) or the date it was analysed (earlier submissions). Older reports
    predate `source_name`, so fall back to the stored tag."""
    name = m.get("source_name") or m.get("source_file") or "—"
    detail = m.get("source_url") or (m.get("source_created_at") or "")[:10]
    text = escape(name) + (f"<br/><font color='#6b7280' size='7'>{escape(detail)}</font>" if detail else "")
    return Paragraph(text, _cell)


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_MUTED)
    canvas.drawString(0.75 * inch, 0.5 * inch, "AI Plagiarism & AI-Generated Content Checker")
    canvas.drawRightString(LETTER[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _table(rows: list[list[str]], col_widths: list[float] | None = None) -> Table:
    t = Table(rows, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e0d8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf8f4")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def generate_report(history_row: dict[str, Any]) -> bytes:
    result = history_row.get("result_json") or {}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        topMargin=0.8 * inch, bottomMargin=0.8 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        title=f"AI Content Analysis Report — {history_row.get('file_name', '')}",
    )
    story: list = []

    story.append(Paragraph("AI Content Analysis Report", _title_style))
    story.append(
        _table(
            [
                ["Field", "Value"],
                ["File", history_row.get("file_name", "—")],
                ["Analysis Type", history_row.get("analysis_type", "—").title()],
                ["Analysis ID", str(history_row.get("id", "—"))],
                ["Date", history_row.get("created_at", "—")],
                ["Status", history_row.get("status", "—")],
            ],
            col_widths=[1.7 * inch, 4.3 * inch],
        )
    )
    story.append(Spacer(1, 4))

    heuristic = result.get("heuristic")
    gemini_text = result.get("gemini_text")
    if heuristic or gemini_text:
        story.append(Paragraph("AI Analysis", _h2))
        rows = [["Signal", "AI-generated likelihood", "Confidence / Verdict"]]
        if gemini_text:
            rows.append([
                "Gemini AI-assisted analysis",
                f"{gemini_text.get('ai_probability', 0):.1f}%",
                str(gemini_text.get("confidence", "—")).title(),
            ])
        if heuristic:
            rows.append([
                "Local heuristic (writing-pattern signals)",
                f"{heuristic.get('ai_likelihood_score', 0):.1f}%",
                str(heuristic.get("verdict", "—")),
            ])
        story.append(_table(rows, col_widths=[2.6 * inch, 1.9 * inch, 1.5 * inch]))
        if gemini_text and gemini_text.get("explanation"):
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Explanation:</b> {escape(str(gemini_text['explanation']))}", _body))

        flagged = (gemini_text or {}).get("flagged_sections") or []
        if flagged:
            story.append(Spacer(1, 8))
            story.append(Paragraph("Flagged Sections", _h2))
            for sec in flagged[:10]:
                story.append(Paragraph(f"&ldquo;{escape(str(sec.get('text', '')))}&rdquo;", _body))
                if sec.get("reason"):
                    story.append(Paragraph(f"<i>{escape(str(sec['reason']))}</i>", _muted))
                story.append(Spacer(1, 4))

    similarity = result.get("similarity")
    if similarity is not None:
        story.append(Paragraph("Similarity Analysis", _h2))
        story.append(
            _table(
                [
                    ["Metric", "Value"],
                    ["Overall similarity", f"{similarity.get('overall_similarity', 0):.1f}%"],
                    ["Matched sections", str(len(similarity.get("matches", [])))],
                    ["Corpus size compared against", f"{similarity.get('corpus_size', 0)} chunk(s)"],
                ],
                col_widths=[2.6 * inch, 3.4 * inch],
            )
        )
        external = similarity.get("external")
        if external and external.get("note"):
            story.append(Spacer(1, 4))
            story.append(Paragraph(escape(external["note"]), _muted))
            for s in external.get("sources") or []:
                story.append(Paragraph(f"{escape(s.get('title', ''))} — {escape(s.get('url', ''))}", _muted))
        matches = similarity.get("matches") or []
        if matches:
            story.append(Spacer(1, 8))
            story.append(Paragraph("Similarity Details", _h2))
            rows = [["Score", "Source", "Matched text"]]
            for m in matches[:10]:
                rows.append([
                    f"{m.get('score', 0):.1f}%",
                    _source_cell(m),
                    Paragraph(escape((m.get("matched_text", "") or "")[:200]), _cell),
                ])
            story.append(_table(rows, col_widths=[0.7 * inch, 1.9 * inch, 3.9 * inch]))
        elif similarity.get("note"):
            story.append(Paragraph(similarity["note"], _muted))

    image_result = result.get("image_result")
    if image_result:
        story.append(Paragraph("Image Analysis", _h2))
        story.append(
            _table(
                [
                    ["Field", "Value"],
                    ["AI-generated likelihood", f"{image_result.get('ai_probability', 0):.1f}%"],
                    ["Confidence", str(image_result.get("confidence", "—")).title()],
                    ["Classification", str(image_result.get("classification", "—")).replace("_", " ").title()],
                ],
                col_widths=[2.2 * inch, 3.8 * inch],
            )
        )
        indicators = image_result.get("indicators") or []
        if indicators:
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>Possible indicators:</b>", _body))
            for ind in indicators:
                story.append(Paragraph(f"&bull; {escape(str(ind))}", _body))
        if image_result.get("explanation"):
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Explanation:</b> {escape(str(image_result['explanation']))}", _body))

    extracted_preview = result.get("extracted_text_preview")
    if extracted_preview:
        story.append(Paragraph("Original Text (excerpt)", _h2))
        preview = extracted_preview[:1500] + ("…" if len(extracted_preview) > 1500 else "")
        story.append(Paragraph(escape(preview).replace("\n", "<br/>"), _muted))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Final Summary", _h2))
    summary_bits = []
    # Lead with the same overall verdict the app headlines, so the report can't
    # say "Likely AI" while the interface says "Uncertain". Records saved before
    # the verdict was archived simply skip this line.
    if result.get("final_verdict"):
        line = f"Overall verdict: {escape(str(result['final_verdict']))}."
        if result.get("verdict_reason"):
            line += f" {escape(str(result['verdict_reason']))}"
        summary_bits.append(line)
    if gemini_text:
        summary_bits.append(f"AI-generated likelihood was estimated at {gemini_text.get('ai_probability', 0):.1f}% ({gemini_text.get('confidence', '—')} confidence).")
    elif heuristic:
        summary_bits.append(f"The local heuristic estimated a {heuristic.get('ai_likelihood_score', 0):.1f}% AI-likelihood ({heuristic.get('verdict', '—')}).")
    if image_result:
        summary_bits.append(f"The image was assessed as {str(image_result.get('classification', '—')).replace('_', ' ')} ({image_result.get('ai_probability', 0):.1f}% likelihood).")
    if similarity is not None:
        summary_bits.append(f"Text similarity against prior submissions on file was {similarity.get('overall_similarity', 0):.1f}%.")
    story.append(Paragraph(" ".join(summary_bits) or "No analysis signals were available for this item.", _body))

    story.append(Spacer(1, 14))
    story.append(KeepTogether([Paragraph("Disclaimer", _h2), Paragraph(DISCLAIMER, _disclaimer_style)]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
