"""
Gemini 2.5 Flash structured AI-generated-content assessment (Feature 1).

This is a SECOND, independent signal shown alongside the existing local
heuristic scorer (app/scoring.py) — it does not replace it. Any failure
(no API key, network error, rate limit, timeout, invalid JSON, schema
mismatch) returns None; callers must fall back to the heuristic-only
result, exactly like app/gemini_summarizer.py already does for the
Summary feature.

Hedged-language rule enforced in the prompt: the model must never claim
certainty ("definitely AI-generated") — only likelihood/probability
language, per the project's disclaimer requirements. flagged_sections are
grounded against the source text before being returned (a quote that
doesn't actually appear in the document is dropped rather than trusted).
"""
from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.gemini_client import (
    GEMINI_MODEL_FLASH,
    TIMEOUT_MS,
    call_gemini,
    is_configured,
    log_failure,
)

_MAX_INPUT_CHARS = 8000  # cost/timeout cap — large documents are truncated, not rejected


class FlaggedSection(BaseModel):
    text: str
    reason: str = ""


class GeminiTextDetection(BaseModel):
    ai_probability: float
    confidence: Literal["low", "medium", "high"]
    flagged_sections: list[FlaggedSection] = []
    explanation: str


_PROMPT_TEMPLATE = """You are assisting with AI-generated text detection for a \
university plagiarism/AI-content checker. You will be shown a document's text. \
Estimate the LIKELIHOOD it was generated (fully or partly) by an AI language model.

This is a probabilistic estimate, NOT proof. Use hedged language such as \
"potentially AI-generated", "AI-generated likelihood", or "AI-assisted analysis" in \
your explanation — never claim the text is "definitely" AI-generated or definitely \
human-written.

For flagged_sections, only quote short passages (a sentence or short phrase) that \
appear VERBATIM in the text below, with a brief reason each was flagged (e.g. \
uniform sentence structure, generic transition phrases, unnatural formality). If \
nothing stands out, return an empty list — do not force a flag.

Respond with the requested JSON: ai_probability (0-100), confidence \
("low"/"medium"/"high" — your confidence in this specific estimate), \
flagged_sections (list of {{text, reason}}, verbatim quotes only), and a 2-4 \
sentence explanation written in hedged, non-definitive language.

TEXT:
{text}
"""


def _grounded_sections(sections: list[FlaggedSection], source_text: str) -> list[FlaggedSection]:
    """Keep only flagged quotes that actually appear in the source text."""
    normalized_source = re.sub(r"\s+", " ", source_text).lower()
    kept = []
    for s in sections:
        normalized_quote = re.sub(r"\s+", " ", s.text).strip().lower()
        if normalized_quote and normalized_quote in normalized_source:
            kept.append(s)
    return kept


def analyze_text_ai(text: str) -> GeminiTextDetection | None:
    if not is_configured():
        return None

    truncated = text[:_MAX_INPUT_CHARS]

    try:
        from google.genai import types as genai_types

        prompt = _PROMPT_TEMPLATE.format(text=truncated)
        response = call_gemini(lambda client: client.models.generate_content(
            model=GEMINI_MODEL_FLASH,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiTextDetection,
                temperature=0.2,
                http_options=genai_types.HttpOptions(timeout=TIMEOUT_MS),
            ),
        ))
        result = response.parsed
        if result is None:
            result = GeminiTextDetection.model_validate(json.loads(response.text))
        if not isinstance(result, GeminiTextDetection):
            return None

        result.flagged_sections = _grounded_sections(result.flagged_sections, truncated)
        result.ai_probability = max(0.0, min(100.0, result.ai_probability))
        return result
    except (ValidationError, json.JSONDecodeError) as exc:
        # Reached the model but couldn't parse its reply — still worth seeing.
        log_failure("text detection / response parsing", exc)
        return None
    except Exception as exc:
        log_failure("text detection", exc)
        return None
