"""
Embedding-model benchmark for the similarity pipeline.

Compares candidate sentence-embedding models on IDENTICAL evaluation data
using the SAME windowing logic as the production pipeline (imported from
app.similarity, not reimplemented) so results are directly comparable to
what /analyze actually does.

Reports, per model:
  - score on each genuine-copy fixture (verbatim / light-modified / paraphrase
    / patchwork) — higher is better, this is what must be CAUGHT
  - score on each false-positive fixture (same-topic-independent / unrelated /
    human academic / pre-1900 classics) — lower is better, this must NOT be
    flagged
  - separation margin = weakest genuine-copy score minus worst false-positive
    score. This is the number that actually matters: a model can only be
    "better" if it makes copies score higher AND originals score lower at
    the SAME time. A model that just shifts everything up or down uniformly
    has not improved anything — margin is threshold-independent, so it is
    the fair way to compare models that produce different score scales.
  - load time, single-batch encode time, and on-disk model size

Run:
    cd backend
    python test_embedding_benchmark.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from app.file_pipeline import build_units
from app.similarity import _windows

EVAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "samples", "eval")
EVAL_DIR = os.path.abspath(EVAL_DIR)

WINDOW_WORDS = 60
STRIDE_WORDS = 30

# (fixture, category) — category drives how it's scored below.
FIXTURES = [
    ("01_source_original.txt", "source"),          # seeds the corpus, not scored
    ("02_copy_verbatim.docx", "copy"),
    ("15_copy_light_modified.docx", "copy"),
    ("03_copy_paraphrased.docx", "copy"),
    ("04_copy_partial.pptx", "copy"),               # patchwork — scored on best passage
    ("14_same_topic_independent.txt", "clean"),     # same topic, independently written
    ("05_unrelated.pdf", "clean"),
    ("09_human_academic.pdf", "clean"),
    ("10_human_gettysburg.txt", "clean"),
    ("11_human_austen.txt", "clean"),
]

CANDIDATES = [
    "sentence-transformers/all-MiniLM-L6-v2",   # current production model
    "sentence-transformers/all-mpnet-base-v2",  # larger, historically stronger on STS/paraphrase
    "BAAI/bge-small-en-v1.5",                   # same size class as current, newer training
]


def extract(fname: str) -> str:
    path = os.path.join(EVAL_DIR, fname)
    if fname.endswith((".txt", ".py")):
        with open(path, encoding="utf-8") as f:
            return f.read()
    with open(path, "rb") as f:
        data = f.read()
    return "\n\n".join(u.text for u in build_units(fname, data) if u.text.strip())


def model_disk_size_mb(model_name: str) -> float:
    """Best-effort size of the model's HF cache folder."""
    cache_root = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
    folder = "models--" + model_name.replace("/", "--")
    path = os.path.join(cache_root, folder)
    if not os.path.isdir(path):
        return -1.0
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.islink(fp):
                fp = os.path.realpath(fp)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    return total / (1024 * 1024)


def bench_model(model_name: str, texts_by_fixture: dict[str, list[str]]) -> dict:
    from sentence_transformers import SentenceTransformer

    t0 = time.perf_counter()
    model = SentenceTransformer(model_name)
    load_s = time.perf_counter() - t0

    all_windows = []
    spans = {}  # fixture -> (start, end) into all_windows
    for fname, windows in texts_by_fixture.items():
        spans[fname] = (len(all_windows), len(all_windows) + len(windows))
        all_windows.extend(windows)

    t0 = time.perf_counter()
    vecs = model.encode(all_windows, normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
    encode_s = time.perf_counter() - t0

    source_start, source_end = spans["01_source_original.txt"]
    source_vecs = vecs[source_start:source_end]

    scores = {}
    for fname, (s, e) in spans.items():
        if fname == "01_source_original.txt":
            continue
        doc_vecs = vecs[s:e]
        if doc_vecs.shape[0] == 0 or source_vecs.shape[0] == 0:
            scores[fname] = {"best": 0.0, "portion_over_45": 0.0}
            continue
        sims = doc_vecs @ source_vecs.T  # (n_windows, n_source_windows)
        best_per_window = np.clip(sims.max(axis=1), 0.0, 1.0)
        scores[fname] = {
            "best": float(best_per_window.max()) * 100,
            "mean": float(best_per_window.mean()) * 100,
            "portion_over_45": float((best_per_window >= 0.45).mean()) * 100,
        }

    return {
        "load_s": load_s,
        "encode_s": encode_s,
        "n_windows": len(all_windows),
        "disk_mb": model_disk_size_mb(model_name),
        "scores": scores,
    }


def main() -> None:
    print("=" * 100)
    print("Preparing windowed text (identical across all models)")
    print("=" * 100)
    texts_by_fixture: dict[str, list[str]] = {}
    for fname, _cat in FIXTURES:
        text = extract(fname)
        windows = _windows(text, WINDOW_WORDS, STRIDE_WORDS)
        texts_by_fixture[fname] = windows
        print(f"  {fname:<32} {len(windows)} window(s)")

    results = {}
    for model_name in CANDIDATES:
        print()
        print("=" * 100)
        print(f"BENCHMARKING: {model_name}")
        print("=" * 100)
        try:
            results[model_name] = bench_model(model_name, texts_by_fixture)
        except Exception as exc:
            print(f"  FAILED to load/run: {type(exc).__name__}: {exc}")
            continue

        r = results[model_name]
        print(f"  load time    : {r['load_s']:.2f}s")
        print(f"  encode time  : {r['encode_s']:.3f}s for {r['n_windows']} windows "
              f"({r['encode_s']/max(r['n_windows'],1)*1000:.1f} ms/window)")
        print(f"  disk size    : {r['disk_mb']:.1f} MB" if r["disk_mb"] >= 0 else "  disk size    : (not cached / unknown)")
        print()
        print(f"  {'fixture':<32}{'category':<10}{'best%':>8}{'portion>=45%':>14}")
        for fname, cat in FIXTURES[1:]:
            s = r["scores"].get(fname, {})
            print(f"  {fname:<32}{cat:<10}{s.get('best',0):>7.1f}%{s.get('portion_over_45',0):>13.1f}%")

    # ── Comparative summary ──────────────────────────────────────────────
    print()
    print("=" * 100)
    print("COMPARATIVE SUMMARY — separation margin (weakest copy score − worst false positive)")
    print("=" * 100)
    copy_files = [f for f, c in FIXTURES if c == "copy"]
    clean_files = [f for f, c in FIXTURES if c == "clean"]

    print(f"  {'model':<42}{'weakest copy':>14}{'worst clean':>13}{'MARGIN':>10}")
    for model_name, r in results.items():
        copy_scores = [r["scores"][f]["best"] for f in copy_files]
        clean_scores = [r["scores"][f]["best"] for f in clean_files]
        weakest_copy = min(copy_scores)
        worst_clean = max(clean_scores)
        margin = weakest_copy - worst_clean
        print(f"  {model_name:<42}{weakest_copy:>13.1f}%{worst_clean:>12.1f}%{margin:>+9.1f}pt")

    print()
    print("Per-fixture false-positive detail (the risk case Goal 2 calls out):")
    for model_name, r in results.items():
        st = r["scores"].get("14_same_topic_independent.txt", {})
        print(f"  {model_name:<42} same-topic-independent best = {st.get('best', 0):.1f}%")


if __name__ == "__main__":
    main()
