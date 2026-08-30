"""
Test perplexity + burstiness scoring in isolation (no API / UI).

Usage:
  python test_scoring.py
  python test_scoring.py --text "Your paragraph here..."
  python test_scoring.py --sample human
  python test_scoring.py --sample ai
  python test_scoring.py --model gpt2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from backend/ without installing as a package
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.scoring import get_scorer

SAMPLES = {
    "human": (
        "Okay so honestly I still don't really get why the midterm felt that hard? "
        "Like, I studied the slides twice, maybe three times if you count skim-reading "
        "at 1am with leftover pizza. My roommate kept blasting music and I kept "
        "rewriting the same paragraph about photosynthesis because every time I "
        "tried to sound 'academic' it just came out weird. Anyway — plants make "
        "sugar from light, I think? Wait, carbon dioxide too. Whatever. Point is "
        "I panicked on question 4 and wrote something about chlorophyll that "
        "probably made zero sense. Hope partial credit is a thing."
    ),
    "ai": (
        "Photosynthesis is a fundamental biological process through which plants, "
        "algae, and certain bacteria convert light energy into chemical energy. "
        "During this process, organisms absorb sunlight and utilize it to transform "
        "carbon dioxide and water into glucose and oxygen. Chlorophyll, the green "
        "pigment found in chloroplasts, plays a critical role by capturing light "
        "energy. Overall, photosynthesis not only sustains plant growth but also "
        "supports life on Earth by producing oxygen and forming the base of most "
        "food chains. Understanding this process is essential for students studying "
        "biology and environmental science."
    ),
}


def result_to_dict(result) -> dict:
    return {
        "ai_likelihood_score": result.ai_likelihood_score,
        "perplexity": result.perplexity,
        "burstiness": result.burstiness,
        "verdict": result.verdict,
        "sentence_breakdown": [
            {"sentence": s.sentence, "perplexity": s.perplexity}
            for s in result.sentence_breakdown
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Test AI Text Detective scoring")
    parser.add_argument("--text", type=str, help="Text to analyze")
    parser.add_argument(
        "--sample",
        choices=["human", "ai", "both"],
        default="both",
        help="Run built-in sample(s)",
    )
    parser.add_argument(
        "--model",
        default="distilgpt2",
        help="HuggingFace causal LM id (default: distilgpt2)",
    )
    parser.add_argument(
        "--ppl-weight",
        type=float,
        default=0.5,
        help="Weight for perplexity in combined score",
    )
    parser.add_argument(
        "--burst-weight",
        type=float,
        default=0.5,
        help="Weight for burstiness in combined score",
    )
    args = parser.parse_args()

    print(f"Loading model '{args.model}' (first run downloads weights)...")
    scorer = get_scorer(args.model)
    scorer.load()
    print(f"Ready on device: {scorer.device}\n")

    jobs: list[tuple[str, str]] = []
    if args.text:
        jobs.append(("custom", args.text))
    elif args.sample == "both":
        jobs.extend(SAMPLES.items())
    else:
        jobs.append((args.sample, SAMPLES[args.sample]))

    for label, text in jobs:
        print("=" * 60)
        print(f"SAMPLE: {label}")
        print("-" * 60)
        preview = text[:120] + ("..." if len(text) > 120 else "")
        print(f"Text: {preview}\n")

        result = scorer.analyze(
            text,
            ppl_weight=args.ppl_weight,
            burst_weight=args.burst_weight,
        )
        payload = result_to_dict(result)
        print(json.dumps(payload, indent=2))
        print()


if __name__ == "__main__":
    main()
