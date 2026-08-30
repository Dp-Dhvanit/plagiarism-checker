"""
Content-aware chart selection for the Summary feature.

Single source of truth for turning real (label, value) pairs into a chart
type — used by both the tabular (CSV/Excel) path and the prose (PDF/DOCX/
PPTX/TXT) path, so the same rules apply everywhere. This module never
invents a number: it only classifies and formats data that has already
been extracted from the document. If the data isn't coherent/meaningful
enough to chart, functions here return None/[] rather than fabricating
something to fill the space.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# Palette for chart series/categories.
CHART_COLORS = [
    "#0d6e6e", "#c47a1a", "#b33a3a", "#7c3aed",
    "#059669", "#1d4ed8", "#dc2626", "#d97706",
    "#0891b2", "#9333ea", "#16a34a", "#ea580c",
]

ChartType = Literal["bar", "hbar", "pie", "line", "grouped-bar"]

MAX_BAR_ITEMS = 8
MAX_HBAR_ITEMS = 15
MIN_ITEMS_FOR_CHART = 2
MIN_ITEMS_FOR_BAR = 3
PIE_MAX_ITEMS = 8
PIE_SUM_LOW, PIE_SUM_HIGH = 85.0, 115.0  # allows rounding / an implicit "other" bucket

_MONTHS = {
    "jan", "january", "feb", "february", "mar", "march", "apr", "april",
    "may", "jun", "june", "jul", "july", "aug", "august", "sep", "sept",
    "september", "oct", "october", "nov", "november", "dec", "december",
}
_TIME_TOKEN_RE = re.compile(
    r"^(q[1-4]|fy\s?\d{2,4}|year\s?\d+|\d{4})$", re.IGNORECASE
)


@dataclass
class CategoryValue:
    label: str
    value: float
    unit: str | None = None        # "%" | "scaled" | None — classification only
    scale_word: str | None = None  # "lakh"/"crore"/... — display only


def _looks_like_time_label(label: str) -> bool:
    token = label.strip().lower()
    if token in _MONTHS:
        return True
    return bool(_TIME_TOKEN_RE.match(token))


def _chart_dict(
    title: str,
    chart_type: ChartType,
    data: list[dict],
    color: str | None = None,
    value_suffix: str = "",
    value_label: str = "Value",
) -> dict:
    return {
        "title": title,
        "type": chart_type,
        "data": data,
        "color": color,
        "value_suffix": value_suffix,
        "value_label": value_label,
    }


def build_line_chart(items: list[CategoryValue], title: str, value_label: str = "Value") -> dict:
    data = [{"name": it.label, "value": round(it.value, 2)} for it in items]
    suffix = "%" if items and items[0].unit == "%" else ""
    return _chart_dict(title, "line", data, color=CHART_COLORS[1], value_suffix=suffix, value_label=value_label)


def select_chart(items: list[CategoryValue], title: str, value_label: str = "Value") -> dict | None:
    """Classify real (label, value) pairs into the most appropriate chart,
    or None if there isn't enough coherent data to chart meaningfully."""
    if len(items) < MIN_ITEMS_FOR_CHART:
        return None

    if all(_looks_like_time_label(it.label) for it in items):
        return build_line_chart(items, title, value_label=value_label)

    if (
        all(it.unit == "%" for it in items)
        and len(items) <= PIE_MAX_ITEMS
        and PIE_SUM_LOW <= sum(it.value for it in items) <= PIE_SUM_HIGH
    ):
        data = [{"name": it.label, "value": round(it.value, 1)} for it in items]
        return _chart_dict(title, "pie", data, value_suffix="%", value_label=value_label)

    if len(items) < MIN_ITEMS_FOR_BAR:
        return None

    suffix = "%" if all(it.unit == "%" for it in items) else ""
    ordered = sorted(items, key=lambda it: it.value, reverse=True)

    if len(ordered) > MAX_BAR_ITEMS:
        top = ordered[:MAX_HBAR_ITEMS]
        data = [{"name": it.label, "value": round(it.value, 2)} for it in top]
        return _chart_dict(title, "hbar", data, value_suffix=suffix, value_label=value_label)

    data = [{"name": it.label, "value": round(it.value, 2)} for it in ordered]
    return _chart_dict(title, "bar", data, color=CHART_COLORS[0], value_suffix=suffix, value_label=value_label)


