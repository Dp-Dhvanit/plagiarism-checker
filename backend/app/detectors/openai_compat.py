"""
Base class for any OpenAI-compatible chat-completions provider.

A surprising number of providers speak the same wire format, so one adapter
covers xAI (Grok), Groq, OpenRouter, Together, DeepSeek, and a local Ollama
or LM Studio server. Subclass it, set four attributes, and register.

Uses `requests` directly rather than the `openai` SDK so the project gains no
new dependency.
"""
from __future__ import annotations

import json
import os
import re

from app.detectors.base import Detector, DetectorResult

# Same hedged framing the Gemini detector uses. The model must never claim
# certainty — this wording is load-bearing for the project's disclaimers.
PROMPT = """You are assisting with AI-generated text detection for a university \
plagiarism checker. Estimate the LIKELIHOOD that the text below was generated \
by an AI language model.

This is a probabilistic estimate, NOT proof. Never claim certainty. Consider \
that skilled human writing can look formulaic, and that AI can be prompted to \
write informally — so a plain, messy or idiosyncratic style is NOT by itself \
evidence of human authorship.

Reply with ONLY a JSON object, no prose and no code fences:
{"ai_probability": <0-100 number>, "confidence": "low"|"medium"|"high", \
"explanation": "<2-3 hedged sentences>"}

TEXT:
"""

MAX_CHARS = 8000


class OpenAICompatDetector(Detector):
    """Talks to any /v1/chat/completions endpoint."""

    #: Environment variable holding the API key.
    env_key: str = ""
    #: Full chat-completions URL.
    endpoint: str = ""
    #: Model id; usually overridable by its own env var in the subclass.
    model: str = ""
    #: Seconds before giving up.
    timeout: int = 45

    def available(self) -> tuple[bool, str]:
        if not os.environ.get(self.env_key):
            return False, f"{self.env_key} is not set on the server."
        return True, ""

    # ── request/response shaping ─────────────────────────────────────────
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {os.environ[self.env_key]}",
            "Content-Type": "application/json",
        }

    def _body(self, text: str) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": PROMPT + text[:MAX_CHARS]}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

    @staticmethod
    def _extract_json(content: str) -> dict | None:
        """Parse the reply, tolerating code fences or surrounding prose."""
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.S)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None

    # ── transport ────────────────────────────────────────────────────────
    def _detect(self, text: str) -> DetectorResult:
        import requests

        resp = requests.post(
            self.endpoint, headers=self._headers(), json=self._body(text), timeout=self.timeout
        )

        if resp.status_code in (401, 403):
            return DetectorResult.unavailable(
                self.name, f"the provider rejected the API key. Check {self.env_key}."
            )
        if resp.status_code == 429:
            return DetectorResult.unavailable(
                self.name, "the provider rate limit or credit balance was exceeded."
            )
        if resp.status_code == 404:
            return DetectorResult.unavailable(
                self.name,
                f"model {self.model!r} was not found — it may have been renamed or retired.",
            )
        if not resp.ok:
            return DetectorResult.unavailable(
                self.name, f"the provider returned HTTP {resp.status_code}."
            )

        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError):
            return DetectorResult.unavailable(
                self.name, "the provider response had an unexpected shape."
            )

        payload = self._extract_json(content)
        if payload is None or "ai_probability" not in payload:
            return DetectorResult.unavailable(
                self.name, "the provider did not return a usable score."
            )

        try:
            score = float(payload["ai_probability"])
        except (TypeError, ValueError):
            return DetectorResult.unavailable(self.name, "the returned score was not numeric.")

        if 0.0 <= score <= 1.0 and isinstance(payload["ai_probability"], float):
            score *= 100.0  # some models answer 0-1 despite the instruction
        score = max(0.0, min(100.0, score))

        confidence = str(payload.get("confidence", "medium")).lower()
        if confidence not in {"low", "medium", "high"}:
            confidence = "medium"

        return DetectorResult(
            provider=self.name,
            ai_probability=round(score, 1),
            verdict=DetectorResult.verdict_for(score),
            confidence=confidence,
            explanation=str(payload.get("explanation", ""))[:600],
            signals={"model": self.model},
        )
