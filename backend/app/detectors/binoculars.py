"""
Cross-perplexity ("Binoculars"-style) detection — local, free, no API key.

Why this beats raw perplexity
-----------------------------
The existing heuristic leans 45% on single-model perplexity, which measures
how *predictable the vocabulary* is, not who wrote it. Measured consequence:
paraphrasing an LLM passage into plainer words moved perplexity 37.8 -> 75.9
and collapsed the score from 50.4 to 9.2 ("Likely Human"), while the text
was still machine-written.

Binoculars instead compares TWO models:

    score = log-perplexity(text | observer)  /  cross-perplexity(observer, performer)

The denominator captures "how surprising is this text to one model, given
what a *similar* model expected" — which normalises away the vocabulary
difficulty that defeats the single-model signal. Human text surprises the
observer far more than the performer predicts, giving a HIGH ratio; machine
text sits close to what both models expect, giving a LOW ratio.

Reference: Hans et al., "Spotting LLMs With Binoculars: Zero-Shot Detection
of Machine-Generated Text" (2024).

    ⚠ MEASURED RESULT ON THIS PROJECT'S CORPUS: IT DID NOT WORK.

Benchmarked against samples/eval/ with known provenance, three shared-vocab
model pairings all produced OVERLAPPING human/AI distributions:

    distilgpt2 + gpt2         dynamic range 0.217   not separable  (2/8)
    distilgpt2 + gpt2-medium  dynamic range 0.165   not separable*
    gpt2       + gpt2-medium  dynamic range 0.058   not separable

    * separates human from *machine-register* AI by a margin of 0.014 —
      far too thin to trust.

The published result uses ~7B-parameter pairs; at the 82M-355M scale that
runs on CPU the cross-perplexity ratio has almost no dynamic range, and
cross-architecture pairs are impossible because Binoculars requires a shared
tokenizer (OPT's 50272-token vocab vs GPT-2's 50257 raises a shape error).

It is therefore DISABLED BY DEFAULT. The implementation is kept because it
is correct and worth revisiting with larger models or a GPU. Enable with:

    ENABLE_BINOCULARS=1

Do not present its score as authoritative without re-running
backend/test_detector_eval.py and confirming separation on your own corpus.
"""
from __future__ import annotations

import math
import os

import torch

from app.detectors.base import Detector, DetectorResult

# Opt-in only — see the measured negative result in the module docstring.
ENABLED = os.environ.get("ENABLE_BINOCULARS", "").strip().lower() in {"1", "true", "yes"}

# Best-measured pairing of the three tested (still not separable on
# style-controlled AI, but the only one that split human from obvious AI).
OBSERVER_MODEL = os.environ.get("BINOCULARS_OBSERVER", "distilgpt2")
PERFORMER_MODEL = os.environ.get("BINOCULARS_PERFORMER", "gpt2-medium")

# Decision band on the Binoculars ratio. LOWER ratio = more machine-like.
# Taken from the distilgpt2/gpt2-medium measurement: human sat at
# 0.932-0.935, machine-register AI at 0.870-0.918. The band is deliberately
# narrow because the observed margin was only 0.014 — anything inside it is
# reported as uncertain rather than forced to a verdict.
RATIO_AI = 0.920     # <= this -> leans machine
RATIO_HUMAN = 0.935  # >= this -> leans human

MIN_WORDS = 40      # below this the ratio is too noisy to report
MAX_TOKENS = 1024


