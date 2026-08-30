# Detection quality — findings and roadmap

Everything below is measured against `samples/eval/`, a corpus of 12 fixtures
with known provenance (verbatim copies, paraphrases, patchwork copies,
pre-1900 human text, and LLM text in several registers). Reproduce with:

```bash
cd backend
python test_similarity_eval.py     # plagiarism engine, isolated DB
python test_detection.py           # content routing + chunking
python test_new_features.py        # history, PDF, image validation
```

---

## 1. What was fixed

### Plagiarism detection was structurally broken — now works

`_chunk_for_similarity()` passed the whole document to `chunk_prose()` as a
single `Unit`. Because `_chunk_units()` only ever splits *between* units, the
target size was never enforced: **a whole document became one embedding.**
A short copied passage was averaged against everything around it.

Measured dilution before the fix:

| Copied share of document | Whole-doc cosine | Reported? |
|---|---|---|
| 100% | 100.0% | yes |
| 45% | 56.7% | **no** (below 0.60 floor) |
| 29% | 51.7% | **no** |
| 17% | 23.1% | **no** |

Fix: overlapping sentence-aligned windows (60 words, 30-word stride for
queries, no overlap when storing), plus the match floor lowered 0.60 → 0.45.
Unrelated passages measure 5.4% cosine, so the new floor keeps a 39.6-point
safety margin.

After, on the same inputs — every case caught:

| Document | Strongest passage | Share matched | Verdict |
|---|---|---|---|
| Verbatim copy | 100.0% | 100% | correct |
| Paraphrased | 85.2% | 100% | correct |
| **Patchwork ~40%** | **84.4%** | **50%** | **was 55.3% with 0 matches** |
| Unrelated | 21.3% | 0% | correct |
| Human academic | 42.3% | 0% | correct |
| Gettysburg (1863) | 7.3% | 0% | correct |
| Austen (1813) | 13.6% | 0% | correct |

### Other fixes

- **Negative percentages.** Cosine is `[-1,1]`; history had stored `-0.4%`.
  Now clamped at 0.
- **Headline metric was corpus-dependent.** `overall_similarity` is a *mean*
  that rises purely as the archive grows, so an early and a late analysis
  were not comparable. Added `top_match` (strongest single passage) and
  `matched_portion` (share of passages over threshold). Both surfaced in the
  UI; `top_match` is now what history stores.
- **Self-plagiarism bug.** Re-uploading a file reported it as a 100% match
  against its own earlier submission. `analyze_similarity()` now accepts
  `exclude_file_name`, wired through the upload path.

---

## 2. What did NOT work — reported honestly

### Binoculars cross-perplexity: hypothesis rejected

The local detector leans 45% on single-model perplexity, which measures
*vocabulary difficulty*, not authorship. Paraphrasing LLM text into plainer
words moved perplexity 37.8 → 75.9 and collapsed the score 50.4 → 9.2
("Likely Human") while the text was still machine-written.

I implemented Binoculars (Hans et al. 2024) expecting it to fix this. **It did
not.** Three shared-vocabulary pairings, all overlapping:

| Observer + performer | Dynamic range | Separable? |
|---|---|---|
| distilgpt2 + gpt2 | 0.217 | no — scored 2/8 vs heuristic's 3/8 |
| distilgpt2 + gpt2-medium | 0.165 | no (obvious AI only, margin 0.014) |
| gpt2 + gpt2-medium | 0.058 | no |