def select_grouped_chart(
    category_labels: list[str],
    series: list[tuple[str, list[float]]],
    title: str,
) -> dict | None:
    """series: list of (metric_name, values) where values is aligned
    index-for-index with category_labels. Tabular-data use only (v1) —
    reliably detecting this structure from unstructured prose would
    require indentation info that document extraction doesn't reliably
    preserve."""
    if len(category_labels) < MIN_ITEMS_FOR_CHART or len(series) < 2:
        return None

    data = []
    for i, label in enumerate(category_labels):
        row = {"name": label}
        for metric_name, values in series:
            if i < len(values):
                row[metric_name] = round(values[i], 2)
        data.append(row)

    chart_series = [
        {"key": name, "label": name, "color": CHART_COLORS[i % len(CHART_COLORS)]}
        for i, (name, _) in enumerate(series)
    ]
    result = _chart_dict(title, "grouped-bar", data, value_label="Value")
    result["series"] = chart_series
    return result


# ── Prose extraction ─────────────────────────────────────────────────────────

_SCALE_MULTIPLIERS = {
    "thousand": 1e3, "k": 1e3,
    "lakh": 1e5,
    "million": 1e6, "m": 1e6,
    "crore": 1e7,
    "billion": 1e9, "bn": 1e9,
}
_CURRENCY_SYMBOLS = r"₹|Rs\.?|INR|\$|€|£"

# A full stripped line: "Label <:|=|–|—|tab> Value[unit]". Deliberately
# excludes a bare hyphen from the delimiter set — that appears inside
# compound words and numeric ranges ("10-15") and would false-positive on
# ordinary prose. Tab IS included: a tab between label and value is an
# unambiguous structural signal (common when slide text is pasted from a
# spreadsheet/table), not something that occurs mid-sentence in prose.
# The leading symbol strip covers arbitrary bullet glyphs (-, •, ●, ▪, ‣,
# ○, », etc.), not just a fixed set of three.
_BULLET_PREFIX = r"^\s*[^\w\s]{0,3}\s*"
_VALUE_RE = (
    rf"(?P<currency>{_CURRENCY_SYMBOLS})?\s*"
    r"(?P<number>-?[\d,]+(?:\.\d+)?)\s*"
    r"(?P<scale>thousand|lakh|million|crore|billion|k|m|bn)?"
    r"\s*(?P<percent>%)?\s*$"
)
_PAIR_LINE_RE = re.compile(
    _BULLET_PREFIX
    + r"(?P<label>[A-Za-z][A-Za-z0-9 &/'.()-]{1,40}?)\s*"
    + r"[:=–—\t]\s*"
    + _VALUE_RE,
    re.IGNORECASE,
)

# Fallback pair: label and value on their OWN separate lines — a common
# slide layout (a caption text box + a big stat-number text box) that
# doesn't produce a same-line delimiter at all.
_VALUE_ONLY_LINE_RE = re.compile(_BULLET_PREFIX + _VALUE_RE, re.IGNORECASE)
_LABEL_ONLY_LINE_RE = re.compile(
    r"^[^\w\s]{0,3}\s*(?P<label>[A-Za-z][A-Za-z &/'()-]{1,39})\s*[:\-–—]?\s*$"
)

MAX_EXTRACTED_PAIRS = 30


