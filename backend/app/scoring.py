"""
Perplexity + burstiness + AI-marker + sentence-uniformity scoring.

Uses DistilGPT-2 token log-probs PLUS four heuristic signals calibrated
on real AI-generator output (Gamma, Beautiful.ai, Canva AI, ChatGPT).
Lower perplexity + lower burstiness + more AI buzzwords + more uniform
sentence lengths → higher AI likelihood score.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# ── Weights (tuned for PPT/PDF + prose) ─────────────────────────────────────
PERPLEXITY_WEIGHT  = 0.45   # GPT-2 perplexity — most reliable signal
BURSTINESS_WEIGHT  = 0.15   # per-sentence perplexity uniformity
MARKER_WEIGHT      = 0.15   # AI buzzword / transition phrase density
UNIFORMITY_WEIGHT  = 0.25   # sentence-length uniformity

# ── Perplexity thresholds ───────────────────────────────────────────────────
PPL_LOW  = 10.0   # ≤ this → strongly AI-like
PPL_HIGH = 60.0   # ≥ this → strongly human-like

# ── Burstiness thresholds ──────────────────────────────────────────────────
BURST_LOW  = 3.0
BURST_HIGH = 80.0   # widened — real AI text can show burst up to ~80

# ── Known AI "tell" words / phrases  (from research on Gamma, ChatGPT, etc.)
AI_TELLS: frozenset[str] = frozenset({
    # transition crutches
    "furthermore", "moreover", "consequently", "additionally",
    "in conclusion", "in summary", "to summarize", "as a result",
    "it is important to note", "it is worth noting", "it should be noted",
    "notably", "significantly", "ultimately", "overall", "in essence",
    "therefore", "thus", "hence", "accordingly", "subsequently",
    "in particular", "in today's world", "in today's fast-paced world",
    "plays a crucial role", "plays a critical role", "plays a key role",
    "plays an important role", "is essential", "are essential",
    "is crucial", "are crucial",
    # AI-favoured buzzwords (Pangram / research lists)
    "delve", "leverage", "leverages", "leveraged", "pivotal",
    "comprehensive", "nuance", "nuanced", "foster", "fosters",
    "landscape", "paradigm", "robust", "seamless", "synergy",
    "utilize", "utilizes", "utilized", "streamline", "streamlines",
    "empower", "empowers", "holistic", "proactive", "scalable",
    "innovative", "encompass", "encompasses", "facilitate", "facilitates",
    "underscores", "underscore", "highlight", "highlights",
    "demonstrate", "demonstrates", "ensure", "ensures",
    "crucial", "vital", "imperative", "fundamental", "transformative",
    "groundbreaking", "cutting-edge", "state-of-the-art",
    "best practices", "key takeaways", "moving forward",
    "going forward", "at the end of the day", "it goes without saying",
    "needless to say", "in order to", "due to the fact that",
})

Verdict = Literal["Likely Human", "Likely AI", "Uncertain"]

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class SentenceScore:
    sentence: str
    perplexity: float


@dataclass
class Signals:
    perplexity_signal:  float
    burstiness_signal:  float
    marker_signal:      float
    uniformity_signal:  float


@dataclass
class AnalysisResult:
    ai_likelihood_score: float
    perplexity: float
    burstiness: float
    verdict: Verdict
    sentence_breakdown: list[SentenceScore]
    signals: Signals = field(default_factory=lambda: Signals(0, 0, 0, 0))


class TextScorer:
    """Lazy-loads a causal LM and scores text for AI likelihood."""

    def __init__(self, model_name: str = "distilgpt2") -> None:
        self.model_name = model_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._tokenizer = None
        self._model = None

    def load(self) -> None:
        if self._model is not None:
            return
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForCausalLM.from_pretrained(self.model_name)
        self._model.to(self.device)
        self._model.eval()
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

    @property
    def tokenizer(self):
        self.load(); return self._tokenizer

    @property
    def model(self):
        self.load(); return self._model

    # ── Text helpers ──────────────────────────────────────────────────────────

    def split_sentences(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        return [p.strip() for p in _SENTENCE_SPLIT.split(text) if p.strip()]

    # ── Perplexity (GPT-2 token NLL) ─────────────────────────────────────────

    def token_nlls(self, text: str) -> list[float]:
        self.load()
        enc = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=1024)
        input_ids = enc["input_ids"].to(self.device)
        if input_ids.shape[1] < 2:
            return []
        with torch.no_grad():
            outputs = self.model(input_ids)
            logits = outputs.logits
        shift_logits = logits[:, :-1, :].contiguous()
        shift_labels = input_ids[:, 1:].contiguous()
        log_probs = torch.nn.functional.log_softmax(shift_logits, dim=-1)
        token_log_probs = log_probs.gather(2, shift_labels.unsqueeze(-1)).squeeze(-1)
        return (-token_log_probs[0]).cpu().tolist()

    def perplexity(self, text: str) -> float:
        nlls = self.token_nlls(text)
        if not nlls:
            return float("nan")
        return float(math.exp(sum(nlls) / len(nlls)))

    def sentence_perplexities(self, text: str) -> list[SentenceScore]:
        results: list[SentenceScore] = []
        for sent in self.split_sentences(text):
            if len(sent.split()) < 3:
                continue
            ppl = self.perplexity(sent)
            if math.isnan(ppl):
                continue
            results.append(SentenceScore(sentence=sent, perplexity=round(ppl, 2)))
        return results

    def burstiness(self, sentence_scores: list[SentenceScore]) -> float:
        """Median absolute deviation of per-sentence perplexity.

        MAD is more robust than std to a single outlier sentence
        that would otherwise inflate burstiness and mask AI text.

        Returns NaN (not 0.0) when there isn't enough sentence data to
        measure burstiness at all — 0.0 would be normalized downstream as
        "confidently uniform / AI-like", which misrepresents "unmeasurable"
        as "measured and low". NaN flows into `_normalize_ai_signal`, which
        already maps NaN to a neutral 0.5 signal.
        """
        if len(sentence_scores) < 2:
            return float("nan")
        values = np.array([s.perplexity for s in sentence_scores], dtype=float)
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        return mad

    # ── AI-marker density ─────────────────────────────────────────────────────

    def marker_density(self, text: str) -> float:
        """
        Fraction of AI-tell tokens found in text.
        Checks both unigrams and bigrams against AI_TELLS.
        Returns 0-1 where 1 = very high AI-tell density.
        """
        lower = text.lower()
        words = re.findall(r"\b[a-z]+\b", lower)
        if not words:
            return 0.0
        bigrams = [words[i] + " " + words[i + 1] for i in range(len(words) - 1)]
        hits = sum(1 for w in words   if w in AI_TELLS)
        hits += sum(1 for b in bigrams if b in AI_TELLS)
        # normalise: ~1 hit per 30 words is already quite AI-like
        density = hits / max(len(words), 1)
        return float(min(density * 30, 1.0))

    # ── Sentence-length uniformity ────────────────────────────────────────────

    def sentence_uniformity(self, text: str) -> float:
        """
        Coefficient of variation (std/mean) of sentence word-counts.
        Low CV → uniform → AI-like.  Returns a 0-1 AI signal.
        """
        sents = [s for s in self.split_sentences(text) if len(s.split()) >= 3]
        lengths = [len(s.split()) for s in sents]
        if len(lengths) < 2:
            return 0.5   # not enough data → neutral
        mean = float(np.mean(lengths))
        std  = float(np.std(lengths, ddof=0))
        cv   = std / (mean + 1e-8)
        # CV typical ranges: AI ~0.05-0.25, human ~0.35-0.80
        # Map: cv=0 → AI signal 1.0, cv≥0.5 → AI signal 0.0
        ai_signal = 1.0 - min(cv / 0.50, 1.0)
        return float(max(0.0, min(1.0, ai_signal)))

    # ── Normalisation helper ──────────────────────────────────────────────────

    @staticmethod
    def _normalize_ai_signal(value: float, low: float, high: float) -> float:
        if math.isnan(value):
            return 0.5
        if high <= low:
            return 0.5
        t = (value - low) / (high - low)
        t = max(0.0, min(1.0, t))
        return 1.0 - t   # lower raw → higher AI signal

    # ── Combined score ────────────────────────────────────────────────────────

    def ai_likelihood(
        self,
        perplexity: float,
        burstiness: float,
        marker_sig: float,
        uniformity_sig: float,
    ) -> tuple[float, Signals]:
        ppl_sig   = self._normalize_ai_signal(perplexity,  PPL_LOW,   PPL_HIGH)
        burst_sig = self._normalize_ai_signal(burstiness,  BURST_LOW, BURST_HIGH)

        signals = Signals(
            perplexity_signal  = round(ppl_sig,        3),
            burstiness_signal  = round(burst_sig,       3),
            marker_signal      = round(marker_sig,      3),
            uniformity_signal  = round(uniformity_sig,  3),
        )

        total_w = (PERPLEXITY_WEIGHT + BURSTINESS_WEIGHT
                   + MARKER_WEIGHT + UNIFORMITY_WEIGHT)
        raw = (
            PERPLEXITY_WEIGHT  * ppl_sig
            + BURSTINESS_WEIGHT  * burst_sig
            + MARKER_WEIGHT      * marker_sig
            + UNIFORMITY_WEIGHT  * uniformity_sig
        ) / total_w

        score = round(max(0.0, min(100.0, raw * 100)), 1)
        return score, signals

    @staticmethod
    def verdict_from_score(score: float) -> Verdict:
        if score >= 60:
            return "Likely AI"
        if score <= 40:
            return "Likely Human"
        return "Uncertain"

    # ── Main entry point ──────────────────────────────────────────────────────

    def analyze(
        self,
        text: str,
        ppl_weight: float | None = None,
        burst_weight: float | None = None,
    ) -> AnalysisResult:
        text = (text or "").strip()
        if not text:
            return AnalysisResult(
                ai_likelihood_score=0.0,
                perplexity=0.0,
                burstiness=0.0,
                verdict="Uncertain",
                sentence_breakdown=[],
                signals=Signals(0, 0, 0, 0),
            )

        overall_ppl    = self.perplexity(text)
        sentence_scores = self.sentence_perplexities(text)
        burst           = self.burstiness(sentence_scores)
        marker_sig      = self.marker_density(text)
        uniformity_sig  = self.sentence_uniformity(text)

        # Score from the RAW (possibly-NaN) values first. `_normalize_ai_signal`
        # already maps NaN -> a neutral 0.5 signal; coercing NaN to 0.0 before
        # scoring (as this used to do) turned "unmeasurable" into "measured as
        # maximally predictable/uniform", which falsely inflates the AI score
        # for very short or malformed input. Coerce to 0.0 only afterward, for
        # the human-readable display fields.
        score, signals = self.ai_likelihood(overall_ppl, burst, marker_sig, uniformity_sig)
        verdict = self.verdict_from_score(score)

        display_ppl = 0.0 if math.isnan(overall_ppl) else round(overall_ppl, 2)
        display_burst = 0.0 if math.isnan(burst) else round(burst, 2)

        return AnalysisResult(
            ai_likelihood_score=score,
            perplexity=display_ppl,
            burstiness=display_burst,
            verdict=verdict,
            sentence_breakdown=sentence_scores,
            signals=signals,
        )


# Singleton used by API
_scorer: TextScorer | None = None


def get_scorer(model_name: str = "distilgpt2") -> TextScorer:
    global _scorer
    if _scorer is None or _scorer.model_name != model_name:
        _scorer = TextScorer(model_name=model_name)
    return _scorer
