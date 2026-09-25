# Upgrade log

Before/after record of the changes applied in this session: local LM Studio
support for the Summary feature, then Phase 1 (security & data integrity)
and Phase 2 (robustness) of the upgrade roadmap.

**16 files touched · 4 new files · 2 phases closed · 6 verification checks run, 0 failed**

---

## Feature — Local LM Studio for the Summary feature

The Summary tab's semantic layer (title, overview, key takeaways) was
Gemini-only — 20 requests/day on the free tier. It now tries a local LM
Studio server first: free, offline, no daily cap. Gemini remains the
automatic fallback if LM Studio isn't running or the call fails, so nothing
breaks for anyone who hasn't set it up.

### `backend/app/gemini_summarizer.py` — edited

Added LM Studio as a provider, tried before Gemini. Uses `requests` directly
against LM Studio's OpenAI-compatible `/v1/chat/completions` endpoint — no
new dependency — and reuses the existing `GeminiResult` schema and
number-grounding guard, so a locally-generated summary is validated exactly
as strictly as a Gemini one.

```diff
 def is_configured() -> bool:
-    return _SDK_AVAILABLE and gemini_keys.is_configured()
+    return _lmstudio_configured() or (_SDK_AVAILABLE and gemini_keys.is_configured())

+def _call_lmstudio(prompt: str) -> GeminiResult | None:
+    resp = requests.post(f"{LMSTUDIO_BASE_URL}/chat/completions", ...)
+    payload = OpenAICompatDetector._extract_json(content)
+    return GeminiResult.model_validate(payload)   # any failure -> None, falls back to Gemini

 def _call():  # inside enhance_summary()
+    if _lmstudio_configured():
+        result = _call_lmstudio(prompt)
+        if result is not None: return result   # else fall through to Gemini
```

### `backend/.env.example` — edited

Documented the two new variables, with instructions on where LM Studio
shows the exact model id to copy.

```diff
+# LMSTUDIO_MODEL=
+# LMSTUDIO_BASE_URL=http://localhost:1234/v1
```

---

## Phase 1 — Security & data integrity

Lowest-effort, highest-value items first: things that could leak, break, or
drift silently.

### `backend/app/db.py` — edited

Every request opened a fresh SQLite connection with no lock timeout —
concurrent writes could throw `database is locked`. Added a 30s wait and
WAL mode, which lets reads proceed while a write is in flight instead of
blocking the whole file.

```diff
 _ensure_dirs()
-conn = sqlite3.connect(DB_PATH)
+conn = sqlite3.connect(DB_PATH, timeout=30)
 conn.row_factory = sqlite3.Row
 conn.execute("PRAGMA foreign_keys = ON")
+conn.execute("PRAGMA journal_mode = WAL")
```

### `backend/app/pdf_report.py` — edited

