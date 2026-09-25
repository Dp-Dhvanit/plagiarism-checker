"""
Endpoint-level regression suite for /analyze and the API's browser-facing
security settings.

Runs against an ISOLATED temporary database and FAKE hosted providers, so it
never touches backend/data/history.db and never spends Gemini/Groq quota.
Everything here was found by exercising the live API:

  * an identical paste was invisible to the plagiarism check, because /analyze
    excluded its own content hash even though it compares BEFORE it stores
  * every /analyze made two Gemini calls for the same text
  * a "Likely Human" headline hid a hosted detector that said 70% AI
  * CORS reflected any origin back with credentials allowed

    cd backend
    python test_analyze_endpoint.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import db

_TMP = tempfile.mkdtemp(prefix="analyze_endpoint_")
db.DB_PATH = os.path.join(_TMP, "endpoint.db")
db.init_db()

from fastapi.testclient import TestClient  # noqa: E402

import app.main as m  # noqa: E402
from app import gemini_client  # noqa: E402
from app.ai_text_detector import GeminiTextDetection  # noqa: E402
from app.detectors import registry  # noqa: E402
from app.detectors.base import Detector, DetectorResult  # noqa: E402
from app.detectors.builtin import GeminiDetector, HeuristicDetector  # noqa: E402
from app.scoring import get_scorer  # noqa: E402

SAMPLES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))

passed = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))


# ── Fakes: nothing here touches the network ─────────────────────────────────

gemini_calls = 0
gemini_probability = 50.0


def fake_analyze_text_ai(text: str):
    global gemini_calls
    gemini_calls += 1
    if gemini_probability is None:  # a failed call: the real function returns None
        return None
    return GeminiTextDetection(
        ai_probability=gemini_probability,
        confidence="medium",
        flagged_sections=[],
        explanation="fake gemini",
    )


class FakeHosted(Detector):
    name, label = "fakehosted", "Fake hosted"
    local, paid = False, False
    probability: float | None = 50.0

    def available(self):
        return (True, "") if self.probability is not None else (False, "off for this test")

    def _detect(self, text):
        return DetectorResult(
            provider=self.name,
            ai_probability=self.probability,
            verdict=DetectorResult.verdict_for(self.probability),
            confidence="medium",
            explanation="fake",
        )


fake_hosted = FakeHosted()
m.analyze_text_ai = fake_analyze_text_ai
gemini_client.is_configured = lambda: True
registry._REGISTRY[:] = [HeuristicDetector(), GeminiDetector(), fake_hosted]

client = TestClient(m.app)


def analyze(text: str) -> dict:
    r = client.post("/analyze", json={"text": text})
    assert r.status_code == 200, r.text
    return r.json()


# Genuinely different subjects, so one test's "fresh" text can't legitimately
# overlap another's. (An earlier draft varied only a marker sentence and
# correctly reported the shared body as 100% overlap.)
_PARAGRAPHS = [
    "The migration of arctic terns spans roughly seventy thousand kilometres each year, the longest "
    "of any animal. Biologists tracking geolocators found that the birds follow a zig-zag route down "
    "the Atlantic, riding prevailing winds instead of flying straight. This detour adds distance but "
    "saves energy, and it is why the estimate is so much larger than the direct line between the poles.",
    "Sourdough bread depends on a living culture of wild yeast and lactic acid bacteria rather than "
    "packaged yeast. Bakers feed the starter with flour and water on a regular schedule, watching for "
    "bubbles and a pleasantly sour smell. A long, cool fermentation develops flavour and makes the crumb "
    "open and chewy, though the timing shifts noticeably with the temperature of the kitchen.",
    "Suspension bridges carry their deck from vertical hangers attached to two enormous main cables. "
    "The cables pass over tall towers and are anchored deep in the ground at each end, so the towers "
    "mostly bear compression while the anchorages resist the pull. Engineers must also design against "
    "wind, since a light and flexible deck can begin to oscillate in a steady crosswind.",
    "A chess opening is judged less by any single move than by the structure it creates. Controlling "
    "the centre with pawns gives the pieces room to develop, while castling early tucks the king away "
    "before the position opens. Beginners often memorise long sequences without understanding the plans "
    "behind them, and are lost the moment an opponent deviates from the book.",
]
_next_paragraph = iter(_PARAGRAPHS)


def unique_prose() -> str:
    """A paragraph no earlier call has returned (up to len(_PARAGRAPHS))."""
    return f"Reference {uuid.uuid4().hex}. {next(_next_paragraph)}"


def main() -> int:
    global gemini_probability
    get_scorer().load()

    print("=" * 70)
    print("DUPLICATE SUBMISSIONS — identical paste must be caught")
    print("=" * 70)
    text = unique_prose()
    first = analyze(text)
    second = analyze(text)
    check("first submission of new text has no overlap",
          first["similarity"]["matched_portion"] == 0.0,
          f"matched_portion={first['similarity']['matched_portion']}")
    check("identical second paste is flagged against the first",
          second["similarity"]["matched_portion"] >= 50 and second["similarity"]["top_match_verified"],
          f"matched_portion={second['similarity']['matched_portion']}, "
          f"verified={second['similarity']['top_match_verified']}")

    print("\n" + "=" * 70)
    print("/reduce-overlap right after /analyze must not match its own stored copy")
    print("=" * 70)
    fresh = unique_prose()
    analyze(fresh)
    rr = client.post("/reduce-overlap", json={"text": fresh})
    check("reduce-overlap responds", rr.status_code == 200, f"{rr.status_code}")
    check("reduce-overlap does not self-match the copy /analyze just stored",
          rr.json()["before"]["matched_portion"] == 0.0,
          f"before.matched_portion={rr.json()['before']['matched_portion']}")

    print("\n" + "=" * 70)
    print("GEMINI — one call per analysis, reused for the detector entry")
    print("=" * 70)
    gemini_probability = 73.0
    before = gemini_calls
    r = analyze(unique_prose())
    check("exactly one Gemini call per /analyze", gemini_calls - before == 1,
          f"{gemini_calls - before} call(s)")
    g_entry = next((d for d in r["detectors"] if d["provider"] == "gemini"), None)
    check("gemini appears in detectors with the same score as the legacy field",
          g_entry is not None and r["gemini"] is not None
          and g_entry["ai_probability"] == r["gemini"]["ai_probability"] == 73.0,
          f"detectors.gemini={g_entry and g_entry['ai_probability']}, legacy={r['gemini'] and r['gemini']['ai_probability']}")
    check("detectors are reported in registry order",
          [d["provider"] for d in r["detectors"]] == ["heuristic", "gemini", "fakehosted"],
          str([d["provider"] for d in r["detectors"]]))

    print("\n" + "=" * 70)
    print("HEADLINE VERDICT — disagreement must not be hidden")
    print("=" * 70)
    with open(os.path.join(SAMPLES, "eval", "07_ai_prose.txt"), encoding="utf-8") as f:
        ai_prose = f.read()

    # heuristic calls this fixture human-leaning (known limitation, see IMPROVEMENTS.md)
    gemini_probability, fake_hosted.probability = 90.0, 90.0
    r = analyze(ai_prose + f"\n\nRef {uuid.uuid4().hex}.")
    local = r["ai_likelihood_score"]
    check("precondition: local detector is not itself calling this AI", local < 60,
          f"local score={local}")
    check("hosted detectors say AI but local says otherwise -> headline is Uncertain",
          r["final_verdict"] == "Uncertain" and "disagree" in (r["verdict_reason"] or ""),
          f"final_verdict={r['final_verdict']!r}, reason={r['verdict_reason']!r}")
    check("local verdict field is left as the local detector's own",
          r["verdict"] != "Likely AI", f"verdict={r['verdict']!r}")

    # Agreement case needs text the LOCAL detector already calls human-leaning
    # (<=40); a 2% hosted score against a 44% local one is disagreement.
    with open(os.path.join(SAMPLES, "eval", "08_ai_prose_edited.txt"), encoding="utf-8") as f:
        human_leaning = f.read()
    gemini_probability, fake_hosted.probability = 2.0, 2.0
    r = analyze(human_leaning + f"\n\nRef {uuid.uuid4().hex}.")
    check("precondition: local detector calls this human-leaning", r["ai_likelihood_score"] <= 40,
          f"local score={r['ai_likelihood_score']}")
    check("everyone agrees on human -> directional verdict is allowed",
          r["final_verdict"] == "Likely Human" and "agree" in r["verdict_reason"],
          f"final_verdict={r['final_verdict']!r}, reason={r['verdict_reason']!r}")

    gemini_probability = None  # Gemini unusable
    fake_hosted.probability = None  # nothing hosted available
    gemini_client.is_configured = lambda: False
    r = analyze(ai_prose + f"\n\nRef {uuid.uuid4().hex}.")
    check("only the local detector ran -> verdict is the local one, and says so",
          r["final_verdict"] == r["verdict"] and "one detector only" in r["verdict_reason"],
          f"final_verdict={r['final_verdict']!r}, reason={r['verdict_reason']!r}")
    gemini_client.is_configured = lambda: True
    gemini_probability, fake_hosted.probability = 50.0, 50.0

    print("\n" + "=" * 70)
    print("LOCAL DETECTOR ALONE cannot accuse (measured: 8.8% of non-native essays flagged)")
    print("=" * 70)

    def res(provider: str, p: float) -> DetectorResult:
        return DetectorResult(provider=provider, ai_probability=p, verdict=DetectorResult.verdict_for(p))

    h = registry.headline([res("heuristic", 69.0)], local_label="Likely AI")
    check("local alone, leaning AI -> headline is Uncertain, and says why",
          h["verdict"] == "Uncertain" and h["basis"] == "single_capped"
          and "second opinion" in h["reason"] and "non-native" in h["reason"], str(h))
    h = registry.headline([res("heuristic", 20.0)], local_label="Likely Human")
    check("local alone, leaning human -> unchanged (a false accusation is the costly error)",
          h["verdict"] == "Likely Human" and h["basis"] == "single", str(h))
    h = registry.headline([res("heuristic", 45.0)], local_label="Uncertain")
    check("local alone, in the middle -> Uncertain", h["verdict"] == "Uncertain" and h["basis"] == "single")
    h = registry.headline([res("heuristic", 69.0), res("groq", 72.0)], local_label="Likely AI")
    check("two detectors agreeing on AI may still say Likely AI",
          h["verdict"] == "Likely AI" and h["basis"] == "agreement", str(h))
    h = registry.headline([res("heuristic", 69.0), res("groq", 20.0)], local_label="Likely AI")
    check("two detectors split -> Uncertain", h["verdict"] == "Uncertain" and h["basis"] == "disagreement")
    check("no detector ran -> Uncertain", registry.headline([], None)["verdict"] == "Uncertain")

    with open(os.path.join(SAMPLES, "ai_text.txt"), encoding="utf-8") as f:
        ai_leaning = f.read()
    gemini_probability, fake_hosted.probability = None, None
    gemini_client.is_configured = lambda: False
    # Analysed as-is: appending a marker sentence to make it unique would itself
    # drop this fixture from 69 to ~46 (the appended-sentence weakness, measured
    # in backend/evaluation), and uniqueness is irrelevant to this check.
    r = analyze(ai_leaning)
    check("through the API: local score >= 60 with no second opinion",
          r["ai_likelihood_score"] >= 60 and r["final_verdict"] == "Uncertain"
          and "second opinion" in r["verdict_reason"],
          f"score={r['ai_likelihood_score']}, final_verdict={r['final_verdict']!r}")
    check("...while the local verdict field still reports what the local detector said",
          r["verdict"] == "Likely AI", f"verdict={r['verdict']!r}")
    gemini_client.is_configured = lambda: True
    gemini_probability, fake_hosted.probability = 50.0, 50.0

    print("\n" + "=" * 70)
    print("HISTORY — the headline verdict is archived with the result")
    print("=" * 70)
    detail = client.get(f"/history/{r['history_id']}").json()
    check("history result_json carries final_verdict + detectors",
          detail["result_json"].get("final_verdict") == r["final_verdict"]
          and len(detail["result_json"].get("detectors", [])) == 3,
          f"final_verdict={detail['result_json'].get('final_verdict')!r}")

    print("\n" + "=" * 70)
    print("BROWSER-FACING SECURITY — CORS and Host checks")
    print("=" * 70)
    hostile = client.get("/health", headers={"Origin": "http://evil.example"})
    check("a foreign origin is NOT granted CORS access",
          "access-control-allow-origin" not in hostile.headers, str(dict(hostile.headers)))
    hostile_pre = client.options(
        "/history/1",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "DELETE"},
    )
    check("preflight from a foreign origin is refused",
          "access-control-allow-origin" not in hostile_pre.headers, f"{hostile_pre.status_code}")
    friendly = client.get("/health", headers={"Origin": "http://localhost:5173"})
    check("the dev frontend origin still works",
          friendly.headers.get("access-control-allow-origin") == "http://localhost:5173")
    check("credentials are not allowed cross-origin",
          "access-control-allow-credentials" not in friendly.headers)
    rebind = TestClient(m.app, base_url="http://evil.example").get("/history")
    check("a foreign Host header (DNS rebinding) is rejected", rebind.status_code == 400,
          f"{rebind.status_code}")
    check("localhost Host header is accepted",
          TestClient(m.app, base_url="http://localhost:8000").get("/health").status_code == 200)

    print("\n" + "=" * 70)
    print(f"\n{passed}/{passed + failed} checks passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
