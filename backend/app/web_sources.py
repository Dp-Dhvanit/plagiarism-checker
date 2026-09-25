"""
Optional external-source check: does this text closely match a Wikipedia
article or an arXiv abstract?

Without this, similarity can only compare against documents previously
analysed in this app, so a fresh install finds nothing. Here a few distinctive
sentences are searched on Wikipedia and arXiv, the pages found are fetched, and
their passages join the comparison for that one request — under exactly the
same semantic-plus-lexical verification as stored submissions
(app/similarity.py). Nothing fetched is stored.

Ground rules, inherited from the similarity engine ("do not fabricate
plagiarism sources"):

* A source is a page that was actually fetched, and it is reported with its
  URL. Every page compared is listed, matched or not.
* "Nothing found" means "not found among the sources checked" — it is never
  presented as proof of originality, and a failed request is reported as a
  failure, not as a clean result.
* Only a few short excerpts of the user's text (as search queries) leave this
  server, and only when the caller opts in. Set EXTERNAL_SOURCES=off to make
  that impossible.

Coverage is what it is: this finds text that is copied or lightly edited from
Wikipedia and arXiv ABSTRACTS. It does not search the wider web, paywalled
papers, or other students' work outside this app.
"""
from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import re
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import quote

import numpy as np

from app.similarity import (
    _SENTENCE_SPLIT,
    _chunk_for_similarity,
    _ngram_containment,
    _tokens,
    _windows,
    _word_jaccard,
)

logger = logging.getLogger("app.web_sources")

# Wikimedia asks API clients to identify themselves with contact details, and
# throttles anonymous generic agents harder. Set EXTERNAL_SOURCES_CONTACT to an
# email or URL to be a good citizen (and to see fewer 429s).
USER_AGENT = "AI-Text-Detective/0.2 ({})".format(
    os.environ.get("EXTERNAL_SOURCES_CONTACT", "").strip() or "local plagiarism-check project"
)
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
ARXIV_API = "https://export.arxiv.org/api/query"

KINDS = ("wikipedia", "arxiv")
LABELS = {"wikipedia": "Wikipedia", "arxiv": "arXiv"}

MAX_QUERIES = 3            # distinctive sentences searched
MAX_PAGES = 4              # Wikipedia articles fetched
MAX_ARTICLE_CHARS = 40_000
MAX_RESPONSE_BYTES = 3_000_000
REQUEST_TIMEOUT = 8.0      # seconds, per request
BUDGET_SECONDS = 15.0      # for each phase (search, then fetch)
MIN_SENTENCE_WORDS = 9

# Passages of a fetched page are embedded only if they share some wording with
# the text being checked — a whole article is thousands of words, and
# embedding all of it would cost seconds to find nothing.
PREFILTER_WORD_JACCARD = 0.12
PREFILTER_NGRAM = 0.05
MAX_WINDOWS_PER_DOC = 25
WINDOW_WORDS = 60

HttpGet = Callable[[str, dict], str]


@dataclass
class ExternalDoc:
    kind: str    # "wikipedia" | "arxiv"
    title: str
    url: str
    text: str


@dataclass
class ExternalCheck:
    #: ok | no_candidates | unavailable | disabled | too_short
    status: str
    note: str
    sources: list[dict] = field(default_factory=list)   # pages actually compared
    corpus: list[dict] = field(default_factory=list)    # rows for analyze_similarity(extra_corpus=)

    def to_dict(self) -> dict:
        return {"status": self.status, "note": self.note, "sources": self.sources}


# ── configuration ───────────────────────────────────────────────────────────

def enabled_providers() -> list[str]:
    """Providers switched on for this server (EXTERNAL_SOURCES, default both).
    'off', 'none' or an empty value disables the feature entirely."""
    raw = os.environ.get("EXTERNAL_SOURCES", "wikipedia,arxiv").strip().lower()
    if raw in ("", "off", "none", "0", "false"):
        return []
    return [p for p in (x.strip() for x in raw.split(",")) if p in KINDS]


# ── HTTP ────────────────────────────────────────────────────────────────────

