"""
Group extraction Units into analyzable Chunks.

Large documents must not be judged on only their first few hundred words —
these functions split (or, more commonly, combine) page/slide Units into
chunks sized for the detectors: prose chunks stay comfortably under GPT-2's
1024-token context window, code chunks follow natural page/slide
boundaries. Each chunk keeps track of which original units it came from,
so results can be traced back to "page 3" / "slide 5" etc.

Units are only merged into the same chunk when they were ADJACENT in the
original document (index N followed by index N+1). The caller typically
passes in a filtered list (e.g. only the code-classified units), which can
skip index numbers where an intervening prose page/slide was filtered out
— that gap must break the chunk, otherwise two unrelated code sections
separated by a paragraph of prose (e.g. Python on page 2, prose on page 4,
Java on page 5) would get silently concatenated into one blob and lose
their separate per-page language/results tracking.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.file_pipeline import Unit

PROSE_TARGET_WORDS = 350   # safe margin under GPT-2's 1024-token context
CODE_MAX_CHARS = 4000


@dataclass
class Chunk:
    kind: Literal["prose", "code"]
    text: str
    unit_indices: list[int]

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def line_count(self) -> int:
        return len([l for l in self.text.splitlines() if l.strip()])


def _chunk_units(units: list[Unit], kind: str, size_limit: int, size_of) -> list[Chunk]:
    chunks: list[Chunk] = []
    buf_text: list[str] = []
    buf_indices: list[int] = []
    buf_size = 0
    prev_index: int | None = None

    def flush():
        nonlocal buf_text, buf_indices, buf_size
        if buf_text:
            chunks.append(Chunk(kind=kind, text="\n\n".join(buf_text), unit_indices=list(buf_indices)))
        buf_text, buf_indices, buf_size = [], [], 0

    for u in units:
        text = u.text.strip()
        if not text:
            continue
        not_adjacent = prev_index is not None and u.index != prev_index + 1
        too_big = buf_size and buf_size + size_of(text) > size_limit
        if not_adjacent or too_big:
            flush()
        buf_text.append(text)
        buf_indices.append(u.index)
        buf_size += size_of(text)
        prev_index = u.index

    flush()
    return chunks


def chunk_prose(units: list[Unit], target_words: int = PROSE_TARGET_WORDS) -> list[Chunk]:
    return _chunk_units(units, "prose", target_words, lambda t: len(t.split()))


def chunk_code(units: list[Unit], max_chars: int = CODE_MAX_CHARS) -> list[Chunk]:
    return _chunk_units(units, "code", max_chars, len)
