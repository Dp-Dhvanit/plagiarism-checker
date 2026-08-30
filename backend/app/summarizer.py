"""
Smart document summarizer v2 + chart data generator.

Modes:
  1. Tabular / CSV  → structured data insights + chart configs
  2. Prose text     → extractive TF-IDF + relevance chart
"""
from __future__ import annotations

import csv
import io
import re
from collections import Counter
from typing import Any, Literal

import numpy as np

from app.chart_selector import (
    CategoryValue,
    build_line_chart,
    build_prose_chart,
    select_chart,
    select_grouped_chart,
)

# ── Stopwords ─────────────────────────────────────────────────────────────────
STOPWORDS = frozenset(
    "a an the and or but in on at to for of is are was were be been being "
    "have has had do does did will would could should may might shall can "
    "it its this that these those he she they we you i me him her them us "
    "not no nor so yet both either neither as if when while than then there "
    "here about above after before between by down from into off out over "
    "through under up with within without just also only even still now "
    "very more most some each all any many much such than then well each "
    "which will from has been about would could".split()
)

DocType = Literal["health_report", "business_report", "research_paper",
                  "academic", "code_document", "general"]

DOC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "health_report": [
        "patient", "diagnosis", "treatment", "symptoms", "medication",
        "clinical", "hospital", "doctor", "physician", "abnormal",
        "blood", "pressure", "cholesterol", "biopsy", "prescription",
    ],
    "business_report": [
        "revenue", "profit", "sales", "market", "quarter", "fiscal",
        "earnings", "growth", "shareholder", "investment", "budget",
        "roi", "kpi", "strategy", "ebitda", "cost", "margin",
    ],
    "research_paper": [
        "hypothesis", "methodology", "abstract", "conclusion", "findings",
        "experiment", "dataset", "statistical", "results", "analysis",
        "literature", "sample", "correlation", "significance", "regression",
    ],
    "academic": [
        "assignment", "marks", "student", "university", "course",
        "lecture", "professor", "exam", "submission", "essay",
        "thesis", "dissertation", "grade", "semester",
    ],
    "code_document": [
        "function", "class", "method", "variable", "algorithm",
        "api", "database", "server", "implementation", "module",
        "import", "library", "framework", "repository",
    ],
}

FOCUS_KEYWORDS: dict[str, list[str]] = {
    "health_report":  ["abnormal", "critical", "urgent", "elevated", "reduced", "diagnosed", "treatment"],
    "business_report": ["increased", "decreased", "growth", "decline", "revenue", "profit", "record"],
    "research_paper":  ["found", "showed", "demonstrated", "significant", "concluded", "result", "suggest"],
    "academic":       ["therefore", "conclude", "important", "key", "main", "primary", "concept"],
    "code_document":  ["implements", "returns", "requires", "algorithm", "usage", "input", "output"],
    "general":        [],
}

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", text) if w.lower() not in STOPWORDS]


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\n{2,}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    return [s.strip() for s in sents if 20 < len(s.strip()) < 600]


def _parse_number(val: str) -> float | None:
    v = val.strip().replace(",", "").replace("$", "").replace("%", "").strip()
    try:
        return float(v)
    except ValueError:
        return None


def _is_tabular(text: str) -> bool:
    lines = [l for l in text.strip().splitlines() if l.strip()][:30]
    if len(lines) < 3:
        return False
    comma_lines = sum(1 for l in lines if l.count(",") >= 3)
    tab_lines   = sum(1 for l in lines if l.count("\t") >= 3)
    return (comma_lines + tab_lines) / len(lines) > 0.5


def _parse_csv_text(text: str) -> tuple[list[str], list[dict[str, str]]]:
    first = text.strip().splitlines()[0] if text.strip() else ""
    delimiter = "\t" if first.count("\t") > first.count(",") else ","
    reader = csv.DictReader(io.StringIO(text.strip()), delimiter=delimiter)
    headers = reader.fieldnames or []
    rows = [dict(r) for r in reader]
    return list(headers), rows


