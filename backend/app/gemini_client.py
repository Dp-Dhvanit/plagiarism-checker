"""
Shared Gemini client access for the new AI-detection features
(text AI-probability + image AI-detection).

Kept as a separate module so app/gemini_summarizer.py's own model config
stays completely untouched — this module is used only by
app/ai_text_detector.py and app/image_detector.py. Multi-key rotation
itself lives in app/gemini_keys.py, shared with the summarizer.
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

from app import gemini_keys

load_dotenv()

logger = logging.getLogger("app.gemini")

# Flash-tier model for the text and image detectors — these need stronger
# reasoning/multimodal quality than the Flash-Lite model the summary layer
# uses. Override with GEMINI_MODEL_FLASH when Google retires a version:
# retired names fail with a 404 that names their replacement.
GEMINI_MODEL_FLASH = os.environ.get("GEMINI_MODEL_FLASH", "gemini-3.6-flash")

# Text-only calls comfortably return inside this budget.
TIMEOUT_MS = 25_000

# Multimodal image analysis is markedly slower: measured 30-47s for a single
# photo against gemini-3.6-flash, and downscaling the image does NOT help
# (the cost is model reasoning time, not upload size). The old shared 25s
# budget made image detection fail every time with 504 DEADLINE_EXCEEDED.
IMAGE_TIMEOUT_MS = 90_000


def is_configured() -> bool:
    return gemini_keys.is_configured()


def call_gemini(fn):
    """Run `fn(client)` with automatic fallback across every configured
    GEMINI_API_KEY (comma-separated) — see app/gemini_keys.py. Callers keep
    their existing try/except around this; only which key answers changes."""
    return gemini_keys.call_with_rotation(fn)


def describe_error(exc: Exception) -> str:
    """A short, user-safe reason for a Gemini failure.

    Never includes the API key, request bodies, or a stack trace — those go
    to the server log via log_failure(). This string is safe to surface in
    an API response.
    """
    msg = str(exc)
    if "no longer available" in msg or "NOT_FOUND" in msg or "404" in msg:
        return (
            f"the configured Gemini model ('{GEMINI_MODEL_FLASH}') was rejected by the API "
            "— it may have been retired for this account. Check GEMINI_MODEL_FLASH in backend/.env."
        )
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        if gemini_keys.key_count() > 1:
            return "every configured Gemini API key hit its rate limit or quota."
        return "the Gemini API rate limit or quota was exceeded."
    if "401" in msg or "403" in msg or "PERMISSION_DENIED" in msg or "API key" in msg:
        return "the Gemini API rejected the credentials. Check GEMINI_API_KEY in backend/.env."
    low = msg.lower()
    if "timeout" in low or "timed out" in low or "deadline" in low:
        return "the Gemini request timed out before the model replied."
    return f"the Gemini request failed ({type(exc).__name__})."


def log_failure(feature: str, exc: Exception) -> None:
    """Put the real error in the server terminal.

    Callers still degrade gracefully (returning None), but a silent failure
    is impossible to debug — so the full exception is always logged here.
    """
    logger.error(
        "Gemini call failed [%s] using model config "
        "(GEMINI_MODEL_FLASH=%s): %s: %s",
        feature,
        GEMINI_MODEL_FLASH,
        type(exc).__name__,
        exc,
        exc_info=True,
    )
