"""
Template for a hosted detection API — COPY THIS FILE to add a provider.

Nothing here is enabled by default. `available()` returns False unless the
provider's API key is present in the environment, so the app behaves exactly
as before until you opt in.

To add a provider (e.g. GPTZero, Sapling, Winston, Originality):

  1. Copy this file to `app/detectors/<provider>.py`.
  2. Fill in ENV_KEY, ENDPOINT, and the two adapter methods
     `_build_request()` and `_parse_response()`.
  3. Register it in `app/detectors/registry.py`.
  4. Put the key in `backend/.env` and document it in `.env.example`.

Cost warning: most hosted detectors are PAID per request. Set `paid = True`
so the UI can label it, and keep it disabled unless you intend to spend.
The two local providers (heuristic, binoculars) stay free forever.
"""
from __future__ import annotations

import os

from app.detectors.base import Detector, DetectorResult

# ── Fill these in ────────────────────────────────────────────────────────
ENV_KEY = "EXAMPLE_DETECTOR_API_KEY"   # env var holding the key
ENDPOINT = "https://api.example.com/v1/detect"
TIMEOUT_SECONDS = 30
MAX_CHARS = 8000                       # truncate to control cost/latency


class HttpDetector(Detector):
    """Generic JSON-over-HTTP detection provider."""

    name = "example"
    label = "Example hosted detector"
    local = False
    paid = True          # flip to False only if the provider is genuinely free

    def available(self) -> tuple[bool, str]:
        if not os.environ.get(ENV_KEY):
            return False, f"{ENV_KEY} is not set on the server."
        try:
            import requests  # noqa: F401
        except ImportError:
            return False, "the 'requests' package is not installed."
        return True, ""

    # ── Adapter: shape the request the provider expects ──────────────────
    def _build_request(self, text: str) -> tuple[dict, dict]:
        """Return (headers, json_body)."""
        key = os.environ[ENV_KEY]
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        body = {"text": text[:MAX_CHARS]}
        return headers, body

    # ── Adapter: pull a 0-100 score out of whatever JSON comes back ──────
    def _parse_response(self, payload: dict) -> DetectorResult:
        """Map the provider's JSON onto DetectorResult.

        Adjust the key paths below to match the provider's schema. Return
        `DetectorResult.unavailable(...)` if the shape is unrecognised —
        never invent a score.
        """
        raw = payload.get("ai_probability")
        if raw is None:
            raw = payload.get("score")
        if raw is None:
            return DetectorResult.unavailable(
                self.name, "the provider response did not contain a score."
            )

        score = float(raw)
        if 0.0 <= score <= 1.0:      # some providers return 0-1
            score *= 100.0
        score = max(0.0, min(100.0, score))

        return DetectorResult(
            provider=self.name,
            ai_probability=round(score, 1),
            verdict=DetectorResult.verdict_for(score),
            confidence=str(payload.get("confidence", "medium")),
            explanation=str(payload.get("explanation", ""))[:600],
            signals={k: v for k, v in payload.items() if isinstance(v, (int, float, str))},
        )

    # ── Transport (rarely needs changing) ────────────────────────────────
    def _detect(self, text: str) -> DetectorResult:
        import requests

        headers, body = self._build_request(text)
        resp = requests.post(ENDPOINT, headers=headers, json=body, timeout=TIMEOUT_SECONDS)

        if resp.status_code == 401 or resp.status_code == 403:
            return DetectorResult.unavailable(self.name, "the provider rejected the API key.")
        if resp.status_code == 429:
            return DetectorResult.unavailable(self.name, "the provider rate limit was exceeded.")
        if not resp.ok:
            return DetectorResult.unavailable(
                self.name, f"the provider returned HTTP {resp.status_code}."
            )

        return self._parse_response(resp.json())
