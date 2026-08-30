"""
Gemini 2.5 Flash multimodal AI-image-detection (Feature 2).

Unlike the text pipeline there is no local heuristic fallback for images —
visual AI-detection has no equivalent to perplexity/burstiness in this
project, so a Gemini failure surfaces as a clear, user-facing error
("image AI-detection unavailable") rather than a fabricated score.

Every result is presented as an AI-assisted estimate, never proof —
enforced in the prompt wording, matching the disclaimer requirements.
"""
from __future__ import annotations

import io
import json
from typing import Literal

from PIL import Image
from pydantic import BaseModel, ValidationError

from app.gemini_client import (
    GEMINI_MODEL_FLASH,
    IMAGE_TIMEOUT_MS,
    describe_error,
    get_client,
    is_configured,
    log_failure,
)

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
_FORMAT_TO_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class ImageDetectionResult(BaseModel):
    ai_probability: float
    confidence: Literal["low", "medium", "high"]
    classification: Literal["potentially_ai_generated", "likely_real", "uncertain"]
    indicators: list[str] = []
    explanation: str


class ImageValidationError(ValueError):
    pass


def validate_image(data: bytes) -> str:
    """Verifies the bytes are a real, undamaged JPG/PNG/WEBP image and
    returns its MIME type. Raises ImageValidationError with a
    user-friendly message otherwise (never a raw exception/stack trace)."""
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageValidationError(
            f"Image is too large ({len(data) / (1024 * 1024):.1f} MB). "
            f"Maximum allowed size is {MAX_IMAGE_BYTES // (1024 * 1024)} MB."
        )
    if not data:
        raise ImageValidationError("The uploaded file is empty.")
    try:
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or "").upper()
        img.verify()
    except Exception:
        raise ImageValidationError(
            "This file is not a valid image or is corrupted. Supported formats: JPG, JPEG, PNG, WEBP."
        )
    mime = _FORMAT_TO_MIME.get(fmt)
    if not mime:
        raise ImageValidationError(
            f"Unsupported image format ({fmt or 'unknown'}). Supported formats: JPG, JPEG, PNG, WEBP."
        )
    return mime


_PROMPT = """You are assisting with AI-generated image detection for a university \
project. Examine the attached image and estimate the LIKELIHOOD it was generated or \
heavily manipulated by an AI image generator (e.g. Midjourney, DALL-E, Stable \
Diffusion, Gemini image generation).

This is a probabilistic, AI-assisted VISUAL estimate — it is NOT definitive proof \
that the image is or isn't AI-generated. Never claim certainty. Use hedged language \
in your explanation ("potentially AI-generated", "likely real", "uncertain") rather \
than absolute claims.

Look for indicators such as: unusual texture patterns, anatomical inconsistencies \
(hands, eyes, teeth), lighting/shadow inconsistencies, repeated or tiled patterns, \
unnatural smoothness, warped background/text, or inconsistent reflections. Only list \
indicators you actually observe in THIS image — do not list generic boilerplate that \
doesn't apply.

Respond with the requested JSON: ai_probability (0-100, your estimated likelihood), \
confidence ("low"/"medium"/"high" — your confidence in this specific estimate), \
classification ("potentially_ai_generated" / "likely_real" / "uncertain"), indicators \
(specific observations, empty list if nothing stood out), and a 2-4 sentence \
explanation written in hedged, non-definitive language.
"""


def analyze_image(data: bytes, mime_type: str) -> tuple[ImageDetectionResult | None, str | None]:
    """Returns (result, reason).

    On any failure (not configured, network error, rate limit, timeout,
    invalid JSON) the result is None and `reason` is a short, user-safe
    explanation — callers must surface that rather than a fabricated score.
    The full exception is always written to the server log.
    """
    if not is_configured():
        return None, (
            "GEMINI_API_KEY is not set on the server, so image detection is disabled. "
            "See backend/.env.example."
        )

    try:
        from google.genai import types as genai_types

        client = get_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL_FLASH,
            contents=[genai_types.Part.from_bytes(data=data, mime_type=mime_type), _PROMPT],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ImageDetectionResult,
                temperature=0.2,
                http_options=genai_types.HttpOptions(timeout=IMAGE_TIMEOUT_MS),
            ),
        )
        result = response.parsed
        if result is None:
            result = ImageDetectionResult.model_validate(json.loads(response.text))
        if not isinstance(result, ImageDetectionResult):
            return None, "the Gemini response did not match the expected result format."
        result.ai_probability = max(0.0, min(100.0, result.ai_probability))
        return result, None
    except (ValidationError, json.JSONDecodeError) as exc:
        log_failure("image detection / response parsing", exc)
        return None, "the Gemini response could not be parsed."
    except Exception as exc:
        log_failure("image detection", exc)
        return None, describe_error(exc)
