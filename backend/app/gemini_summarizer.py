"""
Gemini semantic layer for the Summary feature.

Runs strictly AFTER the existing deterministic extraction/statistics
pipeline (app/summarizer.py, unchanged) — it never re-extracts a document
and never performs the numeric calculations itself. Its only job is to
turn already-computed real numbers into a human-readable overview and key
takeaways, and to recommend (not generate) a chart type.

Hard safety rules enforced here, not just requested via the prompt:
  - Gemini is never sent the full document/dataset — only a small,
    size-capped, already-condensed context.
  - Gemini never supplies chart data points. It may only recommend a
    chart TYPE; the actual chart shown always comes from the existing,
    already-validated chart_selector.py output (real extracted values).
  - Every "important number" Gemini reports is checked against the
    context text actually sent to it before being surfaced — if the
    value doesn't appear there, it's dropped rather than trusted.
  - Any failure at all (no API key, network error, rate limit, timeout,
    invalid JSON, schema-validation failure) returns None. Callers must
    treat None as "use the existing deterministic output, unchanged."
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from app import gemini_keys

load_dotenv()

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
_TIMEOUT_MS = 20_000
_MAX_CONTEXT_CHARS = 4000

# Local LM Studio server (OpenAI-compatible /v1/chat/completions). Tried
# FIRST when configured — it's free, offline, and has no daily cap, unlike
# Gemini's 20/day free tier. Falls back to Gemini automatically if the local
# call fails or LM Studio isn't running; never a hard dependency.
LMSTUDIO_BASE_URL = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1").rstrip("/")
LMSTUDIO_MODEL = os.environ.get("LMSTUDIO_MODEL", "")
_LMSTUDIO_TIMEOUT_S = 60

_logger = logging.getLogger("app.gemini")


def _lmstudio_configured() -> bool:
    return bool(LMSTUDIO_MODEL)


def _log_failure(feature: str, exc: Exception) -> None:
    """Surface the real cause in the server terminal. The caller still
    degrades to the deterministic summary, but never silently."""
    _logger.error(
        "Gemini call failed [%s] (GEMINI_MODEL=%s): %s: %s",
        feature,
        GEMINI_MODEL,
        type(exc).__name__,
        exc,
        exc_info=True,
    )

try:
    from google import genai
    from google.genai import types as genai_types
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
# Response schema — flat-ish, deliberately excludes chart *data* (see module
# docstring: Gemini recommends a chart type, it never emits data points).
# ══════════════════════════════════════════════════════════════════════════════

ChartTypeRec = Literal["bar", "horizontal_bar", "line", "pie", "donut", "scatter", "none"]


class GeminiVisualization(BaseModel):
    recommended: bool = False
    chart_type: ChartTypeRec = "none"
    reason: str = ""


class GeminiNumber(BaseModel):
    label: str
    value: str
    context: str = ""


class GeminiResult(BaseModel):
    title: str
    overview: str
    key_takeaways: list[str]
    important_numbers: list[GeminiNumber] = []
    visualization: GeminiVisualization = GeminiVisualization()


def is_configured() -> bool:
    return _lmstudio_configured() or (_SDK_AVAILABLE and gemini_keys.is_configured())


# ══════════════════════════════════════════════════════════════════════════════
# Compact context builders — capped size, never the raw file/full dataset.
# ══════════════════════════════════════════════════════════════════════════════

def _infer_dtype(values: list[str]) -> str:
    from app.summarizer import _parse_number
    sample = values[:20]
    if not sample:
        return "unknown"
    numeric = sum(1 for v in sample if _parse_number(v) is not None)
    if numeric >= len(sample) * 0.7:
        return "numeric"
    unique = len(set(sample))
    if unique <= 20:
        return "categorical"
    return "text"


def _column_profile(headers: list[str], rows: list[dict], max_columns: int = 25) -> list[dict]:
    """Deterministic, capped column profile (name/dtype/missing %/small
    stats) — new groundwork for the Gemini context only; does not touch or
    duplicate the existing insight-string generation in summarizer.py."""
    from app.summarizer import _parse_number

    n = len(rows)
    profile = []
    for col in headers[:max_columns]:
        raw = [r.get(col, "") for r in rows]
        present = [v.strip() for v in raw if v and v.strip()]
        missing = n - len(present)
        dtype = _infer_dtype(present)

        entry: dict[str, Any] = {
            "name": col,
            "dtype": dtype,
            "missing_pct": round(100 * missing / n, 1) if n else 0.0,
        }
        if dtype == "numeric":
            nums = [v for v in (_parse_number(x) for x in present) if v is not None]
            if nums:
                entry["min"] = round(min(nums), 2)
                entry["max"] = round(max(nums), 2)
                entry["avg"] = round(sum(nums) / len(nums), 2)
        elif dtype == "categorical":
            from collections import Counter
            top = Counter(present).most_common(5)
            entry["top_values"] = [k for k, _ in top]
        profile.append(entry)
    return profile


def _cap(obj: dict) -> dict:
    """Hard cap on serialized context size regardless of dataset size."""
    text = json.dumps(obj, default=str)
    if len(text) <= _MAX_CONTEXT_CHARS:
        return obj
    # Progressively drop lower-priority fields until it fits.
    trimmed = dict(obj)
    for key in ("sample_rows", "columns", "insights"):
        if key in trimmed and isinstance(trimmed[key], list):
            while trimmed[key] and len(json.dumps(trimmed, default=str)) > _MAX_CONTEXT_CHARS:
                trimmed[key] = trimmed[key][:-1]
    return trimmed


def build_tabular_context(filename: str, headers: list[str], rows: list[dict], insights: list[str]) -> dict:
    sample_rows = [
        {k: r.get(k, "") for k in headers[:12]}
        for r in rows[:4]
    ]
    ctx = {
        "kind": "tabular",
        "dataset_name": filename,
        "row_count": len(rows),
        "column_count": len(headers),
        "columns": _column_profile(headers, rows),
        "insights": insights,
        "sample_rows": sample_rows,
    }
    return _cap(ctx)


def build_prose_context(filename: str, doc_type: str, points: list[str], word_count: int) -> dict:
    ctx = {
        "kind": "prose",
        "document_name": filename,
        "document_type": doc_type,
        "word_count": word_count,
        "summary_points": points,
    }
    return _cap(ctx)


# ══════════════════════════════════════════════════════════════════════════════
# Prompt + call + validate
# ══════════════════════════════════════════════════════════════════════════════

_PROMPT_TEMPLATE = """You are a data/document analyst. You are given ALREADY-COMPUTED, \
real statistics and extracted content about a document or dataset — you did not see \
the original file. Your job is to interpret this information for a human reader, \
NOT to recompute or invent anything.