def _http_get(url: str, params: dict) -> str:
    """GET with a descriptive User-Agent (Wikimedia requires one), a timeout,
    and a cap on how much is read. Raises on any failure; callers count it."""
    import requests

    with requests.get(
        url, params=params, headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT, stream=True,
    ) as r:
        r.raise_for_status()
        body, size = [], 0
        for part in r.iter_content(65536):
            size += len(part)
            if size > MAX_RESPONSE_BYTES:
                break
            body.append(part)
        return b"".join(body).decode(r.encoding or "utf-8", errors="replace")


def _provider_of(url: str) -> str:
    return "arxiv" if "arxiv.org" in url else "wikipedia"


# Responses are cached briefly: re-checking the same text (a retry, a rewrite
# loop) should not hit Wikipedia again, and its API etiquette asks for as few
# requests as possible.
_CACHE_TTL = 600.0
_CACHE_MAX = 128
_cache: dict[tuple, tuple[float, str]] = {}
_cache_lock = threading.Lock()


def _cache_key(url: str, params: dict) -> tuple:
    return (url, tuple(sorted((k, str(v)) for k, v in params.items())))


def _cache_get(key: tuple) -> str | None:
    with _cache_lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < _CACHE_TTL:
            return hit[1]
        _cache.pop(key, None)
    return None


def _cache_put(key: tuple, value: str) -> None:
    with _cache_lock:
        if len(_cache) >= _CACHE_MAX:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (time.monotonic(), value)


class _Fetcher:
    """Wraps an HTTP function and keeps score PER PROVIDER, so the caller can
    tell 'nothing matched' from 'could not reach the source' — one provider
    answering with an empty result must not hide that the other one failed.

    A rate-limit or block (429/403/503) opens a circuit for that provider:
    further requests to it are skipped for the rest of this check instead of
    hammering a service that just asked us to slow down.
    """

    def __init__(self, get: HttpGet):
        self._get = get
        self.ok: dict[str, int] = {}
        self.failed: dict[str, int] = {}
        self.blocked: dict[str, str] = {}  # provider -> reason

    def __call__(self, url: str, params: dict) -> str | None:
        provider = _provider_of(url)
        if provider in self.blocked:
            self.failed[provider] = self.failed.get(provider, 0) + 1
            return None
        key = _cache_key(url, params)
        cached = _cache_get(key)
        if cached is not None:
            self.ok[provider] = self.ok.get(provider, 0) + 1
            return cached
        try:
            text = self._get(url, params)
        except Exception as exc:  # noqa: BLE001 - any network/HTTP failure means "not reachable"
            self.failed[provider] = self.failed.get(provider, 0) + 1
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (429, 403, 503):
                self.blocked[provider] = "rate limited"
            logger.warning("external source request failed (%s): %s: %s", provider, type(exc).__name__, exc)
            return None
        self.ok[provider] = self.ok.get(provider, 0) + 1
        _cache_put(key, text)
        return text

    def unreachable(self, providers: list[str]) -> dict[str, str]:
        """Providers that never answered at all, with why — as opposed to ones
        that answered and simply had nothing."""
        return {
            p: self.blocked.get(p, "could not be reached")
            for p in providers
            if self.failed.get(p, 0) > 0 and self.ok.get(p, 0) == 0
        }


# ── choosing what to search for ─────────────────────────────────────────────

def select_queries(text: str, n: int = MAX_QUERIES) -> list[str]:
    """The longest sentence from each of `n` equal slices of the text.

    Long sentences carry the most distinctive wording, and slicing spreads the
    searches across the document so a copied paragraph near the end is as
    likely to be searched as one at the start.
    """
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if len(s.split()) >= MIN_SENTENCE_WORDS]
    if not sentences:
        return []
    n = min(n, len(sentences))
    size = len(sentences) / n
    picks = []
    for i in range(n):
        chunk = sentences[int(i * size): int((i + 1) * size)] or sentences[i:i + 1]
        picks.append(max(chunk, key=lambda s: len(s.split())))
    # Trim: very long sentences make poor search queries.
    return [" ".join(s.split()[:24]) for s in picks]


def _phrase(sentence: str) -> str:
    """A ~10-word phrase from the middle of a sentence, safe to put in quotes.
    The middle avoids the openings people most often change."""
    words = re.sub(r'["\\]', " ", sentence).split()
    return " ".join(words[2:12] if len(words) >= 12 else words)


