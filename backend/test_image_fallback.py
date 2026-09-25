"""
Regression suite for the Gemini -> OpenRouter image-detection fallback
(app/image_detector.py).

Every provider call is mocked — this suite makes:

    0 real Gemini API calls
    0 real OpenRouter API calls

    cd backend
    python test_image_fallback.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import image_detector

passed = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print("=" * 70)
    print("1 — Gemini succeeds -> OpenRouter never called")
    print("=" * 70)
    openrouter_calls = []
    good_result = image_detector.ImageDetectionResult(
        ai_probability=72.0, confidence="medium", classification="potentially_ai_generated",
        indicators=["unnatural smoothness"], explanation="Looks synthetic.",
    )
    image_detector._analyze_image_gemini = lambda data, mime: (good_result, None)
    image_detector._analyze_image_openrouter = lambda data, mime: (openrouter_calls.append(1), (None, "should not be called"))[1]

    result, reason = image_detector.analyze_image(b"fake-bytes", "image/png")
    check("result returned", result is not None)
    check("provider is gemini", result.provider == "gemini", result.provider)
    check("openrouter was never called", len(openrouter_calls) == 0, f"{len(openrouter_calls)} call(s)")
    check("reason is None on success", reason is None)

    print("\n" + "=" * 70)
    print("2 — Gemini fails -> OpenRouter fallback succeeds")
    print("=" * 70)
    fallback_result = image_detector.ImageDetectionResult(
        ai_probability=30.0, confidence="low", classification="likely_real",
        indicators=[], explanation="Looks like an ordinary photo.", provider="openrouter",
    )
    image_detector._analyze_image_gemini = lambda data, mime: (None, "GEMINI_API_KEY quota exceeded")
    image_detector._analyze_image_openrouter = lambda data, mime: (fallback_result, None)

    result, reason = image_detector.analyze_image(b"fake-bytes", "image/png")
    check("result returned from fallback", result is not None)
    check("provider is openrouter", result.provider == "openrouter", result.provider)
    check("reason is None on fallback success (not surfaced as an error)", reason is None)

    print("\n" + "=" * 70)
    print("3 — both providers fail -> clean 'unavailable' result, Gemini's reason surfaces")
    print("=" * 70)
    image_detector._analyze_image_gemini = lambda data, mime: (None, "Gemini quota exceeded")
    image_detector._analyze_image_openrouter = lambda data, mime: (None, "OpenRouter also unavailable")

    result, reason = image_detector.analyze_image(b"fake-bytes", "image/png")
    check("result is None", result is None)
    check("the more informative (Gemini) reason is surfaced", reason == "Gemini quota exceeded", reason)

    print("\n" + "=" * 70)
    print("4 — Gemini fails with no reason at all -> OpenRouter's reason surfaces instead")
    print("=" * 70)
    image_detector._analyze_image_gemini = lambda data, mime: (None, None)
    image_detector._analyze_image_openrouter = lambda data, mime: (None, "OpenRouter reason")

    result, reason = image_detector.analyze_image(b"fake-bytes", "image/png")
    check("result is None", result is None)
    check("falls back to OpenRouter's reason when Gemini's is empty", reason == "OpenRouter reason", reason)

    print("\n" + "=" * 70)
    print(f"{passed}/{passed + failed} checks passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