def _parsed_value(m: re.Match) -> tuple[float, str, str | None] | None:
    """From a match with currency/number/scale/percent groups, return
    (normalized_value, unit_bucket, scale_word_for_display)."""
    raw_number = m.group("number").replace(",", "")
    try:
        number = float(raw_number)
    except ValueError:
        return None
    currency = m.group("currency")
    scale = (m.group("scale") or "").lower() or None
    if m.group("percent"):
        return number, "%", None
    if currency or scale:
        return number * _SCALE_MULTIPLIERS.get(scale, 1.0), "scaled", scale
    return number, "plain", None


def _pick_largest_unit_bucket(candidates: list[CategoryValue]) -> list[CategoryValue]:
    """Keep only the largest unit bucket — mixing units (e.g. "12 meeting
    rooms" with "50% market share") into one chart would be misleading,
    not merely inconsistent."""
    if not candidates:
        return []
    buckets: dict[str, list[CategoryValue]] = {}
    for c in candidates:
        buckets.setdefault(c.unit or "plain", []).append(c)
    largest = max(buckets.values(), key=len)
    return largest if len(largest) >= MIN_ITEMS_FOR_CHART else []


def _extract_same_line_pairs(text: str) -> list[CategoryValue]:
    """Strict pass: "Label <delimiter> Value" on one line."""
    candidates: list[CategoryValue] = []
    seen_labels: set[str] = set()

    for line in text.splitlines():
        line = line.strip()
        if not line or len(candidates) >= MAX_EXTRACTED_PAIRS:
            continue
        m = _PAIR_LINE_RE.match(line)
        if not m:
            continue
        label = m.group("label").strip()
        label_key = label.lower()
        if not label or label_key in seen_labels:
            continue
        parsed = _parsed_value(m)
        if parsed is None:
            continue
        value, unit, scale = parsed
        seen_labels.add(label_key)
        candidates.append(CategoryValue(label=label, value=value, unit=unit, scale_word=scale))

    return candidates


def _extract_adjacent_line_pairs(text: str, exclude_labels: set[str]) -> list[CategoryValue]:
    """Fallback pass: label on one line, value on the very next non-empty
    line — a common slide layout (a caption text box + a separate big
    stat-number text box) that produces no same-line delimiter at all.
    Only used when the strict same-line pass didn't find enough data, so
    a genuine numeric dataset doesn't silently vanish just because it
    isn't formatted on one line."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    candidates: list[CategoryValue] = []
    seen_labels: set[str] = set(exclude_labels)

    i = 0
    while i < len(lines) - 1 and len(candidates) < MAX_EXTRACTED_PAIRS:
        label_m = _LABEL_ONLY_LINE_RE.match(lines[i])
        value_m = _VALUE_ONLY_LINE_RE.match(lines[i + 1])
        if label_m and value_m:
            label = label_m.group("label").strip()
            label_key = label.lower()
            parsed = _parsed_value(value_m) if label and label_key not in seen_labels else None
            if parsed is not None:
                value, unit, scale = parsed
                seen_labels.add(label_key)
                candidates.append(CategoryValue(label=label, value=value, unit=unit, scale_word=scale))
                i += 2
                continue
        i += 1

    return candidates


def extract_quantitative_pairs(text: str) -> list[CategoryValue]:
    """Scan raw source text for real "Label = Value" style data (bullets,
    key-value lines, or a caption line followed by a stat-number line).
    Returns [] if nothing coherent is found — callers must never
    fabricate data to fill that gap."""
    candidates = _extract_same_line_pairs(text)

    if len(candidates) < MIN_ITEMS_FOR_CHART:
        existing = {c.label.lower() for c in candidates}
        candidates = candidates + _extract_adjacent_line_pairs(text, exclude_labels=existing)

    return _pick_largest_unit_bucket(candidates)


def build_prose_chart(text: str, title: str = "Key Figures") -> dict | None:
    pairs = extract_quantitative_pairs(text)
    if not pairs:
        return None
    return select_chart(pairs, title=title, value_label="Value")