# ── providers ───────────────────────────────────────────────────────────────

def _wikipedia_titles(fetch: _Fetcher, query: str) -> list[str]:
    raw = fetch(WIKIPEDIA_API, {
        "action": "query", "list": "search", "srsearch": query, "srlimit": 3,
        "srnamespace": 0, "format": "json", "utf8": 1,
    })
    if raw is None:
        return []
    try:
        return [h["title"] for h in json.loads(raw).get("query", {}).get("search", []) if h.get("title")]
    except (ValueError, AttributeError, TypeError):
        return []


def _wikipedia_search(fetch: _Fetcher, sentence: str) -> list[str]:
    """Exact-phrase search first (precise for copied text); if that finds
    nothing, the sentence itself as a looser query (catches light rewording).

    A phrase hit is trusted (up to 3). The loose query is not: a live run showed
    it returns loosely related articles alongside the real one, so only its top
    hit is kept — otherwise the "compared against" list fills with noise and
    each extra page is another request to a service that rate-limits."""
    return _wikipedia_titles(fetch, f'"{_phrase(sentence)}"') or _wikipedia_titles(fetch, sentence)[:1]


def _wikipedia_article(fetch: _Fetcher, title: str) -> ExternalDoc | None:
    raw = fetch(WIKIPEDIA_API, {
        "action": "query", "prop": "extracts", "explaintext": 1, "exsectionformat": "plain",
        "redirects": 1, "titles": title, "format": "json", "utf8": 1,
    })
    if raw is None:
        return None
    try:
        pages = json.loads(raw).get("query", {}).get("pages", {})
    except (ValueError, AttributeError):
        return None
    for page in pages.values():
        extract = page.get("extract")
        real_title = page.get("title") or title
        if extract:
            return ExternalDoc(
                kind="wikipedia", title=real_title,
                url="https://en.wikipedia.org/wiki/" + quote(real_title.replace(" ", "_")),
                text=extract[:MAX_ARTICLE_CHARS],
            )
    return None


def _arxiv_docs(fetch: _Fetcher, sentence: str) -> list[ExternalDoc]:
    """arXiv abstracts matching a quoted phrase. Abstracts only — the API does
    not return full text."""
    raw = fetch(ARXIV_API, {"search_query": f'all:"{_phrase(sentence)}"', "max_results": 3})
    if raw is None:
        return []
    # The feed comes from a fixed host, but never hand entity declarations to
    # an XML parser (billion-laughs); a real Atom feed has none.
    if "<!DOCTYPE" in raw or "<!ENTITY" in raw:
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    docs = []
    for entry in root.findall("a:entry", ns):
        summary = " ".join((entry.findtext("a:summary", "", ns) or "").split())
        url = (entry.findtext("a:id", "", ns) or "").strip()
        title = " ".join((entry.findtext("a:title", "", ns) or "").split())
        if summary and url.startswith("http"):
            docs.append(ExternalDoc(kind="arxiv", title=title or url, url=url, text=summary))
    return docs


# ── turning fetched pages into comparable passages ──────────────────────────

def build_corpus(docs: list[ExternalDoc], text: str, embed: Callable | None = None) -> list[dict]:
    """Rows shaped like stored corpus chunks, for the passages of `docs` that
    share wording with `text`."""
    if embed is None:
        from app.embeddings import embed_texts as embed

    query_tokens = [_tokens(w) for w in _chunk_for_similarity(text)]
    rows: list[dict] = []
    for doc in docs:
        scored = []
        for w in _windows(doc.text, WINDOW_WORDS, WINDOW_WORDS):
            wt = _tokens(w)
            best_j = max((_word_jaccard(qt, wt) for qt in query_tokens), default=0.0)
            best_n = max((_ngram_containment(qt, wt) for qt in query_tokens), default=0.0)
            if best_j >= PREFILTER_WORD_JACCARD or best_n >= PREFILTER_NGRAM:
                scored.append((max(best_j, best_n), w))
        scored.sort(key=lambda t: t[0], reverse=True)
        keep = [w for _, w in scored[:MAX_WINDOWS_PER_DOC]]
        if not keep:
            continue
        vectors = embed(keep)
        label = f"{LABELS[doc.kind]}: {doc.title}"
        for i, (w, vec) in enumerate(zip(keep, vectors)):
            rows.append({
                "history_id": None, "file_name": label, "display_name": label,
                "submitted_at": None, "chunk_index": i, "chunk_text": w,
                "embedding": np.asarray(vec, dtype=np.float32),
                "kind": doc.kind, "url": doc.url,
            })
    return rows


