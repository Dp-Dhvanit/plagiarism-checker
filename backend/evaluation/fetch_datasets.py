"""
Download labelled human / AI text for measuring the detectors.

    cd backend
    python evaluation/fetch_datasets.py            # essays (Liang et al.) — recommended
    python evaluation/fetch_datasets.py --hc3      # also a sample of HC3 Q&A answers

Writes evaluation/data/samples.jsonl (git-ignored: the data belongs to its
authors, this script just fetches it). One JSON object per line:

    {"id": ..., "text": ..., "label": "human" | "ai", "group": ..., "source": ...}

Sources
-------
* Liang et al., "GPT detectors are biased against non-native English writers"
  (Patterns, 2023), MIT-licensed:
  https://github.com/Weixin-Liang/ChatGPT-Detector-Bias
  Includes 91 real TOEFL essays by non-native English writers — the group
  detectors are known to wrongly flag — plus US student/college essays and
  GPT-3 text, some prompt-engineered specifically to evade detectors.
* HC3 (Guo et al., 2023): human vs ChatGPT answers, via the Hugging Face
  datasets-server. Short Q&A text, a different regime from essays.

Groups (what evaluate.py breaks results down by)
------------------------------------------------
    human_non_native     real TOEFL essays
    human_student        US 8th-grade essays
    human_college        real college-application essays
    human_academic       real course-project abstracts
    ai_plain             GPT-3, plain prompt
    ai_evasive           GPT-3, prompt-engineered to sound more human
    ai_polished          the TOEFL essays rewritten by GPT-4
    human_hc3 / ai_hc3   HC3 answers (only with --hc3)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "samples.jsonl")

LIANG = "https://raw.githubusercontent.com/Weixin-Liang/ChatGPT-Detector-Bias/main/Data_and_Results/"

# (path inside the repo, label, group)
LIANG_SETS = [
    ("Human_Data/TOEFL_real_91", "human", "human_non_native"),
    ("Human_Data/HewlettStudentEssay_real_88", "human", "human_student"),
    ("Human_Data/CollegeEssay_real_70", "human", "human_college"),
    ("Human_Data/CS224N_real_145", "human", "human_academic"),
    ("GPT_Data/CollegeEssay_gpt3_31", "ai", "ai_plain"),
    ("GPT_Data/CS224N_gpt3_145", "ai", "ai_plain"),
    ("GPT_Data/CollegeEssay_gpt3PromptEng_31", "ai", "ai_evasive"),
    ("GPT_Data/CS224N_gpt3PromptEng_145", "ai", "ai_evasive"),
    ("Human_Data/TOEFL_gpt4polished_91", "ai", "ai_polished"),
]

HC3_ROWS = "https://datasets-server.huggingface.co/rows"
HC3_CONFIGS = ["open_qa", "reddit_eli5", "finance", "medicine", "wiki_csai"]
HC3_MIN_WORDS = 60  # shorter answers are too little text for any detector


def fetch_liang(rows: list[dict]) -> None:
    for path, label, group in LIANG_SETS:
        r = requests.get(f"{LIANG}{path}/data.json", timeout=60)
        r.raise_for_status()
        docs = r.json()
        for i, d in enumerate(docs):
            text = (d.get("document") if isinstance(d, dict) else str(d)) or ""
            if text.strip():
                rows.append({
                    "id": f"{path.split('/')[-1]}#{i}", "text": text.strip(),
                    "label": label, "group": group, "source": "liang2023",
                })
        print(f"  {path:45s} {len(docs):4d} texts -> {group}")


def fetch_hc3(rows: list[dict], per_config: int = 60) -> None:
    for cfg in HC3_CONFIGS:
        got = 0
        offset = 0
        while got < per_config and offset < 600:
            r = requests.get(HC3_ROWS, params={
                "dataset": "Hello-SimpleAI/HC3", "config": cfg, "split": "train",
                "offset": offset, "length": 100,
            }, timeout=60)
            r.raise_for_status()
            page = r.json().get("rows", [])
            if not page:
                break
            for item in page:
                row = item["row"]
                for label, key, group in (("human", "human_answers", "human_hc3"),
                                          ("ai", "chatgpt_answers", "ai_hc3")):
                    for a in row.get(key) or []:
                        if len(str(a).split()) >= HC3_MIN_WORDS:
                            rows.append({"id": f"hc3/{cfg}/{row['id']}/{label}", "text": str(a).strip(),
                                         "label": label, "group": group, "source": "hc3"})
                            got += 1
                            break
            offset += 100
        print(f"  HC3 {cfg:12s} {got:4d} answers (>= {HC3_MIN_WORDS} words, both classes)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hc3", action="store_true", help="also fetch a sample of HC3 Q&A answers")
    args = ap.parse_args()

    rows: list[dict] = []
    try:
        print("Liang et al. 2023 essays:")
        fetch_liang(rows)
        if args.hc3:
            print("HC3 answers:")
            fetch_hc3(rows)
    except requests.RequestException as exc:
        print(f"Download failed ({type(exc).__name__}: {exc}). Check your connection and retry.", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(rows)} samples to {os.path.relpath(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
