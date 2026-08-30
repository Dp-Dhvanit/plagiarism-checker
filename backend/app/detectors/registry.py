"""
Which detectors the app runs, and how their opinions combine.

Register a provider by adding it to `_REGISTRY`. Anything unavailable
(missing key, missing model) is skipped automatically.
"""
from __future__ import annotations

import concurrent.futures

from app.detectors.base import Detector, DetectorResult
from app.detectors.binoculars import BinocularsDetector
from app.detectors.builtin import GeminiDetector, HeuristicDetector
from app.detectors.free_providers import (
    GroqDetector,
    OllamaDetector,
    OpenRouterDetector,
)

# EVERY provider registered here is free to run. Each self-disables when its
# key is missing, so the list is safe to leave fully populated — nothing is
# called, and nothing is billed, until you add a key.
#
# Deliberately NOT registered: app/detectors/grok.py (xAI). It works and is
# kept as a worked example, but xAI has no free tier — only metered credits.
# Add `GrokDetector()` here if you ever decide to pay for it.
_REGISTRY: list[Detector] = [
    HeuristicDetector(),
    # Self-disabling: benchmarking showed cross-perplexity does not separate
    # human from AI text at CPU model scale. ENABLE_BINOCULARS=1 to opt in.
    BinocularsDetector(),
    # Hosted second opinions, best free allowance first.
    GroqDetector(),        # 1,000/day (70B) — the most generous free tier
    GeminiDetector(),      # genuinely free but only 20/day
    OpenRouterDetector(),  # free rotating model pool
    OllamaDetector(),      # unlimited, fully local, no key
]


def available_detectors() -> list[dict]:
    """Report which providers are usable right now, for diagnostics/UI."""
    out = []
    for d in _REGISTRY:
        ok, reason = d.available()
        out.append(
            {
                "name": d.name,
                "label": d.label,
                "local": d.local,
                "paid": d.paid,
                "available": ok,
                "reason": reason,
            }
        )
    return out


def run_all(
    text: str, timeout: float = 120.0, exclude: set[str] | None = None
) -> list[DetectorResult]:
    """Run every available provider in parallel.

    Providers are independent, so a slow hosted call never blocks the local
    ones. Each provider already swallows its own exceptions.

    `exclude` skips providers by name — used by /analyze to avoid re-running
    the local scorer, whose result the endpoint already has.
    """
    exclude = exclude or set()
    selected = [d for d in _REGISTRY if d.name not in exclude]

    results: list[DetectorResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected) or 1) as pool:
        futures = {pool.submit(d.detect, text): d for d in selected}
        for fut in concurrent.futures.as_completed(futures, timeout=timeout):
            det = futures[fut]
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                results.append(
                    DetectorResult.unavailable(det.name, f"provider crashed ({type(exc).__name__}).")
                )

    order = {d.name: i for i, d in enumerate(_REGISTRY)}
    results.sort(key=lambda r: order.get(r.provider, 99))
    return results


def consensus(results: list[DetectorResult]) -> dict:
    """Combine provider opinions WITHOUT inventing precision.

    Deliberately does not average scores into one authoritative number.
    Detectors that disagree are reported as disagreeing — that IS the
    finding, and hiding it behind a mean would overstate confidence.
    """
    ran = [r for r in results if r.ran]
    if not ran:
        return {
            "agreement": "none",
            "summary": "No detector was able to score this text.",
            "providers_ran": 0,
        }

    verdicts = {r.verdict for r in ran}
    scores = [r.ai_probability for r in ran]
    spread = max(scores) - min(scores)

    # One detector agreeing with itself is not consensus — say so plainly
    # rather than dressing a single opinion up as corroboration.
    if len(ran) == 1:
        only = ran[0]
        return {
            "agreement": "single",
            "summary": (
                f"Only one detector could score this text ({only.provider}). "
                "There is no second opinion to corroborate it."
            ),
            "providers_ran": 1,
            "min_score": round(only.ai_probability, 1),
            "max_score": round(only.ai_probability, 1),
            "spread": 0.0,
        }

    if len(verdicts) == 1:
        agreement = "unanimous"
        summary = f"All {len(ran)} detectors agree: {next(iter(verdicts)).replace('_', ' ')}."
    elif spread >= 40:
        agreement = "conflicted"
        summary = (
            f"Detectors disagree sharply ({min(scores):.0f}-{max(scores):.0f}). "
            "Treat this result as inconclusive."
        )
    else:
        agreement = "mixed"
        summary = f"Detectors partially agree ({min(scores):.0f}-{max(scores):.0f})."

    return {
        "agreement": agreement,
        "summary": summary,
        "providers_ran": len(ran),
        "min_score": round(min(scores), 1),
        "max_score": round(max(scores), 1),
        "spread": round(spread, 1),
    }
