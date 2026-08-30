"""
Regression suite for the similarity / plagiarism engine.

Runs against an ISOLATED temporary database, so it never touches
backend/data/history.db and never pollutes the real comparison corpus.

Fixtures live in samples/eval/. Run:

    cd backend
    python test_similarity_eval.py

These thresholds encode measured behaviour, not aspirations. Before the
windowing fix, the partial-copy case scored 55.3% with ZERO reported
passages; it now reports 84% with half the document flagged.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import db

_TMP = tempfile.mkdtemp(prefix="sim_eval_")
db.DB_PATH = os.path.join(_TMP, "eval.db")
db.init_db()

from app.file_pipeline import build_units  # noqa: E402
from app.similarity import (  # noqa: E402
    MATCH_THRESHOLD,
    analyze_similarity,
    store_reference_chunks,
)

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
    print("SIMILARITY REGRESSION — isolated corpus")
    print("=" * 70)

    # Seed the corpus with the original only.
    source = extract("01_source_original.txt")
    seed = analyze_similarity(source)
    check("empty corpus reports no match", seed.top_match == 0.0, f"top={seed.top_match}")

    hid = db.insert_history(
        file_name="01_source_original.txt", file_type="txt", analysis_type="text",
        ai_probability=0.0, similarity_score=0.0, confidence="low",
        status="analyzed", result_json={},
    )
    store_reference_chunks(hid, "01_source_original.txt", source)

    print("\n-- copies must be caught --")
    verbatim = analyze_similarity(extract("02_copy_verbatim.docx"))
    check("verbatim copy flagged", verbatim.top_match >= 95, f"top={verbatim.top_match}%")
    check("verbatim: whole document matched", verbatim.matched_portion >= 90,
          f"portion={verbatim.matched_portion}%")

    para = analyze_similarity(extract("03_copy_paraphrased.docx"))
    check("paraphrase caught", para.top_match >= 70, f"top={para.top_match}%")

    partial = analyze_similarity(extract("04_copy_partial.pptx"))
    check("patchwork copy caught", partial.top_match >= 70, f"top={partial.top_match}%")
    check("patchwork reports passages", len(partial.matches) >= 1,
          f"{len(partial.matches)} passage(s)")
    check("patchwork portion is partial, not total",
          10 <= partial.matched_portion <= 90, f"portion={partial.matched_portion}%")

    print("\n-- originals must stay clean --")
    for fname, label in [
        ("05_unrelated.pdf", "unrelated document"),
        ("09_human_academic.pdf", "human academic"),
        ("10_human_gettysburg.txt", "Gettysburg 1863"),
        ("11_human_austen.txt", "Austen 1813"),
    ]:
        r = analyze_similarity(extract(fname))
        check(f"{label} not flagged", len(r.matches) == 0,
              f"top={r.top_match}% (threshold {MATCH_THRESHOLD*100:.0f}%)")

    print("\n-- invariants --")
    allr = [verbatim, para, partial]
    check("no negative percentages", all(r.top_match >= 0 for r in allr))
    check("top >= mean for every result",
          all(r.top_match >= r.overall_similarity - 0.05 for r in allr))

    dup = analyze_similarity(source, exclude_file_name="01_source_original.txt")
    check("re-upload does not self-flag", len(dup.matches) == 0,
          f"top={dup.top_match}% with filename excluded")

    print("\n" + "=" * 70)
    print(f"{passed}/{passed + failed} checks passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        code = main()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(code)
