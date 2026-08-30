"""
File-detection orchestrator: extract -> classify -> chunk -> detect -> aggregate.

Used by `/upload` only. Entirely separate from the Summary pipeline —
does not import anything from `app.summarizer` or `app.main`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.file_pipeline import build_units, Unit
from app.content_classifier import classify_block, classify_document, BlockClass
from app.chunking import chunk_prose, chunk_code, Chunk
from app.text_quality import assess as assess_quality
from app.scoring import get_scorer, AnalysisResult, Signals
from app.code_analyzer import analyze_code, CodeAnalysisResult, CodeSignals

Status = Literal["analyzed", "code", "mixed", "insufficient_text", "unanalyzable", "extraction_failure"]


@dataclass
class PipelineResult:
    status: Status
    text_result: AnalysisResult | None
    code_result: CodeAnalysisResult | None
    chunks_analyzed: int
    chunks_skipped: int
    message: str | None
    structure: str
    document_class: str | None
    languages_detected: list[str]
    extracted_preview: str = ""
    # Full (uncapped) prose text — used by the Gemini AI-detection and
    # similarity pipelines (app/ai_text_detector.py, app/similarity.py),
    # which need more than the 3000-char preview kept for the API response.
    full_prose_text: str = ""


def _structure_label(filename: str) -> str:
    fn = filename.lower()
    if fn.endswith(".pdf"):
        return "pdf_pages"
    if fn.endswith((".pptx", ".ppt")):
        return "pptx_slides"
    return "flat"


def _aggregate_prose(chunks: list[Chunk]) -> tuple[AnalysisResult | None, int, int, int, int]:
    """Returns (aggregate_result_or_None, chunks_analyzed, chunks_skipped, skipped_words, total_words)."""
    scorer = get_scorer()
    analyzed: list[tuple[AnalysisResult, int]] = []
    skipped_words = 0
    skipped_count = 0
    total_words = 0

    for c in chunks:
        total_words += c.word_count
        quality = assess_quality(c.text)
        if quality.status != "ok":
            skipped_words += c.word_count
            skipped_count += 1
            continue
        result = scorer.analyze(c.text)
        analyzed.append((result, max(c.word_count, 1)))

    if not analyzed:
        return None, 0, skipped_count, skipped_words, total_words

    total_w = sum(w for _, w in analyzed)
    score = sum(r.ai_likelihood_score * w for r, w in analyzed) / total_w
    ppl = sum(r.perplexity * w for r, w in analyzed) / total_w
    burst = sum(r.burstiness * w for r, w in analyzed) / total_w
    sig_ppl = sum(r.signals.perplexity_signal * w for r, w in analyzed) / total_w
    sig_burst = sum(r.signals.burstiness_signal * w for r, w in analyzed) / total_w
    sig_marker = sum(r.signals.marker_signal * w for r, w in analyzed) / total_w
    sig_unif = sum(r.signals.uniformity_signal * w for r, w in analyzed) / total_w

    sentence_breakdown = []
    for r, _ in analyzed:
        sentence_breakdown.extend(r.sentence_breakdown)

    agg_score = round(score, 1)
    agg = AnalysisResult(
        ai_likelihood_score=agg_score,
        perplexity=round(ppl, 2),
        burstiness=round(burst, 2),
        verdict=scorer.verdict_from_score(agg_score),
        sentence_breakdown=sentence_breakdown,
        signals=Signals(round(sig_ppl, 3), round(sig_burst, 3), round(sig_marker, 3), round(sig_unif, 3)),
    )
    return agg, len(analyzed), skipped_count, skipped_words, total_words


def _build_multi_explanation(score: float, languages: list[str], n_chunks: int) -> str:
    verdict = "likely AI-generated" if score >= 60 else "likely human-written" if score <= 40 else "of uncertain origin"
    lang_txt = languages[0] if len(languages) == 1 else f"{len(languages)} languages ({', '.join(languages)})"
    return (
        f"Analyzed {n_chunks} code section(s) across {lang_txt}. Combined pattern signals suggest "
        f"this code is {verdict}. This is a heuristic, pattern-based estimate, not a proven "
        f"detection — treat it as a signal for review, not a verdict."
    )


def aggregate_code(chunks: list[Chunk]) -> tuple[CodeAnalysisResult | None, list[str]]:
    results = [analyze_code(c.text) for c in chunks if c.text.strip()]
    if not results:
        return None, []

    total_lines = sum(max(r.lines_analyzed, 1) for r in results)
    score = sum(r.ai_code_probability * max(r.lines_analyzed, 1) for r in results) / total_lines

    languages: list[str] = []
    for r in results:
        if r.detected_language not in languages:
            languages.append(r.detected_language)

    def wavg(attr: str) -> float:
        return sum(getattr(r.signals, attr) * max(r.lines_analyzed, 1) for r in results) / total_lines

    signals = CodeSignals(
        comment_density=round(wavg("comment_density"), 3),
        generic_comment_ratio=round(wavg("generic_comment_ratio"), 3),
        docstring_coverage=round(wavg("docstring_coverage"), 3),
        naming_consistency=round(wavg("naming_consistency"), 3),
        error_handling_density=round(wavg("error_handling_density"), 3),
        avg_identifier_length=round(wavg("avg_identifier_length"), 2),
        func_length_uniformity=round(wavg("func_length_uniformity"), 3),
        cleanness_score=round(wavg("cleanness_score"), 3),
        edge_case_density=round(wavg("edge_case_density"), 3),
        line_uniformity=round(wavg("line_uniformity"), 3),
    )
    confidence = "High" if total_lines >= 60 else "Medium" if total_lines >= 20 else "Low"
    lang_label = languages[0] if len(languages) == 1 else f"multiple ({', '.join(languages)})"
    agg_score = round(score, 1)

    agg = CodeAnalysisResult(
        ai_code_probability=agg_score,
        human_code_probability=round(100.0 - agg_score, 1),
        confidence=confidence,
        detected_language=lang_label,
        code_blocks_found=sum(r.code_blocks_found for r in results),
        signals=signals,
        explanation=_build_multi_explanation(agg_score, languages, len(results)),
        lines_analyzed=total_lines,
    )
    return agg, languages


def run(filename: str, data: bytes) -> PipelineResult:
    structure = _structure_label(filename)

    try:
        units = build_units(filename, data)
    except Exception as exc:
        return PipelineResult("extraction_failure", None, None, 0, 0,
                               f"Could not extract content from this file: {exc}",
                               structure, None, [])

    non_empty = [u for u in units if u.text.strip()]
    if not non_empty:
        return PipelineResult(
            "extraction_failure", None, None, 0, 0,
            "No extractable text was found in this file (it may be empty, image-only, or scanned).",
            structure, None, [],
        )

    classified: list[tuple[Unit, BlockClass]] = [(u, classify_block(u.text)) for u in non_empty]
    weighted: list[tuple[BlockClass, int]] = [
        (cls, len(u.text.splitlines()) if cls == "code" else len(u.text.split()))
        for u, cls in classified
    ]
    doc_class = classify_document(weighted)

    prose_units = [u for u, c in classified if c in ("prose", "mixed")]
    code_units = [u for u, c in classified if c in ("code", "mixed")]

    prose_chunks = chunk_prose(prose_units) if prose_units else []
    code_chunks = chunk_code(code_units) if code_units else []

    if prose_chunks:
        text_result, analyzed_n, skipped_n, skipped_words, total_words = _aggregate_prose(prose_chunks)
    else:
        text_result, analyzed_n, skipped_n, skipped_words, total_words = None, 0, 0, 0, 0

    code_result, languages = aggregate_code(code_chunks) if code_chunks else (None, [])

    has_text = text_result is not None
    has_code = code_result is not None

    if has_text and has_code:
        status, message = "mixed", None
    elif has_code:
        status, message = "code", None
    elif has_text:
        status, message = "analyzed", None
    else:
        combined_prose = "\n\n".join(u.text for u in prose_units).strip()
        if combined_prose:
            quality = assess_quality(combined_prose)
            status, message = quality.status, quality.reason
        else:
            status, message = "extraction_failure", "No readable prose or code content was found in this file."

    if skipped_n and status in ("analyzed", "mixed"):
        note = f" ({skipped_n} short or unreadable section(s) of this document were skipped.)"
        message = (message or "") + note

    preview_source = "\n\n".join(u.text for u in (prose_units or non_empty)).strip()
    extracted_preview = preview_source[:3000]

    return PipelineResult(
        status=status,
        text_result=text_result,
        code_result=code_result,
        chunks_analyzed=analyzed_n,
        chunks_skipped=skipped_n,
        message=message,
        structure=structure,
        document_class=doc_class,
        languages_detected=languages,
        extracted_preview=extracted_preview,
        full_prose_text=preview_source if text_result is not None else "",
    )
