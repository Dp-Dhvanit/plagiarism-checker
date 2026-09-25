"""
Regression suite for the opt-in external-source check (app/web_sources.py) and
for match provenance.

Everything runs OFFLINE against a fake HTTP layer and an ISOLATED temporary
database. Beyond the mechanics, this pins the honesty rules the module makes:

  * an unreachable source is reported as unreachable, never as a clean result
  * "nothing found" is worded as "not found among the sources checked"
  * unrelated text gets NO match even when a search returns a page
  * the whole text is never sent out — only a few short search queries
  * matches always say where they came from (URL, or submission + date)

    cd backend
    python test_web_sources.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import db

_TMP = tempfile.mkdtemp(prefix="web_sources_")
db.DB_PATH = os.path.join(_TMP, "web.db")
db.init_db()

from fastapi.testclient import TestClient  # noqa: E402

import app.main as m  # noqa: E402
from app import web_sources as ws  # noqa: E402
from app.detectors import registry  # noqa: E402
from app.detectors.builtin import HeuristicDetector  # noqa: E402
from app.scoring import get_scorer  # noqa: E402
from app.similarity import analyze_similarity  # noqa: E402

passed = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))


# ── Fixtures ────────────────────────────────────────────────────────────────

TITLE = "Lake Baikal"
COPIED = (
    "Lake Baikal in southern Siberia is the deepest and oldest freshwater lake on Earth, "
    "holding roughly one fifth of the planet's unfrozen fresh water. It is more than "
    "six hundred kilometres long and reaches a maximum depth of about sixteen hundred metres. "
    "Hundreds of rivers and streams flow into the lake, but only the Angara river drains it. "
    "The lake is home to thousands of species of plants and animals, most of which are found "
    "nowhere else, including the Baikal seal, one of the few freshwater seals in the world."
)
FILLER_A = (
    "The region around the lake experiences long winters during which the surface freezes "
    "solid enough to carry heavy vehicles across the ice for several months of the year. "
) * 3
FILLER_B = (
    "Local communities have fished the waters for centuries and tourism has grown steadily "
    "since the railway reached the southern shore in the early twentieth century. "
) * 3
ARTICLE = f"{FILLER_A}\n\n{COPIED}\n\n{FILLER_B}"

STUDENT_COPY = (
    "For my geography assignment I chose to write about a famous lake in Russia. "
    + COPIED
    + " I found this topic really interesting and I hope you enjoy reading my report."
)
ORIGINAL = (
    "Sourdough bread depends on a living culture of wild yeast and lactic acid bacteria rather "
    "than packaged yeast. Bakers feed the starter with flour and water on a regular schedule, "
    "watching for bubbles and a pleasantly sour smell. A long, cool fermentation develops flavour "
    "and makes the crumb open and chewy, though the timing shifts with the kitchen temperature."
)

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>Deep Freshwater Lakes as Sentinels of Climate Change</title>
    <summary>{summary}</summary>
  </entry>
</feed>"""
EMPTY_ATOM = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'


class RateLimited(Exception):
    """What requests raises for a 429: an exception carrying the response."""

    def __init__(self):
        super().__init__("429 Client Error: Too Many Requests")
        self.response = type("Resp", (), {"status_code": 429})()


def make_http(*, wiki_hits=(TITLE,), article=ARTICLE, atom=None, fail=False, wiki_429=False, log=None):
    """A fake of the network: Wikipedia search + extract endpoints and arXiv.

    Each fake is a fresh 'network', so the response cache is cleared with it —
    otherwise one scenario's answers would leak into the next."""
    ws._cache.clear()
    def get(url: str, params: dict) -> str:
        if log is not None:
            log.append((url, dict(params)))
        if fail:
            raise ConnectionError("network unreachable")
        if wiki_429 and url == ws.WIKIPEDIA_API:
            raise RateLimited()
        if url == ws.WIKIPEDIA_API:
            if params.get("list") == "search":
                return json.dumps({"query": {"search": [{"title": t} for t in wiki_hits]}})
            if params.get("prop") == "extracts":
                return json.dumps({"query": {"pages": {"1": {"title": params["titles"], "extract": article}}}})
        if url == ws.ARXIV_API:
            return atom if atom is not None else EMPTY_ATOM
        raise AssertionError(f"unexpected request to {url}")
    return get


