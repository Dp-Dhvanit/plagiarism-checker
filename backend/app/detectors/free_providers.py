"""
Genuinely free detection providers.

Every provider in this file costs nothing to run. No credit card, no metered
credits, no per-request billing. Limits checked August 2026:

  Groq       openai/gpt-oss-120b and gpt-oss-20b: 30 req/min, 1,000 req/day,
             but the BINDING limit is 200,000 tokens/day — at this project's
             ~2,000 tokens/call that is ~100 analyses/day in practice.
             (Groq's model lineup changes often — the classic Llama 3.x
             models this file originally targeted have since been retired
             from the free tier. Check console.groq.com/docs/models before
             assuming a model id still exists.)
  OpenRouter free rotating pool via ":free" model suffix; limits vary by
             model and change often
  Ollama     unlimited, fully offline, no key — you run the model yourself

Compare Gemini's free tier: genuinely free but hard-capped at 20 requests/day,
which this project exhausted during a single afternoon of testing.

Contrast with app/detectors/grok.py, which is NOT registered by default
because xAI has no free tier (metered credits only).
"""
from __future__ import annotations

import os

from app.detectors.openai_compat import OpenAICompatDetector


class GroqDetector(OpenAICompatDetector):
    """Groq — free tier, no credit card, very fast inference.

    Best free option by request volume. Key: https://console.groq.com/keys
    Model ids drift; override with GROQ_MODEL and check
    https://console.groq.com/docs/models when a 404 appears.
    """

    name = "groq"
    label = "Groq (Llama)"
    local = False
    paid = False

    env_key = "GROQ_API_KEY"
    endpoint = (
        os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
        + "/chat/completions"
    )
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    timeout = 45


class OpenRouterDetector(OpenAICompatDetector):
    """OpenRouter — free model pool via the ':free' suffix.

    Useful as a spare tyre when Groq's daily cap is reached. Free-model
    availability rotates, so treat a 404 as "pick a different model", not a
    bug. Key: https://openrouter.ai/keys
    """

    name = "openrouter"
    label = "OpenRouter (free pool)"
    local = False
    paid = False

    env_key = "OPENROUTER_API_KEY"
    endpoint = (
        os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        + "/chat/completions"
    )
    model = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    timeout = 60


class OllamaDetector(OpenAICompatDetector):
    """Ollama — fully local, unlimited, no API key, no network.

    The only option with no cap of any kind. Requires `ollama serve` running
    and the model pulled (`ollama pull llama3.2`). Quality is lower than the
    hosted 70B models, but it never runs out and nothing leaves the machine.
    """

    name = "ollama"
    label = "Ollama (local)"
    local = True
    paid = False

    env_key = "OLLAMA_MODEL"  # presence of a model name is the opt-in
    endpoint = (
        os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        + "/chat/completions"
    )
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    timeout = 120  # local CPU inference is slow

    def _headers(self) -> dict:
        # Ollama ignores auth; sending a bogus Bearer token is harmless but
        # pointless, so send only the content type.
        return {"Content-Type": "application/json"}

    def available(self) -> tuple[bool, str]:
        if not os.environ.get("OLLAMA_MODEL"):
            return False, (
                "OLLAMA_MODEL is not set. Install Ollama, run `ollama pull llama3.2`, "
                "then set OLLAMA_MODEL=llama3.2 for unlimited local detection."
            )
        return True, ""
