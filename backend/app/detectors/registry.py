"""
Which detectors the app runs, and how their opinions combine.

Register a provider by adding it to `_REGISTRY`. Anything unavailable
(missing key, missing model) is skipped automatically.
"""
from __future__ import annotations

import concurrent.futures
import os

from app.detectors.base import Detector, DetectorResult

# Backstop ceiling for the WHOLE parallel batch, not a per-provider timeout
# (each provider already enforces its own — see gemini_client.py's
# TIMEOUT_MS/IMAGE_TIMEOUT_MS and openai_compat.py's `timeout=45`). This
# only matters if some call slips past its own timeout entirely (e.g. a
# hung connection), so it rarely triggers in practice. Override with
# DETECTOR_TIMEOUT_S if you add a provider with a slower internal timeout.
_DEFAULT_TIMEOUT_S = float(os.environ.get("DETECTOR_TIMEOUT_S", "60"))
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


def get_detector(name: str) -> Detector | None:
    return next((d for d in _REGISTRY if d.name == name), None)


def in_registry_order(results: list[DetectorResult]) -> list[DetectorResult]:
    """Sort opinions the way the registry lists providers, so results the
    caller obtained separately (local score, an already-made Gemini call)
    read the same as if every provider had just run."""
    order = {d.name: i for i, d in enumerate(_REGISTRY)}
    return sorted(results, key=lambda r: order.get(r.provider, 99))


def run_all(
    text: str, timeout: float = _DEFAULT_TIMEOUT_S, exclude: set[str] | None = None
) -> list[DetectorResult]:
    """Run every available provider in parallel.

    Providers are independent, so a slow hosted call never blocks the local
    ones. Each provider already swallows its own exceptions.

    `exclude` skips providers by name — used by /analyze to avoid re-running
    the local scorer and the Gemini call, whose results the endpoint already
    has.
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

    return in_registry_order(results)


_VERDICT_LABEL = {
    "likely_ai": "Likely AI",
    "likely_human": "Likely Human",
    "uncertain": "Uncertain",
}


def headline(results: list[DetectorResult], local_label: str | None = None) -> dict:
    """The single verdict shown at the top of a result, and the reason for it.

    Deliberately conservative: a directional verdict ("Likely AI" / "Likely
    Human") is issued only when every detector that ran points the same way,
    or when only one could run — which the reason says plainly. Any
    disagreement becomes "Uncertain". Detectors are known to misjudge some
    human writing (non-native English, heavily edited text), and wrongly
    accusing someone costs more than declining to call it.

    `local_label` is the local scorer's own verdict string. It is used when
    the local detector is the only one that ran, so the single-detector case
    reads exactly as it did before detectors were combined.
    """
    ran = [r for r in results if r.ran]
    if not ran:
        return {
            "verdict": "Uncertain",
            "reason": "No detector was able to score this text.",
            "basis": "none",
        }

    labels = {d.name: d.label for d in _REGISTRY}

    if len(ran) == 1:
        only = ran[0]
        label = (
            local_label
            if only.provider == "heuristic" and local_label
            else _VERDICT_LABEL.get(only.verdict, "Uncertain")
        )
        who = labels.get(only.provider, only.provider)
        if only.provider == "heuristic" and label == "Likely AI":
            # Measured (backend/evaluation, 837 labelled essays): the local
            # detector called 8.8% of non-native English essays AI (95% CI
            # 5-16%; 0% of native writing) and caught 32.5% of AI text. Raising
            # the threshold does not fix it: at 75 it stops flagging humans but
            # also catches under 4% of AI. So on its own it cannot support an
            # accusation. It can still say the text leans that way — the score
            # and per-sentence map remain on screen.
            return {
                "verdict": "Uncertain",
                "reason": (
                    f"Only one detector ran ({who}), and it leans towards AI. On its own that is "
                    "not enough to call: in our testing it wrongly flagged roughly 1 in 11 essays "
                    "by non-native English writers and caught only about a third of AI-written text. "
                    "A second opinion is needed for a verdict."
                ),
                "basis": "single_capped",
            }
        return {
            "verdict": label,
            "reason": (
                f"Based on one detector only ({who}); "
                "no second opinion was available to corroborate it."
            ),
            "basis": "single",
        }

    verdicts = {r.verdict for r in ran}
    if len(verdicts) == 1:
        return {
            "verdict": _VERDICT_LABEL.get(next(iter(verdicts)), "Uncertain"),
            "reason": f"All {len(ran)} detectors that ran agree.",
            "basis": "agreement",
        }

    scores = [r.ai_probability for r in ran]
    return {
        "verdict": "Uncertain",
        "reason": (
            f"The {len(ran)} detectors that ran disagree "
            f"({min(scores):.0f}–{max(scores):.0f}% AI)."
        ),
        "basis": "disagreement",
    }


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