Strict rules:
- Every number you mention in "important_numbers" MUST be copied from the data below \
  (the exact value, or an obviously-derived rounding of it) — never invent a number, \
  column, trend, correlation, or causation that isn't directly supported by the data below.
- If the purpose/subject of the dataset cannot be confidently determined from the data \
  below, say so plainly in the overview rather than guessing.
- Do not fabricate chart data. You only RECOMMEND a chart type (bar, horizontal_bar, \
  line, pie, donut, scatter, or none) — you do not supply chart values.
- If there is no meaningful quantitative pattern worth visualizing, set \
  visualization.recommended to false and chart_type to "none".

DATA:
{context_json}

Respond with the requested JSON structure: a short "title" (a few words), a 2-4 \
sentence "overview", 3-6 "key_takeaways" (concise, human-readable, no raw \
Total/Avg/Min/Max style dumps), up to 5 "important_numbers" (each with label, value, \
and a one-sentence context — only numbers that appear in the data above), and a \
"visualization" recommendation as described above.

Reply with ONLY a JSON object, no prose and no code fences, matching exactly this shape:
{{"title": "...", "overview": "...", "key_takeaways": ["...", "..."], \
"important_numbers": [{{"label": "...", "value": "...", "context": "..."}}], \
"visualization": {{"recommended": true, "chart_type": "bar", "reason": "..."}}}}
"""


def _numbers_grounded_in_context(numbers: list[GeminiNumber], context: dict) -> list[GeminiNumber]:
    """Keep only important_numbers whose value actually appears in the
    context we sent — a cheap, effective guard against hallucinated figures."""
    context_text = json.dumps(context, default=str)

    def _normalize(s: str) -> str:
        return re.sub(r"[,\s]", "", s).lower()

    context_norm = _normalize(context_text)
    kept = []
    for num in numbers:
        digits = re.findall(r"-?\d+(?:\.\d+)?", num.value)
        if not digits:
            continue
        if all(_normalize(d) in context_norm for d in digits):
            kept.append(num)
    return kept


def _call_lmstudio(prompt: str) -> GeminiResult | None:
    """Ask a local LM Studio server (OpenAI-compatible /v1/chat/completions).

    Any failure — server not running, model not loaded, bad JSON — returns
    None so the caller falls back to Gemini or the deterministic summary,
    exactly like a Gemini failure does.
    """
    import requests
    from app.detectors.openai_compat import OpenAICompatDetector

    try:
        resp = requests.post(
            f"{LMSTUDIO_BASE_URL}/chat/completions",
            json={
                "model": LMSTUDIO_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=_LMSTUDIO_TIMEOUT_S,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        _log_failure("summary / lmstudio request", exc)
        return None

    payload = OpenAICompatDetector._extract_json(content)
    if payload is None:
        _log_failure("summary / lmstudio parsing", ValueError("no JSON object in response"))
        return None
    try:
        return GeminiResult.model_validate(payload)
    except ValidationError as exc:
        _log_failure("summary / lmstudio schema", exc)
        return None


async def enhance_summary(context: dict, kind: Literal["tabular", "prose"]) -> GeminiResult | None:
    if not is_configured():
        return None

    import asyncio

    def _call() -> GeminiResult | None:
        prompt = _PROMPT_TEMPLATE.format(context_json=json.dumps(context, default=str, indent=2))

        if _lmstudio_configured():
            result = _call_lmstudio(prompt)
            if result is not None:
                result.important_numbers = _numbers_grounded_in_context(result.important_numbers, context)
                return result
            # Local server unavailable/failed — fall through to Gemini only
            # if it's actually configured; otherwise give up here.
            if not (_SDK_AVAILABLE and gemini_keys.is_configured()):
                return None

        try:
            response = gemini_keys.call_with_rotation(lambda client: client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiResult,
                    temperature=0.2,
                    http_options=genai_types.HttpOptions(timeout=_TIMEOUT_MS),
                ),
            ))
            result = response.parsed
            if result is None:
                # Known SDK quirk: nested-schema parsing can return None
                # even when the model produced valid JSON — fall back to
                # manual parse+validate before giving up.
                result = GeminiResult.model_validate(json.loads(response.text))
            if not isinstance(result, GeminiResult):
                return None

            result.important_numbers = _numbers_grounded_in_context(result.important_numbers, context)
            return result
        except (ValidationError, json.JSONDecodeError) as exc:
            _log_failure("summary / response parsing", exc)
            return None
        except Exception as exc:
            # Any SDK/API/network failure (missing key, rate limit, timeout,
            # server error, etc.) — fall back to the deterministic pipeline,
            # but never silently: the real cause goes to the server log.
            _log_failure("summary", exc)
            return None

    return await asyncio.to_thread(_call)
