# AI Text Detective

Detect whether text, code, or documents were likely written by an AI or a human, and summarize documents with auto-generated charts.

## Project structure

```
SVG/
├── backend/                 # FastAPI + detection engines
│   ├── app/
│   │   ├── main.py          # API routes (analyze, upload, humanize, detect-code, summarize)
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

The frontend implements the "Deep Space Intelligence" design system defined in
`stitch-references/*/DESIGN.md` (all 13 references share one token set).

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
- `POST /analyze` — text in, AI-likelihood score out (`{ "text": "..." }`)
- `POST /upload` — same, but from a PDF/PPTX/DOCX/TXT file
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
