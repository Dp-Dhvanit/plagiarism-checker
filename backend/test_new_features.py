"""
Test the DB layer, similarity pipeline, image validation, and PDF report
generation for the 4 new features — in isolation, no running API server
required. Does NOT call the real Gemini API (no key needed) — the
Gemini-backed pieces (ai_text_detector.py, image_detector.py's actual
model call) are exercised only through the live API when GEMINI_API_KEY
is set; this script covers everything that doesn't need it.

Usage:
  python test_new_features.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PASS = "PASS"
FAIL = "FAIL"
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, condition, detail))
    print(f"[{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def test_db() -> None:
    print("=" * 70)
    print("DB — analysis_history + reference_chunks")
    from app import db
    import tempfile

    tmp_dir = tempfile.mkdtemp()
    db.DB_PATH = str(Path(tmp_dir) / "test_history.db")
    db.init_db()

    hid = db.insert_history(
        file_name="essay.pdf", file_type="pdf", analysis_type="text",
        ai_probability=72.5, similarity_score=10.0, confidence="high",
        status="analyzed", result_json={"heuristic": {"ai_likelihood_score": 72.5}},
    )
    check("insert_history returns an id", isinstance(hid, int) and hid > 0, f"id={hid}")

    row = db.get_history(hid)
    check("get_history round-trips result_json", row is not None and row["result_json"]["heuristic"]["ai_likelihood_score"] == 72.5)

    hid2 = db.insert_history(
        file_name="photo.png", file_type="png", analysis_type="image",
        ai_probability=81.0, similarity_score=None, confidence="medium",
        status="analyzed", result_json={"image_result": {}},
    )
    items = db.list_history(filter_type="all", sort="newest")
    check("list_history returns both rows", len(items) == 2, f"{len(items)} rows")
    text_only = db.list_history(filter_type="text")
    check("list_history filter=text excludes image row", len(text_only) == 1 and text_only[0]["id"] == hid)

    stats = db.get_dashboard_stats()
    check("dashboard stats: total_analyses == 2", stats["total_analyses"] == 2, str(stats))
    check("dashboard stats: ai_flagged counts >=60 rows", stats["ai_flagged"] == 2, str(stats))

    import numpy as np
    db.insert_reference_chunks(hid, "essay.pdf", ["chunk one text", "chunk two text"], np.random.rand(2, 384).astype(np.float32))
    corpus = db.get_all_reference_chunks()
    check("reference_chunks stored", len(corpus) == 2, f"{len(corpus)} chunks")

    deleted = db.delete_history(hid)
    check("delete_history returns True for existing id", deleted is True)
    corpus_after = db.get_all_reference_chunks()
    check("deleting history cascades to reference_chunks", len(corpus_after) == 0, f"{len(corpus_after)} chunks left")
    check("delete_history returns False for missing id", db.delete_history(hid) is False)

    db.delete_history(hid2)


def test_similarity_empty_corpus() -> None:
    print("\n" + "=" * 70)
    print("SIMILARITY — empty corpus must report 'no comparable submissions', not fabricate a score")
    from app import db
    from app.similarity import analyze_similarity
    import tempfile

    db.DB_PATH = str(Path(tempfile.mkdtemp()) / "empty.db")
    db.init_db()

    result = analyze_similarity("This is a short document with a handful of sentences to test chunking behavior.")
    check("empty corpus -> overall_similarity is 0", result.overall_similarity == 0.0)
    check("empty corpus -> corpus_size is 0", result.corpus_size == 0)
    check("empty corpus -> note explains why", "no comparable" in result.note.lower())


def test_similarity_with_match() -> None:
    print("\n" + "=" * 70)
    print("SIMILARITY — a near-duplicate document must be flagged as a match")
    from app import db
    from app.similarity import analyze_similarity, store_reference_chunks
    import tempfile

    db.DB_PATH = str(Path(tempfile.mkdtemp()) / "match.db")
    db.init_db()

    original = (
        "Climate change is driven primarily by the accumulation of greenhouse gases "
        "in the atmosphere, largely from burning fossil fuels for energy and transport. "
        "Rising global temperatures are causing more frequent extreme weather events, "
        "melting polar ice caps, and shifting precipitation patterns worldwide."
    )
    hid = db.insert_history(
        file_name="source_essay.txt", file_type="txt", analysis_type="text",
        ai_probability=20.0, similarity_score=0.0, confidence="low",
        status="analyzed", result_json={},
    )
    store_reference_chunks(hid, "source_essay.txt", original)

    near_duplicate = original  # identical text -> should be a near-perfect match
    result = analyze_similarity(near_duplicate)
    check("near-duplicate -> overall_similarity is high", result.overall_similarity >= 90.0, f"{result.overall_similarity}")
    check("near-duplicate -> at least one match reported", len(result.matches) >= 1)
    if result.matches:
        check("match cites the real source file", result.matches[0].source_file == "source_essay.txt")


def test_image_validation() -> None:
    print("\n" + "=" * 70)
    print("IMAGE VALIDATION — valid PNG accepted, garbage bytes rejected")
    from app.image_detector import validate_image, ImageValidationError
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(120, 180, 200)).save(buf, format="PNG")
    mime = validate_image(buf.getvalue())
    check("valid PNG -> mime type detected", mime == "image/png", mime)

    try:
        validate_image(b"not an image, just some random bytes")
        check("garbage bytes -> raises ImageValidationError", False)
    except ImageValidationError:
        check("garbage bytes -> raises ImageValidationError", True)

    try:
        validate_image(b"")
        check("empty bytes -> raises ImageValidationError", False)
    except ImageValidationError:
        check("empty bytes -> raises ImageValidationError", True)


def test_pdf_report() -> None:
    print("\n" + "=" * 70)
    print("PDF REPORT — generates a well-formed PDF from a fake history row")
    from app.pdf_report import generate_report

    fake_row = {
        "id": 1,
        "file_name": "essay.pdf",
        "analysis_type": "text",
        "created_at": "2026-08-23T10:00:00+00:00",
        "status": "analyzed",
        "result_json": {
            "heuristic": {"ai_likelihood_score": 65.0, "verdict": "Uncertain", "perplexity": 22.1, "burstiness": 5.4},
            "gemini_text": {
                "ai_probability": 70.0, "confidence": "medium",
                "flagged_sections": [{"text": "Furthermore, it is crucial to note", "reason": "generic transition phrase"}],
                "explanation": "The text shows some patterns potentially associated with AI generation.",
            },
            "similarity": {
                "overall_similarity": 18.0,
                "matches": [{"query_excerpt": "sample excerpt", "matched_text": "sample match", "source_file": "other.pdf", "source_history_id": 2, "score": 62.0}],
                "chunks_compared": 4, "corpus_size": 10, "note": "",
            },
            "image_result": None,
            "extracted_text_preview": "This is a preview of the extracted document text used for the report.",
        },
    }
    pdf_bytes = generate_report(fake_row)
    check("PDF generation returns non-empty bytes", len(pdf_bytes) > 500, f"{len(pdf_bytes)} bytes")
    check("output starts with the PDF magic header", pdf_bytes[:5] == b"%PDF-")


def main() -> None:
    test_db()
    test_similarity_empty_corpus()
    test_similarity_with_match()
    test_image_validation()
    test_pdf_report()

    print("\n" + "=" * 70)
    passed = sum(1 for _, ok, _ in _results if ok)
    total = len(_results)
    print(f"\n{passed}/{total} checks passed.")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
