"""
Regression suite for the Code Optimizer (app/code_optimizer.py).

Every provider is a FAKE Python function substituted into
app.code_optimizer.PROVIDERS — this suite makes:

    0 real Gemini API calls
    0 real Groq API calls
    0 real OpenRouter API calls

    cd backend
    python test_code_optimizer.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import code_optimizer

passed = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))


def reset_providers() -> None:
    code_optimizer.PROVIDERS["groq"] = lambda prompt: None
    code_optimizer.PROVIDERS["openrouter"] = lambda prompt: None
    code_optimizer.PROVIDERS["gemini"] = lambda prompt: None


SAMPLE = """def add(a, b):
    result = a + b
    return result

def add2(x, y):
    result = x + y
    return result

def multiply(a, b):
    total = 0
    for i in range(b):
        total = total + a
    return total
"""

GOOD_OPTIMIZED = """def add(a, b):
    return a + b

def add2(x, y):
    return x + y

def multiply(a, b):
    return a * b
"""


def main() -> int:
    print("=" * 70)
    print("1 — a genuinely better, valid candidate is accepted")
    print("=" * 70)
    reset_providers()
    code_optimizer.PROVIDERS["groq"] = lambda prompt: {
        "optimized_code": GOOD_OPTIMIZED,
        "changes": ["Removed redundant intermediate variables", "Replaced manual loop with *"],
        "summary": "Simplified three functions.",
    }
    r = code_optimizer.optimize_code(SAMPLE, language="python")
    check("available", r.available)
    check("provider is groq", r.provider == "groq", r.provider)
    check("changed is True", r.changed is True)
    check("lines actually reduced (computed locally, not from the model)",
          r.optimized.lines < r.original.lines, f"{r.original.lines} -> {r.optimized.lines}")
    check("function count preserved (3 -> 3)",
          r.original.functions == r.optimized.functions == 3,
          f"{r.original.functions} -> {r.optimized.functions}")
    check("Python syntax validated", r.validation_passed and r.validation_label == "Python syntax valid")
    check("changes list is non-empty and came from the provider payload", len(r.changes) == 2)

    print("\n" + "=" * 70)
    print("2 — a candidate that drops a function is rejected, original preserved")
    print("=" * 70)
    reset_providers()
    code_optimizer.PROVIDERS["groq"] = lambda prompt: {
        "optimized_code": "def add(a, b):\n    return a + b\n",
        "changes": ["dropped stuff"], "summary": "bad",
    }
    r = code_optimizer.optimize_code(SAMPLE, language="python")
    check("not available (rejected)", r.available is False)
    check("original code preserved exactly", r.optimized_code.strip() == SAMPLE.strip())
    check("error message matches the specified copy",
          r.error == "An optimized version was generated but failed validation. The original code has been preserved.")

    print("\n" + "=" * 70)
    print("3 — invalid Python syntax from the provider is rejected")
    print("=" * 70)
    reset_providers()
    code_optimizer.PROVIDERS["groq"] = lambda prompt: {
        "optimized_code": "def add(a, b:\n    return a + b", "changes": ["x"], "summary": "y",
    }
    r = code_optimizer.optimize_code(SAMPLE, language="python")
    check("not available (syntax error caught)", r.available is False)
    check("original code preserved exactly on syntax failure", r.optimized_code.strip() == SAMPLE.strip())

    print("\n" + "=" * 70)
    print("4 — all providers unavailable -> clean 'unavailable' result, analysis unaffected")
    print("=" * 70)
    reset_providers()
    r = code_optimizer.optimize_code(SAMPLE, language="python")
    check("not available", r.available is False)
    check("error message matches the specified copy",
          r.error == "Code analysis completed, but optimization is currently unavailable.")
    check("original code returned unchanged, never empty/corrupted",
          r.optimized_code.strip() == SAMPLE.strip())

    print("\n" + "=" * 70)
    print("5 — model reports nothing safe to change: honest, not a failure")
    print("=" * 70)
    reset_providers()
    code_optimizer.PROVIDERS["groq"] = lambda prompt: {
        "optimized_code": SAMPLE, "changes": [], "summary": "Already optimal.",
    }
    r = code_optimizer.optimize_code(SAMPLE, language="python")
    check("available is True (this is a valid outcome, not an error)", r.available is True)
    check("changed is False", r.changed is False)
    check("no changes listed", r.changes == [])

    print("\n" + "=" * 70)
    print("6 — include_gemini gating")
    print("=" * 70)
    reset_providers()
    calls: list[int] = []
    code_optimizer.PROVIDERS["gemini"] = lambda prompt: (calls.append(1), None)[1]
    code_optimizer.optimize_code(SAMPLE, language="python", include_gemini=False)
    check("gemini never called when include_gemini=False (default)", len(calls) == 0, f"{len(calls)} call(s)")
    code_optimizer.optimize_code(SAMPLE, language="python", include_gemini=True)
    check("gemini called when include_gemini=True (still mocked, not live)", len(calls) == 1, f"{len(calls)} call(s)")

    print("\n" + "=" * 70)
    print("7 — non-Python language falls back to the honest, weaker structural check")
    print("=" * 70)
    reset_providers()
    js_sample = "function add(a, b) { return a + b; }\nfunction sub(a, b) { return a - b; }\n"
    code_optimizer.PROVIDERS["groq"] = lambda prompt: {
        "optimized_code": "const add = (a, b) => a + b;\nconst sub = (a, b) => a - b;\n",
        "changes": ["Converted to arrow functions"], "summary": "Simplified.",
    }
    r = code_optimizer.optimize_code(js_sample, language="javascript")
    check("available", r.available)
    check("validation label is the weaker structural check, not claimed as syntax-valid",
          r.validation_label == "Structural check passed", r.validation_label)
    check("balanced braces accepted", r.validation_passed)

    js_broken = "function add(a, b) { return a + b;\n"  # missing closing brace
    code_optimizer.PROVIDERS["groq"] = lambda prompt: {
        "optimized_code": js_broken, "changes": ["x"], "summary": "y",
    }
    r2 = code_optimizer.optimize_code(js_sample, language="javascript")
    check("unbalanced braces rejected", r2.available is False)

    print("\n" + "=" * 70)
    print("8 — complexity: model claim carried through + a real local cross-check")
    print("=" * 70)
    reset_providers()
    NESTED_LOOP_CODE = """def has_duplicate(items):
    for i in range(len(items)):
        for j in range(len(items)):
            if i != j and items[i] == items[j]:
                return True
    return False