def detect_doc_type(text: str) -> DocType:
    lower = text.lower()
    scores = {dtype: sum(1 for kw in kws if kw in lower) for dtype, kws in DOC_TYPE_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else "general"  # type: ignore


# ══════════════════════════════════════════════════════════════════════════════
# Chart data generators
# ══════════════════════════════════════════════════════════════════════════════

def _column_value_counts(rows: list[dict], col: str, limit: int) -> list[CategoryValue]:
    vals = [r.get(col, "").strip() for r in rows if r.get(col, "").strip()]
    top = Counter(vals).most_common(limit)
    return [CategoryValue(label=k, value=float(v), unit="plain") for k, v in top]


def _charts_from_tabular(headers: list[str], rows: list[dict]) -> list[dict]:
    """Builds up to 4 charts from real column data, picking chart type per
    column shape (composition/time-series/many-categories/multi-metric)
    via chart_selector instead of a fixed bar/pie recipe."""
    if not headers or not rows:
        return []

    charts: list[dict] = []
    date_patterns = [r"^\d{4}-\d{2}-\d{2}$", r"^\d{1,2}/\d{1,2}/\d{4}$", r"^[A-Za-z]+ \d{4}$"]

    numeric_cols, categorical_cols, date_cols = [], [], []
    for col in headers:
        vals = [r.get(col, "").strip() for r in rows if r.get(col, "").strip()]
        if not vals:
            continue
        sample = vals[:20]
        if any(re.match(p, v) for v in sample for p in date_patterns):
            date_cols.append(col)
            continue
        num_count = sum(1 for v in sample if _parse_number(v) is not None)
        if num_count >= len(sample) * 0.7:
            numeric_cols.append(col)
            continue
        unique = {v for v in vals if v}
        if 2 <= len(unique) <= 20:
            categorical_cols.append(col)

    # Chart 1: distribution of the first categorical column (counts)
    if categorical_cols:
        col = categorical_cols[0]
        items = _column_value_counts(rows, col, limit=15)
        chart = select_chart(items, title=f"{col} Distribution", value_label="Count")
        if chart:
            charts.append(chart)

    # Chart 2: a date column plotted against the first numeric column —
    # real parsed date values, so this is built directly rather than
    # routed through select_chart's regex-based time-label guessing.
    if date_cols and numeric_cols:
        date_col, num_col = date_cols[0], numeric_cols[0]
        paired: dict[str, float] = {}
        for r in rows:
            d = r.get(date_col, "").strip()
            n = _parse_number(r.get(num_col, ""))
            if d and n is not None:
                paired[d] = paired.get(d, 0.0) + n
        if paired:
            items = [CategoryValue(label=k, value=v) for k, v in sorted(paired.items())]
            charts.append(build_line_chart(items, title=f"{num_col} over {date_col}", value_label=num_col))

    # Chart 3: multiple numeric columns sharing the first categorical
    # column -> grouped bar; otherwise fall back to a single "total by
    # category" chart, as before.
    if categorical_cols:
        cat_col = categorical_cols[0]
        cat_values = sorted({r.get(cat_col, "").strip() for r in rows if r.get(cat_col, "").strip()})
        if cat_values and len(numeric_cols) >= 2:
            series = []
            for num_col in numeric_cols[:3]:
                grouped: dict[str, float] = {}
                for r in rows:
                    cat = r.get(cat_col, "").strip()
                    num = _parse_number(r.get(num_col, ""))
                    if cat and num is not None:
                        grouped[cat] = grouped.get(cat, 0.0) + num
                series.append((num_col, [grouped.get(c, 0.0) for c in cat_values]))
            chart = select_grouped_chart(cat_values, series, title=f"{cat_col} by Metric")
            if chart:
                charts.append(chart)
        elif cat_values and numeric_cols:
            num_col = numeric_cols[0]
            grouped: dict[str, float] = {}
            for r in rows:
                cat = r.get(cat_col, "").strip()
                num = _parse_number(r.get(num_col, ""))
                if cat and num is not None:
                    grouped[cat] = grouped.get(cat, 0.0) + num
            items = [CategoryValue(label=k, value=v) for k, v in grouped.items()]
            chart = select_chart(items, title=f"Total {num_col} by {cat_col}", value_label=num_col)
            if chart:
                charts.append(chart)

    # Chart 4: distribution of a second/third categorical column
    for col in categorical_cols[1:3]:
        items = _column_value_counts(rows, col, limit=15)
        chart = select_chart(items, title=f"{col} Breakdown", value_label="Count")
        if chart:
            charts.append(chart)
        if len(charts) >= 4:
            break

    return charts[:4]  # cap at 4 charts, same as before


# ══════════════════════════════════════════════════════════════════════════════
# Tabular summarizer
# ══════════════════════════════════════════════════════════════════════════════

def summarize_tabular(text: str) -> tuple[list[str], list[dict]]:
    try:
        headers, rows = _parse_csv_text(text)
    except Exception:
        return ["Could not parse the tabular data."], []

    if not headers or not rows:
        return ["The dataset appears empty or could not be read."], []

    insights: list[str] = []
    n = len(rows)
    date_patterns = [r"^\d{4}-\d{2}-\d{2}$", r"^\d{1,2}/\d{1,2}/\d{4}$"]

    col_preview = ", ".join(f'"{h}"' for h in headers[:7])
    if len(headers) > 7:
        col_preview += f" and {len(headers) - 7} more"
    insights.append(f"The dataset contains {n:,} record{'s' if n != 1 else ''} across {len(headers)} columns: {col_preview}.")

    numeric_cols, categorical_cols, date_cols = [], [], []
    for col in headers:
        vals = [r.get(col, "").strip() for r in rows if r.get(col, "").strip()]
        if not vals:
            continue
        sample = vals[:20]
        if any(re.match(p, v) for v in sample for p in date_patterns):
            date_cols.append(col); continue
        num_count = sum(1 for v in sample if _parse_number(v) is not None)
        if num_count >= len(sample) * 0.7:
            numeric_cols.append(col); continue
        unique = {v for v in vals if v}
        if 2 <= len(unique) <= 20:
            categorical_cols.append(col)

    for col in date_cols[:1]:
        vals = sorted({r.get(col, "").strip() for r in rows if r.get(col, "").strip()})
        if vals:
            insights.append(f"Date range ({col}): {vals[0]} → {vals[-1]}.")

    for col in numeric_cols[:4]:
        nums = [_parse_number(r.get(col, "")) for r in rows]
        nums = [v for v in nums if v is not None]
        if not nums:
            continue
        total, avg = sum(nums), sum(nums) / len(nums)
        insights.append(
            f'"{col}": Total = {total:,.2f} | Avg = {avg:,.2f} | Min = {min(nums):,.2f} | Max = {max(nums):,.2f}.'
        )

    for col in categorical_cols[:4]:
        vals = [r.get(col, "").strip() for r in rows if r.get(col, "").strip()]
        unique = sorted(set(vals))
        top = Counter(vals).most_common(3)
        cat_str = ", ".join(f'"{c}"' for c in unique[:7])
        if len(unique) > 7:
            cat_str += f" … ({len(unique)} total)"
        top_str = " | ".join(f'{v}: {c:,}' for v, c in top)
        insights.append(f'"{col}" — {len(unique)} categories: {cat_str}. Top: {top_str}.')

    insights.append(
        f"Suitable for trend analysis, performance comparison, and decision-making "
        f"based on {len(numeric_cols)} numeric and {len(categorical_cols)} categorical columns."
    )

    charts = _charts_from_tabular(headers, rows)
    return insights[:9], charts


# ══════════════════════════════════════════════════════════════════════════════
# Prose extractive summarizer
# ══════════════════════════════════════════════════════════════════════════════

def extractive_summarize(text: str, n_points: int = 8, doc_type: DocType = "general") -> tuple[list[str], list[dict]]:
    sentences = _split_sentences(text)
    if not sentences:
        fallback = [s.strip() for s in text.splitlines() if len(s.strip()) > 25][:n_points]
        return (fallback or ["Could not extract meaningful content from this document."]), []

    all_words = _tokenize(text)
    freq = Counter(all_words)
    max_f = max(freq.values(), default=1)
    norm_freq = {w: f / max_f for w, f in freq.items()}
    focus = set(FOCUS_KEYWORDS.get(doc_type, []))

    scored = []
    for idx, sent in enumerate(sentences):
        words = _tokenize(sent)
        if not words:
            continue
        tfidf = sum(norm_freq.get(w, 0) for w in words) / len(words)
        pos_ratio = idx / max(len(sentences) - 1, 1)
        pos_bonus = 0.2 if pos_ratio <= 0.20 or pos_ratio >= 0.85 else 0.0
        focus_bonus = 0.15 * sum(1 for w in words if w in focus) / max(len(words), 1)
        length_ok = min(len(words) / 10.0, 1.0)
        scored.append(((tfidf + pos_bonus + focus_bonus) * length_ok, idx, sent))

    # Top n sorted by score desc, then restore document order
    top_by_score = sorted(scored, key=lambda x: x[0], reverse=True)[:n_points]
    top_by_order = sorted(top_by_score, key=lambda x: x[1])

    points = [s for _, _, s in top_by_order]

    # Chart from real numbers found in the source document (never from the
    # summary's own internal relevance ranking) — None if nothing coherent
    # is found, in which case no chart is shown rather than a fabricated one.
    chart = build_prose_chart(text, title="Key Figures")
    charts = [chart] if chart else []

    return points, charts


# ══════════════════════════════════════════════════════════════════════════════
# Main entry points
# ══════════════════════════════════════════════════════════════════════════════

def summarize_document(text: str, n_points: int = 8) -> tuple[DocType, list[str], list[dict]]:
    """Returns (doc_type, bullet_points, charts)."""
    if _is_tabular(text):
        points, charts = summarize_tabular(text)
        return "general", points, charts  # type: ignore
    doc_type = detect_doc_type(text)
    points, charts = extractive_summarize(text, n_points=n_points, doc_type=doc_type)
    return doc_type, points, charts


def summarize_csv_bytes(data: bytes) -> tuple[DocType, list[str], list[dict]]:
    text = data.decode("utf-8", errors="ignore")
    points, charts = summarize_tabular(text)
    return "general", points, charts  # type: ignore
