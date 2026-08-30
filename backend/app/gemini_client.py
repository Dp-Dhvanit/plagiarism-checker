"""
Shared Gemini client singleton for the new AI-detection features
(text AI-probability + image AI-detection).

Mirrors the lazy-singleton pattern already used in app/gemini_summarizer.py,
kept as a separate module so that file's own client/model config stay
completely untouched — this module is used only by app/ai_text_detector.py
and app/image_detector.py.
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

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

try:
    from google import genai
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False


def is_configured() -> bool:
    return _SDK_AVAILABLE and bool(os.environ.get("GEMINI_API_KEY"))


_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        _client = genai.Client(api_key=api_key)
    return _client


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
