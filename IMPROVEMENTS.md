# Detection quality — findings and roadmap

## PASS 3 — Trustworthy verdicts, a measuring stick, external sources, provenance

Full numbers and caveats: `backend/evaluation/README.md`. Tests added:
`test_analyze_endpoint.py` (28 checks) and `test_web_sources.py` (50); the
five older suites are unchanged and still pass (93). Everything below was found
by driving the running app, not by reading code.

### Bugs fixed (each has a regression check)

| Found | Cause | Fix |
|---|---|---|
| An identical paste was invisible to plagiarism | `/analyze` excluded its own content hash, but similarity runs *before* the text is stored, so the exclusion only hid earlier copies | Exclusion kept only in `/reduce-overlap`, the one place that needs it |
| Every analysis made two Gemini calls | The legacy panel and the "gemini" detector each called it for the same text — half the free quota | One call, reused; Gemini, similarity and hosted detectors now run concurrently |
| "Likely Human" headline while Groq said 70% AI, and a note claiming the second opinion "didn't run" | Headline came from the local score alone; the note tested only the legacy Gemini field | Headline from `detectors.registry.headline()`; result page shows every detector |
| CORS echoed any origin back with credentials allowed | `allow_origins=["*"]` + `allow_credentials=True` | Dev origins only, no credentials, plus a Host check against DNS rebinding |
| Image-failure copy said the image "was not stored or shared anywhere" | It had already been sent to Google when the 429 came back | Copy now says so |
| `/analyze` returned 500 if no "gemini" detector was registered | `_assemble_detectors` assumed it | Skips it |

### The finding that changed the design

Measured on 837 labelled texts (91 are TOEFL essays by non-native writers):
the local detector called **8.8% of non-native essays AI (CI 5–16%) and 0% of
native writing**, at equal length (mean score 46.7 vs 24.9). It is not a length
effect and no threshold fixes it (at ≥75 it flags no humans but catches 3.6% of
AI text). So the headline rule is: a directional verdict only when every
detector that ran agrees, and the local detector alone cannot say "Likely AI".
On 40 texts scored by both the local detector and Groq, their false positives
were *different* texts, so agreement produced 0 of 16 false accusations (vs 3 of
16 for "either") — consistent with, not proof of, agreement being safer.

Corrected on the way: the appended-sentence evasion I first saw as 69→40 is
milder on average (−4.2 points; 33% of caught AI texts fall below the line,
none flip to "human").

### Plagiarism: external sources and provenance

`app/web_sources.py` is an opt-in check against Wikipedia and arXiv abstracts:
a few distinctive sentences are searched, the pages found join that one
request's comparison under the same semantic-plus-lexical verification, and
nothing is stored. Every page compared is listed with its URL; "nothing found"
is worded as "not found among the sources checked".

The **live** run found two things the fake-network tests could not:
Wikipedia answered a burst of ~10 parallel requests with 429 (its etiquette asks
for serial requests), and — worse — when Wikipedia failed but arXiv returned an
empty feed, the result read "no matching pages found on Wikipedia and arXiv",
a failure passed off as a clean result. Requests are now serial per provider,
a 429 stops further requests to that provider, responses are cached for 10
minutes, and each provider's outcome is tracked separately so one answering
"nothing" can never hide that the other could not be reached.

Matches now say where they came from: an earlier submission by name and date
(with a link to its history record, `#history/<id>`), or an external page by URL.

### Known limits (not solved here)

* Coverage is Wikipedia and arXiv *abstracts* only — not the wider web, paywalled
  papers, or other people's work outside this app.
* Live check against the real APIs (the intro of a real article): a verbatim
  copy was found and 100% verified; a lightly reworded copy was also found
  (88% word / 85% trigram overlap) via the looser fallback query, which also
  dragged in three unrelated articles — so that query now keeps only its top hit.
  A heavier rewrite that no search surfaces will simply not be found.
* Wikipedia still rate-limits anonymous use after roughly ten requests in quick
  succession (three checks in ~20 s hit it). A check made in that state says so
  ("Wikipedia rate limited, so it was not checked") instead of reporting clean.
  Setting `EXTERNAL_SOURCES_CONTACT` in `.env` identifies the client politely.
* The evaluation data is 2023-era GPT text; the hosted-detector sample is small.
* Text length: a 31 KB paste takes ~43 s and a 250 KB one over 3 minutes; there
  is still no input cap or background job queue.

## PASS 2 — Similarity/plagiarism accuracy, embedding benchmark, verified rewrite

This pass continues directly from Pass 1 below (same windowing fix, same
eval corpus, same "never fabricate a score" discipline). It does not touch
Summary, AI image detection, or the Gemini key. Nothing here re-enables
Binoculars — it is still disabled, unchanged.

