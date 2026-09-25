"""
Multimodal AI-image-detection (Feature 2). Gemini primary, a free
OpenRouter vision model as fallback when Gemini is unavailable/fails.

Unlike the text pipeline there is no LOCAL heuristic fallback for images —
visual AI-detection has no equivalent to perplexity/burstiness in this
project — but it no longer has to be Gemini-or-nothing either: a second,
genuinely free provider means a Gemini outage (quota, account issue) isn't
automatically a full feature outage. If BOTH fail, that surfaces as a
clear, user-facing error ("image AI-detection unavailable") rather than a
fabricated score.

Model choice for the OpenRouter side is deliberate, not the auto-router
alias used elsewhere in this project (openrouter/free): a real check
against OpenRouter's live model catalog found the auto-router can resolve
to a content-SAFETY classifier for vision requests (returns "User Safety:
safe" instead of describing the image) rather than a genuine vision model
— useless here. nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free was
verified directly (real image description, valid structured JSON output)
and isn't proxied through Google's infrastructure, so it stays independent
of whatever is affecting the Gemini keys.

Every result is presented as an AI-assisted estimate, never proof —
enforced in the prompt wording, matching the disclaimer requirements.
"""
from __future__ import annotations

import base64
import io
import json
import os
from typing import Literal

from PIL import Image
from pydantic import BaseModel, ValidationError

from app.gemini_client import (
    GEMINI_MODEL_FLASH,
    IMAGE_TIMEOUT_MS,
    call_gemini,
    describe_error,
    is_configured,
    log_failure,
)

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
_FORMAT_TO_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}

OPENROUTER_VISION_MODEL = os.environ.get(
    "OPENROUTER_VISION_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
)
# A second, independently-hosted candidate — live testing showed the
# primary model's shared free capacity can be oversubscribed ("Upstream
# error from Nvidia: ResourceExhausted"), so one overloaded provider
# shouldn't take down the whole fallback. Tried only if the primary fails.
OPENROUTER_VISION_MODEL_2 = os.environ.get(
    "OPENROUTER_VISION_MODEL_2", "dots-studio/dots-3-note-preview:free"
)
_OPENROUTER_TIMEOUT_S = 75


class ImageDetectionResult(BaseModel):
    ai_probability: float
    confidence: Literal["low", "medium", "high"]
    classification: Literal["potentially_ai_generated", "likely_real", "uncertain"]
    indicators: list[str] = []
    explanation: str
    # Which provider actually produced this result — "gemini" (primary) or
    # "openrouter" (fallback). Transparency only.
    provider: str = "gemini"


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


def _analyze_image_gemini(data: bytes, mime_type: str) -> tuple[ImageDetectionResult | None, str | None]:
    if not is_configured():
        return None, "GEMINI_API_KEY is not set on the server."

    try:
        from google.genai import types as genai_types

        response = call_gemini(lambda client: client.models.generate_content(
            model=GEMINI_MODEL_FLASH,
            contents=[genai_types.Part.from_bytes(data=data, mime_type=mime_type), _PROMPT],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ImageDetectionResult,
                temperature=0.2,
                http_options=genai_types.HttpOptions(timeout=IMAGE_TIMEOUT_MS),
            ),
        ))
        result = response.parsed
        if result is None:
            result = ImageDetectionResult.model_validate(json.loads(response.text))
        if not isinstance(result, ImageDetectionResult):
            return None, "the Gemini response did not match the expected result format."
        result.provider = "gemini"
        result.ai_probability = max(0.0, min(100.0, result.ai_probability))
        return result, None
    except (ValidationError, json.JSONDecodeError) as exc:
        log_failure("image detection / response parsing", exc)
        return None, "the Gemini response could not be parsed."
    except Exception as exc:
        log_failure("image detection", exc)
        return None, describe_error(exc)


def _call_openrouter_vision_model(model: str, data: bytes, mime_type: str, key: str) -> tuple[ImageDetectionResult | None, str | None]:
    try:
        import requests
        from app.detectors.openai_compat import OpenAICompatDetector

        endpoint = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/") + "/chat/completions"
        b64 = base64.b64encode(data).decode("ascii")
        resp = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                    ],
                }],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=_OPENROUTER_TIMEOUT_S,
        )
        if resp.status_code in (401, 403):
            return None, "OpenRouter rejected the API key. Check OPENROUTER_API_KEY."
        if resp.status_code == 429:
            return None, "OpenRouter's rate limit or credit balance was exceeded."
        if resp.status_code == 404:
            return None, f"model {model!r} was not found — it may have been renamed or retired."
        if not resp.ok:
            return None, f"OpenRouter returned HTTP {resp.status_code}."

        body = resp.json()
        # OpenRouter can return HTTP 200 at the gateway level while the
        # underlying provider actually failed — the real error is embedded
        # in the body instead of the status code (observed live: a 200
        # wrapping "Upstream error from Nvidia: ResourceExhausted..."
        # when that free model's shared capacity is oversubscribed).
        if "error" in body:
            err = body["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            return None, f"model {model!r} is temporarily unavailable ({msg[:150]})."
        if "choices" not in body:
            return None, "the OpenRouter response had an unexpected shape."

        content = body["choices"][0]["message"]["content"]
        payload = OpenAICompatDetector._extract_json(content)
        if payload is None:
            return None, "the OpenRouter response did not contain a usable result."
        result = ImageDetectionResult.model_validate(payload)
        result.provider = "openrouter"
        result.ai_probability = max(0.0, min(100.0, result.ai_probability))
        return result, None
    except (ValidationError, json.JSONDecodeError) as exc:
        log_failure(f"image detection / openrouter ({model}) response parsing", exc)
        return None, "the OpenRouter response could not be parsed."
    except Exception as exc:
        log_failure(f"image detection / openrouter ({model})", exc)
        return None, f"the OpenRouter request failed ({type(exc).__name__})."


def _analyze_image_openrouter(data: bytes, mime_type: str) -> tuple[ImageDetectionResult | None, str | None]:
    """Fallback path — real vision models, deliberately pinned rather than
    OpenRouter's `openrouter/free` auto-router (see module docstring: the
    auto-router can resolve vision requests to a content-safety classifier
    instead of a genuine image-understanding model). Tries a second
    candidate if the first is oversubscribed/unavailable, since a single
    free model's shared capacity is not something this app controls."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None, "OPENROUTER_API_KEY is not set on the server."

    reason = None
    for model in (OPENROUTER_VISION_MODEL, OPENROUTER_VISION_MODEL_2):
        result, reason = _call_openrouter_vision_model(model, data, mime_type, key)
        if result is not None:
            return result, None
    return None, reason


def analyze_image(data: bytes, mime_type: str) -> tuple[ImageDetectionResult | None, str | None]:
    """Returns (result, reason).

    Tries Gemini first, then a free OpenRouter vision model if Gemini is
    unavailable or fails for any reason — an image-detection outage no
    longer has to mean Gemini specifically is down. On any failure of
    BOTH the result is None and `reason` describes the Gemini failure
    (the more informative one for a server operator to act on); the full
    exception for each attempt is always written to the server log.
    """
    result, reason = _analyze_image_gemini(data, mime_type)
    if result is not None:
        return result, None

    fallback_result, fallback_reason = _analyze_image_openrouter(data, mime_type)
    if fallback_result is not None:
        return fallback_result, None

    return None, reason or fallback_reason
