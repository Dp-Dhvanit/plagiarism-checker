"""
Rule-based text humanizer.

Strategy:
- If ai_likelihood_score > 35 → humanize ALL sentences
- Otherwise → only humanize the most AI-like half (lowest perplexity)
Replacements cover buzzwords, transition phrases, contractions,
and sentence-opener variation.
"""
from __future__ import annotations

import random
import re

# ── AI buzzword → human alternatives ────────────────────────────────────────
WORD_REPLACEMENTS: dict[str, list[str]] = {
    # long-form phrases first (must come before single-word patterns)
    r"\bit is important to note that\b":  ["worth mentioning,", "it's worth saying that", "keep in mind that"],
    r"\bit is worth noting that\b":       ["interestingly,", "worth knowing,", "it turns out that"],
    r"\bit should be noted( that)?\b":    ["worth knowing,", "keep in mind,"],
    r"\bin today's fast-paced world\b":   ["these days,", "nowadays,"],
    r"\bin today's world\b":              ["today,", "these days,"],
    r"\bplays a (?:crucial|critical|key|pivotal|important) role\b": ["is really important", "matters a lot", "is key here"],
    r"\b(?:is|are) (?:essential|crucial|vital|imperative)\b":       ["is needed", "really matters", "is key"],
    r"\bbest practices\b":                ["good approaches", "smart ways to do it"],
    r"\bkey takeaways?\b":                ["main points", "things to remember"],
    r"\bmoving forward\b":                ["going ahead", "from here"],
    r"\bgoing forward\b":                 ["from here on", "going ahead"],
    r"\bin conclusion\b":                 ["to wrap up,", "all in all,", "so,"],
    r"\bin summary\b":                    ["to sum up,", "basically,", "in short,"],
    r"\bto summarize\b":                  ["to sum up,", "in short,"],
    r"\bas a result\b":                   ["so", "because of this", "which means"],
    r"\bconsequently\b":                  ["so", "because of this"],
    r"\bfurthermore\b":                   ["also,", "and,", "plus,", "on top of that,"],
    r"\bmoreover\b":                      ["also,", "plus,", "on top of that,"],
    r"\badditionally\b":                  ["also,", "and"],
    r"\btherefore\b":                     ["so", "which means", "that's why"],
    r"\bthus\b":                          ["so", "and so"],
    r"\bhence\b":                         ["that's why", "so"],
    r"\baccordingly\b":                   ["so", "because of that"],
    r"\bsubsequently\b":                  ["then", "after that", "next"],
    r"\bnotably\b":                       ["interestingly,", "interestingly enough,"],
    r"\bsignificantly\b":                 ["a lot", "quite a bit", "noticeably"],
    r"\bultimately\b":                    ["in the end,", "when it comes down to it,"],
    r"\boverall\b":                       ["all in all,", "on the whole,", "generally speaking,"],
    r"\bin essence\b":                    ["basically,", "at its core,"],
    r"\butilize\b":                       ["use"],
    r"\butilizes\b":                      ["uses"],
    r"\butilized\b":                      ["used"],
    r"\bleverage\b":                      ["use", "take advantage of"],
    r"\bleverages\b":                     ["uses"],
    r"\bleveraged\b":                     ["used"],
    r"\bfacilitate\b":                    ["help", "make easier", "support"],
    r"\bfacilitates\b":                   ["helps", "makes easier"],
    r"\bencompass\b":                     ["cover", "include"],
    r"\bencompasses\b":                   ["covers", "includes"],
    r"\bpivotal\b":                       ["key", "important", "big"],
    r"\bcomprehensive\b":                 ["thorough", "full", "wide-ranging"],
    r"\brobust\b":                        ["strong", "solid", "reliable"],
    r"\bseamless\b":                      ["smooth", "easy"],
    r"\binnovative\b":                    ["new", "fresh", "creative"],
    r"\btransformative\b":                ["game-changing", "huge"],
    r"\bempower\b":                       ["help", "enable"],
    r"\bempowers\b":                      ["helps", "enables"],
    r"\bholistic\b":                      ["all-round", "complete"],
    r"\bproactive\b":                     ["forward-thinking", "ahead of the curve"],
    r"\bscalable\b":                      ["flexible", "adaptable"],
    r"\bstreamline\b":                    ["simplify", "speed up"],
    r"\bstreamlines\b":                   ["simplifies", "speeds up"],
    r"\bfoster\b":                        ["build", "grow", "encourage"],
    r"\bfosters\b":                       ["builds", "encourages", "helps grow"],
    r"\blandscape\b":                     ["field", "space", "area"],
    r"\bparadigm\b":                      ["approach", "way of thinking", "model"],
    r"\bsynergy\b":                       ["teamwork", "working together"],
    r"\bensure\b":                        ["make sure"],
    r"\bensures\b":                       ["makes sure"],
    r"\bdemonstrate\b":                   ["show"],
    r"\bdemonstrates\b":                  ["shows"],
    r"\bhighlight\b":                     ["point out", "show"],
    r"\bhighlights\b":                    ["points out", "shows"],
    r"\bnuanced\b":                       ["complex", "layered", "subtle"],
    r"\bnuance\b":                        ["detail", "complexity"],
    r"\bfundamental\b":                   ["basic", "core", "essential"],
    r"\bimperative\b":                    ["important", "necessary"],
    r"\bvital\b":                         ["important", "key"],
    r"\bdelve\b":                         ["dig", "look"],
    r"\bdelves\b":                        ["digs", "looks"],
    r"\bunderscore\b":                    ["show", "highlight"],
    r"\bunderscores\b":                   ["shows", "highlights"],
    r"\bgroundbreaking\b":                ["new", "exciting", "big"],
    r"\bstate-of-the-art\b":              ["latest", "cutting-edge"],
    r"\bcritical\b":                      ["important", "key"],
    r"\bcrucial\b":                       ["important", "key"],
    r"\bsupport\b":                       ["back up", "help with"],
    r"\bsupports\b":                      ["backs up", "helps with"],
    r"\bcontribute\b":                    ["help", "add to"],
    r"\bcontributes\b":                   ["helps", "adds to"],
    r"\bassist\b":                        ["help"],
    r"\bassists\b":                       ["helps"],
    r"\bobtain\b":                        ["get"],
    r"\bobtains\b":                       ["gets"],
    r"\bpurchase\b":                      ["buy"],
    r"\bpurchases\b":                     ["buys"],
    r"\brequire\b":                       ["need"],
    r"\brequires\b":                      ["needs"],
    r"\bprovide\b":                       ["give", "offer"],
    r"\bprovides\b":                      ["gives", "offers"],
    r"\bcomponent\b":                     ["part", "piece"],
    r"\bcomponents\b":                    ["parts", "pieces"],
    r"\bindividuals\b":                   ["people"],
    r"\bindividual\b":                    ["person", "someone"],
    r"\badditional\b":                    ["extra", "more"],
    r"\bnumerous\b":                      ["many", "lots of"],
    r"\bcommence\b":                      ["start", "begin"],
    r"\bcommences\b":                     ["starts", "begins"],
    r"\bterminate\b":                     ["end", "stop"],
    r"\bterminates\b":                    ["ends", "stops"],
    r"\bconsequence\b":                   ["result", "outcome"],
    r"\bconsequences\b":                  ["results", "outcomes"],
}

