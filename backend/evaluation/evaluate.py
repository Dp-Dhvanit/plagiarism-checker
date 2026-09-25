"""
Measure the AI-text detectors against labelled human / AI writing.

    cd backend
    python evaluation/fetch_datasets.py                  # once
    python evaluation/evaluate.py                        # local detector, 25 texts per group
    python evaluation/evaluate.py --full                 # everything (slow)
    python evaluation/evaluate.py --robustness           # also: does one appended sentence flip the verdict?
    python evaluation/evaluate.py --hosted groq --hosted-limit 10   # spends free-tier quota

What it reports, and why it is shaped this way
----------------------------------------------
The number that matters in a classroom is the FALSE-POSITIVE rate: how often
genuine human writing is called AI. It is reported per group with a 95% Wilson
interval, because 25-90 essays cannot support a claim of "3.2%" — the interval
shows what the sample can and cannot say. Non-native English writing is broken
out on purpose: perplexity-based detectors are known to misjudge it
(Liang et al., 2023), and this app should be measured against that, not assume
it away.

Scores are turned into calls with the app's own thresholds
(app/detectors/base.py): >= 60 is "AI", <= 40 is "human", between is
"uncertain" — an abstention, which is neither a hit nor a false alarm.

Nothing here is a pass/fail gate; it is a ruler. Run it before and after a
change to a detector to see whether the change helped.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from collections import defaultdict

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(_BACKEND, ".env"))  # hosted detectors read their keys from here

from app.detectors.base import AI_THRESHOLD, HUMAN_THRESHOLD  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "samples.jsonl")
RESULTS = os.path.join(HERE, "results")

# One unusual, human-sounding sentence. Used by --robustness to test whether a
# single appended sentence can flip a verdict (it moved a score 69 -> 40 once).
APPENDED = (
    "Honestly, my cat knocked a mug off the desk while I was typing this, "
    "so the ending feels a bit rushed."
)


# ── data ────────────────────────────────────────────────────────────────────

def load_samples(limit_per_group: int | None, groups: set[str] | None, seed: int = 0) -> list[dict]:
    if not os.path.exists(DATA):
        sys.exit(f"No data at {os.path.relpath(DATA)}. Run: python evaluation/fetch_datasets.py")
    by_group: dict[str, list[dict]] = defaultdict(list)
    with open(DATA, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if groups is None or row["group"] in groups:
                by_group[row["group"]].append(row)
    rng = random.Random(seed)  # fixed seed: the same subset every run, so runs are comparable
    out: list[dict] = []
    for g in sorted(by_group):
        rows = by_group[g]
        rng.shuffle(rows)
        out.extend(rows if limit_per_group is None else rows[:limit_per_group])
    return out


# ── detectors ───────────────────────────────────────────────────────────────

def make_local_scorer():
    """The app's own local scorer, gated exactly as /analyze gates it (text too
    short or not prose is skipped there, so it is skipped here)."""
    from app.scoring import get_scorer
    from app.text_quality import assess

    scorer = get_scorer()
    scorer.load()

    def score(text: str) -> float | None:
        if assess(text).status != "ok":
            return None
        return scorer.analyze(text).ai_likelihood_score

    return score


def make_hosted_scorer(name: str, sleep: float):
    from app.detectors.registry import get_detector

    det = get_detector(name)
    if det is None:
        sys.exit(f"Unknown detector {name!r}.")
    ok, reason = det.available()
    if not ok:
        sys.exit(f"Detector {name!r} is not available: {reason}")

    def score(text: str) -> float | None:
        time.sleep(sleep)  # stay under the provider's per-minute limit
        res = det.detect(text)
        return res.ai_probability if res.ran else None

    return score


def run(samples: list[dict], scorer, label: str) -> dict[str, float | None]:
    scores: dict[str, float | None] = {}
    t0 = time.time()
    for i, s in enumerate(samples, 1):
        scores[s["id"]] = scorer(s["text"])
        if i % 10 == 0 or i == len(samples):
            rate = (time.time() - t0) / i
            print(f"  [{label}] {i}/{len(samples)}  ({rate:.1f}s each, ~{rate * (len(samples) - i):.0f}s left)", flush=True)
    return scores


# ── statistics ──────────────────────────────────────────────────────────────

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes of n."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - half) / denom), min(1.0, (centre + half) / denom)


def auroc(pos: list[float], neg: list[float]) -> float | None:
    """Probability a random AI text outscores a random human text (ties = 0.5)."""
    if not pos or not neg:
        return None
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def call(score: float) -> str:
    if score >= AI_THRESHOLD:
        return "ai"
    if score <= HUMAN_THRESHOLD:
        return "human"
    return "uncertain"


def pct(x: float) -> str:
    return f"{100 * x:5.1f}%"


def summarise(samples: list[dict], scores: dict[str, float | None]) -> dict:
    groups: dict[str, dict] = {}
    for s in samples:
        g = groups.setdefault(s["group"], {"label": s["label"], "scores": [], "skipped": 0})
        sc = scores.get(s["id"])
        if sc is None:
            g["skipped"] += 1
        else:
            g["scores"].append(sc)

    for g in groups.values():
        n = len(g["scores"])
        calls = [call(x) for x in g["scores"]]
        g["n"] = n
        g["mean"] = sum(g["scores"]) / n if n else None
        g["called_ai"] = calls.count("ai")
        g["uncertain"] = calls.count("uncertain")
        g["called_human"] = calls.count("human")
        g["ai_ci"] = wilson(g["called_ai"], n)

    human_scores = [x for g in groups.values() if g["label"] == "human" for x in g["scores"]]
    ai_scores = [x for g in groups.values() if g["label"] == "ai" for x in g["scores"]]
    fp = sum(g["called_ai"] for g in groups.values() if g["label"] == "human")
    tp = sum(g["called_ai"] for g in groups.values() if g["label"] == "ai")
    return {
        "groups": groups,
        "false_positives": fp, "human_n": len(human_scores),
        "true_positives": tp, "ai_n": len(ai_scores),
        "fpr_ci": wilson(fp, len(human_scores)),
        "tpr_ci": wilson(tp, len(ai_scores)),
        "auroc": auroc(ai_scores, human_scores),
    }


def render(title: str, summary: dict) -> None:
    print("\n" + "=" * 92)
    print(f"{title}   (AI call: score >= {AI_THRESHOLD:.0f}, human call: <= {HUMAN_THRESHOLD:.0f}, between = uncertain)")
    print("=" * 92)
    print(f"{'group':18s} {'truth':6s} {'n':>4s} {'mean':>6s} | {'called AI':>9s} {'95% CI':>15s} | {'uncertain':>9s} | {'called human':>12s}")
    for name, g in sorted(summary["groups"].items(), key=lambda kv: (kv[1]["label"], kv[0])):
        if not g["n"]:
            print(f"{name:18s} {g['label']:6s}    0   (all {g['skipped']} skipped)")
            continue
        n = g["n"]
        lo, hi = g["ai_ci"]
        note = f"   ({g['skipped']} skipped)" if g["skipped"] else ""
        print(f"{name:18s} {g['label']:6s} {n:4d} {g['mean']:6.1f} | "
              f"{pct(g['called_ai'] / n):>9s} {f'[{100 * lo:.0f}-{100 * hi:.0f}%]':>15s} | "
              f"{pct(g['uncertain'] / n):>9s} | {pct(g['called_human'] / n):>12s}{note}")
    print("-" * 92)
    if summary["human_n"]:
        lo, hi = summary["fpr_ci"]
        print(f"False-positive rate (human called AI): {summary['false_positives']}/{summary['human_n']} "
              f"= {pct(summary['false_positives'] / summary['human_n']).strip()}  95% CI [{100 * lo:.1f}-{100 * hi:.1f}%]")
    if summary["ai_n"]:
        lo, hi = summary["tpr_ci"]
        print(f"True-positive rate  (AI called AI):    {summary['true_positives']}/{summary['ai_n']} "
              f"= {pct(summary['true_positives'] / summary['ai_n']).strip()}  95% CI [{100 * lo:.1f}-{100 * hi:.1f}%]")
    if summary["auroc"] is not None:
        print(f"AUROC (ranking quality, threshold-free): {summary['auroc']:.3f}   (0.5 = coin flip, 1.0 = perfect)")


def robustness(samples: list[dict], scores: dict[str, float | None], scorer) -> dict | None:
    """Re-score AI texts that were caught, after appending one human-sounding sentence."""
    caught = [s for s in samples
              if s["label"] == "ai" and scores.get(s["id"]) is not None and scores[s["id"]] >= AI_THRESHOLD]
    if not caught:
        print("\nRobustness: no AI text scored >= threshold, nothing to perturb.")
        return None
    print(f"\nRobustness: appending one sentence to {len(caught)} AI texts that were caught...")
    deltas, flipped, to_human = [], 0, 0
    for s in caught:
        after = scorer(s["text"] + " " + APPENDED)
        if after is None:
            continue
        deltas.append(after - scores[s["id"]])
        flipped += after < AI_THRESHOLD
        to_human += after <= HUMAN_THRESHOLD
    n = len(deltas)
    lo, hi = wilson(flipped, n)
    out = {"n": n, "mean_delta": sum(deltas) / n, "no_longer_ai": flipped, "now_human": to_human,
           "flip_ci": (lo, hi)}
    print(f"  mean score change: {out['mean_delta']:+.1f} points")
    print(f"  no longer called AI: {flipped}/{n} = {pct(flipped / n).strip()}  95% CI [{100 * lo:.0f}-{100 * hi:.0f}%]")
    print(f"  flipped all the way to 'human': {to_human}/{n}")
    print(f"  appended sentence: {APPENDED!r}")
    return out


# ── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=25, help="texts per group for the local detector (default 25)")
    ap.add_argument("--full", action="store_true", help="use every text in every group")
    ap.add_argument("--groups", help="comma-separated group names to include")
    ap.add_argument("--robustness", action="store_true", help="also test the appended-sentence evasion")
    ap.add_argument("--hosted", help="comma-separated hosted detectors to also evaluate, e.g. groq (uses quota)")
    ap.add_argument("--hosted-limit", type=int, default=10, help="texts per group for hosted detectors (default 10)")
    ap.add_argument("--sleep", type=float, default=2.5, help="seconds between hosted calls (default 2.5)")
    ap.add_argument("--json", help="also write per-text scores and summaries to this file")
    args = ap.parse_args()

    groups = set(args.groups.split(",")) if args.groups else None
    limit = None if args.full else args.limit
    samples = load_samples(limit, groups)
    print(f"Loaded {len(samples)} texts across {len({s['group'] for s in samples})} groups.")

    report: dict = {"thresholds": {"ai": AI_THRESHOLD, "human": HUMAN_THRESHOLD}, "detectors": {}}

    local = make_local_scorer()
    local_scores = run(samples, local, "local")
    summary = summarise(samples, local_scores)
    render("LOCAL STATISTICAL DETECTOR", summary)
    report["detectors"]["local"] = {"summary": _jsonable(summary),
                                    "scores": {k: v for k, v in local_scores.items()}}
    if args.robustness:
        report["robustness_local"] = robustness(samples, local_scores, local)

    for name in [h.strip() for h in (args.hosted or "").split(",") if h.strip()]:
        subset = load_samples(args.hosted_limit, groups)
        scorer = make_hosted_scorer(name, args.sleep)
        scores = run(subset, scorer, name)
        summ = summarise(subset, scores)
        render(f"HOSTED DETECTOR: {name}  ({args.hosted_limit} per group)", summ)
        report["detectors"][name] = {"summary": _jsonable(summ), "scores": scores}

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        print(f"\nWrote {args.json}")
    return 0


def _jsonable(summary: dict) -> dict:
    out = dict(summary)
    out["groups"] = {k: {kk: vv for kk, vv in v.items() if kk != "scores"} for k, v in summary["groups"].items()}
    return out


if __name__ == "__main__":
    sys.exit(main())