class BinocularsDetector(Detector):
    name = "binoculars"
    label = "cross-perplexity"
    local = True
    paid = False

    def __init__(self) -> None:
        self._obs = None
        self._perf = None
        self._tok = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_error: str | None = None

    # ── lifecycle ────────────────────────────────────────────────────────
    def _load(self) -> None:
        if self._obs is not None or self._load_error:
            return
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self._tok = AutoTokenizer.from_pretrained(OBSERVER_MODEL)
            if self._tok.pad_token is None:
                self._tok.pad_token = self._tok.eos_token
            self._obs = AutoModelForCausalLM.from_pretrained(OBSERVER_MODEL).to(self._device).eval()
            self._perf = AutoModelForCausalLM.from_pretrained(PERFORMER_MODEL).to(self._device).eval()
        except Exception as exc:  # noqa: BLE001
            self._load_error = f"could not load local models ({type(exc).__name__})"

    def available(self) -> tuple[bool, str]:
        if not ENABLED:
            return False, (
                "disabled by default — cross-perplexity did not separate human from "
                "AI text at this model scale on the project's own eval corpus. "
                "Set ENABLE_BINOCULARS=1 to experiment with it."
            )
        self._load()
        if self._load_error:
            return False, self._load_error
        return True, ""

    # ── scoring ──────────────────────────────────────────────────────────
    def _detect(self, text: str) -> DetectorResult:
        words = len(text.split())
        if words < MIN_WORDS:
            return DetectorResult.unavailable(
                self.name,
                f"needs at least {MIN_WORDS} words to be meaningful (got {words}).",
            )

        self._load()
        enc = self._tok(text, return_tensors="pt", truncation=True, max_length=MAX_TOKENS)
        ids = enc["input_ids"].to(self._device)
        if ids.shape[1] < 2:
            return DetectorResult.unavailable(self.name, "text too short to score.")

        with torch.no_grad():
            obs_logits = self._obs(ids).logits
            perf_logits = self._perf(ids).logits

        shift_labels = ids[:, 1:]
        obs_shift = obs_logits[:, :-1, :]
        perf_shift = perf_logits[:, :-1, :]

        # log-perplexity of the text under the observer
        obs_logprobs = torch.nn.functional.log_softmax(obs_shift, dim=-1)
        token_lp = obs_logprobs.gather(2, shift_labels.unsqueeze(-1)).squeeze(-1)
        log_ppl = float(-token_lp.mean())

        # cross-perplexity: observer's surprise at the PERFORMER's distribution
        perf_probs = torch.nn.functional.softmax(perf_shift, dim=-1)
        x_entropy = float(-(perf_probs * obs_logprobs).sum(dim=-1).mean())

        if x_entropy <= 1e-6:
            return DetectorResult.unavailable(self.name, "degenerate cross-entropy.")

        ratio = log_ppl / x_entropy
        score = self._ratio_to_score(ratio)

        return DetectorResult(
            provider=self.name,
            ai_probability=round(score, 1),
            verdict=DetectorResult.verdict_for(score),
            confidence=self._confidence(ratio, words),
            explanation=(
                f"Cross-perplexity ratio {ratio:.3f} "
                f"({'below' if ratio <= RATIO_AI else 'above' if ratio >= RATIO_HUMAN else 'inside'} "
                "the decision band). Lower ratios indicate text that two "
                "related language models both found unsurprising, which is "
                "characteristic of machine generation."
            ),
            signals={
                "binoculars_ratio": round(ratio, 4),
                "log_perplexity": round(log_ppl, 4),
                "cross_perplexity": round(x_entropy, 4),
                "observer_model": OBSERVER_MODEL,
                "performer_model": PERFORMER_MODEL,
                "words_scored": words,
            },
        )

    @staticmethod
    def _ratio_to_score(ratio: float) -> float:
        """Map the ratio onto 0-100, clamped, with AI at the low end."""
        if math.isnan(ratio):
            return 50.0
        if ratio <= RATIO_AI:
            # deep in machine territory; saturate toward 100
            over = (RATIO_AI - ratio) / max(RATIO_AI, 1e-6)
            return min(100.0, 75.0 + over * 200.0)
        if ratio >= RATIO_HUMAN:
            under = (ratio - RATIO_HUMAN) / max(RATIO_HUMAN, 1e-6)
            return max(0.0, 25.0 - under * 200.0)
        # inside the band -> interpolate 75 (AI edge) down to 25 (human edge)
        span = RATIO_HUMAN - RATIO_AI
        t = (ratio - RATIO_AI) / max(span, 1e-6)
        return 75.0 - t * 50.0

    @staticmethod
    def _confidence(ratio: float, words: int) -> str:
        margin = min(abs(ratio - RATIO_AI), abs(ratio - RATIO_HUMAN))
        if words < 120:
            return "low"
        if margin > 0.12:
            return "high"
        if margin > 0.05:
            return "medium"
        return "low"