# ── orchestration ───────────────────────────────────────────────────────────

def _wikipedia_chain(fetch: _Fetcher, queries: list[str], deadline: float) -> list[ExternalDoc]:
    """Search, then fetch — strictly one request at a time. Wikipedia's API
    etiquette asks for serial requests, and it answers a burst with 429."""
    titles: list[str] = []
    for q in queries:
        if time.monotonic() > deadline:
            break
        for t in _wikipedia_search(fetch, q):
            if t not in titles:
                titles.append(t)
        if len(titles) >= MAX_PAGES:
            break
    docs: list[ExternalDoc] = []
    for t in titles[:MAX_PAGES]:
        if time.monotonic() > deadline:
            break
        doc = _wikipedia_article(fetch, t)
        if doc is not None:
            docs.append(doc)
    return docs


def _describe_failures(down: dict[str, str]) -> str:
    return " and ".join(f"{LABELS[p]} {why}" for p, why in down.items())


def check_external(
    text: str,
    *,
    providers: list[str] | None = None,
    http_get: HttpGet | None = None,
    embed: Callable | None = None,
) -> ExternalCheck:
    """Search the enabled providers for pages matching `text`, and return the
    passages to compare it against plus an honest account of what happened.

    Each provider's outcome is tracked separately: one answering "no results"
    never hides that the other could not be reached."""
    providers = enabled_providers() if providers is None else providers
    if not providers:
        return ExternalCheck("disabled", "External source checks are turned off on this server.")

    queries = select_queries(text)
    if not queries:
        return ExternalCheck(
            "too_short", "The text has no sentence long enough to search for on external sources."
        )

    fetch = _Fetcher(http_get or _http_get)
    deadline = time.monotonic() + BUDGET_SECONDS

    # Wikipedia is one serial chain; arXiv is a different service and runs beside it.
    jobs = {}
    if "wikipedia" in providers:
        jobs["wikipedia"] = lambda: _wikipedia_chain(fetch, queries, deadline)
    if "arxiv" in providers:
        longest = max(queries, key=lambda q: len(q.split()))
        jobs["arxiv"] = lambda: _arxiv_docs(fetch, longest)

    docs: list[ExternalDoc] = []
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs))
    futures = {pool.submit(fn): name for name, fn in jobs.items()}
    try:
        for fut in concurrent.futures.as_completed(futures, timeout=BUDGET_SECONDS + 5):
            try:
                docs.extend(fut.result())
            except Exception:  # noqa: BLE001
                logger.exception("external source task %s crashed", futures[fut])
    except concurrent.futures.TimeoutError:
        logger.warning("external source check hit its time budget")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    down = fetch.unreachable(providers)

    if not docs:
        if len(down) == len(providers):
            return ExternalCheck(
                "unavailable",
                f"{_describe_failures(down)}, so only earlier submissions were compared. "
                "This says nothing about whether the text is original.",
            )
        reached = " and ".join(LABELS[p] for p in providers if p not in down)
        note = (
            f"No matching pages were found on {reached}. That means not found among the "
            "sources checked, not that the text is original."
        )
        if down:
            note += f" {_describe_failures(down)}, so it was not checked."
        return ExternalCheck("no_candidates", note)

    sources = [{"kind": d.kind, "title": d.title, "url": d.url} for d in docs]
    corpus = build_corpus(docs, text, embed)
    counts = {k: sum(1 for d in docs if d.kind == k) for k in KINDS}
    parts = [f"{n} {LABELS[k]} {'page' if k == 'wikipedia' else 'abstract'}{'s' if n != 1 else ''}"
             for k, n in counts.items() if n]
    note = "Also compared against " + " and ".join(parts) + ". Only these pages were checked."
    if down:
        note += f" {_describe_failures(down)}, so it was not checked."
    elif sum(fetch.failed.values()):
        note += " Some requests failed, so coverage may be incomplete."
    return ExternalCheck("ok", note, sources=sources, corpus=corpus)
