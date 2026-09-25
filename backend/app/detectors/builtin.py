"""Wrappers around the detectors the project already had."""
from __future__ import annotations

from app.detectors.base import Detector, DetectorResult


class HeuristicDetector(Detector):
    """The existing local statistical scorer (app/scoring.py).

    Kept because it is instant and offline, but note its measured limits:
    it leans heavily on vocabulary difficulty, so machine text written in a
    plain register reads as human. Treat it as one input, not a verdict.
    """

    name = "heuristic"
    label = "Local statistical"
    local = True
    paid = False

    def available(self) -> tuple[bool, str]:
        return True, ""

    def _detect(self, text: str) -> DetectorResult:
        from app.scoring import get_scorer

        r = get_scorer().analyze(text)
        return DetectorResult(
            provider=self.name,
            ai_probability=r.ai_likelihood_score,
            verdict=DetectorResult.verdict_for(r.ai_likelihood_score),
            confidence="low",
            explanation=(
                f"Perplexity {r.perplexity}, burstiness {r.burstiness}. "
                "Derived from writing-pattern statistics only."
            ),
            signals={
                "perplexity": r.perplexity,
                "burstiness": r.burstiness,
                "perplexity_signal": r.signals.perplexity_signal,
                "burstiness_signal": r.signals.burstiness_signal,
                "marker_signal": r.signals.marker_signal,
                "uniformity_signal": r.signals.uniformity_signal,
            },
        )


class GeminiDetector(Detector):
    """The existing server-side Gemini check (app/ai_text_detector.py).

    Free tier is sufficient for this project's volume.
    """

    name = "gemini"
    label = "Gemini"
    local = False
    paid = False  # free tier

    def available(self) -> tuple[bool, str]:
        from app.gemini_client import is_configured

        if not is_configured():
            return False, "GEMINI_API_KEY is not set on the server."
        return True, ""

    def _detect(self, text: str) -> DetectorResult:
        from app.ai_text_detector import analyze_text_ai

        return self.from_detection(analyze_text_ai(text))

    def from_detection(self, g) -> DetectorResult:
        """Turn an already-obtained Gemini result (or None) into this
        provider's opinion. /analyze calls Gemini once for the legacy panel
        and reuses that result here — asking twice for the same text spent
        two of the free tier's 20 daily requests per analysis."""
        ok, reason = self.available()
        if not ok:
            return DetectorResult.unavailable(self.name, reason)
        if g is None:
            return DetectorResult.unavailable(
                self.name, "the AI-assisted check did not return a usable result."
            )
        return DetectorResult(
            provider=self.name,
            ai_probability=g.ai_probability,
            verdict=DetectorResult.verdict_for(g.ai_probability),
            confidence=g.confidence,
            explanation=g.explanation,
            signals={"flagged_sections": len(g.flagged_sections)},
        )
