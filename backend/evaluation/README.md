# Detector evaluation

A ruler for the AI-text detectors: run it before and after changing a detector
or a threshold and see whether the change helped, instead of judging by eye.

```bash
cd backend
python evaluation/fetch_datasets.py                 # once: downloads ~840 labelled texts
python evaluation/evaluate.py                       # local detector, 25 texts per group (~3 min)
python evaluation/evaluate.py --full --robustness   # everything + the appended-sentence test (~25 min)
python evaluation/evaluate.py --hosted groq --hosted-limit 12 --groups human_non_native,ai_plain
                                                    # a hosted detector — spends free-tier quota
```

The data is downloaded to `evaluation/data/` and results are written to
`evaluation/results/`; both are git-ignored (the data belongs to its authors).
Sources: Liang et al., *GPT detectors are biased against non-native English
writers* (Patterns, 2023, MIT-licensed) and, with `--hc3`, HC3.

## What it measures

The number that matters in a classroom is the **false-positive rate**: how often
genuine human writing is called AI. It is reported per group with a 95% Wilson
interval, because a few dozen essays cannot support "3.2%" — the interval shows
what the sample can and cannot say. Calls use the app's own thresholds
(`app/detectors/base.py`): score ≥ 60 is "AI", ≤ 40 is "human", in between is
"uncertain" (an abstention: neither a hit nor a false alarm).

Groups: `human_non_native` (real TOEFL essays), `human_student`, `human_college`,
`human_academic`, and AI text: `ai_plain` (GPT-3), `ai_evasive` (GPT-3
prompt-engineered to sound human), `ai_polished` (the TOEFL essays rewritten by
GPT-4).

## Baseline — local statistical detector, 2026-09-20, all 837 texts

| Group | n | Called AI | 95% CI | Uncertain | Called human |
|---|---:|---:|---:|---:|---:|
| human_academic | 145 | 0.0% | 0–3% | 14.5% | 85.5% |
| human_college | 70 | 0.0% | 0–5% | 14.3% | 85.7% |
| human_student | 88 | 0.0% | 0–4% | 6.8% | 93.2% |
| **human_non_native** | 91 | **8.8%** | **5–16%** | 67.0% | 24.2% |
| ai_plain | 176 | 61.9% | 55–69% | 31.8% | 6.2% |
| ai_evasive | 176 | 12.5% | 8–18% | 48.9% | 38.6% |
| ai_polished | 91 | 14.3% | 9–23% | 50.5% | 35.2% |

AUROC 0.83. False-positive rate 2.0% overall — a figure that hides the
concentration: **every one of the 8 false positives is a non-native writer**.

* **It is not a length effect.** In the same 60–150-word range, native writers
  scored a mean of 24.9 (0 of 64 called AI, 89% cleared) and non-native writers
  46.7 (8 of 91 called AI, 24% cleared). A minimum-length rule would only have
  hidden this, because every non-native essay in the data is short.
* **A higher threshold does not fix it.** At ≥ 75 no human is flagged, but the
  detector then catches 3.6% of AI text (32.5% at 60).
* **What that means for a verdict.** If 10% of submissions were AI-written (an
  assumed classroom base rate, not a measurement), only about 3 in 10 "Likely
  AI" calls on non-native writers would be correct. So `registry.headline()` does
  not let the local detector assert "Likely AI" on its own.
* **Appending one human-sounding sentence** to AI text the detector had caught:
  mean score change −4.2 points, 33% of texts (95% CI 26–41%) no longer called
  AI, none flipped all the way to "human".

### Hosted detector (Groq), small subset — treat as indicative only

48 texts requested, 40 scored by both detectors (some Groq calls did not
return). Groq caught 75% of AI text (92% of the prompt-engineered kind, where the
local detector catches 12%) but flagged 2 of 16 human texts (12.5%, CI 3.5–36%).
The human texts each detector wrongly flagged were **different texts**, and none
was flagged by both — so requiring the detectors to agree gave 0 of 16 false
accusations (against 3 of 16 for "either detector"), at the cost of catching 25%
of AI text. That is consistent with agreement being a safer basis for a verdict,
not proof of it: 0 of 16 has an upper bound near 19%.

## Limits of this evaluation

* The AI text is GPT-3 / GPT-4 from 2023. Current models may behave differently.
* The non-native set is 91 short TOEFL essays from one prompt style; other
  non-native writing may differ. The intervals above are wide for that reason.
* The hosted subset is tiny. Re-run with larger `--hosted-limit` (mind the
  free-tier quota) before drawing conclusions about any hosted detector.
* Nothing here is a pass/fail gate — it is a measurement.
