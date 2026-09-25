"""
Similarity-aware rewrite: reduces VERIFIED overlap against the stored
corpus. This is a distinct concern from app/humanizer.py, which rewrites
sentences to lower the local AI-*detector* score (perplexity-driven) — that
module is untouched by this one and still serves the "Reduce AI phrasing"
feature.

Why this isn't just "call humanize_sentence() on the flagged text"
--------------------------------------------------------------------------
Measured on samples/eval/15 and /16 (a light-modified copy and a realistic
paraphrase, both with verified overlap): applying the existing word-level
humanizer to every sentence in the flagged passages touched only 5/14 and
1/6 sentences — most factual prose contains none of its listed AI buzzwords
— and moved verified overlap by 0.0 percentage points in every case. Word
substitution alone does not touch sentence-level structure, and structure
is exactly what survives a synonym swap in an embedding.

Adding sentence-ORDER shuffling and clause-order swapping within each
flagged run, on top of the existing word substitution, moved verified
overlap by -16.7pt and -23.3pt on those same two fixtures. But on a third
fixture (a patchwork copy) the same transform made it WORSE (+3.9pt to
cosine, +0pt to verified overlap) — a single blind attempt is not reliably
an improvement. That is exactly why this module never trusts one attempt:
it generates a few bounded candidates, re-runs the real similarity check on
each, and returns whichever one is actually verified as better — or the
untouched original, honestly, if none of them are.

Pipeline
--------
    original text
      -> analyze_similarity()                      (existing, unmodified)
      -> locate contiguous runs of VERIFIED sentences
      -> up to MAX_ATTEMPTS candidate rewrites of those runs only
      -> analyze_similarity() again on each full candidate
      -> keep the candidate with the lowest matched_portion, but ONLY if
         it is actually lower than the original's — never return a worse
         or merely-different version as if it were an improvement
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from app import rewrite_providers
from app.humanizer import humanize_sentence
from app.similarity import SimilarityResult, _SENTENCE_SPLIT, analyze_similarity

MAX_ATTEMPTS = 3  # bounded — never loop indefinitely chasing a lower score

# Capturing group isolates the bare conjunction so it can be reused as the
# new joiner without dragging the leading comma along with it (a bug caught
# by testing: naively re-slicing the full match produced "...down, , dark
# roofing..." because the comma survived string trimming).
#
# Widened from the original 7 connectors (and/but/so/while/though/which/when)
# to also catch causal/conditional/temporal clauses — because/since/
# although/if/unless/after/before/as/until — which the narrower list simply
# never matched, leaving most non-"and/but"-style sentences untouched by
# structural restructuring (see MEASURED RESULT below).
_CLAUSE_SPLIT = re.compile(
    r",\s+(and|but|so|while|though|which|when|"
    r"because|since|although|if|unless|after|before|as|until)\s+",
    re.IGNORECASE,
)

# Sentences that OPEN with a subordinate clause ("When X happens, Y occurs.")
# were invisible to _CLAUSE_SPLIT above, which requires the comma to come
# BEFORE the connector. This catches that shape and swaps it to
# "Y occurs when X happens." — same words, same facts, different order.
_FRONT_CLAUSE_SPLIT = re.compile(
    r"^(when|while|although|because|since|if|unless|after|before|as|until)\s+"
    r"(.+?),\s+(.+?)([.!?]?)$",
    re.IGNORECASE,
)


def _is_fixed_idiom(connector: str, clause: str) -> bool:
    """"as well (as)" is a fixed idiom, not a true subordinate clause —
    swapping it produces broken grammar ("Well as being fast, as well.").
    Every other connector added above introduces a genuine clause, so this
    is the one deliberate exception."""
    return connector.lower() == "as" and clause.strip().lower().startswith("well")


@dataclass
class RewriteResult:
    original_text: str
    rewritten_text: str
    changed: bool
    improved: bool
    attempts_tried: int
    sentences_rewritten: int
    before: SimilarityResult
    after: SimilarityResult
    note: str
    # Which specific passages the rewrite targeted, for transparency.
    targeted_excerpts: list[str] = field(default_factory=list)
    # Which candidate source actually won: "local" | "groq" | "openrouter" |
    # "gemini" | "none" (nothing beat the original). Transparency only —
    # never used to decide anything, the similarity numbers already did that.
    source: str = "none"
    # Every candidate source that was actually attempted, in order — may be
    # shorter than the full provider list if overlap was fully cleared early
    # or a later source was skipped after an earlier one already succeeded.
    sources_tried: list[str] = field(default_factory=list)


def _restructure_sentence(s: str, rng: random.Random) -> str:
    """Swap the two halves of a clause-connector sentence when one exists,
    then apply the existing word-level substitutions. Tries a front-loaded
    subordinate clause first ("When X, Y." -> "Y, when X."), then a
    mid-sentence comma-conjunction swap (existing behavior, now with more
    connectors). Falls back to word substitution alone for sentences with
    neither shape."""
    s = s.strip()
    if not s:
        return s

    fm = _FRONT_CLAUSE_SPLIT.match(s)
    if fm and rng.random() < 0.85:  # leave some sentences structurally as-is for variety
        connector = fm.group(1)
        subordinate = fm.group(2).strip()
        main = fm.group(3).strip()
        end_punct = fm.group(4) or "."
        if subordinate and main and not _is_fixed_idiom(connector, subordinate):
            main_cap = main[0].upper() + main[1:]
            subordinate_low = subordinate[0].lower() + subordinate[1:]
            return humanize_sentence(f"{main_cap}, {connector.lower()} {subordinate_low}{end_punct}")

    m = _CLAUSE_SPLIT.search(s)
    if m and rng.random() < 0.85:  # leave some sentences structurally as-is for variety
        left = s[: m.start()].rstrip(". ")
        joiner_word = m.group(1)
        right = s[m.end() :].rstrip(". ")
        if left and right and not _is_fixed_idiom(joiner_word, right):
            right_cap = right[0].upper() + right[1:]
            left_low = left[0].lower() + left[1:] if left else left
            s = f"{right_cap}, {joiner_word} {left_low}."
    return humanize_sentence(s)


def _is_better_candidate(candidate: SimilarityResult, current_best: SimilarityResult) -> bool:
    """Strictly-better comparison BETWEEN CANDIDATES (picking the best of
    several generated attempts) — matched_portion first, top_match as a
    tie-break among candidates already tied on it.

    NOT used to decide whether the final result counts as an improvement
    over the ORIGINAL — see the `improved` computation in
    rewrite_to_reduce_overlap(), which is deliberately stricter (matched_
    portion alone) so a top_match-only movement can never be reported as
    "improved" when verified overlap didn't actually drop. That exact gap
    was measured: a fully-verbatim fixture stayed at 100% matched_portion
    while top_match fell 100->77.1, and the old logic called it "improved."
    """
    if candidate.matched_portion < current_best.matched_portion:
        return True
    if candidate.matched_portion == current_best.matched_portion and candidate.top_match < current_best.top_match:
        return True
    return False


def _generate_ai_candidate(
    sentences: list[str], runs: list[tuple[int, int]], provider_fn
) -> tuple[str, int] | None:
    """One candidate rewrite via an AI provider: each flagged run is sent as
    ONE passage (never the whole document), validated, and spliced back in
    place of the original sentences it replaced. Returns None — reject the
    WHOLE candidate, not a partial one — if the provider fails or produces
    an invalid result for ANY run."""
    out = list(sentences)
    n_rewritten = 0
    for start, end in runs:
        original_passage = " ".join(sentences[start:end])
        raw = provider_fn(original_passage)
        if raw is None:
            return None
        candidate_passage = rewrite_providers.strip_code_fences(raw.strip())
        ok, _reason = rewrite_providers.validate_candidate(original_passage, candidate_passage)
        if not ok:
            return None
        out[start:end] = [candidate_passage]
        n_rewritten += end - start
    return " ".join(p for p in out if p), n_rewritten


def _find_touched_runs(sentences: list[str], targets: set[str]) -> list[tuple[int, int]]:
    """Contiguous index ranges [start, end) of sentences that fall inside a
    targeted excerpt. Kept contiguous so shuffling reorders within a single
    flagged passage, never mixing unrelated parts of the document."""
    touched = [any(s.strip() and s.strip() in t for t in targets) for s in sentences]
    runs = []
    i = 0
    while i < len(sentences):
        if touched[i]:
            j = i
            while j < len(sentences) and touched[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def _generate_candidate(sentences: list[str], runs: list[tuple[int, int]], seed: int) -> tuple[str, int]:
    """One candidate rewrite: shuffle sentence order within each flagged
    run and restructure each sentence. Returns (text, sentences_rewritten)."""
    rng = random.Random(seed)
    out = list(sentences)
    n_rewritten = 0
    for start, end in runs:
        run = sentences[start:end]
        if len(run) > 1:
            order = list(range(len(run)))
            rng.shuffle(order)
            run = [run[k] for k in order]
        run = [_restructure_sentence(s, rng) for s in run]
        out[start:end] = run
        n_rewritten += end - start
    return " ".join(p for p in out if p), n_rewritten


def rewrite_to_reduce_overlap(
    text: str,
    exclude_file_name: str | None = None,
    max_attempts: int = MAX_ATTEMPTS,
    include_gemini: bool = False,
) -> RewriteResult:
    """Rewrite only the passages VERIFIED as overlapping with stored
    documents, then confirm the rewrite actually reduced that overlap
    before returning it.

    Deliberately targets VERIFIED matches only, not merely-semantic
    ("possible") ones — a document that shares a topic with something on
    file but has no corroborated overlap is not rewritten, because there is
    nothing established to fix. See app/similarity.py for what "verified"
    means here.

    Candidate sources, tried in this order, each validated by the SAME
    analyze_similarity() call — the AI providers only ever generate a
    candidate, they never decide whether it helped:
      1. the local rule-based restructurer (free, deterministic, up to
         `max_attempts` tries) — unchanged from the original implementation
      2. Groq
      3. OpenRouter
      4. Gemini — ONLY when `include_gemini=True`. Default is False:
         Gemini is never called unless the caller explicitly opts in, per
         its limited free quota. Automated tests must always leave this False.
    Every source after the first is skipped once verified overlap is fully
    cleared (matched_portion == 0), and any source that fails (missing key,
    network error, invalid output) is simply skipped — never raises.
    """
    before = analyze_similarity(text, exclude_file_name=exclude_file_name)
    verified_excerpts = {m.query_excerpt for m in before.matches if m.verified}

    if not verified_excerpts:
        return RewriteResult(
            original_text=text,
            rewritten_text=text,
            changed=False,
            improved=False,
            attempts_tried=0,
            sentences_rewritten=0,
            before=before,
            after=before,
            note=(
                "No verified overlap was found, so nothing was rewritten. "
                "A high semantic-similarity score alone (same topic, different wording) "
                "is not treated as something to fix."
            ),
            targeted_excerpts=[],
            source="none",
            sources_tried=[],
        )

    sentences = [s for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    runs = _find_touched_runs(sentences, verified_excerpts)

    best_text = text
    best_result = before
    best_rewritten_count = 0
    best_source = "none"
    attempts_tried = 0
    sources_tried: list[str] = []

    # 1. Local candidates — unchanged loop/semantics; attempts_tried keeps
    # its exact original meaning (bounds THIS loop only).
    for attempt in range(max_attempts):
        attempts_tried += 1
        candidate_text, n_rewritten = _generate_candidate(sentences, runs, seed=attempt)
        candidate_result = analyze_similarity(candidate_text, exclude_file_name=exclude_file_name)
        if _is_better_candidate(candidate_result, best_result):
            best_text, best_result, best_rewritten_count, best_source = (
                candidate_text, candidate_result, n_rewritten, "local",
            )
        if best_result.matched_portion == 0.0:
            break
    sources_tried.append("local")

    # 2-4. AI candidates — one attempt each, in order, skipped once overlap
    # is already fully cleared. Gemini only when explicitly requested.
    ai_sources = [("groq", rewrite_providers.PROVIDERS["groq"]),
                  ("openrouter", rewrite_providers.PROVIDERS["openrouter"])]
    if include_gemini:
        ai_sources.append(("gemini", rewrite_providers.PROVIDERS["gemini"]))

    for source_name, provider_fn in ai_sources:
        if best_result.matched_portion == 0.0:
            break
        sources_tried.append(source_name)
        generated = _generate_ai_candidate(sentences, runs, provider_fn)
        if generated is None:
            continue  # provider unavailable, failed, or produced an invalid candidate
        candidate_text, n_rewritten = generated
        candidate_result = analyze_similarity(candidate_text, exclude_file_name=exclude_file_name)
        if _is_better_candidate(candidate_result, best_result):
            best_text, best_result, best_rewritten_count, best_source = (
                candidate_text, candidate_result, n_rewritten, source_name,
            )

    # Deliberately STRICT: matched_portion alone, never a top_match-only
    # tie-break — see _is_better_candidate's docstring for the measured bug
    # this fixes (a fully-verbatim fixture stayed at 100% matched_portion
    # while top_match moved, and the old logic called that "improved").
    improved = best_result.matched_portion < before.matched_portion
    changed = best_text != text

    if improved:
        note = (
            f"Verified overlap reduced from {before.matched_portion:.0f}% to "
            f"{best_result.matched_portion:.0f}% (via {best_source}, {attempts_tried} local attempt"
            f"{'s' if attempts_tried != 1 else ''}, sources tried: {', '.join(sources_tried)})."
        )
    elif changed:
        note = (
            "A rewrite was generated but verified overlap did not measurably improve "
            f"({before.matched_portion:.0f}% before, {best_result.matched_portion:.0f}% after — "
            f"sources tried: {', '.join(sources_tried)}). "
            "Returning the original rather than a change that doesn't help."
        )
        best_text, best_result, best_rewritten_count, best_source = text, before, 0, "none"
    else:
        note = (
            f"No rewrite attempt reduced the verified overlap "
            f"(sources tried: {', '.join(sources_tried)}); returning the original text."
        )

    return RewriteResult(
        original_text=text,
        rewritten_text=best_text,
        changed=best_text != text,
        improved=improved,
        attempts_tried=attempts_tried,
        sentences_rewritten=best_rewritten_count,
        before=before,
        after=best_result,
        note=note,
        targeted_excerpts=sorted(verified_excerpts, key=len, reverse=True)[:5],
        source=best_source,
        sources_tried=sources_tried,
    )
