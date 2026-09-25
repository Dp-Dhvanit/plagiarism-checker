"""
AI-assisted source-code optimization (Code Optimizer).

A genuinely new capability — app/code_analyzer.py only estimates AI-
authorship likelihood via regex heuristics and calls no AI provider at all.
This module is the first thing in the Code Analysis screen to actually
call an LLM.

Same principle as app/rewrite_providers.py (Remove Plagiarism): providers
only ever GENERATE a candidate. They are never trusted for correctness
claims. What actually gets shown is decided locally:
  - metrics (line/function/class/import counts) computed from the real
    before/after strings, never the model's own numbers
  - validation: real AST parsing for Python, a much weaker brace/paren/
    bracket-balance check for every other language (no new dependency
    means no real parser for those — this is disclosed, not overstated)

Provider order: Groq -> OpenRouter -> Gemini (only if include_gemini=True,
same quota-conscious gating as Remove Plagiarism). No local candidate
generator exists here — turning "make this code shorter without changing
behavior" into a deterministic rule-based transform the way the local
plagiarism rewriter does for sentence restructuring is not a safe,
general operation, so this feature is AI-only with local validation as
the safety net instead.
"""
from __future__ import annotations

import ast
import logging
import os
import re
from dataclasses import dataclass, field

logger = logging.getLogger("app.code_optimizer")

OPTIMIZE_PROMPT = """You are a source-code optimization assistant.

Analyze the supplied {language} source code and produce a more concise version while preserving its intended behavior.

Prioritize, in this exact order:
1. correctness
2. behavior preservation
3. syntax validity
4. readability
5. maintainability
6. code reduction

Rules:
- Do not remove functionality. Do not invent functionality.
- Do not change APIs, function signatures, class interfaces, database behavior, or any externally visible behavior, unless the original code is clearly redundant and the change is demonstrably safe.
- Do not rewrite the code merely for stylistic reasons.
- If the code cannot be safely optimized, return the ORIGINAL code unchanged and say so.
- Line reduction is the LOWEST priority. A small, safe reduction is better than a large, risky one.

Also estimate Big-O time and space complexity for the code BEFORE and AFTER your change. Use standard notation (e.g. "O(1)", "O(n)", "O(n^2)", "O(log n)", "O(n log n)"). Base it on the dominant loops/recursion/data-structure operations actually present. If you cannot determine it confidently, use "O(?)" rather than guessing.

Respond with ONLY a JSON object, no prose and no code fences:
{{"optimized_code": "<the optimized source, or the original unchanged if nothing safe to change>", "changes": ["<short factual description of one actual change>", "..."], "summary": "<one sentence>", "complexity": {{"before": {{"time": "O(...)", "space": "O(...)"}}, "after": {{"time": "O(...)", "space": "O(...)"}}, "reasoning": "<one short sentence>"}}}}

Use \\n for newlines inside optimized_code. If nothing was safely changeable, "changes" must be an empty list and optimized_code must equal the original.

SOURCE CODE:
{code}
"""

MAX_CODE_CHARS = 12000

_CLASS_RE: dict[str, str] = {
    "python": r"^\s*class\s+\w+",
    "javascript": r"^\s*(?:export\s+)?class\s+\w+",
    "typescript": r"^\s*(?:export\s+)?class\s+\w+",
    "java": r"^\s*(?:public|private|protected)?\s*(?:static\s+)?class\s+\w+",
    "csharp": r"^\s*(?:public|private|protected|internal)?\s*class\s+\w+",
    "cpp": r"^\s*class\s+\w+",
    "kotlin": r"^\s*class\s+\w+",
    "php": r"^\s*class\s+\w+",
    "ruby": r"^\s*class\s+\w+",
    "swift": r"^\s*(?:class|struct)\s+\w+",
}
_IMPORT_RE: dict[str, str] = {
    "python": r"^\s*(?:import|from)\s+\w",
    "javascript": r"^\s*import\s+",
    "typescript": r"^\s*import\s+",
    "java": r"^\s*import\s+",
    "csharp": r"^\s*using\s+\w",
    "cpp": r"^\s*#include\s+",
    "c": r"^\s*#include\s+",
    "go": r"^\s*import\s+",
    "ruby": r"^\s*require\s+",
    "php": r"^\s*(?:use|require|include)",
    "kotlin": r"^\s*import\s+",
    "swift": r"^\s*import\s+",
}
_FUNC_RE: dict[str, str] = {
    "python": r"^\s*(?:async\s+)?def\s+\w+",
    "javascript": r"(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\()",
    "typescript": r"(?:function\s+\w+|(?:const|let)\s+\w+\s*=\s*(?:async\s*)?\()",
    "java": r"(?:public|private|protected|static)\s+\w[\w<>]*\s+\w+\s*\(",
    "csharp": r"(?:public|private|protected|static)\s+\w[\w<>]*\s+\w+\s*\(",
    "cpp": r"\w+\s+\w+\s*\([^)]*\)\s*(?:const\s*)?\{",
    "c": r"\w+\s+\w+\s*\([^)]*\)\s*\{",
    "go": r"func\s+\w+\s*\(",
    "ruby": r"^\s*def\s+\w+",
    "php": r"function\s+\w+\s*\(",
    "kotlin": r"fun\s+\w+\s*\(",
    "swift": r"func\s+\w+\s*\(",
}