Corpus grew from 12 to 16 fixtures. Four were added because the existing set
had no case for the exact failure Goal 2 warned about — nothing tested
"same topic, independently written" against a real source, and nothing sat
between "verbatim" and "adversarially perfect paraphrase" on the realism
spectrum:

```
samples/eval/14_same_topic_independent.txt      same subject as 01, no copying, different facts
samples/eval/15_copy_light_modified.docx        near-verbatim, a handful of word swaps
samples/eval/16_copy_paraphrased_moderate.docx  realistic reworded copy — most plagiarism looks like this
samples/eval/03_copy_paraphrased.docx           (pre-existing) adversarial full rewrite, kept as the hard case
```

Reproduce everything below:

```bash
cd backend
python test_similarity_eval.py         # plagiarism engine, isolated DB — 25 checks
python test_originality_rewrite.py     # verified rewrite loop, isolated DB — 23 checks
python test_embedding_benchmark.py     # 3-model comparison on identical data
python test_detection.py               # unaffected — 13 checks
python test_new_features.py            # unaffected — 21 checks
```

### Baseline (recorded before any change in this pass)

```
test_similarity_eval.py : 14/14
test_detection.py       : 13/13
test_new_features.py    : 21/21
```
Same numbers `IMPROVEMENTS.md` already reported for Pass 1 — confirmed
fresh, not assumed. One number in that baseline run was a live warning
sign, not a failure: **human academic prose scored 42.3% against the 45%
match threshold — 2.7 points of margin.** That crack is exactly what this
pass's evidence traces back to a real bug, not noise.

### Goal 4 first: what is the actual bottleneck

Built `test_embedding_benchmark.py` and ran the current model plus two
candidates against every fixture, using the SAME windowing code the
production pipeline uses (imported, not reimplemented):

**Current model performance** — `sentence-transformers/all-MiniLM-L6-v2`:
weakest genuine-copy score 78.3%, worst false-positive (same-topic
independent writing) 80.9% → **margin −2.6pt (already broken)**. 87MB,
23ms/window.

**Candidate model performance**:
- `sentence-transformers/all-mpnet-base-v2` (larger, historically stronger
  on STS benchmarks): weakest-copy 78.1%, worst-clean 85.6% → **margin
  −7.5pt — WORSE than current**. Also 418MB and 138ms/window, 6× slower.
- `BAAI/bge-small-en-v1.5` (same size class, newer training): weakest-copy
  92.0%, worst-clean 89.0% → margin **+2.9pt on this one measure**, but it
  achieves that by inflating cosine for EVERYTHING — unrelated document
  63.6%, human academic prose 82.3%, an 1863 speech 66.0%, an 1813 novel
  58.4%. All four would sit above the 45% match threshold. This is a
  retrieval-tuned model doing what it was trained for (rank plausible
  candidates high) applied to a task that needs the opposite (reject
  implausible ones outright).

**Decision: Keep `all-MiniLM-L6-v2`.** Neither candidate is an improvement.
mpnet is slower, larger, and measurably worse at the one thing that matters.
bge-small would turn the false-positive problem into a false-positive
catastrophe. The bottleneck was never the encoder.

### Goal 1 + 2: the real bottleneck and its fix

The embedding benchmark proved it structurally: at **every** embedding
model tested, "independently written on the same topic" scores as high or
higher than the weakest genuine copy. No amount of swapping encoders fixes
that, because it isn't an encoder problem — cosine similarity measures
semantic closeness, and two pieces of writing about the same narrow topic
are, correctly, semantically close. That is not a flaw to patch out of the
embedding; it is the wrong question being asked of it alone.

**Fix: corroborate every candidate match with lexical evidence before
"strongly flagging" it** (word Jaccard overlap + trigram containment,
computed only for candidates that already cleared the cosine floor — cheap,
pure Python, no new dependency). Floors picked from measured data, not
guessed:

| Case | word overlap | 3-gram containment |
|---|---|---|
| Verbatim / light edits | 97–100% | 94–100% |
| Realistic reworded copy | 32% | 11% |
| Genuinely-copied patchwork span | 19–67% | 18–84% |
| **Same-topic, independently written** | **15%** | **1%** |
| Unrelated / academic / classics | 6–12% | 0% |

`word_jaccard ≥ 25% OR 3gram_containment ≥ 15%` sits in the gap between the
weakest real copy and the strongest false-positive candidate, with several
points of margin on both sides — separating **every** copy case from
**every** clean case in the corpus except one (see "known limitation"
below).

A match is now `verified` (semantic + lexical corroboration) or reported
separately as topical/`possible` (semantic only, explicitly hedged, never
counted as "copied"). Two new headline numbers replace relying on raw
cosine alone: `matched_portion` (share of the document with VERIFIED
overlap) and `possible_portion` (share that is merely topically similar).
`top_match` is kept for transparency but is now paired with
`top_match_verified` — the number that used to imply plagiarism on its own
now has to say whether anything backs it up.