"""
    OPTIMIZED_SET_CODE = """def has_duplicate(items):
    return len(items) != len(set(items))
"""
    code_optimizer.PROVIDERS["groq"] = lambda prompt: {
        "optimized_code": OPTIMIZED_SET_CODE,
        "changes": ["Replaced O(n^2) nested loop with a set-based length check"],
        "summary": "Used a set to detect duplicates in linear time.",
        "complexity": {
            "before": {"time": "O(n^2)", "space": "O(1)"},
            "after": {"time": "O(n)", "space": "O(n)"},
            "reasoning": "Nested loop replaced by a single pass building a set.",
        },
    }
    r = code_optimizer.optimize_code(NESTED_LOOP_CODE, language="python")
    check("model's complexity claim carried through (before.time)", r.complexity.before.time == "O(n^2)", r.complexity.before.time)
    check("model's complexity claim carried through (after.time)", r.complexity.after.time == "O(n)", r.complexity.after.time)
    check("reasoning carried through", r.complexity.reasoning != "")
    check("LOCAL loop-nesting cross-check: before has depth 2 (real AST count, not the model's claim)",
          r.complexity.loop_nesting_before == 2, r.complexity.loop_nesting_before)
    check("LOCAL loop-nesting cross-check: after has depth 0 (no loops left)",
          r.complexity.loop_nesting_after == 0, r.complexity.loop_nesting_after)

    print("\n-- malformed/missing complexity from the provider degrades safely --")
    reset_providers()
    code_optimizer.PROVIDERS["groq"] = lambda prompt: {
        "optimized_code": GOOD_OPTIMIZED, "changes": ["x"], "summary": "y",
        "complexity": {"before": {"time": "not-bigo-format"}},  # malformed
    }
    r2 = code_optimizer.optimize_code(SAMPLE, language="python")
    check("malformed complexity value falls back to O(?) instead of showing garbage",
          r2.complexity.before.time == "O(?)", r2.complexity.before.time)

    print("\n-- non-Python language gets no local loop-nesting cross-check (honest, not guessed) --")
    reset_providers()
    code_optimizer.PROVIDERS["groq"] = lambda prompt: {
        "optimized_code": "const add = (a, b) => a + b;\n", "changes": ["x"], "summary": "y",
        "complexity": {"before": {"time": "O(1)", "space": "O(1)"}, "after": {"time": "O(1)", "space": "O(1)"}},
    }
    r3 = code_optimizer.optimize_code("function add(a, b) { return a + b; }\n", language="javascript")
    check("no local loop-nesting number fabricated for a non-Python language",
          r3.complexity.loop_nesting_before is None and r3.complexity.loop_nesting_after is None)

    print("\n" + "=" * 70)
    print(f"{passed}/{passed + failed} checks passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
