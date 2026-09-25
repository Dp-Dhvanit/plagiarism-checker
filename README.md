# AI Text Detective

Detect whether text, code, or documents were likely written by an AI or a human, and summarize documents with auto-generated charts.

## Project structure

```
SGP/
├── backend/                 # FastAPI + detection engines
│   ├── evaluation/          # Labelled-data ruler for the detectors — see its README
│   ├── app/
│   │   ├── main.py          # API routes (analyze, upload, humanize, detect-code, summarize)
│   │   ├── detectors/        # Local + hosted AI-text detectors and how their opinions combine
│   │   ├── web_sources.py    # Opt-in Wikipedia / arXiv comparison for plagiarism
│   │   ├── scoring.py        # Perplexity + burstiness + AI-marker text scoring
│   │   ├── code_analyzer.py  # AI-code detection signals
│   │   ├── humanizer.py      # Rule-based AI-text rewriter
│   │   └── summarizer.py     # Document/CSV summarizer + chart data
│   ├── test_scoring.py
│   └── requirements.txt
└── frontend/                 # React + Tailwind + Recharts
    └── src/
        ├── App.jsx            # Boot screen -> shell -> surface routing (#hash)
        ├── components/
        │   ├── layout/        # AppShell, TopBar, SideNav, BootScreen
        │   ├── common/        # Design-system primitives (GlassCard, ScoreRing,
        │   │                  #   ScoreBar, DropZone, StatusBadge, Button, ...)
        │   ├── analysis/      # Processing experience (AnalysisRunner, StageList,
        │   │                  #   ProgressRail, LogStream)
        │   ├── result/        # Shared result panels (headline, signals, Gemini,
        │   │                  #   similarity, code, image, PDF report button)
        │   ├── text/ file/ code/ image/ summary/   # Feature surfaces
        │   ├── history/       # History list + detail
        │   └── dashboard/     # Overview / module launcher
        ├── data/               # Design tokens, nav, analysis stage scripts, samples
        └── lib/                # api.js (fetch + abort), useAnalysisRun.js, format.js
```

## Interface

The frontend is a light, off-white interface with a lavender accent, plus a dark theme
(toggle in the top bar; the choice is remembered, and with none saved it follows the
operating system). Coral, amber and green are reserved for AI-concern, uncertain and
human-leaning signals. Neutral colours are CSS variables defined for both themes in
`src/index.css` and mapped in `tailwind.config.js`; accent hues are in
`src/data/constants.js`. The logo has two artworks, `public/logo-*.png` (light) and
`public/logo-dark-*.png` (white disc and bones for dark backgrounds). Vite does not
hot-reload `tailwind.config.js` — restart `npm run dev` after editing it.
(`stitch-references/` holds the earlier dark "Deep Space Intelligence" design references
and no longer describes the app.)

- Results lead with one headline verdict, then each detector's own opinion side by
  side. A directional verdict ("Likely AI" / "Likely Human") is only issued when every
  detector that ran agrees; otherwise it reads "Uncertain" and says why. The local
  detector alone can never headline "Likely AI" — see `backend/evaluation/README.md`
  for the measurements behind that.
- Opening the app plays a short boot sequence that **actually probes `GET /health`**,
  so an unreachable backend is reported immediately instead of failing later.
- Each analysis type has a staged processing view whose stages mirror what that
  endpoint really does. The sequence is paced by a script but can only *finish*
  when the real request resolves — progress eases toward 92%, then creeps while
  the request is still out, and completes only on the response. Abort cancels the
  in-flight fetch for real via `AbortController`.
- Product name and terminal label live in `src/data/constants.js` (`BRAND`,
  `TERMINAL_NAME`) if you want to rebrand the shell.

## Backend setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

## Test scoring in isolation (do this first)

```bash
cd backend
python test_scoring.py
```

Options:

```bash
python test_scoring.py --sample human
python test_scoring.py --sample ai
python test_scoring.py --text "Paste any paragraph here..."
python test_scoring.py --model gpt2
python test_scoring.py --ppl-weight 0.6 --burst-weight 0.4
```

First run downloads DistilGPT-2 weights from HuggingFace.

## API (after scoring looks good)

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

- `GET /health`
- `POST /analyze` — text in, AI-likelihood score out (`{ "text": "...", "check_web": false }`).
  The response carries every detector's opinion (`detectors`, `consensus`), the headline
  verdict and its reason (`final_verdict`, `verdict_reason`), and similarity matches with
  provenance (`source_name`, `source_kind`, `source_created_at`, `source_url`).
- `POST /upload` — same, but from a PDF/PPTX/DOCX/TXT file (optional form field `check_web`)
- `POST /humanize` — rewrite AI-flagged sentences to sound more human
- `POST /detect-code` — upload a source file (or a document containing code) for AI-code detection
- `POST /detect-code-text` — same, for pasted code (`{ "code": "...", "filename": "" }`)
- `POST /summarize` — extract key points + chart data from a document or CSV/Excel file
- `POST /analyze/image` — AI-generated-image likelihood for a JPG/PNG/WEBP
- `GET /history` · `GET /history/{id}` · `DELETE /history/{id}` — stored analyses
- `GET /dashboard` — aggregate counts for the overview surface
- `GET /report/{id}` — PDF report for a stored analysis

`GEMINI_API_KEY` is read server-side only (see `backend/.env.example`); it is never
sent to the browser. Without it, text analysis falls back to the local statistical
detector, summaries stay extractive, and image detection reports itself as
unavailable rather than returning a fabricated score.

**Privacy.** AI-assisted checks send the submitted text (or image) from the server to
the providers you configure (Groq, Google Gemini, ...). `check_web` is off unless the
user ticks it; when on, a few short excerpts are sent to wikipedia.org and arxiv.org
as search queries and nothing else leaves the server. Set `EXTERNAL_SOURCES=off` to
disable that entirely.

**Browser access.** CORS is restricted to the dev frontend origins and requests must
carry a `localhost` / `127.0.0.1` Host header (this stops other web pages, and DNS
rebinding, reaching a local instance). To serve the UI from elsewhere set
`CORS_ORIGINS` and `ALLOWED_HOSTS`.

## Tests and evaluation

The backend tests are standalone scripts (no pytest):

```bash
cd backend
python test_detection.py
python test_new_features.py
python test_similarity_eval.py
python test_originality_rewrite.py
python test_gemini_key_rotation.py
python test_analyze_endpoint.py
python test_web_sources.py
```

`test_analyze_endpoint.py` and `test_web_sources.py` use fake providers and an isolated
database, so they spend no API quota and never touch `backend/data/history.db`.
To measure detector accuracy on labelled data, see `backend/evaluation/README.md`.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173` and proxies API calls to the backend on port 8000 (see `vite.config.js`).

## How it works

**Text detection** combines four signals into a 0–100 AI-likelihood score:
1. **Perplexity** — How surprised GPT-2 is by the text. Lower = more predictable = often more AI-like.
2. **Burstiness** — Variance of per-sentence perplexity. Humans vary more; AI tends to be uniform.
3. **AI-marker density** — Frequency of AI buzzwords/transition phrases ("leverage", "furthermore", ...).
4. **Sentence-length uniformity** — AI tends to produce more evenly-sized sentences.

**Code detection** scores source code on cleanliness (absence of debug artifacts), edge-case handling, naming/line-length uniformity, and comment/docstring patterns — signals tuned for modern AI coding assistants rather than just comment style.