# ── Contraction map ──────────────────────────────────────────────────────────
CONTRACTIONS: list[tuple[str, str]] = [
    (r"\bIt is\b",       "It's"),
    (r"\bit is\b",       "it's"),
    (r"\bThey are\b",    "They're"),
    (r"\bthey are\b",    "they're"),
    (r"\bWe are\b",      "We're"),
    (r"\bwe are\b",      "we're"),
    (r"\bThat is\b",     "That's"),
    (r"\bthat is\b",     "that's"),
    (r"\bThese are\b",   "These are"),
    (r"\bis not\b",      "isn't"),
    (r"\bare not\b",     "aren't"),
    (r"\bdoes not\b",    "doesn't"),
    (r"\bDo not\b",      "Don't"),
    (r"\bdo not\b",      "don't"),
    (r"\bwill not\b",    "won't"),
    (r"\bcannot\b",      "can't"),
    (r"\bhas not\b",     "hasn't"),
    (r"\bhave not\b",    "haven't"),
    (r"\bwould not\b",   "wouldn't"),
    (r"\bcould not\b",   "couldn't"),
    (r"\bshould not\b",  "shouldn't"),
    (r"\bI am\b",        "I'm"),
    (r"\bYou are\b",     "You're"),
    (r"\byou are\b",     "you're"),
    (r"\bHe is\b",       "He's"),
    (r"\bhe is\b",       "he's"),
    (r"\bShe is\b",      "She's"),
    (r"\bshe is\b",      "she's"),
]

