"""
Test the analyzability gate, prose/code classification, and chunking in
isolation (no API / UI / model download required for most cases).

Usage:
  python test_detection.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.text_quality import assess
from app.content_classifier import classify_block
from app.chunking import chunk_prose, chunk_code
from app.file_pipeline import Unit

PASS = "PASS"
FAIL = "FAIL"
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, condition, detail))
    print(f"[{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def main() -> None:
    print("=" * 70)
    print("TEST A — gibberish input must be unanalyzable, not scored")
    r = assess("cnsdcsdcscdscdscdscd")
    check("gibberish -> unanalyzable", r.status == "unanalyzable", r.reason)

    print("\nTEST A2 — keyboard-mashing input must be unanalyzable")
    r = assess("asdfghjklqwerty")
    check("keyboard-mash -> unanalyzable", r.status == "unanalyzable", r.reason)

    print("\nTEST B — short-but-real text must be 'insufficient', not an error")
    r = assess("Hello world.")
    check("short text -> insufficient", r.status == "insufficient", r.reason)

    print("\nTEST B2 — symbols/numbers must be unanalyzable")
    r = assess("12345 67890 !!!!! $$$ ###")
    check("symbols/numbers -> unanalyzable", r.status == "unanalyzable", r.reason)

    print("\nTEST B3 — repeated characters must be unanalyzable")
    r = assess("aaaaaaaaaaaaaaaaaaaa")
    check("repeated chars -> unanalyzable", r.status == "unanalyzable", r.reason)

    print("\nTEST C/D — a normal paragraph must pass the gate ('ok')")
    r = assess(
        "The history of computing spans many decades of innovation, beginning "
        "with mechanical calculators and evolving through vacuum tubes into "
        "the modern era of digital devices used by billions of people today."
    )
    check("normal paragraph -> ok", r.status == "ok", r.reason)

    print("\n" + "=" * 70)
    print("TEST E — Python snippet must classify as code, not prose")
    cls = classify_block("def calculate_sum(a, b):\n    return a + b\n\ndef multiply(x, y):\n    return x * y")
    check("python snippet -> code", cls == "code", f"got {cls!r}")

    print("\nTEST F — C# snippet must classify as code, not prose")
    cls = classify_block(
        "public class Student\n{\n    public string Name { get; set; }\n"
        "    public int Age { get; set; }\n}"
    )
    check("c# snippet -> code", cls == "code", f"got {cls!r}")

    print("\nTEST — a normal paragraph mentioning code-ish words must stay prose")
    cls = classify_block(
        "You should return the item to the store if possible, since the "
        "policy allows returns within thirty days of the original purchase date."
    )
    check("prose mentioning 'return' -> prose", cls == "prose", f"got {cls!r}")

    print("\n" + "=" * 70)
    print("TEST I — large document must be split into multiple chunks covering all of it")
    paragraph = (
        "The history of computing spans many decades of innovation, beginning with "
        "mechanical calculators and evolving through vacuum tubes, transistors, and "
        "integrated circuits into the modern era of ubiquitous digital devices. "
    )
    units = [Unit(index=i + 1, source=f"page {i + 1}", text=paragraph * 3) for i in range(12)]
    chunks = chunk_prose(units)
    total_words_in = sum(len(u.text.split()) for u in units)
    total_words_out = sum(c.word_count for c in chunks)
    check("large doc -> multiple chunks", len(chunks) > 1, f"{len(chunks)} chunks")
    check("large doc -> full coverage (no dropped content)", total_words_in == total_words_out,
          f"{total_words_out}/{total_words_in} words captured")

    print("\nTEST — code chunking must NOT merge non-adjacent pages "
          "(e.g. Python on page 2, prose on page 4, C# on page 5)")
    code_units = [
        Unit(index=2, source="page 2", text="def f():\n    return 1"),
        Unit(index=5, source="page 5", text="public class C {\n    void M() {}\n}"),
    ]
    code_chunks = chunk_code(code_units)
    check("non-adjacent pages -> separate chunks", len(code_chunks) == 2,
          f"got {len(code_chunks)} chunk(s), indices={[c.unit_indices for c in code_chunks]}")

    adjacent_units = [
        Unit(index=2, source="page 2", text="def f():\n    return 1"),
        Unit(index=3, source="page 3", text="def g():\n    return 2"),
    ]
    adjacent_chunks = chunk_code(adjacent_units)
    check("adjacent pages -> merged into one chunk", len(adjacent_chunks) == 1,
          f"got {len(adjacent_chunks)} chunk(s)")

    print("\n" + "=" * 70)
    passed = sum(1 for _, ok, _ in _results if ok)
    total = len(_results)
    print(f"\n{passed}/{total} checks passed.")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
