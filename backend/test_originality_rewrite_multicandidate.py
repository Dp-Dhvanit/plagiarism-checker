"""
Regression suite for the multi-candidate Remove Plagiarism architecture
(local + Groq + OpenRouter + optional Gemini candidate generators,
app/originality_rewriter.py + app/rewrite_providers.py).

Runs against an ISOLATED temporary database, same pattern as
test_originality_rewrite.py. Every AI provider is a FAKE Python function
substituted into app.rewrite_providers.PROVIDERS — this suite makes:

    0 real Gemini API calls
    0 real Groq API calls
    0 real OpenRouter API calls

The real, unmodified analyze_similarity() (local embeddings) is what
actually judges every candidate — exactly like production.

    cd backend
    python test_originality_rewrite_multicandidate.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import db

_TMP = tempfile.mkdtemp(prefix="rewrite_multicandidate_")
db.DB_PATH = os.path.join(_TMP, "eval.db")
db.init_db()

from app import rewrite_providers  # noqa: E402
from app.originality_rewriter import rewrite_to_reduce_overlap  # noqa: E402
from app.similarity import store_reference_chunks  # noqa: E402

passed = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))


# A source paragraph, stored once as "on file" so later text can be checked
# against it for verified overlap. Long enough (4 sentences) that a genuine
# restructuring has real room to move matched_portion, unlike a short,
# name/date-dense passage where nearly every word must be preserved (see
# app/originality_rewriter.py's own docstring for that measured limit).
SOURCE_TEXT = (
    "Urban heat islands form when a city runs measurably warmer than the "
    "countryside around it. The cause is not mysterious: asphalt and dark "
    "roofing absorb sunlight that grass and tree canopy would otherwise "
    "reflect, and the stored heat bleeds back out long after sunset. Anyone "
    "who has walked across a parking lot in the evening has felt this "
    "directly. Measurements in mid-sized cities typically show a difference "
    "of three to five degrees between the dense core and the outlying "
    "suburbs, though the gap widens on still, cloudless nights when there "
    "is no wind to mix the air."
)

# A near-verbatim copy of the source — guaranteed to clear the verified-
# overlap floor.
COPY_TEXT = SOURCE_TEXT

# A genuinely well-restructured paraphrase of the same facts — written by
# hand here to stand in for "what a good AI rewrite would look like."
# Verified empirically (not assumed) against the real analyze_similarity()
# before being locked into this test: drops matched_portion 100% -> 0%.
GOOD_REWRITE = (
    "A city can end up noticeably hotter than the land surrounding it, and "
    "the reason behind that isn't hard to pin down. Dark roofing and paved "
    "surfaces soak up sunlight that would normally bounce off grass and "
    "trees, then release that trapped warmth well after the sun goes down "
    "-- something anyone who has crossed a parking lot at night already "
    "knows firsthand. City centers in mid-sized places tend to run three to "
    "five degrees hotter than their suburbs, and that gap grows even wider "
    "on calm, clear nights when there's no breeze to stir the air around."
)


def setup_corpus() -> None:
    hid = db.insert_history(
        file_name="source.txt", file_type="txt", analysis_type="text",
        ai_probability=0.0, similarity_score=0.0, confidence="low",
        status="analyzed", result_json={},
    )
    store_reference_chunks(hid, "source.txt", SOURCE_TEXT)


def reset_providers() -> None:
    rewrite_providers.PROVIDERS["groq"] = lambda passage: None
    rewrite_providers.PROVIDERS["openrouter"] = lambda passage: None
    rewrite_providers.PROVIDERS["gemini"] = lambda passage: None


def main() -> int:
    setup_corpus()

    print("=" * 70)
    print("1 — local candidate works when all providers are unavailable")
    print("=" * 70)
    reset_providers()
    r = rewrite_to_reduce_overlap(COPY_TEXT)
    check("verified overlap starts at 100%", r.before.matched_portion == 100.0, f"{r.before.matched_portion}")
    # groq/openrouter are still ATTEMPTED (they just return None) since
    # local alone doesn't fully clear overlap on this fixture — only a
    # source that already reached matched_portion==0 gets skipped.
    check("every source got a chance to run", r.sources_tried == ["local", "groq", "openrouter"],
          str(r.sources_tried))
    check("source is 'local' or 'none' (never a provider that returned nothing)",
          r.source in ("local", "none"), r.source)

    print("\n" + "=" * 70)
    print("2 — Groq candidate genuinely improves the result")
    print("=" * 70)
    reset_providers()
    rewrite_providers.PROVIDERS["groq"] = lambda passage: GOOD_REWRITE
    r = rewrite_to_reduce_overlap(COPY_TEXT)
    check("groq was tried", "groq" in r.sources_tried, str(r.sources_tried))
    check("groq candidate accepted as the winner", r.source == "groq", r.source)
    check("verified overlap actually dropped", r.after.matched_portion < r.before.matched_portion,
          f"before={r.before.matched_portion} after={r.after.matched_portion}")
    check("'improved' is strictly true (matched_portion dropped, not a secondary-metric fluke)",
          r.improved is True)
    check("the factual figure (three to five degrees) survived the rewrite",
          "three to" in r.rewritten_text and "five degrees" in r.rewritten_text,
          r.rewritten_text[:200])

    print("\n" + "=" * 70)
    print("3 — OpenRouter candidate genuinely improves the result")
    print("=" * 70)
    reset_providers()
    rewrite_providers.PROVIDERS["openrouter"] = lambda passage: GOOD_REWRITE
    r = rewrite_to_reduce_overlap(COPY_TEXT)
    check("openrouter was tried", "openrouter" in r.sources_tried, str(r.sources_tried))
    check("openrouter candidate accepted as the winner", r.source == "openrouter", r.source)
    check("verified overlap actually dropped", r.after.matched_portion < r.before.matched_portion)

    print("\n" + "=" * 70)
    print("4 — invalid provider output is rejected (empty response)")
    print("=" * 70)
    reset_providers()
    rewrite_providers.PROVIDERS["groq"] = lambda passage: ""
    rewrite_providers.PROVIDERS["openrouter"] = lambda passage: "   "
    r = rewrite_to_reduce_overlap(COPY_TEXT)
    check("empty groq/openrouter output never wins", r.source not in ("groq", "openrouter"), r.source)
    check("verified overlap unchanged from local-only result",
          r.after.matched_portion == 100.0, f"{r.after.matched_portion}")

    print("\n" + "=" * 70)
    print("5 — meta-commentary output is rejected")
    print("=" * 70)
    reset_providers()
    rewrite_providers.PROVIDERS["groq"] = lambda passage: f"Here's the rewritten text: {GOOD_REWRITE}"
    r = rewrite_to_reduce_overlap(COPY_TEXT)
    check("meta-commentary-prefixed groq output never wins", r.source != "groq", r.source)

    print("\n" + "=" * 70)
    print("6 — candidate worse than (or equal to) the original is rejected")
    print("=" * 70)
    reset_providers()
    rewrite_providers.PROVIDERS["groq"] = lambda passage: passage  # verbatim echo — no improvement possible
    r = rewrite_to_reduce_overlap(COPY_TEXT)
    check("verbatim-echo groq candidate does not win", r.source != "groq", r.source)
    check("result never reports improved from a non-improving candidate",
          r.improved is False or r.after.matched_portion < r.before.matched_portion)

    print("\n" + "=" * 70)
    print("7/8 — multiple candidates compared, the genuinely better one wins")
    print("=" * 70)
    reset_providers()
    WEAKER_REWRITE = SOURCE_TEXT.replace("measurably", "noticeably")  # trivial edit, barely changes overlap
    rewrite_providers.PROVIDERS["groq"] = lambda passage: WEAKER_REWRITE
    rewrite_providers.PROVIDERS["openrouter"] = lambda passage: GOOD_REWRITE
    r = rewrite_to_reduce_overlap(COPY_TEXT)
    check("both providers were tried", set(r.sources_tried) >= {"groq", "openrouter"}, str(r.sources_tried))
    check("the genuinely better candidate (openrouter) won, not just whichever ran first",
          r.source == "openrouter", r.source)

    print("\n" + "=" * 70)
    print("9 — all candidates fail -> original text returned unchanged")
    print("=" * 70)
    reset_providers()  # everything returns None
    r = rewrite_to_reduce_overlap(COPY_TEXT, max_attempts=0)  # also disable the local generator
    check("nothing changed", r.changed is False)
    check("rewritten text equals the original exactly", r.rewritten_text == COPY_TEXT)
    check("source is 'none'", r.source == "none", r.source)
    check("original text is untouched/not corrupted", r.original_text == COPY_TEXT)

    print("\n" + "=" * 70)
    print("10 — include_gemini=False (default): Gemini is NEVER called")
    print("=" * 70)
    reset_providers()
    gemini_calls = []
    rewrite_providers.PROVIDERS["gemini"] = lambda passage: (gemini_calls.append(1), None)[1]
    r = rewrite_to_reduce_overlap(COPY_TEXT)  # include_gemini defaults to False
    check("gemini provider function was never invoked", len(gemini_calls) == 0, f"{len(gemini_calls)} call(s)")
    check("'gemini' does not appear in sources_tried", "gemini" not in r.sources_tried, str(r.sources_tried))

    print("\n" + "=" * 70)
    print("11 — include_gemini=True: Gemini CAN be called (still mocked, not live)")
    print("=" * 70)
    reset_providers()
    gemini_calls = []

    def fake_gemini(passage: str):
        gemini_calls.append(1)
        return None  # simulate "no help", we're only checking it gets a chance to run

    rewrite_providers.PROVIDERS["gemini"] = fake_gemini
    r = rewrite_to_reduce_overlap(COPY_TEXT, include_gemini=True)
    check("gemini provider function WAS invoked when explicitly requested",
          len(gemini_calls) >= 1, f"{len(gemini_calls)} call(s)")
    check("'gemini' appears in sources_tried", "gemini" in r.sources_tried, str(r.sources_tried))

    print("\n" + "=" * 70)
    print(f"{passed}/{passed + failed} checks passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        code = main()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(code)
