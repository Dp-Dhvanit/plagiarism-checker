"""Common contract every detection provider implements."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger("app.detectors")

DetectorVerdict = Literal["likely_ai", "likely_human", "uncertain", "unavailable"]

# Scores in the 40-60 band are treated as genuinely inconclusive rather than
# being rounded toward a verdict. This mirrors the existing scoring.py bands.
AI_THRESHOLD = 60.0
HUMAN_THRESHOLD = 40.0


@dataclass
class DetectorResult:
    """One provider's opinion. Never a claim of certainty."""

    provider: str
    #: 0-100 estimated likelihood the text is machine-generated.
    ai_probability: float | None
    verdict: DetectorVerdict
    #: Provider's own confidence in THIS estimate: low | medium | high.
    confidence: str = "low"
    explanation: str = ""
    #: Free-form provider-specific numbers, surfaced as technical detail.
    signals: dict = field(default_factory=dict)
    #: Populated instead of a score when the provider could not run.
    error: str | None = None
    elapsed_ms: int = 0

    @property
    def ran(self) -> bool:
        return self.ai_probability is not None and self.error is None

    @staticmethod
    def verdict_for(score: float) -> DetectorVerdict:
        if score >= AI_THRESHOLD:
            return "likely_ai"
        if score <= HUMAN_THRESHOLD:
            return "likely_human"
        return "uncertain"

    @classmethod
    def unavailable(cls, provider: str, reason: str) -> "DetectorResult":
        return cls(
            provider=provider,
            ai_probability=None,
            verdict="unavailable",
            error=reason,
        )


class Detector(ABC):
    """A single detection provider.

    Implementations must never raise out of `detect()`. A provider that
    cannot run returns `DetectorResult.unavailable(...)` so one broken
    provider can't take down the whole analysis.
    """

    #: Short stable id used in API responses and the UI.
    name: str = "detector"
    #: Human-readable label.
    label: str = "Detector"
    #: True when the provider needs no network and no API key.
    local: bool = True
    #: True when the provider costs money to call.
    paid: bool = False

    @abstractmethod
    def available(self) -> tuple[bool, str]:
        """Return (usable, reason_if_not)."""

    @abstractmethod
    def _detect(self, text: str) -> DetectorResult:
        """Do the actual work. May raise; `detect()` handles failures."""

    def detect(self, text: str) -> DetectorResult:
        import time

        ok, reason = self.available()
        if not ok:
            return DetectorResult.unavailable(self.name, reason)

        t0 = time.perf_counter()
        try:
            result = self._detect(text)
        except Exception as exc:  # noqa: BLE001 - one provider must not break the run
            logger.error(
                "Detector %r failed: %s: %s", self.name, type(exc).__name__, exc, exc_info=True
            )
            return DetectorResult.unavailable(
                self.name, f"the {self.label} check failed ({type(exc).__name__})."
            )
        result.elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return result