# ── Natural sentence openers to inject variety ───────────────────────────────
HUMAN_OPENERS = [
    "Basically, ", "Honestly, ", "In fact, ", "Actually, ",
    "To be fair, ", "Worth noting — ", "Here's the thing: ",
    "The reality is ", "Think of it this way: ", "Put simply, ",
]

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _apply_replacements(text: str) -> str:
    for pattern, options in WORD_REPLACEMENTS.items():
        replacement = random.choice(options)
        def _repl(m: re.Match, rep: str = replacement) -> str:
            orig = m.group(0)
            return rep[0].upper() + rep[1:] if orig and orig[0].isupper() and rep else rep
        text = re.sub(pattern, _repl, text, count=1, flags=re.IGNORECASE)
    return text


def _apply_contractions(text: str) -> str:
    for pattern, contraction in CONTRACTIONS:
        text = re.sub(pattern, contraction, text, count=1)
    return text


def _maybe_add_opener(sentence: str) -> str:
    """10% chance to prepend a natural human opener to vary tone."""
    if random.random() < 0.12 and len(sentence) > 30:
        opener = random.choice(HUMAN_OPENERS)
        # Lowercase the first letter of the original sentence
        sentence = opener + sentence[0].lower() + sentence[1:]
    return sentence


def humanize_sentence(sentence: str) -> str:
    s = _apply_replacements(sentence)
    s = _apply_contractions(s)
    s = _maybe_add_opener(s)
    return s


def humanize_text(
    text: str,
    sentence_scores: list[dict],
    ai_score: float = 50.0,
) -> tuple[str, int]:
    """
    Humanize AI-like sentences.

    - ai_score > 35  → humanize EVERY sentence (the whole text is AI-like)
    - ai_score ≤ 35  → humanize only the bottom half by perplexity (most AI-like)
    - No scores      → humanize everything

    Returns (humanized_text, number_of_sentences_changed).
    """
    sentences = _SENT_SPLIT.split(text.strip())
    if not sentences:
        return text, 0

    if ai_score > 35 or not sentence_scores:
        # High AI score → rewrite all sentences
        to_humanize = set(range(len(sentences)))
    else:
        # Partially AI → rewrite the most AI-like half (lowest perplexity)
        ppl_lookup: dict[str, float] = {s["sentence"]: s["perplexity"] for s in sentence_scores}
        scored = sorted(
            [(i, ppl_lookup.get(sentences[i], float("inf"))) for i in range(len(sentences))],
            key=lambda x: x[1],
        )
        half = max(1, len(scored) // 2)
        to_humanize = {idx for idx, _ in scored[:half]}

    humanized_sents = []
    for i, sent in enumerate(sentences):
        if i in to_humanize:
            humanized_sents.append(humanize_sentence(sent))
        else:
            humanized_sents.append(sent)

    changed = sum(1 for o, h in zip(sentences, humanized_sents) if o != h)
    return " ".join(humanized_sents), changed