Two reasons: the published result uses ~7B pairs, and at the 82M–355M scale
that runs on CPU the ratio has almost no dynamic range. Cross-*architecture*
pairs are impossible — Binoculars needs a shared tokenizer (OPT's 50272-token
vocab vs GPT-2's 50257 raises a shape error).

Shipped **disabled by default** (`ENABLE_BINOCULARS=1` to experiment). The
code is correct and worth revisiting on a GPU with larger models.

### The real ceiling

On 6 of 8 known-AI fixtures written in a human register, **every** detector
failed — heuristic 3/8, Binoculars 2/8, Gemini 5/8. This is not a bug in this
project; it is the state of the art. Statistical detectors measure how
machine-like text *reads*, and an LLM told to write messily produces text that
is statistically human.

**Implication: never present an AI score as authoritative.** The UI already
hedges correctly. Keep it that way.

---

## 3. Cost reality (free-tier constraint)

Measured: `gemini-3.6-flash` free tier is **20 requests/day**. Testing
exhausted it and every subsequent call returned `429 RESOURCE_EXHAUSTED`
(handled gracefully — logged, request still returned 200).

That is roughly 20 analyses per day total. For a demo that is fine; for real
classroom use it is not.

**Project rule: nothing registered may cost money.** `_REGISTRY` contains
only free providers, and `available_detectors()` reports a `paid` flag so a
metered provider can never sneak in unnoticed.

Free allowances, checked August 2026:

| Provider | Free allowance | Notes |
|---|---|---|
| **Groq** | **1,000 req/day** (llama-3.3-70b)<br>14,400 req/day (llama-3.1-8b) | No credit card. Best free tier by far. |
| Gemini | 20 req/day | Genuinely free but exhausted in one afternoon of testing. |
| OpenRouter | rotating `:free` model pool | Availability changes; 404 means pick another model. |
| Ollama | unlimited | Fully local and offline. Lower quality, but no cap ever. |
| heuristic + similarity | unlimited | Local, no key, no network. |

Recommended: **Groq as the primary hosted opinion, Gemini as the second.**
Groq alone is 50× Gemini's daily allowance, and running both means neither
cap can take the feature down.

### Deliberately excluded: xAI (Grok)

`app/detectors/grok.py` is written, working, and **not registered**. xAI has
no free tier — only $25 of metered signup credit (~$0.0004/analysis). It is
kept purely as a worked example of subclassing `OpenAICompatDetector`. To
use it you must both set `XAI_API_KEY` and add `GrokDetector()` to
`_REGISTRY`; two deliberate steps, so it cannot start billing by accident.

Paid detector APIs (GPTZero, Originality, Winston) are per-request and far
more expensive. Supported via the template, flagged `paid = True`, none
registered.

---

## 4. Adding a provider

Structure is in `backend/app/detectors/`:

```
base.py           Detector ABC + DetectorResult (never raises out of detect())
registry.py       what runs; run_all() in parallel; consensus() reporting
builtin.py        heuristic + Gemini wrappers
binoculars.py     local cross-perplexity (disabled; see above)
openai_compat.py  base for ANY /v1/chat/completions provider
free_providers.py Groq + OpenRouter + Ollama (all free, all registered)
grok.py           xAI example — NOT registered (no free tier)
http_provider.py  template for non-OpenAI-shaped APIs
```

**OpenAI-compatible provider (easiest — Together, DeepSeek, LM Studio, …):**
subclass `OpenAICompatDetector` and set four attributes:

```python
class GroqDetector(OpenAICompatDetector):
    name, label = "groq", "Groq"
    local, paid = False, False
    env_key  = "GROQ_API_KEY"
    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    model    = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
```

Then add it to `_REGISTRY` and put the key in `.env`. Set `paid = True`
honestly if it is metered — the flag is surfaced to the UI.

**Anything else:** copy `http_provider.py` and fill `_build_request()` /
`_parse_response()`.

Providers without a key self-disable with a clear reason, so the registry is
safe to leave fully populated.

`consensus()` deliberately does **not** average scores into one number.
Detectors that disagree are reported as disagreeing; hiding a 40-point spread
behind a mean would manufacture confidence that does not exist.

---

## 5. Roadmap

### Next (high value, low risk)

- **Surface `detectors[]` and `consensus` in the UI.** The API now returns
  both from `/analyze` and `/upload`; the result page still renders only the
  legacy single `gemini` panel. Showing where providers disagree is the whole
  point of running several.
- **Self-match for pasted text.** The filename exclusion covers uploads;
  pasted text is always stored as `"Pasted text"` so it can still self-match.
  Use a content hash instead of a filename.
- **Corpus growth.** `MAX_REFERENCE_CHUNKS` is 20,000 and windowing roughly
  doubles chunks per document. Add pruning before this matters.

### Then

- **Cut `MARKER_WEIGHT`.** The AI-buzzword list is trivially defeated by
  find-and-replace and contributes 15% of the score. Measure with
  `test_detection.py` before/after.
- **Sentence-level plagiarism highlighting.** The data already exists —
  matched passages carry offsets. Render them inline like the AI heatmap.
- **Cache embeddings by content hash.** Re-analysing the same document
  recomputes every embedding.

### Only with a GPU

- Revisit Binoculars with 1B+ shared-vocab pairs and re-run the benchmark
  before trusting it.

### Explicitly not recommended

- Chasing higher AI-detection accuracy with more heuristics. The measured
  ceiling is a property of the problem. Effort is better spent on the
  similarity engine, which demonstrably works.
