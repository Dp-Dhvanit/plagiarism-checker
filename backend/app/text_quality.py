"""
Analyzability gate for text/AI detection.

Decides whether input is even suitable for AI-authorship analysis, BEFORE
any perplexity/burstiness scoring runs. Nonsense input (keyboard-mashing,
random characters, mostly symbols/numbers, repeated characters) must never
reach the scorer — it has no "AI-likelihood", it's simply not language.

This is a hand-rolled, dependency-free heuristic (no nltk/wordfreq/langdetect
are installed in this project, and none are added here). It is explicitly
NOT a trained language-identification model — it is a handful of cheap,
explainable checks that catch the specific failure modes real users
produce (keyboard mashes, repeated-char spam, symbol/number soup, and
plain "too short to say anything"). The thresholds below are engineering
judgment calls, not values fit to a labeled dataset — tune them if real
usage shows false positives/negatives.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Status = Literal["ok", "insufficient", "unanalyzable"]

# ── Tunable thresholds (heuristic, not empirically calibrated) ─────────────
MIN_WORDS_FOR_ANALYSIS = 12       # below this (and not gibberish) -> "insufficient"
GIBBERISH_TOKEN_RATIO = 0.5       # >= this fraction of flagged tokens -> "unanalyzable"
MIN_ALPHA_RATIO = 0.40            # overall alphabetic-char ratio below this -> "unanalyzable"
REPEATED_CHAR_RUN = 5             # 5+ identical consecutive chars -> "unanalyzable"

KEYBOARD_MIN_TOKEN_LEN = 5
KEYBOARD_MIN_COVERAGE = 0.5
KEYBOARD_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
_KEYBOARD_WINDOWS: list[str] = []
for _row in KEYBOARD_ROWS:
    for _r in (_row, _row[::-1]):
        for _i in range(len(_r) - KEYBOARD_MIN_TOKEN_LEN + 1):
            _KEYBOARD_WINDOWS.append(_r[_i:_i + KEYBOARD_MIN_TOKEN_LEN])

NO_VOWEL_MIN_LEN = 5              # token >= this length with zero vowels -> gibberish
LOW_VOWEL_MIN_LEN = 8             # token >= this length with low vowel ratio -> gibberish
LOW_VOWEL_RATIO = 0.15
_VOWELS = set("aeiou")

# A small set of very common English words, used only as a soft confidence
# booster in ambiguous cases — NOT a gate, and NOT a claim of real language
# identification.
COMMON_WORDS: frozenset[str] = frozenset("""
the a an and or but if then so because while is are was were be been being
i you he she it we they me him her us them my your his its our their this
that these those there here what who whom which whose when where why how
not no yes do does did have has had will would can could should shall may
might must in on at to for of with without from by as about into over under
up down out off again further once more most other some such only own same
too very just also all any both each few will people time year work day
life world hand part child eye woman man thing place house school country
group case system fact water money story example number problem service
company report question government night point home family student area
result different used using use good new first last long great little own
other old right big high small able hello world thanks please help
""".split())

_TOKEN_RE = re.compile(r"[A-Za-z']+")


@dataclass
class QualityResult:
    status: Status
    reason: str
    word_count: int


def _vowel_ratio(token: str) -> float:
    letters = [c for c in token.lower() if c.isalpha()]
    if not letters:
        return 0.0
    vowels = sum(1 for c in letters if c in _VOWELS or c == "y")
    return vowels / len(letters)


def _keyboard_coverage(token: str) -> float:
    """Fraction of the token's characters covered by a contiguous keyboard-row match."""
    lower = token.lower()
    if len(lower) < KEYBOARD_MIN_TOKEN_LEN:
        return 0.0
    covered = [False] * len(lower)
    for window in _KEYBOARD_WINDOWS:
        start = 0
        while True:
            idx = lower.find(window, start)
            if idx == -1:
                break
            for i in range(idx, idx + len(window)):
                covered[i] = True
            start = idx + 1
    return sum(covered) / len(lower)


def _is_gibberish_token(token: str) -> bool:
    if len(token) < NO_VOWEL_MIN_LEN:
        return False
    if _keyboard_coverage(token) >= KEYBOARD_MIN_COVERAGE:
        return True
    ratio = _vowel_ratio(token)
    if ratio == 0.0:
        return True
    if len(token) >= LOW_VOWEL_MIN_LEN and ratio < LOW_VOWEL_RATIO:
        return True
    return False


def _longest_repeated_run(text: str) -> int:
    best = run = 1
    for i in range(1, len(text)):
        if text[i] == text[i - 1] and not text[i].isspace():
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best if text else 0


def assess(text: str) -> QualityResult:
    """Decide whether `text` is suitable for AI-authorship scoring."""
    stripped = (text or "").strip()
    if not stripped:
        return QualityResult("insufficient", "No text provided.", 0)

    tokens = _TOKEN_RE.findall(stripped)
    word_count = len(stripped.split())

    # 1. Alphabetic-character ratio (catches mostly symbols/numbers)
    letters = sum(1 for c in stripped if c.isalpha())
    alpha_ratio = letters / len(stripped)
    if alpha_ratio < MIN_ALPHA_RATIO:
        return QualityResult(
            "unanalyzable",
            "Input is mostly non-alphabetic characters (symbols/numbers), not language.",
            word_count,
        )

    # 2. Long repeated-character run (catches "aaaaaaaa", "!!!!!!!" spam)
    if _longest_repeated_run(stripped) >= REPEATED_CHAR_RUN:
        return QualityResult(
            "unanalyzable",
            "Input contains a long run of a repeated character, not natural language.",
            word_count,
        )

    # 3. Gibberish-token ratio (catches keyboard-mashing / random letter strings)
    if tokens:
        flagged = sum(1 for t in tokens if _is_gibberish_token(t))
        if flagged / len(tokens) >= GIBBERISH_TOKEN_RATIO:
            return QualityResult(
                "unanalyzable",
                "Text does not resemble natural language (looks like keyboard-mashing "
                "or a random character string).",
                word_count,
            )
    else:
        return QualityResult(
            "unanalyzable",
            "No recognizable words found in the input.",
            word_count,
        )

    # 4. Enough evidence to say anything meaningful?
    if word_count < MIN_WORDS_FOR_ANALYSIS:
        return QualityResult(
            "insufficient",
            f"Not enough text for a reliable assessment (found {word_count} "
            f"word{'s' if word_count != 1 else ''}, need at least {MIN_WORDS_FOR_ANALYSIS}).",
            word_count,
        )

    return QualityResult("ok", "Looks analyzable.", word_count)
