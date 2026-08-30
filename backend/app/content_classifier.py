"""
Prose vs. code content routing.

Decides whether a block of text (a pasted snippet, a PDF page, a PPTX
slide) is prose, code, mixed, or empty — so the detection pipeline never
runs prose AI-detection over raw source code (or vice versa).

Reuses `is_code_line()` from `app.code_analyzer` (already used internally
by that module's own `extract_code_blocks`) rather than inventing a new
code-detection heuristic — read-only reuse, no changes to that module's
behavior.
"""
from __future__ import annotations

import re
from typing import Literal

from app.code_analyzer import is_code_line

BlockClass = Literal["prose", "code", "mixed", "empty"]
DocClass = Literal["PROSE_DOMINANT", "CODE_DOMINANT", "MIXED"]

CODE_LINE_RATIO_FOR_CODE = 0.5
CODE_LINE_RATIO_FOR_PROSE = 0.15

DOC_CODE_FRACTION_DOMINANT = 0.70
DOC_PROSE_FRACTION_DOMINANT = 0.30

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _pseudo_lines(text: str) -> list[str]:
    """Split into line-like units for is_code_line() to scan.

    Pasted plain-text prose often has zero real newline characters (a
    <textarea> wraps visually, but the string itself is one physical
    line) — treating the whole paragraph as "1 line" would let a couple
    of incidental code-ish tokens flip the whole thing to "code". If
    newline density is low, split on sentence boundaries instead so each
    pseudo-line is a meaningful, sentence-sized unit.
    """
    newline_count = text.count("\n")
    if newline_count >= max(1, len(text) // 200):
        return text.splitlines()
    parts = _SENTENCE_SPLIT.split(text)
    return parts if len(parts) > 1 else [text]


def classify_block(text: str) -> BlockClass:
    stripped = (text or "").strip()
    if not stripped:
        return "empty"

    lines = [l for l in _pseudo_lines(stripped) if l.strip()]
    if not lines:
        return "empty"

    code_lines = sum(1 for l in lines if is_code_line(l))
    ratio = code_lines / len(lines)

    if ratio >= CODE_LINE_RATIO_FOR_CODE:
        return "code"
    if ratio <= CODE_LINE_RATIO_FOR_PROSE:
        return "prose"
    return "mixed"


def classify_document(weighted_classifications: list[tuple[BlockClass, int]]) -> DocClass:
    """Roll up per-unit classifications into a document-level verdict.

    `weighted_classifications` is a list of (classification, weight) pairs,
    where weight is that unit's word (prose) or line (code) count — so one
    giant code page and one tiny prose page don't average out to 50/50.
    "mixed" units contribute half their weight to the code side, as a
    reasonable approximation.
    """
    code_weight = 0.0
    total_weight = 0.0
    for cls, weight in weighted_classifications:
        if cls == "empty" or weight <= 0:
            continue
        total_weight += weight
        if cls == "code":
            code_weight += weight
        elif cls == "mixed":
            code_weight += weight * 0.5

    if total_weight == 0:
        return "PROSE_DOMINANT"

    code_fraction = code_weight / total_weight
    if code_fraction >= DOC_CODE_FRACTION_DOMINANT:
        return "CODE_DOMINANT"
    if code_fraction <= DOC_PROSE_FRACTION_DOMINANT:
        return "PROSE_DOMINANT"
    return "MIXED"
