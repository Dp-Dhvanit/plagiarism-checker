"""
Text similarity / potential-overlap analysis (Feature 1).

Architecture (per spec): extracted text -> chunks -> embeddings -> cosine
similarity -> matching passages -> similarity report. Deliberately does
NOT ask an LLM "is this plagiarism" — that question is answered by
comparing embeddings, a much more grounded signal.

The comparison corpus is exactly this app's own analysis history
(app/db.py's reference_chunks table) — every previously analyzed text
document. There is no external plagiarism index wired into this project,
and rule 14 ("do not fabricate plagiarism sources") means we don't
pretend there is one. A "source" is always a real prior submission on
file; an empty corpus is reported as such, not papered over with a fake
score.

Similarity is reported as a text-overlap signal, not a plagiarism
verdict — "similarity" and "plagiarism" are intentionally kept separate
in both field names and UI copy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from app import db
from app.embeddings import cosine_similarity_matrix, embed_texts

# ── Passage windowing ────────────────────────────────────────────────────
# Similarity is measured over small overlapping passages, NOT over whole
# documents. The previous approach handed the entire text to chunk_prose()
# as a single Unit; because _chunk_units() only ever splits *between* units,
# the target size was never enforced and a whole document collapsed into one
# embedding. A short stolen paragraph was then averaged against everything
# around it and fell below the reporting threshold — measured dilution:
#   100% of a passage stolen -> cosine 100%  (reported)
#    45% stolen              -> cosine  57%  (missed at the old 0.60 floor)
#    29% stolen              -> cosine  52%  (missed)
# Windowing restores localisation so patchwork copying is actually found.
SIMILARITY_WINDOW_WORDS = 60   # size of one comparable passage
SIMILARITY_QUERY_STRIDE = 30   # 50% overlap when querying, so a stolen
                               # passage is never split across a boundary
SIMILARITY_STORE_STRIDE = 60   # no overlap when storing, to keep the corpus small

# Cosine floor for surfacing a passage as a reported match. Lowered from
# 0.60: genuinely unrelated passages measure between -6% and +9% cosine, so
# 0.45 keeps an enormous safety margin while catching patchwork copying that
# 0.60 silently dropped.
MATCH_THRESHOLD = 0.45
MAX_MATCHES = 8

# Kept for backwards compatibility with existing callers/tests.
SIMILARITY_TARGET_WORDS = 120


@dataclass
class SimilarityMatch:
    query_excerpt: str
    matched_text: str
    source_file: str
    source_history_id: int
    score: float  # 0-100


@dataclass
class SimilarityResult:
    overall_similarity: float
    matches: list[SimilarityMatch] = field(default_factory=list)
    chunks_compared: int = 0
    corpus_size: int = 0
    note: str = ""
    # Strongest single-passage match, 0-100. This is the honest headline
    # figure: unlike `overall_similarity` (a mean over passages) it does not
    # drift as the archive grows, and it is not diluted by original text
    # surrounding a copied passage.
    top_match: float = 0.0
    # Share of this document's passages that crossed MATCH_THRESHOLD, 0-100.
    # Answers "how much of it is copied", which the mean cannot.
    matched_portion: float = 0.0


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _windows(text: str, window_words: int, stride_words: int) -> list[str]:
    """Split text into overlapping, sentence-aligned passages.

    Windows break on sentence boundaries so a reported match reads as real
    prose rather than a fragment. A sentence longer than the window becomes
    its own passage rather than being cut mid-thought.
    """
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]
    if not sentences:
        return []

    lengths = [len(s.split()) for s in sentences]
    out: list[str] = []
    start = 0

    while start < len(sentences):
        total = 0
        end = start
        while end < len(sentences) and total < window_words:
            total += lengths[end]
            end += 1
        out.append(" ".join(sentences[start:end]))
        if end >= len(sentences):
            break
        # Step forward by roughly `stride_words`, always at least one sentence.
        advanced = 0
        step = start
        while step < end and advanced < stride_words:
            advanced += lengths[step]
            step += 1
        start = max(step, start + 1)

    # Drop duplicates that overlap can produce at the tail.
    seen: set[str] = set()
    unique = []
    for w in out:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


def _chunk_for_similarity(text: str, stride: int = SIMILARITY_QUERY_STRIDE) -> list[str]:
    return _windows(text, SIMILARITY_WINDOW_WORDS, stride)


def analyze_similarity(text: str, exclude_file_name: str | None = None) -> SimilarityResult:
    """Compare `text` against the stored corpus.

    `exclude_file_name` drops prior submissions with the same filename from
    the comparison. Without it, re-analysing a document reports it as a
    100% match against its own earlier upload, which reads as plagiarism
    when it is simply the same file submitted twice.
    """
    query_chunks = _chunk_for_similarity(text)
    if not query_chunks:
        return SimilarityResult(overall_similarity=0.0, note="No text available to compare.")

    corpus = db.get_all_reference_chunks()

    if exclude_file_name:
        corpus = [c for c in corpus if c["file_name"] != exclude_file_name]

    if not corpus:
        return SimilarityResult(
            overall_similarity=0.0,
            chunks_compared=len(query_chunks),
            corpus_size=0,
            note="No comparable prior submissions on file yet — similarity results will "
                 "populate as more documents are analyzed.",
        )

    query_vecs = embed_texts(query_chunks)
    corpus_vecs = np.stack([c["embedding"] for c in corpus])
    sims = cosine_similarity_matrix(query_vecs, corpus_vecs)  # (n_query, n_corpus)

    best_per_chunk: list[float] = []
    matches: list[SimilarityMatch] = []
    for qi, qchunk in enumerate(query_chunks):
        best_j = int(np.argmax(sims[qi]))
        # Cosine is [-1, 1]; a passage with no relation to anything on file
        # can score slightly negative. Clamping at 0 keeps the reported
        # figure a real percentage (history previously stored -0.4%).
        best_score = max(0.0, float(sims[qi, best_j]))
        best_per_chunk.append(best_score)
        if best_score >= MATCH_THRESHOLD:
            c = corpus[best_j]
            matches.append(
                SimilarityMatch(
                    query_excerpt=qchunk,
                    matched_text=c["chunk_text"],
                    source_file=c["file_name"],
                    source_history_id=c["history_id"],
                    score=round(best_score * 100, 1),
                )
            )

    matches.sort(key=lambda m: m.score, reverse=True)
    overall = round(100 * float(np.mean(best_per_chunk)), 1) if best_per_chunk else 0.0

    # Headline figures that stay meaningful as the archive grows.
    top = round(100 * max(best_per_chunk), 1) if best_per_chunk else 0.0
    n_flagged = sum(1 for s in best_per_chunk if s >= MATCH_THRESHOLD)
    portion = round(100 * n_flagged / len(best_per_chunk), 1) if best_per_chunk else 0.0

    return SimilarityResult(
        overall_similarity=overall,
        matches=matches[:MAX_MATCHES],
        chunks_compared=len(query_chunks),
        corpus_size=len(corpus),
        note="" if matches else "No individual passages crossed the match threshold.",
        top_match=top,
        matched_portion=portion,
    )


def store_reference_chunks(history_id: int, file_name: str, text: str) -> None:
    """Add this document's chunks to the comparison corpus for FUTURE analyses.

    Must be called only after analyze_similarity() has already compared
    against the existing corpus — otherwise a document would trivially
    match itself.

    Stored windows do NOT overlap: overlap helps a query avoid splitting a
    copied passage, but in the corpus it would only duplicate embeddings.
    """
    chunks = _chunk_for_similarity(text, stride=SIMILARITY_STORE_STRIDE)
    if not chunks:
        return
    vectors = embed_texts(chunks)
    db.insert_reference_chunks(history_id, file_name, chunks, vectors)
