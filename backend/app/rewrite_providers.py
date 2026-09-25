"""
AI-generated rewrite candidates for the Remove Plagiarism feature
(app/originality_rewriter.py).

These functions only ever GENERATE a candidate rewrite of a short,
already-identified passage — they are never the plagiarism detector and
their output is never trusted on its own. app/similarity.py's
analyze_similarity() remains the sole source of truth for whether a
candidate actually helped; validate_candidate() below only screens out
obviously-broken output before spending a similarity check on it.

Deliberately NOT built on app/detectors/openai_compat.py: that adapter's
request/response contract is fixed to AI-probability detection
({"ai_probability", "confidence", "explanation"}), which doesn't fit
"return rewritten text." Same wire conventions (raw requests.post, same
header/timeout/error-handling style), different response shape — a sibling,
not a reuse-by-force.

Every _*_rewrite() function returns the raw provider text on success, or
None on ANY failure (missing key, network error, bad response, provider
not configured) — callers must treat None as "this source is unavailable
right now" and move on to the next one, never crash.
"""
from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger("app.rewrite_providers")

REWRITE_PROMPT = """You are rewriting a short passage that was flagged as \
copied/overlapping with another document, so it needs different phrasing \
while keeping the exact same meaning.

Rules — follow exactly:
- Preserve names, dates, numbers, citations, URLs, code, technical terms, \
and factual meaning EXACTLY as given. Never invent, remove, or alter any of these.
- Restructure sentence order and clause structure naturally. Do not just \
swap individual words for synonyms.
- Do not add commentary, explanation, headers, or code fences.
- Output ONLY the rewritten passage, nothing else — no preamble, no quotes around it.

PASSAGE:
{passage}
"""

# A flagged run is always a short excerpt, never a full document — this cap
# is a cost/timeout guard, not a truncation of real usage.
MAX_PASSAGE_CHARS = 4000

_META_COMMENTARY_MARKERS = (
    "here's the rewritten", "here is the rewritten", "as an ai", "i cannot",
    "i'm sorry", "i am sorry", "as a language model", "rewritten passage:",
    "rewritten text:", "sure, here", "sure! here",
)


def _looks_like_meta_commentary(text: str) -> bool:
    low = text.strip().lower()
    return any(low.startswith(m) for m in _META_COMMENTARY_MARKERS)


def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def validate_candidate(original_passage: str, candidate: str) -> tuple[bool, str]:
    """Cheap, local, deterministic checks BEFORE a candidate is even worth
    running through analyze_similarity(). Returns (ok, reason_if_rejected)."""
    if not candidate or not candidate.strip():
        return False, "empty response"
    cleaned = strip_code_fences(candidate)
    if not cleaned:
        return False, "empty after stripping code fences"
    if _looks_like_meta_commentary(cleaned):
        return False, "contains meta-commentary rather than just the rewrite"
    ratio = len(cleaned) / max(len(original_passage), 1)
    if not (0.5 <= ratio <= 2.0):
        return False, f"length ratio {ratio:.2f} outside safe bounds (likely truncated or padded)"
    return True, ""


def _openai_compat_rewrite(endpoint: str, key: str, model: str, passage: str, timeout: int) -> str | None:
    import requests

    try:
        resp = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": REWRITE_PROMPT.format(passage=passage[:MAX_PASSAGE_CHARS])}],
                "temperature": 0.4,
            },
            timeout=timeout,
        )
        if not resp.ok:
            logger.info("rewrite provider HTTP %s from %s", resp.status_code, endpoint)
            return None
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001 — any failure here just means "try the next source"
        logger.info("rewrite provider call failed (%s): %s", endpoint, exc)
        return None


def groq_rewrite(passage: str) -> str | None:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    endpoint = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/") + "/chat/completions"
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    return _openai_compat_rewrite(endpoint, key, model, passage, timeout=45)


def openrouter_rewrite(passage: str) -> str | None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    endpoint = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/") + "/chat/completions"
    model = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
    return _openai_compat_rewrite(endpoint, key, model, passage, timeout=60)


def gemini_rewrite(passage: str) -> str | None:
    """Reuses the EXISTING Gemini client/key-rotation infrastructure
    (app/gemini_client.py, app/gemini_keys.py) — no second Gemini client."""
    try:
        from app import gemini_keys
        from app.gemini_client import GEMINI_MODEL_FLASH, TIMEOUT_MS, is_configured

        if not is_configured():
            return None
        from google.genai import types as genai_types

        def _call(client):
            return client.models.generate_content(
                model=GEMINI_MODEL_FLASH,
                contents=REWRITE_PROMPT.format(passage=passage[:MAX_PASSAGE_CHARS]),
                config=genai_types.GenerateContentConfig(
                    temperature=0.4,
                    http_options=genai_types.HttpOptions(timeout=TIMEOUT_MS),
                ),
            )

        response = gemini_keys.call_with_rotation(_call)
        return response.text
    except Exception as exc:  # noqa: BLE001
        logger.info("gemini rewrite call failed: %s", exc)
        return None


# Looked up by name at CALL TIME (not imported individually) so tests can
# monkeypatch entries here without touching originality_rewriter.py.
PROVIDERS: dict[str, "callable"] = {
    "groq": groq_rewrite,
    "openrouter": openrouter_rewrite,
    "gemini": gemini_rewrite,
}