**Before → after, same fixtures, real numbers:**

| Document | top_match (before/after — unchanged) | matched_portion (before) | matched_portion (after) |
|---|---|---|---|
| Verbatim copy | 100.0% | 100.0% | 100.0% (unchanged — genuinely all copied) |
| Light-modified copy | 98.3% | 100.0%* | 100.0% (unchanged — genuinely all copied) |
| **Realistic paraphrase (new)** | 90.6% | *(field didn't exist)* | **40.0%, top_match_verified=True** |
| Patchwork (~40% copied) | 84.4% | 50.0%* | 50.0% (unchanged — correctly partial) |
| **Same-topic independent (new)** | 80.9% | *(would have been ~100% under the old cosine-only rule)* | **0.0%, top_match_verified=False** |
| Unrelated / academic / classics | 5.5–42.3% | 0.0% | 0.0% (unchanged) |

\* Pass-1's `matched_portion` already existed but meant "cosine ≥ 0.45",
which is exactly the number that would have wrongly caught same-topic
writing too — this pass didn't just add a field, it changed what "counts."

This is the concrete fix to the false positive the task specifically
called out: *"Artificial intelligence is changing education" is NOT
automatically plagiarism just because it discusses the same subject as
something on file.* Measured: it no longer is. `matched_portion` goes to
0%, `top_match_verified` is `False`, and the response carries an explicit
hedge: *"High topical similarity found, but no matching phrasing was
verified — this can indicate a shared subject rather than copied content."*

**Known limitation, disclosed rather than hidden:** an adversarially
thorough paraphrase that replaces every content word (`03_copy_paraphrased`,
kept in the corpus specifically as this hard case) shares 0% trigrams with
its source. Lexical corroboration cannot help there by construction — there
is nothing lexical left to corroborate. It still surfaces as a
high-cosine, *unverified* match (85.2%, hedged, not hidden) rather than
being silently dropped, and in practice about 20% of even this extreme case
still clears verification because a rewrite that thorough is very hard to
sustain across an entire document. No published technique separates this
exact case from same-topic writing using signals this cheap; that is
reported as a real, measured ceiling, not solved.

Frontend surfacing (`SimilarityPanel.jsx`, `TextResultPanel.jsx`,
`HistoryDetailPanel.jsx`) was updated to show verified vs. topical overlap
as two separate bars with distinct badges, and history storage
(`similarity_score` on the `history` table) now stores the verified figure
instead of raw cosine — so the History list and the dashboard's average
don't silently inherit the same false-positive risk the detail view no
longer has.

### Goal 3: verified rewrite (`app/originality_rewriter.py`, new)

Tested the obvious first move — reusing `humanizer.py`'s existing
word-substitution rewriter (built for lowering the AI-*detector* score, not
overlap) directly on flagged passages — **before writing anything new**, as
required. Measured result: it touched only 5/14 and 1/6 sentences on the
light-modified and moderate-paraphrase fixtures (most factual prose
contains none of its listed AI buzzwords) and moved verified overlap by
**0.0 percentage points** in every case tried. Confirmed: not fit for this
job, reused nothing further from it beyond the per-sentence primitive.

Added sentence-order shuffling and clause-order swapping within each
flagged passage, on top of that same word-substitution primitive. Tested
this second hypothesis the same way: it moved verified overlap by **−16.7pt
and −23.3pt** on two fixtures — but made a third one **worse** (+3.9pt).
One blind transform is not reliably an improvement. That result is exactly
why the shipped implementation never trusts a single attempt: it generates
up to 3 bounded candidates, re-runs the real `analyze_similarity()` on each
one, and keeps only a candidate that is a measured improvement over the
original — never a candidate that merely looks different, and never more
than 3 tries.

Pipeline as built, matching the requested shape exactly:

```
text -> analyze_similarity()                (existing, unmodified)
     -> locate contiguous VERIFIED runs      (possible/topical text is never touched)
     -> up to 3 candidate rewrites           (reorder + clause-swap + word substitution)
     -> analyze_similarity() on each         (real re-check, not estimated)
     -> keep the strictly-better candidate, or the untouched original if none improve
```

**Before → after, measured, `test_originality_rewrite.py`:**

| Document | matched_portion before | matched_portion after | attempts | improved |
|---|---|---|---|---|
| Verbatim copy | 100.0% | 100.0% (top_match 100.0%→77.1%) | 3 | true (peak score dropped; the fully-verified span itself is real and inherently hard to hide) |
| Light-modified copy | 100.0% | 80.0% | 3 | true |
| Realistic paraphrase | 40.0% | 0.0% | 1–3† | true |
| Patchwork | 50.0% | 25.0% | 3 | true |
| Same-topic independent | 0.0% | 0.0% (0 attempts made) | 0 | correctly declines — nothing verified to fix |

† Bounded-attempt outcomes vary run to run for this fixture specifically —
it has only one flagged sentence run, giving little room to reorder, so
sometimes 1 of 3 attempts clears it and sometimes none do within the bound.
When none succeed, the tool returns the untouched original and says so
plainly rather than claiming an improvement that didn't happen. This
variability is itself evidence the safety check is real, not decorative.

A genuine formatting bug was caught by this testing, not shipped: the
clause-swap transform initially produced `"...goes down, , dark roofing..."`
— a stray leading comma dragged along from the regex match span. Fixed by
capturing the conjunction word in its own group instead of re-slicing the
full match. Covered by a dedicated regression check
(`test_originality_rewrite.py`: "no double-comma artefacts").

A second real bug surfaced during live (non-isolated-DB) testing, not
caught by the regression suite because that suite correctly uses a fresh
database every run: pasted text is stored under the literal display label
`"Pasted text"` for every submission, so calling `/analyze` and then
immediately `/reduce-overlap` on the *same* pasted text — the natural next
click — made the second call self-match against the copy the first call
had just stored. Fixed with `_pasted_text_tag()`: a content-hash identifier
used only for corpus tagging/exclusion, never shown as the history
display name (which stays "Pasted text"). Verified live: analyzing fresh
text then immediately requesting a rewrite now correctly reports 0%
matched_portion in both calls, not a spurious self-match.

New endpoint: `POST /reduce-overlap` (`{text, file_name?}` →
`{rewritten, changed, improved, attempts_tried, before, after, note}`).
No new frontend UI was built for it — the task explicitly scoped frontend
work to "necessary for measurable detection quality," and this is a
backend capability that is fully tested and independently verifiable
through the API; wiring a button is a small, separate follow-up if wanted.

### Full regression tally, this pass

```
test_detection.py            13/13  (unchanged — untouched code)
test_new_features.py         21/21  (unchanged — untouched code)
test_similarity_eval.py      25/25  (was 14 — 11 new checks for Goals 1/2)
test_originality_rewrite.py  23/23  (new file — Goal 3)
─────────────────────────────────────────────────────────────
TOTAL                        82/82
```

Live end-to-end verification (not just isolated-DB unit tests): restarted
the real backend, hit `/analyze` and the new `/reduce-overlap` over actual
HTTP with fixtures that had never touched the persistent `history.db`,
confirmed the JSON response carries `top_match_verified`, `matched_portion`,
`possible_portion`, and per-match `word_overlap`/`ngram_overlap`/`verified`
end-to-end, and confirmed the self-match fix holds for genuinely new
content submitted through the real API, not just the test harness.

### Files changed, this pass

```
backend/app/similarity.py              corroboration signals, verified/possible split
backend/app/originality_rewriter.py    new — verified rewrite loop
backend/app/main.py                    new fields wired through; /reduce-overlap;
                                        pasted-text self-match fix; history stores
                                        verified overlap instead of raw cosine
backend/test_similarity_eval.py        extended: 14→25 checks
backend/test_originality_rewrite.py    new: 23 checks
backend/test_embedding_benchmark.py    new — reusable for re-benchmarking later
samples/eval/14_15_16_*                new fixtures (see above)
frontend/.../SimilarityPanel.jsx       verified vs. possible overlap, shown separately
frontend/.../TextResultPanel.jsx       headline number is verified overlap, not raw cosine
frontend/.../HistoryDetailPanel.jsx    same headline fix, for consistency
```

No changes to: `app/summarizer.py`, `app/gemini_summarizer.py`,
`app/image_detector.py`, `app/humanizer.py` (reused, not modified),
`app/detectors/` (Binoculars still disabled, untouched), any Gemini
credential path, or any frontend page outside the three listed above.

### What's next, evidence-ranked

- **Corpus growth**: windowing roughly doubles chunks per document, and
  `MAX_REFERENCE_CHUNKS` is still 20,000 (unchanged this pass). Not yet a
  problem; worth a pruning strategy before it is.
- **Content-hash self-exclusion for uploaded files, not just pasted text**:
  today's fix covers pasted text specifically (the gap this pass found);
  the existing filename-based exclusion for uploads is coarser (two
  different files with the same name would incorrectly exclude each
  other) but was not in scope for this pass's testing and not measured as
  an active problem.
- **The verbatim-copy ceiling**: even after rewriting, a fully-copied
  document couldn't be pushed below 100% matched_portion in testing — every
  sentence in it was genuinely, entirely copied, so restructuring alone
  (without changing content) has an honest limit. This is correct behavior,
  not a bug: the tool should not be able to launder a wholesale copy into
  something that reads as original.

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