def main() -> int:
    get_scorer().load()

    print("=" * 70)
    print("CONFIGURATION")
    print("=" * 70)
    saved = os.environ.get("EXTERNAL_SOURCES")
    try:
        os.environ.pop("EXTERNAL_SOURCES", None)
        check("default enables both providers", ws.enabled_providers() == ["wikipedia", "arxiv"])
        os.environ["EXTERNAL_SOURCES"] = "off"
        check("'off' disables the feature", ws.enabled_providers() == [])
        os.environ["EXTERNAL_SOURCES"] = "wikipedia, junk"
        check("unknown provider names are ignored", ws.enabled_providers() == ["wikipedia"])
    finally:
        if saved is None:
            os.environ.pop("EXTERNAL_SOURCES", None)
        else:
            os.environ["EXTERNAL_SOURCES"] = saved

    print("\n" + "=" * 70)
    print("QUERY SELECTION — what leaves the machine")
    print("=" * 70)
    queries = ws.select_queries(STUDENT_COPY)
    check("selects up to 3 queries", 1 <= len(queries) <= ws.MAX_QUERIES, f"{len(queries)}")
    check("every query is a real sentence of the text, trimmed short",
          all(len(q.split()) <= 24 and q.split()[0] in STUDENT_COPY for q in queries))
    check("no query is the whole text", all(len(q) < len(STUDENT_COPY) / 2 for q in queries))
    check("text with no sentence long enough gives no queries", ws.select_queries("Too short. Also short.") == [])

    print("\n" + "=" * 70)
    print("COPIED TEXT is found, with a real URL")
    print("=" * 70)
    log: list = []
    chk = ws.check_external(STUDENT_COPY, providers=["wikipedia"], http_get=make_http(log=log))
    check("status ok", chk.status == "ok", chk.status)
    expected_url = "https://en.wikipedia.org/wiki/Lake_Baikal"
    check("the page compared is listed with its URL",
          any(s["url"] == expected_url and s["kind"] == "wikipedia" for s in chk.sources), str(chk.sources))
    check("note states which pages were checked", "Wikipedia" in chk.note and "Only these pages" in chk.note, chk.note)
    check("some article passages were kept for comparison", len(chk.corpus) > 0, f"{len(chk.corpus)} passages")

    without = analyze_similarity(STUDENT_COPY)
    with_ext = analyze_similarity(STUDENT_COPY, extra_corpus=chk.corpus)
    check("without external pages nothing is found (empty database)", without.matched_portion == 0.0)
    check("with them, the copied wording is verified", with_ext.matched_portion >= 50.0,
          f"matched_portion={with_ext.matched_portion}")
    top = with_ext.matches[0] if with_ext.matches else None
    check("match carries Wikipedia provenance",
          top is not None and top.source_kind == "wikipedia" and top.source_url == expected_url
          and top.source_history_id is None and top.verified,
          str(top and (top.source_kind, top.source_url, top.source_history_id, top.verified)))
    check("passages on file counts stored passages only", with_ext.corpus_size == 0,
          f"corpus_size={with_ext.corpus_size}")

    print("\n" + "=" * 70)
    print("PRIVACY — only short queries are sent, never the document")
    print("=" * 70)
    sent = [str(v) for _, p in log for v in p.values()]
    check("no request parameter contains the whole text", all(len(v) < 300 for v in sent),
          f"longest={max(len(v) for v in sent)} chars")
    check("search terms came from the text",
          any(str(p.get("srsearch", "")).strip('"').split()[0] in STUDENT_COPY for _, p in log if "srsearch" in p))
    check("requests go only to the fixed provider hosts", all(u in (ws.WIKIPEDIA_API, ws.ARXIV_API) for u, _ in log))

    print("\n" + "=" * 70)
    print("HONESTY — no fabricated matches, no silent failures")
    print("=" * 70)
    embedded: list[int] = []

    def counting_embed(texts):
        embedded.append(len(texts))
        from app.embeddings import embed_texts
        return embed_texts(texts)

    unrelated = ws.check_external(ORIGINAL, providers=["wikipedia"], http_get=make_http(), embed=counting_embed)
    check("unrelated text: the page is still listed as compared", unrelated.status == "ok" and len(unrelated.sources) == 1)
    sim = analyze_similarity(ORIGINAL, extra_corpus=unrelated.corpus)
    check("unrelated text gets NO verified match", sim.matched_portion == 0.0 and not sim.top_match_verified,
          f"matched_portion={sim.matched_portion}, corpus passages kept={len(unrelated.corpus)}")

    from app.similarity import _windows
    total_windows = len(_windows(ARTICLE, ws.WINDOW_WORDS, ws.WINDOW_WORDS))
    embedded.clear()
    ws.check_external(STUDENT_COPY, providers=["wikipedia"], http_get=make_http(), embed=counting_embed)
    check("only passages sharing wording are embedded (not the whole article)",
          sum(embedded) < total_windows, f"embedded {sum(embedded)} of {total_windows} article passages")

    down = ws.check_external(STUDENT_COPY, providers=["wikipedia", "arxiv"], http_get=make_http(fail=True))
    check("unreachable sources -> status 'unavailable', not a clean result",
          down.status == "unavailable" and not down.corpus and "could not be reached" in down.note, down.note)

    none_found = ws.check_external(STUDENT_COPY, providers=["wikipedia"], http_get=make_http(wiki_hits=()))
    check("no pages found -> worded as 'not found among sources checked'",
          none_found.status == "no_candidates" and "not that the text is original" in none_found.note, none_found.note)

    check("disabled provider list -> 'disabled', no requests",
          ws.check_external(STUDENT_COPY, providers=[], http_get=make_http(fail=True)).status == "disabled")
    check("text too short to search -> 'too_short'",
          ws.check_external("Short one. Another short.", providers=["wikipedia"], http_get=make_http()).status == "too_short")

    print("\n" + "=" * 70)
    print("RATE LIMITS, PARTIAL FAILURE, ETIQUETTE  (all found against the live API)")
    print("=" * 70)
    # Wikipedia answers 429 but arXiv answers with an empty feed. The old
    # code counted arXiv's answer as success and reported "no matching pages
    # found on Wikipedia and arXiv" — a failure passed off as a clean result.
    calls429: list = []
    partial = ws.check_external(STUDENT_COPY, providers=["wikipedia", "arxiv"],
                                http_get=make_http(wiki_429=True, log=calls429))
    check("Wikipedia rate-limited + arXiv empty: the failure is NOT reported as 'no matches'",
          partial.status == "no_candidates" and "Wikipedia rate limited" in partial.note
          and "No matching pages were found on Wikipedia" not in partial.note, partial.note)
    check("...and only arXiv is claimed as checked", "found on arXiv" in partial.note, partial.note)
    wiki_calls = [c for c in calls429 if c[0] == ws.WIKIPEDIA_API]
    check("a 429 stops further requests to that provider (circuit breaker)", len(wiki_calls) == 1,
          f"{len(wiki_calls)} Wikipedia request(s) after being told to slow down")

    all_429 = ws.check_external(STUDENT_COPY, providers=["wikipedia"], http_get=make_http(wiki_429=True))
    check("all providers rate-limited -> 'unavailable', with the reason",
          all_429.status == "unavailable" and "rate limited" in all_429.note
          and "says nothing about whether the text is original" in all_429.note, all_429.note)

    import threading, time as _time
    live = {"now": 0, "max": 0}
    lock = threading.Lock()
    inner = make_http()

    def tracking(url, params):
        if url == ws.WIKIPEDIA_API:
            with lock:
                live["now"] += 1
                live["max"] = max(live["max"], live["now"])
            _time.sleep(0.03)
            try:
                return inner(url, params)
            finally:
                with lock:
                    live["now"] -= 1
        return inner(url, params)

    ws.check_external(STUDENT_COPY, providers=["wikipedia"], http_get=tracking)
    check("Wikipedia requests are strictly serial (its API etiquette)", live["max"] == 1,
          f"max concurrent = {live['max']}")

    cache_log: list = []
    cached_net = make_http(log=cache_log)
    ws.check_external(STUDENT_COPY, providers=["wikipedia"], http_get=cached_net)
    first_calls = len(cache_log)
    ws.check_external(STUDENT_COPY, providers=["wikipedia"], http_get=cached_net)
    check("re-checking the same text makes no new requests (cached)",
          first_calls > 0 and len(cache_log) == first_calls, f"{first_calls} then {len(cache_log) - first_calls} more")

    print("\n" + "=" * 70)
    print("ARXIV abstracts")
    print("=" * 70)
    abstract_atom = ATOM.format(summary=COPIED)
    a = ws.check_external(STUDENT_COPY, providers=["arxiv"], http_get=make_http(atom=abstract_atom))
    check("an arXiv abstract is found and linked",
          a.status == "ok" and a.sources and a.sources[0]["kind"] == "arxiv"
          and a.sources[0]["url"] == "http://arxiv.org/abs/2401.00001v1", str(a.sources))
    hostile = "<?xml version='1.0'?><!DOCTYPE x [<!ENTITY a 'aaaa'>]><feed xmlns='http://www.w3.org/2005/Atom'>&a;</feed>"
    h = ws.check_external(STUDENT_COPY, providers=["arxiv"], http_get=make_http(atom=hostile))
    check("a feed with entity declarations is ignored, not parsed", h.status == "no_candidates", h.status)
    bad = ws.check_external(STUDENT_COPY, providers=["arxiv"], http_get=make_http(atom="<feed><entry>"))
    check("malformed XML is survived", bad.status == "no_candidates", bad.status)

    print("\n" + "=" * 70)
    print("END TO END through the API (check_web opt-in)")
    print("=" * 70)
    net: list = []
    ws._http_get = make_http(log=net)
    m.analyze_text_ai = lambda text: None                   # no Gemini
    registry._REGISTRY[:] = [HeuristicDetector()]           # no hosted detectors
    client = TestClient(m.app)

    r = client.post("/analyze", json={"text": STUDENT_COPY}).json()
    check("default: no external request is made", not net and r["similarity"]["external"] is None,
          f"{len(net)} request(s)")

    net.clear()
    r = client.post("/analyze", json={"text": STUDENT_COPY + " ", "check_web": True}).json()
    sim = r["similarity"]
    check("check_web=true reports what it did",
          sim["external"] and sim["external"]["status"] == "ok" and sim["external"]["sources"],
          str(sim["external"] and sim["external"]["status"]))
    ext_match = next((x for x in sim["matches"] if x["source_kind"] == "wikipedia"), None)
    check("API match carries source_kind/url and no history id",
          ext_match is not None and ext_match["source_url"] == expected_url and ext_match["source_history_id"] is None
          and ext_match["verified"], str(ext_match and {k: ext_match[k] for k in ("source_kind", "source_url", "source_history_id")}))
    stored = client.get(f"/history/{r['history_id']}").json()["result_json"]["similarity"]
    check("history keeps the external result", stored["external"]["status"] == "ok")

    r = client.post("/analyze", json={"text": ORIGINAL, "check_web": True}).json()
    check("unrelated text via the API: page listed, no external match",
          r["similarity"]["external"]["status"] == "ok"
          and not any(x["source_kind"] == "wikipedia" and x["verified"] for x in r["similarity"]["matches"]))

    ws._http_get = make_http(fail=True)
    r = client.post("/analyze", json={"text": STUDENT_COPY + "  ", "check_web": True})
    check("network failure does not fail the analysis", r.status_code == 200
          and r.json()["similarity"]["external"]["status"] == "unavailable",
          f"{r.status_code} / {r.json()['similarity']['external']['status']}")

    ws._http_get = make_http()
    up = client.post("/upload", files={"file": ("copied.txt", STUDENT_COPY.encode())}, data={"check_web": "true"})
    check("/upload accepts the check_web form field",
          up.status_code == 200 and up.json()["similarity"]["external"]["status"] == "ok", f"{up.status_code}")
    up2 = client.post("/upload", files={"file": ("copied2.txt", (STUDENT_COPY + " ").encode())})
    check("/upload without the field makes no external check",
          up2.status_code == 200 and up2.json()["similarity"]["external"] is None)

    print("\n" + "=" * 70)
    print("PROVENANCE — an earlier submission says which one, and when")
    print("=" * 70)
    ws._http_get = make_http(fail=True)
    # A paragraph no earlier step submitted, so the only possible source is `first`.
    fresh = (
        "Suspension bridges carry their deck from vertical hangers attached to two enormous main "
        "cables. The cables pass over tall towers and are anchored deep in the ground at each end, "
        "so the towers mostly bear compression while the anchorages resist the pull. Engineers must "
        "also design against wind, since a light and flexible deck can begin to oscillate in a "
        "steady crosswind."
    )
    first = client.post("/analyze", json={"text": fresh}).json()
    again = client.post("/analyze", json={"text": fresh}).json()
    pm = again["similarity"]["matches"][0] if again["similarity"]["matches"] else None
    check("match names the earlier submission and links its history id",
          pm is not None and pm["source_kind"] == "submission" and pm["source_history_id"] == first["history_id"]
          and pm["source_name"] == "Pasted text" and pm["source_url"] is None,
          str(pm and {k: pm[k] for k in ("source_kind", "source_history_id", "source_name")}))
    ok_date = False
    try:
        ok_date = pm is not None and datetime.fromisoformat(pm["source_created_at"]).year >= 2024
    except (TypeError, ValueError):
        pass
    check("match carries the date the earlier submission was analysed", ok_date,
          str(pm and pm["source_created_at"]))
    check("the internal storage tag is not what the UI is told to show",
          pm is not None and "(" not in pm["source_name"], str(pm and pm["source_name"]))

    print("\n" + "=" * 70)
    print("PDF REPORT — provenance renders, and hostile characters can't break it")
    print("=" * 70)
    import io
    import pdfplumber
    from app.pdf_report import generate_report

    hostile_name = 'Wikipedia: <b>Tom & "Jerry"</b>'
    hostile_url = "https://en.wikipedia.org/wiki/Tom_&_Jerry?a=1&b=<2>"
    row = {
        "id": 9, "file_name": "essay.txt", "analysis_type": "text",
        "created_at": "2026-09-20T10:00:00+00:00", "status": "analyzed",
        "result_json": {
            "heuristic": {"ai_likelihood_score": 30.0, "verdict": "Likely Human", "perplexity": 40.0, "burstiness": 9.0},
            "gemini_text": None,
            "similarity": {
                "overall_similarity": 50.0, "chunks_compared": 3, "corpus_size": 0, "note": "",
                "matches": [
                    {"query_excerpt": "q", "matched_text": "copied <text> & more", "source_file": hostile_name,
                     "source_name": hostile_name, "source_kind": "wikipedia", "source_url": hostile_url,
                     "source_history_id": None, "score": 91.0, "verified": True},
                    {"query_excerpt": "q", "matched_text": "an earlier essay", "source_file": "Pasted text (0123456789ab)",
                     "source_name": "Pasted text", "source_kind": "submission", "source_created_at": "2026-09-01T08:00:00+00:00",
                     "source_history_id": 3, "score": 88.0, "verified": True},
                    {"query_excerpt": "q", "matched_text": "legacy record", "source_file": "old.pdf",
                     "source_history_id": 2, "score": 60.0},  # predates every provenance field
                ],
                "external": {"status": "ok", "note": "Also compared against 1 Wikipedia page & <1> more.",
                             "sources": [{"kind": "wikipedia", "title": "Tom & Jerry", "url": hostile_url}]},
            },
            "image_result": None, "extracted_text_preview": "preview",
        },
    }
    try:
        pdf = generate_report(row)
        pdf_ok = pdf[:5] == b"%PDF-"
    except Exception as exc:  # noqa: BLE001
        pdf, pdf_ok = b"", False
        print(f"    generate_report raised {type(exc).__name__}: {exc}")
    check("report renders with hostile markup characters in names, URLs and notes", pdf_ok, f"{len(pdf)} bytes")
    if pdf_ok:
        with pdfplumber.open(io.BytesIO(pdf)) as doc:
            body = "\n".join((p.extract_text() or "") for p in doc.pages)
        flat = " ".join(body.split())
        check("hostile source name appears as literal text, not interpreted as markup",
              'Tom & "Jerry"' in flat and "<b>" in flat, flat[flat.find("Wikipedia:"):][:60])
        check("external check note and page list are in the report",
              "Also compared against 1 Wikipedia page" in flat and "Tom & Jerry" in flat)
        check("earlier submission is shown by name and date, not by storage tag",
              "Pasted text" in flat and "2026-09-01" in flat and "0123456789ab" not in flat)
        check("a record from before provenance existed still renders", "old.pdf" in flat)

    print("\n" + "=" * 70)
    print(f"\n{passed}/{passed + failed} checks passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