Four spots inserted user-submitted or AI-generated text straight into
ReportLab's mini-XML `Paragraph` markup with no escaping — flagged-section
quotes, explanations, image indicators, and the raw extracted-text preview
(the biggest one: your own document's content, verbatim). A stray `<` or
`&` could break the report layout. All four now go through
`xml.sax.saxutils.escape()` first, matching the pattern already used for
similarity source names.

```diff
-story.append(Paragraph(f"&ldquo;{sec.get('text', '')}&rdquo;", _body))
+story.append(Paragraph(f"&ldquo;{escape(str(sec.get('text', '')))}&rdquo;", _body))
 ...
-story.append(Paragraph(preview.replace("\n", "<br/>"), _muted))
+story.append(Paragraph(escape(preview).replace("\n", "<br/>"), _muted))
```

### `backend/requirements.txt` — edited

Every dependency was an open-ended `>=` — a transitive major bump (numpy's
ABI break, a transformers API change) had no ceiling and could silently
break a fresh install. Pinned to exactly what's installed and tested in
`backend/.venv`.

| package | before | after |
|---|---|---|
| torch | `>=2.9.0` | `==2.13.0` |
| transformers | `>=4.47.0` | `==5.16.1` |
| fastapi | `>=0.115.0` | `==0.141.1` |
| numpy | `>=2.0.0` | `==2.5.2` |
| google-genai | `>=1.0.0` | `==2.20.0` |
| sentence-transformers | `>=3.0.0` | `==6.0.0` |
| + 10 more | `>=…` | exact pin |

### `frontend/src/components/layout/TopBar.jsx` — edited

The API-docs link had `127.0.0.1:8000` baked in. Now reads an env var, with
that same address as the fallback — no behavior change today, but the app
no longer ships a hardcoded address if it's ever pointed at a different
backend.

```diff
-href="http://127.0.0.1:8000/docs"
+href={`${import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000"}/docs`}
```

### `frontend/.env.example` — new file

Documents `VITE_API_BASE`, and notes that every actual API call already
goes through Vite's same-origin dev proxy — this variable is only for that
one docs link.

### `frontend/eslint.config.js` — new file

No linter existed at all, despite an `eslint-disable-line` comment in the
code referencing one. Added a flat ESLint config with `react-hooks` +
`react-refresh` plugins, installed the packages, and ran it: **0 errors**,
4 pre-existing unused-variable warnings left untouched.

---

## Phase 2 — Robustness

Things that would misbehave under real concurrent load or a flaky network,
rather than in a single-user dev session.

### `backend/app/main.py` — edited

PDF/DOCX/PPTX parsing is CPU-bound and was called synchronously inside
`async def` route handlers — it blocked the event loop, stalling every
other in-flight request during a large upload. Both call sites now run off
the event loop.

```diff
-pipeline = run_detection_pipeline(filename, data)
+pipeline = await asyncio.to_thread(run_detection_pipeline, filename, data)
 ...
-text = _extract_by_filename(data, filename, join_bullets=False)
+text = await asyncio.to_thread(_extract_by_filename, data, filename, join_bullets=False)
```

### `backend/app/scoring.py`, `embeddings.py`, `detectors/binoculars.py` — edited (×3)

Each lazy-loads a model into a singleton on first use with a plain
`if self._model is not None: return` check — no protection against two
concurrent first requests both racing past that check and each loading
their own copy into memory. Added double-checked locking with
`threading.Lock` to all three.

```diff
 def load(self) -> None:
     if self._model is not None: return
+    with self._load_lock:
+        if self._model is not None: return
         self._model = AutoModelForCausalLM.from_pretrained(...)
```

### `frontend/src/components/common/ErrorBoundary.jsx` — new file

No error boundary existed anywhere — a render-time exception in any single
tab blanked the entire app. Added a class component (React has no hook
equivalent for `componentDidCatch`) that catches locally and resets
automatically when the user switches tabs.

```diff
 export default class ErrorBoundary extends Component {
+  static getDerivedStateFromError(error) { return { error }; }
+  componentDidUpdate(prev) {
+    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null });
+  }
```

### `frontend/src/App.jsx` — edited

Wrapped just the active surface, not the whole shell — so if a tab
crashes, the top bar and side nav stay usable and the user can navigate
away.

```diff
 <div key={surface} className="animate-rise">
-  <Surface onNavigate={navigate} />
+  <ErrorBoundary resetKey={surface}>
+    <Surface onNavigate={navigate} />
+  </ErrorBoundary>
 </div>
```

### `backend/app/gemini_keys.py` — edited

A quota error (429) already rotated to the next API key — but a transient
blip (a dropped connection, a 5xx) failed the whole call outright with no
retry. Added a short retry-with-backoff on the *same* key for transient
errors only. Deliberately excluded: a request that already timed out
(retrying after burning a 25-90s budget once isn't worth it — move to the
next key instead) and anything that looks permanent (bad key, bad request,
model not found), which still fails immediately.

```diff
 except Exception as exc:
-    if not is_quota_error(exc): raise
-    _mark_exhausted(key); last_exc = exc
+    if is_quota_error(exc): _mark_exhausted(key); last_exc = exc; break
+    if _is_permanent_error(exc): raise
+    last_exc = exc
+    if _is_timeout_error(exc) or attempt == len(_RETRY_BACKOFF_S): break
+    time.sleep(_RETRY_BACKOFF_S[attempt])   # 0.5s, then 1.5s
```

### `backend/app/detectors/registry.py` — edited

The whole parallel batch of hosted detectors had a hard 120s ceiling.
Every provider already enforces its own timeout (25-90s), so 120s was just
a generous backstop — lowered the default to 60s and made it configurable,
in case a future provider needs more room.

```diff
-def run_all(text: str, timeout: float = 120.0, ...):
+_DEFAULT_TIMEOUT_S = float(os.environ.get("DETECTOR_TIMEOUT_S", "60"))
+def run_all(text: str, timeout: float = _DEFAULT_TIMEOUT_S, ...):
```

---

## Decision log

Two points where the right answer depends on how you actually use the app,
not just the code.

**Should `/history/{id}` and `/report/{id}` require auth?**
Anyone who can reach the backend can read or delete any entry by its
numeric id — there's no user concept anywhere in the app. **Left as-is**,
per your call: this runs locally on 127.0.0.1 for one person, so building
auth infrastructure now would be effort spent on a risk that doesn't apply
yet. Worth revisiting the moment this gets deployed anywhere reachable by
more than you.

**What to tackle after Phase 1?**
Chose **Phase 2 first, then the accuracy work** (eval harness + a stronger
perplexity backbone) — robustness fixes are smaller and lower-risk, and
finishing them first keeps the model-swap work isolated as its own pass.

---

## Verified — what was actually run, not just written

- [x] Every edited Python file passed `py_compile` individually
- [x] `db.init_db()` executed against the real project venv — WAL mode applies cleanly
- [x] `import app.main` succeeds end-to-end after all backend edits (full dependency graph loads)
- [x] `npm run lint` — 0 errors, 4 unrelated pre-existing warnings, untouched
- [x] `npm run build` — production bundle builds clean (680KB single-chunk warning noted, that's a Phase 4 code-splitting item, not a regression)
- [x] `npm audit --omit=dev` — 0 vulnerabilities in anything actually shipped to users
- [x] Backend (`uvicorn`, port 8000) and frontend (`vite`, port 5173) both started and responded (`/health` → `{"status":"ok"}`, `/` → `200 OK`)

---

## Next up

**Phase 3 — Architecture**
- Split `main.py` into `routers/` + `schemas.py`
- Centralize env config with `pydantic-settings`
- Shared `useAnalysisTab` hook (Text/Code/Image/File tabs are ~90% identical)
- Structured logging with request IDs

**Phase 4 — Performance**
- `React.lazy` code-splitting per tab
- Batch sentence-perplexity scoring
- Cached/ANN lookup for the reference corpus

**Accuracy — chosen direction**
- Build an eval harness (precision/recall/F1, tracked per change)
- Swap the DistilGPT-2 backbone for a stronger reference model
- Binoculars already tried at CPU scale — measured not separable (see its
  own module docstring); would need a much larger model pair to reconsider