def _count_lines(code: str) -> int:
    return len([l for l in code.splitlines() if l.strip()])


def _count_matches(code: str, pattern: str | None) -> int:
    if not pattern:
        return 0
    return len(re.findall(pattern, code, re.MULTILINE))


def _max_loop_nesting_python(code: str) -> int | None:
    """Real, locally-computed cross-check for Python only (where a real
    parser is available) — max nested for/while depth, a genuine lower
    bound on polynomial-loop complexity. NOT a full complexity analysis
    (misses recursion, data-structure operation costs) — shown alongside
    the model's own Big-O claim, never in place of it. Returns None if the
    code doesn't parse; no equivalent is computed for other languages,
    since a regex-based guess there would be unreliable enough to be
    actively misleading rather than just incomplete."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    max_depth = 0

    def visit(node: ast.AST, depth: int) -> None:
        nonlocal max_depth
        is_loop = isinstance(node, (ast.For, ast.While, ast.AsyncFor))
        new_depth = depth + 1 if is_loop else depth
        max_depth = max(max_depth, new_depth)
        for child in ast.iter_child_nodes(node):
            visit(child, new_depth)

    visit(tree, 0)
    return max_depth


@dataclass
class LocalMetrics:
    lines: int
    functions: int
    classes: int
    imports: int


def _local_metrics(code: str, language: str) -> LocalMetrics:
    return LocalMetrics(
        lines=_count_lines(code),
        functions=_count_matches(code, _FUNC_RE.get(language)),
        classes=_count_matches(code, _CLASS_RE.get(language)),
        imports=_count_matches(code, _IMPORT_RE.get(language)),
    )


# ── Validation ────────────────────────────────────────────────────────────

def _validate_python(original: str, optimized: str) -> tuple[bool, list[str]]:
    try:
        ast.parse(optimized)
    except SyntaxError as exc:
        return False, [f"Python syntax error at line {exc.lineno}: {exc.msg}"]

    notes = ["Python syntax valid"]
    try:
        orig_tree = ast.parse(original)
        opt_tree = ast.parse(optimized)
        orig_funcs = {n.name for n in ast.walk(orig_tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        opt_funcs = {n.name for n in ast.walk(opt_tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        orig_classes = {n.name for n in ast.walk(orig_tree) if isinstance(n, ast.ClassDef)}
        opt_classes = {n.name for n in ast.walk(opt_tree) if isinstance(n, ast.ClassDef)}
        missing_funcs = orig_funcs - opt_funcs
        missing_classes = orig_classes - opt_classes
        if missing_funcs:
            notes.append(f"Function(s) dropped: {', '.join(sorted(missing_funcs))}")
            return False, notes
        if missing_classes:
            notes.append(f"Class(es) dropped: {', '.join(sorted(missing_classes))}")
            return False, notes
        notes.append("Functions and classes preserved")
    except SyntaxError:
        pass  # original itself didn't parse; the optimized-code check above already ran
    return True, notes


def _validate_structural_balance(optimized: str) -> tuple[bool, list[str]]:
    """Weak, honest fallback for every language without a real parser
    available (no new dependency was permitted): brace/paren/bracket
    balance only. This is NOT a syntax check and is labeled as such."""
    pairs = {")": "(", "]": "[", "}": "{"}
    opens = set(pairs.values())
    stack: list[str] = []
    in_string: str | None = None
    i = 0
    while i < len(optimized):
        ch = optimized[i]
        if in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == in_string:
                in_string = None
        elif ch in ("'", '"', "`"):
            in_string = ch
        elif ch in opens:
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack[-1] != pairs[ch]:
                return False, [f"Structural check failed: unbalanced '{ch}'"]
            stack.pop()
        i += 1
    if stack:
        return False, [f"Structural check failed: unclosed '{stack[-1]}'"]
    return True, ["Structural check passed (brace/paren/bracket balance — not a full syntax check)"]


def _validate(language: str, original: str, optimized: str) -> tuple[bool, str, list[str]]:
    if language == "python":
        ok, notes = _validate_python(original, optimized)
        return ok, "Python syntax valid" if ok else "Python validation failed", notes
    ok, notes = _validate_structural_balance(optimized)
    return ok, "Structural check passed" if ok else "Structural check failed", notes


# ── Candidate validation (before it's even worth running local checks) ────

_META_MARKERS = ("here's the optimized", "here is the optimized", "as an ai", "i cannot", "i'm sorry")


def _looks_like_meta_commentary(text: str) -> bool:
    low = text.strip().lower()
    return any(low.startswith(m) for m in _META_MARKERS)


# ── Provider calls — same wire conventions as app/rewrite_providers.py,
# different response contract (JSON with optimized_code/changes/summary
# instead of plain rewritten text), so kept as its own small functions
# rather than forced through that module's helpers. ─────────────────────

def _extract_json(content: str) -> dict | None:
    from app.detectors.openai_compat import OpenAICompatDetector
    return OpenAICompatDetector._extract_json(content)


def _call_openai_compat(endpoint: str, key: str, model: str, prompt: str, timeout: int) -> dict | None:
    import requests
    try:
        resp = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout,
        )
        if not resp.ok:
            logger.info("code_optimizer provider HTTP %s from %s", resp.status_code, endpoint)
            return None
        content = resp.json()["choices"][0]["message"]["content"]
        return _extract_json(content)
    except Exception as exc:  # noqa: BLE001
        logger.info("code_optimizer provider call failed (%s): %s", endpoint, exc)
        return None


def _groq_optimize(prompt: str) -> dict | None:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    endpoint = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/") + "/chat/completions"
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    return _call_openai_compat(endpoint, key, model, prompt, timeout=60)


def _openrouter_optimize(prompt: str) -> dict | None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    endpoint = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/") + "/chat/completions"
    model = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
    return _call_openai_compat(endpoint, key, model, prompt, timeout=75)


def _gemini_optimize(prompt: str) -> dict | None:
    try:
        from app import gemini_keys
        from app.gemini_client import GEMINI_MODEL_FLASH, TIMEOUT_MS, is_configured
        if not is_configured():
            return None
        from google.genai import types as genai_types

        def _call(client):
            return client.models.generate_content(
                model=GEMINI_MODEL_FLASH,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                    http_options=genai_types.HttpOptions(timeout=TIMEOUT_MS),
                ),
            )

        response = gemini_keys.call_with_rotation(_call)
        text = response.text
        return _extract_json(text) if text else None
    except Exception as exc:  # noqa: BLE001
        logger.info("code_optimizer gemini call failed: %s", exc)
        return None


PROVIDERS: dict[str, "callable"] = {
    "groq": _groq_optimize,
    "openrouter": _openrouter_optimize,
    "gemini": _gemini_optimize,
}


# ── Orchestration ─────────────────────────────────────────────────────────

_VALID_BIGO = re.compile(r"^O\([^)]*\)$")


@dataclass
class ComplexitySide:
    time: str = "O(?)"
    space: str = "O(?)"


@dataclass
class ComplexityEstimate:
    # The MODEL's own claim — never locally verified, always labeled as an
    # estimate in the UI. A real general-purpose complexity analyzer is a
    # much bigger undertaking than this feature warrants.
    before: ComplexitySide = field(default_factory=ComplexitySide)
    after: ComplexitySide = field(default_factory=ComplexitySide)
    reasoning: str = ""
    # A genuinely LOCAL cross-check, Python only (real parser available) —
    # max nested for/while depth. None for every other language, and None
    # for Python if the code didn't parse. Not a full complexity analysis
    # (misses recursion and data-structure costs) — a lower-bound signal
    # shown next to the model's claim, not a replacement for it.
    loop_nesting_before: int | None = None
    loop_nesting_after: int | None = None


@dataclass
class OptimizationResult:
    available: bool
    provider: str | None
    optimized_code: str
    changed: bool
    changes: list[str] = field(default_factory=list)
    summary: str = ""
    original: LocalMetrics = field(default_factory=lambda: LocalMetrics(0, 0, 0, 0))
    optimized: LocalMetrics = field(default_factory=lambda: LocalMetrics(0, 0, 0, 0))
    validation_passed: bool = False
    validation_label: str = ""
    validation_notes: list[str] = field(default_factory=list)
    complexity: ComplexityEstimate = field(default_factory=ComplexityEstimate)
    error: str | None = None


def _parse_complexity_side(raw: dict | None) -> ComplexitySide:
    raw = raw or {}
    time = str(raw.get("time", "O(?)")).strip() or "O(?)"
    space = str(raw.get("space", "O(?)")).strip() or "O(?)"
    if not _VALID_BIGO.match(time):
        time = "O(?)"
    if not _VALID_BIGO.match(space):
        space = "O(?)"
    return ComplexitySide(time=time, space=space)


def _try_candidate(provider_fn, code: str, language: str) -> tuple[str, list[str], str, dict] | None:
    prompt = OPTIMIZE_PROMPT.format(language=language, code=code[:MAX_CODE_CHARS])
    payload = provider_fn(prompt)
    if not payload or "optimized_code" not in payload:
        return None
    optimized_code = str(payload.get("optimized_code", "")).strip()
    if not optimized_code or _looks_like_meta_commentary(optimized_code):
        return None
    changes = [str(c) for c in (payload.get("changes") or []) if str(c).strip()]
    summary = str(payload.get("summary", "")).strip()
    complexity_raw = payload.get("complexity") if isinstance(payload.get("complexity"), dict) else {}
    return optimized_code, changes, summary, complexity_raw


def optimize_code(code: str, language: str = "unknown", include_gemini: bool = False) -> OptimizationResult:
    code = code.strip()
    original_metrics = _local_metrics(code, language)

    sources = [("groq", PROVIDERS["groq"]), ("openrouter", PROVIDERS["openrouter"])]
    if include_gemini:
        sources.append(("gemini", PROVIDERS["gemini"]))

    any_failed_validation = False

    for source_name, provider_fn in sources:
        candidate = _try_candidate(provider_fn, code, language)
        if candidate is None:
            continue
        optimized_code, changes, summary, complexity_raw = candidate

        complexity = ComplexityEstimate(
            before=_parse_complexity_side(complexity_raw.get("before")),
            after=_parse_complexity_side(complexity_raw.get("after")),
            reasoning=str(complexity_raw.get("reasoning", "")).strip(),
            loop_nesting_before=_max_loop_nesting_python(code) if language == "python" else None,
            loop_nesting_after=_max_loop_nesting_python(optimized_code) if language == "python" else None,
        )

        if optimized_code.strip() == code.strip():
            # Model itself reported nothing safe to change — an honest,
            # valid outcome, not a failure.
            return OptimizationResult(
                available=True, provider=source_name, optimized_code=code, changed=False,
                changes=[], summary=summary or "No safe optimization was found.",
                original=original_metrics, optimized=original_metrics,
                validation_passed=True, validation_label="No change proposed",
                validation_notes=["The model reported no safe reduction was possible."],
                complexity=complexity,
            )

        valid, label, notes = _validate(language, code, optimized_code)
        if not valid:
            logger.info("code_optimizer: %s candidate failed validation: %s", source_name, notes)
            any_failed_validation = True
            continue  # try the next source rather than showing broken code

        optimized_metrics = _local_metrics(optimized_code, language)
        return OptimizationResult(
            available=True, provider=source_name, optimized_code=optimized_code, changed=True,
            changes=changes, summary=summary,
            original=original_metrics, optimized=optimized_metrics,
            validation_passed=True, validation_label=label, validation_notes=notes,
            complexity=complexity,
        )

    if any_failed_validation:
        return OptimizationResult(
            available=False, provider=None, optimized_code=code, changed=False,
            original=original_metrics, optimized=original_metrics,
            validation_passed=False, validation_label="Validation failed",
            error="An optimized version was generated but failed validation. The original code has been preserved.",
        )
    return OptimizationResult(
        available=False, provider=None, optimized_code=code, changed=False,
        original=original_metrics, optimized=original_metrics,
        validation_passed=False, validation_label="Unavailable",
        error="Code analysis completed, but optimization is currently unavailable.",
    )
