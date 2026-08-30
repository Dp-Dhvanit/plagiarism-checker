"""
xAI (Grok) detection provider.

Cost, checked August 2026 — read this before enabling:

  * There is NO free API tier. New accounts get $25 in signup credits.
  * Grok 4.1 Fast is roughly $0.20 per 1M input tokens.

For this project a detection call is ~1,500 input + ~200 output tokens, so
one analysis costs on the order of $0.0004. The $25 signup credit therefore
covers tens of thousands of analyses — effectively free at student-project
volume, but it IS a metered account, not a free tier. Treat the credit as
finite and keep the local detectors as the fallback.

Contrast with Gemini's free tier, which is genuinely free but hard-capped at
20 requests/day. Running both gives an independent second opinion and means
neither cap stops the app: whichever provider is unavailable is simply
skipped, and `consensus()` reports on whoever answered.

Model ids change (this project already survived a Gemini retirement mid-
build). `GROK_MODEL` is env-overridable and a 404 is reported with the model
name so the cause is obvious. Current ids: https://console.x.ai/team/default/models
"""
from __future__ import annotations

import os

from app.detectors.openai_compat import OpenAICompatDetector


class GrokDetector(OpenAICompatDetector):
    name = "grok"
    label = "Grok (xAI)"
    local = False
    paid = True  # metered credits, not a free tier

    env_key = "XAI_API_KEY"
    endpoint = os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/") + "/chat/completions"
    # Cheapest capable option by default; override in .env if renamed.
    model = os.environ.get("GROK_MODEL", "grok-4.1-fast")
    timeout = 45
