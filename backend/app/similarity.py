"""
Text similarity / potential-overlap analysis (Feature 1).

Architecture (per spec): extracted text -> chunks -> embeddings -> cosine
similarity -> matching passages -> similarity report. Deliberately does
NOT ask an LLM "is this plagiarism" — that question is answered by
comparing embeddings, a much more grounded signal.

The comparison corpus is this app's own analysis history (app/db.py's
reference_chunks table) — every previously analyzed text document — plus,
only when the caller opts in, a few external pages fetched for that one
request (app/web_sources.py: Wikipedia articles, arXiv abstracts). There is
no bulk external plagiarism index, and rule 14 ("do not fabricate plagiarism
sources") means we don't pretend there is one. A "source" is always a real
page or prior submission, reported with its provenance; an empty corpus is
reported as such, not papered over with a fake score.

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

# ── Corroboration signals ────────────────────────────────────────────────
# Embedding cosine alone cannot separate "independently written on the same
# topic" from "copied and thoroughly reworded" — both land at 80-82% cosine
# on this project's own eval fixtures (see samples/eval/14 vs 03). Neither a
# larger model (all-mpnet-base-v2) nor a differently-trained one
# (BAAI/bge-small-en-v1.5) fixed this; bge-small made it much worse by
# inflating cosine for ALL text, including genuinely unrelated documents, to
# 60-82% (see backend/test_embedding_benchmark.py). The fix is a second,
# independent signal, not a different encoder.
#
# Word-overlap (Jaccard) and n-gram containment measure something cosine
# does not: whether the SAME WORDS appear in the same short sequences. A
# copied-and-reworded passage retains more shared vocabulary and multi-word
# fragments than independently written text on the same subject, even when
# both score similarly on pure semantic similarity.
#
# Floors below are set from measured data on samples/eval/ (see
# backend/test_similarity_eval.py for the exact numbers this encodes):
#   verbatim / light edits          : word_jaccard 97-100%, 3gram 94-100%
#   realistic reworded copy         : word_jaccard 32%,     3gram 11%
#   genuinely-copied patchwork spans: word_jaccard 19-67%,  3gram 18-84%
#   same-topic, independently written: word_jaccard 15%,    3gram  1%
#   unrelated / academic / classics : word_jaccard  6-12%,  3gram  0%
# 0.25 / 0.15 sit in the gap between the worst genuine copy and the best
# false-positive candidate, with several points of margin on both signals.
#
# KNOWN LIMIT, disclosed rather than hidden: an adversarially thorough
# rewrite that replaces every content word (samples/eval/03) shares 0%
# trigrams with its source and does not clear either floor. It still shows
# up as a HIGH-cosine, UNVERIFIED match — visible, correctly hedged, not
# silently dropped — but it is not "strongly flagged" the way a corroborated
# match is. No signal available to this pipeline catches a rewrite that
# thorough; that is reported as a limitation, not solved.
VERIFIED_WORD_JACCARD_FLOOR = 0.25
VERIFIED_NGRAM_FLOOR = 0.15
NGRAM_N = 3

_WORD_RE = re.compile(r"[a-z0-9']+")


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _word_jaccard(a_tokens: list[str], b_tokens: list[str]) -> float:
    sa, sb = set(a_tokens), set(b_tokens)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _ngram_containment(query_tokens: list[str], source_tokens: list[str], n: int = NGRAM_N) -> float:
    """Fraction of the QUERY's n-grams that also appear in the source.

    Containment rather than Jaccard: the source window and query window can
    differ in length, and what matters is how much of the query's exact
    phrasing was lifted, not how much of a possibly-longer source it covers.
    """
    if len(query_tokens) < n:
        return 0.0
    q_ngrams = {tuple(query_tokens[i : i + n]) for i in range(len(query_tokens) - n + 1)}
    if not q_ngrams:
        return 0.0
    if len(source_tokens) < n:
        return 0.0
    s_ngrams = {tuple(source_tokens[i : i + n]) for i in range(len(source_tokens) - n + 1)}
    return len(q_ngrams & s_ngrams) / len(q_ngrams)

# Kept for backwards compatibility with existing callers/tests.
SIMILARITY_TARGET_WORDS = 120


@dataclass
class SimilarityMatch:
    query_excerpt: str
    matched_text: str
    source_file: str  # the corpus tag; for display prefer `source_name`
    source_history_id: int | None  # None for an external source (no history row)
    score: float  # 0-100, raw embedding cosine
    # Corroborating lexical evidence for this specific pair (0-100 each).
    word_overlap: float = 0.0
    ngram_overlap: float = 0.0
    # True when word_overlap or ngram_overlap clears its floor — i.e. this
    # is not semantic similarity alone, the same words appear in the same
    # short sequences. Strongly-worded plagiarism claims should require
    # this; a high `score` without it is a weaker, hedged signal.
    verified: bool = False
    # Provenance — where the matched passage really came from. Always a real,
    # retrievable source: an earlier submission on file ("submission", with
    # the date it was analysed) or an external page ("wikipedia" / "arxiv",
    # with its URL). Never invented.
    source_name: str = ""
    source_created_at: str | None = None
    source_kind: str = "submission"
    source_url: str | None = None


@dataclass
class SimilarityResult:
    overall_similarity: float
    matches: list[SimilarityMatch] = field(default_factory=list)
    chunks_compared: int = 0
    corpus_size: int = 0
    note: str = ""
    # Strongest single-passage match, 0-100 — raw embedding cosine, kept for
    # visibility even when unverified (see `top_match_verified`). This is
    # NOT the same as a plagiarism claim: same-topic writing can also score
    # high here. Check top_match_verified before treating it as strong.
    top_match: float = 0.0
    # Whether top_match is backed by lexical corroboration (see
    # SimilarityMatch.verified). False means "closest semantic match found,
    # but no shared phrasing" — report it hedged, not as a strong finding.
    top_match_verified: bool = False
    # Share of this document's passages that are VERIFIED copies, 0-100.
    # Answers "how much of it is corroborated as copied" — semantic-only
    # matches (topic overlap without shared phrasing) do NOT count here,
    # which is what keeps this number low for independently written text
    # on the same subject.
    matched_portion: float = 0.0
    # Share of passages that cleared the cosine floor but were NOT verified
    # — i.e. semantically close without shared phrasing. A same-topic
    # document typically shows up here instead of in matched_portion.
    possible_portion: float = 0.0
    # What the optional external-source check did (see app/web_sources.py):
    # {"status", "note", "sources": [{"kind", "title", "url"}]}. None when the
    # caller did not ask for it.
    external: dict | None = None


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


def analyze_similarity(
    text: str,
    exclude_file_name: str | None = None,
    extra_corpus: list[dict] | None = None,
) -> SimilarityResult:
    """Compare `text` against the stored corpus.

    `exclude_file_name` drops prior submissions with the same filename from
    the comparison. Without it, re-analysing a document reports it as a
    100% match against its own earlier upload, which reads as plagiarism
    when it is simply the same file submitted twice.

    `extra_corpus` adds passages that are not in the database — the external
    pages fetched by app/web_sources.py for this one request. Each is a dict
    shaped like a stored chunk (chunk_text, embedding, file_name, ...) with a
    `kind` and `url`. They are compared exactly like stored passages, under
    the same semantic-plus-lexical verification, and are never persisted.
    """
    query_chunks = _chunk_for_similarity(text)
    if not query_chunks:
        return SimilarityResult(overall_similarity=0.0, note="No text available to compare.")

    corpus = db.get_all_reference_chunks()

    if exclude_file_name:
        corpus = [c for c in corpus if c["file_name"] != exclude_file_name]

    stored_count = len(corpus)  # "passages on file" means stored ones, not the request's external pages
    if extra_corpus:
        corpus = corpus + list(extra_corpus)

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
    query_tokens = [_tokens(q) for q in query_chunks]
    corpus_tokens = [_tokens(c["chunk_text"]) for c in corpus]

    best_per_chunk: list[float] = []
    verified_flags: list[bool] = []
    matches: list[SimilarityMatch] = []
    for qi, qchunk in enumerate(query_chunks):
        best_j = int(np.argmax(sims[qi]))
        # Cosine is [-1, 1]; a passage with no relation to anything on file
        # can score slightly negative. Clamping at 0 keeps the reported
        # figure a real percentage (history previously stored -0.4%).
        best_score = max(0.0, float(sims[qi, best_j]))
        best_per_chunk.append(best_score)

        if best_score < MATCH_THRESHOLD:
            verified_flags.append(False)
            continue

        # Lexical corroboration — only computed for candidates that already
        # cleared the semantic floor, so this never runs on obviously
        # unrelated pairs. See the module-level comment for where the
        # floors below come from.
        q_tok, s_tok = query_tokens[qi], corpus_tokens[best_j]
        jaccard = _word_jaccard(q_tok, s_tok)
        ngram = _ngram_containment(q_tok, s_tok, NGRAM_N)
        verified = jaccard >= VERIFIED_WORD_JACCARD_FLOOR or ngram >= VERIFIED_NGRAM_FLOOR
        verified_flags.append(verified)

        c = corpus[best_j]
        matches.append(
            SimilarityMatch(
                query_excerpt=qchunk,
                matched_text=c["chunk_text"],
                source_file=c["file_name"],
                source_history_id=c.get("history_id"),
                score=round(best_score * 100, 1),
                word_overlap=round(jaccard * 100, 1),
                ngram_overlap=round(ngram * 100, 1),
                verified=verified,
                source_name=c.get("display_name") or c["file_name"],
                source_created_at=c.get("submitted_at"),
                source_kind=c.get("kind", "submission"),
                source_url=c.get("url"),
            )
        )

    # Verified matches first (the actionable ones), then semantic-only,
    # each group ordered by raw score.
    matches.sort(key=lambda m: (not m.verified, -m.score))
    overall = round(100 * float(np.mean(best_per_chunk)), 1) if best_per_chunk else 0.0

    # Headline figures that stay meaningful as the archive grows.
    top = round(100 * max(best_per_chunk), 1) if best_per_chunk else 0.0
    top_idx = int(np.argmax(best_per_chunk)) if best_per_chunk else -1
    top_verified = bool(verified_flags[top_idx]) if top_idx >= 0 else False

    n_verified = sum(1 for v in verified_flags if v)
    n_possible = sum(
        1 for s, v in zip(best_per_chunk, verified_flags) if s >= MATCH_THRESHOLD and not v
    )
    total = len(best_per_chunk) or 1
    verified_portion = round(100 * n_verified / total, 1)
    possible_portion = round(100 * n_possible / total, 1)

    if any(m.verified for m in matches):
        note = ""
    elif matches:
        # High semantic similarity exists, but nothing corroborates it as
        # copied phrasing rather than a shared subject.
        note = (
            "High topical similarity found, but no matching phrasing was verified — "
            "this can indicate a shared subject rather than copied content."
        )
    else:
        note = "No individual passages crossed the match threshold."

    return SimilarityResult(
        overall_similarity=overall,
        matches=matches[:MAX_MATCHES],
        chunks_compared=len(query_chunks),
        corpus_size=stored_count,
        note=note,
        top_match=top,
        top_match_verified=top_verified,
        matched_portion=verified_portion,
        possible_portion=possible_portion,
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
