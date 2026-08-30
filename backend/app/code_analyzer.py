"""
Code AI-detection engine — v2 with modern AI code signals.

Key insight: GPT-4/Gemini code is NOT detected by comments alone.
Modern AI writes clean, minimal-comment code that is detectable by:
  1. Zero debug artifacts (no TODO, commented-out code, temp vars)
  2. Thorough edge-case handling
  3. Consistent line-length distribution
  4. Uniform function structure
  5. Perfect naming convention adherence

Seven weighted signals → AI-likelihood score 0-100.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import numpy as np

# ── Language fingerprints ────────────────────────────────────────────────────
LANG_SIGNATURES: dict[str, dict] = {
    "python": {
        "keywords": ["def ", "import ", "class ", "elif ", "self.", "__init__", "print(", "lambda "],
        "comment_re": r"#[^\n]*",
        "docstring_re": r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'',
        "error_re": r"\btry\b[\s\S]*?\bexcept\b",
        "func_re": r"^\s*def\s+\w+",
        "edge_patterns": [
            r"\bis\s+None\b", r"\bis\s+not\s+None\b", r"\bisinstance\s*\(",
            r"\bValueError\b", r"\bTypeError\b", r"\bKeyError\b",
            r"\braise\s+\w+Error", r"\bassert\s+\w+", r"if\s+not\s+\w+",
        ],
    },
    "javascript": {
        "keywords": ["function ", "const ", "let ", "var ", "=>", "console.log", "require(", "async ", "await "],
        "comment_re": r"//[^\n]*|/\*[\s\S]*?\*/",
        "docstring_re": r"/\*\*[\s\S]*?\*/",
        "error_re": r"\btry\s*\{[\s\S]*?\}\s*catch\s*\(",
        "func_re": r"(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\()",
        "edge_patterns": [
            r"=== null", r"!== null", r"=== undefined", r"typeof\s+\w+",
            r"\bthrow\s+new\s+\w+Error", r"Array\.isArray", r"instanceof\s+\w+",
        ],
    },
    "typescript": {
        "keywords": ["interface ", ": string", ": number", ": boolean", "type ", "export ", "import {"],
        "comment_re": r"//[^\n]*|/\*[\s\S]*?\*/",
        "docstring_re": r"/\*\*[\s\S]*?\*/",
        "error_re": r"\btry\s*\{[\s\S]*?\}\s*catch\s*\(",
        "func_re": r"(?:function\s+\w+|(?:const|let)\s+\w+\s*=\s*(?:async\s*)?\()",
        "edge_patterns": [r"=== null", r"!== null", r"\bthrow\s+new\s+\w+Error", r"instanceof\s+\w+"],
    },
    "java": {
        "keywords": ["public class", "System.out.println", "import java.", "extends ", "implements ", "@Override", "void "],
        "comment_re": r"//[^\n]*|/\*[\s\S]*?\*/",
        "docstring_re": r"/\*\*[\s\S]*?\*/",
        "error_re": r"\btry\s*\{[\s\S]*?\}\s*catch\s*\(",
        "func_re": r"(?:public|private|protected|static)\s+\w[\w<>]*\s+\w+\s*\(",
        "edge_patterns": [
            r"== null", r"!= null", r"Objects\.requireNonNull", r"IllegalArgumentException",
            r"NullPointerException", r"instanceof\s+\w+",
        ],
    },
    "cpp": {
        "keywords": ["#include ", "std::", "cout <<", "cin >>", "int main(", "::", "namespace "],
        "comment_re": r"//[^\n]*|/\*[\s\S]*?\*/",
        "docstring_re": r"/\*\*[\s\S]*?\*/",
        "error_re": r"\btry\s*\{[\s\S]*?\}\s*catch\s*\(",
        "func_re": r"\w+\s+\w+\s*\([^)]*\)\s*(?:const\s*)?\{",
        "edge_patterns": [r"== nullptr", r"!= nullptr", r"== NULL", r"\bthrow\s+\w+\(", r"assert\("],
    },
    "c": {
        "keywords": ["#include ", "printf(", "scanf(", "malloc(", "free(", "NULL", "typedef "],
        "comment_re": r"//[^\n]*|/\*[\s\S]*?\*/",
        "docstring_re": r"/\*[\s\S]*?\*/",
        "error_re": r"if\s*\([^)]*(?:error|err|errno|failed|fail|NULL)[^)]*\)",
        "func_re": r"\w+\s+\w+\s*\([^)]*\)\s*\{",
        "edge_patterns": [r"== NULL", r"!= NULL", r"\berrno\b", r"if\s*\(!"],
    },
    "csharp": {
        "keywords": ["using System", "namespace ", "Console.WriteLine", "public class", "async Task", ".NET"],
        "comment_re": r"//[^\n]*|/\*[\s\S]*?\*/",
        "docstring_re": r"///[^\n]*",
        "error_re": r"\btry\s*\{[\s\S]*?\}\s*catch\s*\(",
        "func_re": r"(?:public|private|protected|static)\s+\w[\w<>]*\s+\w+\s*\(",
        "edge_patterns": [r"== null", r"!= null", r"ArgumentNullException", r"ArgumentException", r"throw\s+new\s+\w+Exception"],
    },
    "php": {
        "keywords": ["<?php", "echo ", "$_", "->", "array(", "function ", "namespace "],
        "comment_re": r"//[^\n]*|#[^\n]*|/\*[\s\S]*?\*/",
        "docstring_re": r"/\*\*[\s\S]*?\*/",
        "error_re": r"\btry\s*\{[\s\S]*?\}\s*catch\s*\(",
        "func_re": r"function\s+\w+\s*\(",
        "edge_patterns": [r"=== null", r"is_null\(", r"isset\(", r"throw\s+new\s+\w+Exception"],
    },
    "go": {
        "keywords": ["package main", "func ", "import (", "fmt.Println", ":=", "goroutine", "chan "],
        "comment_re": r"//[^\n]*|/\*[\s\S]*?\*/",
        "docstring_re": r"//[^\n]*",
        "error_re": r"if\s+err\s*!=\s*nil",
        "func_re": r"func\s+\w+\s*\(",
        "edge_patterns": [r"!= nil", r"== nil", r"if\s+err\s*!=\s*nil", r"errors\.New\(", r"fmt\.Errorf\("],
    },
    "ruby": {
        "keywords": ["def ", "puts ", "require ", " end", "do |", "attr_accessor", "class "],
        "comment_re": r"#[^\n]*",
        "docstring_re": r"=begin[\s\S]*?=end",
        "error_re": r"\bbegin\b[\s\S]*?\brescue\b",
        "func_re": r"^\s*def\s+\w+",
        "edge_patterns": [r"\.nil\?", r"raise\s+\w+Error", r"rescue\s+\w+Error"],
    },
    "kotlin": {
        "keywords": ["fun ", "val ", "var ", "println(", "data class", "companion object", "suspend "],
        "comment_re": r"//[^\n]*|/\*[\s\S]*?\*/",
        "docstring_re": r"/\*\*[\s\S]*?\*/",
        "error_re": r"\btry\s*\{[\s\S]*?\}\s*catch\s*\(",
        "func_re": r"fun\s+\w+\s*\(",
        "edge_patterns": [r"== null", r"!= null", r"\?\.", r"?: throw", r"require\(", r"check\("],
    },
    "swift": {
        "keywords": ["func ", "let ", "var ", "print(", "guard let", "struct ", "protocol "],
        "comment_re": r"//[^\n]*|/\*[\s\S]*?\*/",
        "docstring_re": r"///[^\n]*",
        "error_re": r"\bdo\s*\{[\s\S]*?\}\s*catch\b",
        "func_re": r"func\s+\w+\s*\(",
        "edge_patterns": [r"guard\s+let", r"if\s+let", r"guard\s+\w+\s*!=\s*nil", r"throw\s+\w+Error"],
    },
    "sql": {
        "keywords": ["SELECT ", "FROM ", "WHERE ", "INSERT INTO", "CREATE TABLE", "ALTER TABLE", "JOIN "],
        "comment_re": r"--[^\n]*|/\*[\s\S]*?\*/",
        "docstring_re": r"/\*[\s\S]*?\*/",
        "error_re": r"BEGIN\s+TRY[\s\S]*?END\s+CATCH",
        "func_re": r"CREATE\s+(?:FUNCTION|PROCEDURE)\s+\w+",
        "edge_patterns": [r"IS NULL", r"IS NOT NULL", r"ISNULL\(", r"COALESCE\(", r"CASE\s+WHEN"],
    },
}

EXT_TO_LANG: dict[str, str] = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".java": "java", ".cpp": "c++", ".c": "c", ".cs": "c#",
    ".php": "php", ".go": "go", ".rb": "ruby", ".kt": "kotlin",
    ".swift": "swift", ".sql": "sql",
}

# AI-generic comment clichés
GENERIC_COMMENT_RE = re.compile(
    r"(?:this\s+(?:function|method|class|module)\s+(?:is|does|handles|performs|implements))|"
    r"(?:initialize[sd]?\s+(?:the|a|an))|"
    r"(?:returns?\s+the\s+\w+)|"
    r"(?:creates?\s+(?:a|an)\s+\w+)|"
    r"(?:(?:main|core|helper|utility)\s+(?:function|method|class|logic))|"
    r"(?:example\s+usage)|"
    r"(?:implementation\s+of)|"
    r"(?:main\s+entry\s+point)|"
    r"(?:calculates?\s+(?:the|a)\s+\w+)",
    re.IGNORECASE,
)

# Human-like debug artifacts — their ABSENCE is a strong AI signal
DEBUG_PRINT_RE = re.compile(
    r'\bprint\s*\(\s*["\'](?:debug|test|temp|here|got|val|check|result|output|x|y)',
    re.IGNORECASE,
)
COMMENTED_CODE_RE = re.compile(
    r'^\s*(?:#|//)\s*(?:def |class |if |for |while |import |return |print |var |let |const )',
    re.MULTILINE,
)
TODO_RE = re.compile(r'(?:#|//)\s*(?:TODO|FIXME|HACK|XXX)\b', re.IGNORECASE)
TEMP_VAR_RE = re.compile(r'\b(?:temp|tmp|foo|bar|baz|x2|n2|val2|result2|myvar|my_var|dummy)\b', re.IGNORECASE)
BARE_EXCEPT_RE = re.compile(r'except\s*:', re.MULTILINE)


@dataclass
class CodeSignals:
    comment_density: float
    generic_comment_ratio: float
    docstring_coverage: float
    naming_consistency: float
    error_handling_density: float
    avg_identifier_length: float
    func_length_uniformity: float
    # New signals (v2)
    cleanness_score: float       # 0-1: 1 = no debug artifacts = AI-like
    edge_case_density: float     # 0-1: thorough validation = AI-like
    line_uniformity: float       # 0-1: uniform line lengths = AI-like


@dataclass
class CodeAnalysisResult:
    ai_code_probability: float
    human_code_probability: float
    confidence: str
    detected_language: str
    code_blocks_found: int
    signals: CodeSignals
    explanation: str
    lines_analyzed: int


# ── Language detection ────────────────────────────────────────────────────────

def detect_language(code: str, filename: str = "") -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in EXT_TO_LANG:
        return EXT_TO_LANG[ext]
    scores: dict[str, int] = {}
    for lang, sig in LANG_SIGNATURES.items():
        score = sum(1 for kw in sig["keywords"] if kw.lower() in code.lower())
        if score:
            scores[lang] = score
    return max(scores, key=scores.get) if scores else "unknown"


# ── Code-line extraction from mixed documents ─────────────────────────────────

_CODE_LINE_RE = re.compile(
    r"(?:\b(?:def|class|import|from|return|elif|lambda|yield)\b"
    r"|\b(?:function|const|let|var|async|await)\b"
    r"|\b(?:public|private|protected|static|void|int|string|bool)\b"
    r"|\b(?:SELECT|FROM|WHERE|INSERT|CREATE|ALTER|JOIN)\b"
    r"|\b(?:func|package|goroutine)\b"
    r"|[{}\[\]();]|->|=>|::)",
    re.IGNORECASE,
)

def is_code_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) < 3:
        return False
    return len(_CODE_LINE_RE.findall(stripped)) >= 2

def extract_code_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks, current = [], []
    for line in lines:
        if is_code_line(line) or (current and line.strip() == ""):
            current.append(line)
        else:
            if len([l for l in current if l.strip()]) >= 4:
                blocks.append("\n".join(current).strip())
            current = []
    if len([l for l in current if l.strip()]) >= 4:
        blocks.append("\n".join(current).strip())
    return [b for b in blocks if b.strip()]


# ── Individual metric functions ───────────────────────────────────────────────

def _get_sig(language: str) -> dict:
    return LANG_SIGNATURES.get(language, LANG_SIGNATURES["python"])

def _count_comments(code: str, language: str) -> tuple[int, int]:
    sig = _get_sig(language)
    matches = re.findall(sig["comment_re"], code, re.MULTILINE)
    generic = sum(1 for m in matches if GENERIC_COMMENT_RE.search(m))
    return len(matches), generic

def _count_functions(code: str, language: str) -> list:
    return re.findall(_get_sig(language)["func_re"], code, re.MULTILINE)

def _count_docstrings(code: str, language: str) -> int:
    return len(re.findall(_get_sig(language)["docstring_re"], code, re.DOTALL))

def _count_error_blocks(code: str, language: str) -> int:
    return len(re.findall(_get_sig(language)["error_re"], code, re.DOTALL | re.IGNORECASE))

def _naming_consistency(code: str) -> float:
    identifiers = [i for i in re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b", code)
                   if len(i) > 2 and i.lower() not in {"the", "and", "for", "not", "are", "was", "its"}]
    if len(identifiers) < 5:
        return 0.5
    snake = sum(1 for i in identifiers if "_" in i and i == i.lower())
    camel = sum(1 for i in identifiers if re.match(r"[a-z][a-zA-Z0-9]*[A-Z]", i))
    pascal = sum(1 for i in identifiers if re.match(r"^[A-Z][a-zA-Z0-9]+$", i))
    return max(snake, camel, pascal) / len(identifiers)

def _avg_identifier_length(code: str) -> float:
    ids = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b", code)
    return float(np.mean([len(i) for i in ids])) if ids else 5.0

def _function_length_cv(code: str, language: str) -> float:
    sig = _get_sig(language)
    positions = [m.start() for m in re.finditer(sig["func_re"], code, re.MULTILINE)]
    if len(positions) < 2:
        return 0.5
    lengths = [len(code[positions[i]:positions[i+1]].splitlines()) for i in range(len(positions)-1)]
    mean = float(np.mean(lengths))
    return float(np.std(lengths) / mean) if mean > 0 else 0.5

# ── NEW v2 signals ────────────────────────────────────────────────────────────

def _cleanness_score(code: str) -> float:
    """
    AI-cleanness: absence of human debug artifacts.
    0.0 = many human artifacts (likely human)
    1.0 = perfectly clean (AI-like)
    """
    artifacts = [
        bool(DEBUG_PRINT_RE.search(code)),
        bool(COMMENTED_CODE_RE.search(code)),
        bool(TODO_RE.search(code)),
        bool(TEMP_VAR_RE.search(code)),
        bool(BARE_EXCEPT_RE.search(code)),
        # Orphaned variable: single-letter non-loop vars
        bool(re.search(r"\b(?:a|b|c|d|e|g|h|k|m|n|p|q|s|t|u|v|w|x|y|z)\s*=\s*[^=]", code)),
    ]
    count = sum(artifacts)
    # 0 artifacts = 1.0 (AI-clean), each artifact reduces score
    return max(0.0, 1.0 - count * 0.2)

def _edge_case_density(code: str, language: str) -> float:
    """
    AI tends to handle ALL edge cases systematically.
    """
    patterns = _get_sig(language).get("edge_patterns", [])
    if not patterns:
        return 0.5
    count = sum(len(re.findall(p, code, re.IGNORECASE)) for p in patterns)
    funcs = max(len(_count_functions(code, language)), 1)
    # Normalize: 2+ checks per function → very thorough → AI-like
    return min(count / (funcs * 2.0), 1.0)

def _line_uniformity(code: str) -> float:
    """
    AI code tends to have more uniform line lengths (lower CV).
    """
    lengths = [len(l) for l in code.splitlines()
               if l.strip() and not l.strip().startswith(("#", "//", "/*", "*"))]
    if len(lengths) < 6:
        return 0.5
    mean = float(np.mean(lengths))
    std = float(np.std(lengths))
    cv = std / max(mean, 1.0)
    # CV < 0.6 → very uniform → AI-like (score near 1.0)
    # CV > 1.5 → very varied → human-like (score near 0.0)
    return float(max(0.0, min(1.0, 1.0 - (cv - 0.3) / 1.2)))


# ── Combined scoring ──────────────────────────────────────────────────────────

def compute_signals(code: str, language: str) -> CodeSignals:
    code_lines = [l for l in code.splitlines() if l.strip() and not l.strip().startswith(("#", "//", "*", "/*"))]
    total_lines = max(len(code_lines), 1)
    total_comments, generic = _count_comments(code, language)
    funcs = _count_functions(code, language)
    docstrings = _count_docstrings(code, language)
    errors = _count_error_blocks(code, language)

    return CodeSignals(
        comment_density=round(total_comments / total_lines, 3),
        generic_comment_ratio=round(generic / max(total_comments, 1), 3),
        docstring_coverage=round(min(docstrings / max(len(funcs), 1), 1.0), 3),
        naming_consistency=round(_naming_consistency(code), 3),
        error_handling_density=round(min(errors / max(len(funcs), 1), 1.0), 3),
        avg_identifier_length=round(_avg_identifier_length(code), 2),
        func_length_uniformity=round(max(0.0, 1.0 - _function_length_cv(code, language)), 3),
        cleanness_score=round(_cleanness_score(code), 3),
        edge_case_density=round(_edge_case_density(code, language), 3),
        line_uniformity=round(_line_uniformity(code), 3),
    )


def signals_to_ai_score(s: CodeSignals) -> float:
    """
    Weighted combination of all signals → 0-100 AI likelihood.

    v2 weights emphasise cleanness + edge cases + line uniformity
    which are far more reliable signals for modern AI (GPT-4/Gemini).
    """
    raw = (
        0.25 * s.cleanness_score            # STRONGEST: no debug artifacts
        + 0.18 * s.edge_case_density         # thorough edge handling
        + 0.15 * s.line_uniformity           # consistent line lengths
        + 0.12 * s.naming_consistency        # naming convention adherence
        + 0.10 * s.func_length_uniformity    # function length uniformity
        + 0.10 * s.generic_comment_ratio     # cliché AI comments
        + 0.10 * s.docstring_coverage        # full docstring on everything
    )
    return round(max(0.0, min(100.0, raw * 100)), 1)


def _build_explanation(score: float, s: CodeSignals, language: str) -> str:
    reasons: list[str] = []

    # Cleanness (v2 primary signal)
    if s.cleanness_score >= 0.8:
        reasons.append("no debug artifacts found (no TODO, no commented-out code, no temp variables)")
    elif s.cleanness_score <= 0.4:
        reasons.append("contains human debug artifacts (TODO, commented-out code, or temp variable names)")

    # Edge cases
    if s.edge_case_density >= 0.5:
        reasons.append("systematic, comprehensive edge-case handling (null checks, type validation)")
    elif s.edge_case_density <= 0.1:
        reasons.append("sparse or no edge-case validation (more typical of quick human code)")

    # Line uniformity
    if s.line_uniformity >= 0.7:
        reasons.append("very uniform line-length distribution")
    elif s.line_uniformity <= 0.3:
        reasons.append("varied, unpredictable line lengths (human characteristic)")

    # Naming
    if s.naming_consistency >= 0.85:
        reasons.append("perfectly consistent naming convention throughout")
    elif s.naming_consistency <= 0.4:
        reasons.append("mixed naming conventions (human characteristic)")

    # Comments / docstrings
    if s.generic_comment_ratio > 0.4:
        reasons.append('generic, template-like comments (e.g. "This function returns…")')
    if s.docstring_coverage > 0.7:
        reasons.append("full docstring coverage on every function")
    if s.docstring_coverage < 0.1 and s.cleanness_score > 0.7:
        reasons.append("minimal comments but still perfectly clean code (modern AI pattern)")

    if not reasons:
        reasons.append("balanced mix of AI and human coding patterns")

    verdict = ("likely AI-generated" if score >= 60
               else "likely human-written" if score <= 40
               else "of uncertain origin")

    return (
        f"This {language} code appears {verdict}. "
        f"Key indicators: {'; '.join(reasons[:4])}. "
        f"This is a heuristic estimate based on code-style patterns (comments, naming, "
        f"edge-case handling, structure) — not a proven detection or a trained AI-code "
        f"classifier. Treat it as a signal for further review, not a verdict."
    )


# ── Main entry ────────────────────────────────────────────────────────────────

def analyze_code(code: str, filename: str = "", code_blocks: Optional[list[str]] = None) -> CodeAnalysisResult:
    language = detect_language(code, filename)
    blocks = code_blocks or [code]
    combined = "\n\n".join(blocks)
    signals = compute_signals(combined, language)
    score = signals_to_ai_score(signals)
    total_lines = len(combined.splitlines())
    confidence = "High" if total_lines >= 60 else "Medium" if total_lines >= 20 else "Low"
    return CodeAnalysisResult(
        ai_code_probability=score,
        human_code_probability=round(100.0 - score, 1),
        confidence=confidence,
        detected_language=language,
        code_blocks_found=len(blocks),
        signals=signals,
        explanation=_build_explanation(score, signals, language),
        lines_analyzed=total_lines,
    )
