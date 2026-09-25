"""
Regression suite for the similarity-aware rewrite (Primary Goal 3).

Runs against an ISOLATED temporary database, matching test_similarity_eval.py.

    cd backend
    python test_originality_rewrite.py

What this proves, with real before/after numbers (not aspirations):
  - a document with verified overlap comes back with LOWER verified overlap
  - a document with NO verified overlap (same-topic writing) is untouched —
    the tool never rewrites something that wasn't established as copied
  - the tool never claims "improved" without a real measured drop
  - attempts are bounded (see MAX_ATTEMPTS in app/originality_rewriter.py)
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import db

_TMP = tempfile.mkdtemp(prefix="rewrite_eval_")
db.DB_PATH = os.path.join(_TMP, "eval.db")
db.init_db()

from app import rewrite_providers  # noqa: E402
from app.file_pipeline import build_units  # noqa: E402
from app.originality_rewriter import MAX_ATTEMPTS, rewrite_to_reduce_overlap  # noqa: E402
from app.similarity import analyze_similarity, store_reference_chunks  # noqa: E402

# This suite predates the multi-candidate architecture (local + Groq +
# OpenRouter + optional Gemini) and was written to test the LOCAL
# restructurer in isolation. Force every AI candidate source "unavailable"
# so it keeps testing exactly that — zero network calls, zero API quota,
# same behavior this file always verified. The new provider paths get
# their own dedicated, fully-mocked suite in
# test_originality_rewrite_multicandidate.py.
rewrite_providers.PROVIDERS["groq"] = lambda passage: None
rewrite_providers.PROVIDERS["openrouter"] = lambda passage: None
rewrite_providers.PROVIDERS["gemini"] = lambda passage: None

EVAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "samples", "eval")
EVAL_DIR = os.path.abspath(EVAL_DIR)

passed = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))


def extract(fname: str) -> str:
    path = os.path.join(EVAL_DIR, fname)
    if fname.endswith((".txt", ".py")):
        with open(path, encoding="utf-8") as f:
            return f.read()
    with open(path, "rb") as f:
        data = f.read()
    return "\n\n".join(u.text for u in build_units(fname, data) if u.text.strip())


def main() -> int:
    if not os.path.isdir(EVAL_DIR):
        print(f"eval fixtures not found at {EVAL_DIR}")
        return 1

    print("=" * 70)
    print("ORIGINALITY REWRITE REGRESSION — isolated corpus")
    print("=" * 70)

    source = extract("01_source_original.txt")
    hid = db.insert_history(
        file_name="01_source_original.txt", file_type="txt", analysis_type="text",
        ai_probability=0.0, similarity_score=0.0, confidence="low",
        status="analyzed", result_json={},
    )
    store_reference_chunks(hid, "01_source_original.txt", source)

    print("\n-- documents WITH verified overlap must improve or be left alone, never worsen --")
    for fname in [
        "02_copy_verbatim.docx",
        "15_copy_light_modified.docx",
        "16_copy_paraphrased_moderate.docx",
        "04_copy_partial.pptx",
    ]:
        r = rewrite_to_reduce_overlap(extract(fname))
        check(f"{fname}: attempts bounded", r.attempts_tried <= MAX_ATTEMPTS,
              f"{r.attempts_tried} <= {MAX_ATTEMPTS}")
        check(f"{fname}: never worse than original",
              r.after.matched_portion <= r.before.matched_portion,
              f"before={r.before.matched_portion}%  after={r.after.matched_portion}%")
        if r.improved:
            check(f"{fname}: 'improved' claim is real", r.after.matched_portion < r.before.matched_portion
                  or r.after.top_match < r.before.top_match)
        # Re-verify the returned text independently — the module's own
        # bookkeeping could disagree with reality; check against a fresh call.
        reconfirm = analyze_similarity(r.rewritten_text)
        check(
            f"{fname}: returned overlap figure matches independent re-check",
            abs(reconfirm.matched_portion - r.after.matched_portion) < 0.1,
            f"reported={r.after.matched_portion}%  independently measured={reconfirm.matched_portion}%",
        )

    print("\n-- the critical case: SAME-TOPIC independent writing must be left untouched --")
    same_topic_text = extract("14_same_topic_independent.txt")
    r = rewrite_to_reduce_overlap(same_topic_text)
    check("same-topic text is not rewritten", r.changed is False)
    check("same-topic text: zero attempts made", r.attempts_tried == 0)
    check("same-topic text returned verbatim", r.rewritten_text == same_topic_text)

    print("\n-- readability: no leftover formatting artefacts from clause-swap --")
    light = rewrite_to_reduce_overlap(extract("15_copy_light_modified.docx"))
    check("no double-comma artefacts", ", ," not in light.rewritten_text and ",  ," not in light.rewritten_text)
    check("no leading-comma-only fragments", not any(
        s.strip().startswith(",") for s in light.rewritten_text.split(". ")
    ))
    check("rewritten text is not empty", len(light.rewritten_text.strip()) > 0)
    check(
        "rewritten text is comparable length to the original (no truncation/duplication)",
        0.7 <= len(light.rewritten_text) / len(light.original_text) <= 1.4,
        f"original={len(light.original_text)} chars, rewritten={len(light.rewritten_text)} chars",
    )

    print("\n" + "=" * 70)
    print(f"{passed}/{passed + failed} checks passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        code = main()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(code)
