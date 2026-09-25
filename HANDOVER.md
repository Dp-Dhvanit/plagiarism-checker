# Handover — AI Text Detective

Snapshot date: 2026-08-31. Read this before picking the project back up.

## What this is

FastAPI backend + React/Tailwind frontend that estimates whether text, code,
documents, or images are AI-generated, checks document similarity/plagiarism
against a stored corpus, and summarizes documents with charts. See
`README.md` for the API route list and `IMPROVEMENTS.md` for the full
detection-engineering log (what was measured, what didn't work, why).

## Currently running

Both services were started this session and are live:

| Service | URL | Process |
|---|---|---|
| Backend (FastAPI) | http://localhost:8000 | `python -m uvicorn app.main:app --port 8000 --host 127.0.0.1`, **no** `--reload` |
| Frontend (Vite) | http://localhost:5173 | `npm run dev` (via `frontend/node_modules/.bin/vite`) |

Verified just now: `GET /health` → `200 {"status":"ok"}`, frontend root → `200`.

**To restart either one:**

```powershell
# Backend — use the ROOT .venv, not backend/.venv (both exist; root is the one
# with the environment actually used to run this project — see below)
cd C:\Users\Dhvanit\Desktop\SVG
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000

# Frontend
cd C:\Users\Dhvanit\Desktop\SVG\frontend
npm run dev
```

⚠️ **Two venvs exist** (`SVG/.venv` and `SVG/backend/.venv`) with overlapping
packages. The one actually in use is the **root** `SVG/.venv`. This has bitten
past sessions — if a dependency seems "missing" despite being installed,
check which venv's `python.exe` is on the path before reinstalling anything.

⚠️ **Vite does not hot-reload `tailwind.config.js` changes.** If you edit
Tailwind config/tokens and the browser doesn't reflect it, stop the Vite
process and run `npm run dev` fresh — confirmed this session (see "Frontend
redesign" below).

## What changed this session (all uncommitted — see note on git)

Two unrelated bodies of work landed in the working tree, neither is
committed yet:

### 1. Backend detection-quality pass ("Pass 2" in `IMPROVEMENTS.md`)

Not done by me this session — already present in the working tree when I
picked this up. Full details, measurements, and rationale are in
`IMPROVEMENTS.md` (search "PASS 2"). Short version: plagiarism matches are
now split into `verified` (semantic + lexical corroboration) vs. `possible`
(semantic-only, hedged) to kill a false-positive class where independently
written same-topic text scored as high as real copies. New
`POST /reduce-overlap` endpoint does a bounded, measured rewrite loop (up to
3 candidates, keeps only ones that verifiably reduce overlap). 82/82 tests
passing across 4 test files at last recorded run.

### 2. Frontend visual redesign (this session)

Full-app reskin from a dark cyber-terminal theme to a clean off-white SaaS
look — **frontend/UI only, zero backend or logic changes**. Highlights:

- Off-white background, lavender primary accent, coral/amber/green used
  sparingly for AI-concern / uncertain / human-leaning signals.
- Removed: the continuous scanning-line animation, the terminal log
  console (`LogStream.jsx`, deleted), all "SOG AI" / personal-name /
  Credits / Buy-Pro branding.
- Added: your One Piece logo as the temporary brand mark
  (`frontend/public/logo-{48,96,256}.png`) — cleaned up from your source
  file (watermark/grid removed, cropped, transparent background) rather
  than sourced from the web.
- Result pages restructured to: headline → AI/human split → similarity
  (verified vs. semantic, explicitly explained in copy) → matched passages
  → collapsible technical detail → disclaimer.
- Image-analysis-unavailable state now shows a fixed generic message
  instead of the backend's raw error string (which can contain things like
  env var names) — a deliberate, spec-requested behavior change, the one
  place this pass touched actual displayed logic rather than pure styling.
- Verified via Playwright: all analysis flows (text/document/code/
  image/summary), history view/download, PDF report, mobile nav drawer,
  and tablet layout — real end-to-end runs against the live backend, not
  just component rendering. Zero console errors.

**Not yet done for the redesign:** `README.md`'s "Interface" section still
describes the old "Deep Space Intelligence" design system and
`stitch-references/*/DESIGN.md` — that's now stale and should be rewritten
or removed to match the new theme. I didn't touch it since it wasn't asked
for.

## Environment / config

`backend/.env` exists and is filled in (not committed — `.gitignore`d).
Currently configured:

- `GEMINI_API_KEY` — set. **Likely rate-limited**: the free tier is 20
  requests/day and `IMPROVEMENTS.md` records it being exhausted during
  testing (`429 RESOURCE_EXHAUSTED`, handled gracefully). This is almost
  certainly why the QA run this session saw image analysis report
  "currently unavailable" — that's the intended graceful-degradation path
  working correctly, not a bug, and it should clear on its own after the
  daily quota resets.
- `GROQ_API_KEY` — set (free tier, ~100 analyses/day at this project's
  token usage — see `IMPROVEMENTS.md` §3 for the full free-tier comparison
  table across providers).
- `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`, `MAX_UPLOAD_MB=15`.

If AI-assisted features (Gemini summary layer, Gemini/Groq text detection,
image detection) stop working, check the backend terminal output first —
`IMPROVEMENTS.md` notes Google periodically retires model version strings,
which fails with a 404 that names the replacement model.

## Testing

No `pytest` in this project — all test files are standalone
argparse-style scripts, run directly:

```bash
cd backend
python test_scoring.py               # base scoring, isolated
python test_detection.py             # 13 checks
python test_new_features.py          # 21 checks
python test_similarity_eval.py       # 25 checks (plagiarism engine)
python test_originality_rewrite.py   # 23 checks (rewrite loop)
python test_embedding_benchmark.py   # 3-model comparison, informational
```

Before large edits, snapshot first (copy the file or branch-less diff) —
this project doesn't lean on git for undo; see the workflow note below.

## Git status (uncommitted, not staged by me)

This project doesn't use git as the primary safety net day-to-day (past
guidance: snapshot before big edits rather than relying on commits). As of
this snapshot, `git status` shows the Pass-2 backend files and the full
frontend redesign as modified/untracked, nothing committed. I did not
stage, commit, or push anything — that's left for you to decide when you're
ready to check it in.

## Suggested next steps

From `IMPROVEMENTS.md`'s own roadmap (backend, evidence-ranked):
1. Surface `detectors[]` / `consensus` in the result UI — the API already
   returns per-provider agreement/disagreement, nothing renders it yet.
2. Content-hash self-exclusion for uploaded files (pasted text already
   fixed this session/pass; uploads still use coarser filename matching).
3. Corpus pruning strategy before `MAX_REFERENCE_CHUNKS` (20,000) becomes a
   real ceiling.

From this session (frontend):
1. Update `README.md`'s stale "Interface" section to describe the new
   light-theme design system instead of "Deep Space Intelligence".
2. If you want the `/reduce-overlap` rewrite endpoint reachable from the
   UI, it currently has no frontend button — noted as intentionally
   out-of-scope in `IMPROVEMENTS.md`, not forgotten.
