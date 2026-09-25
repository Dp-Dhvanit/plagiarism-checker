import { useState } from "react";
import PageHeader from "../common/PageHeader.jsx";
import GlassCard from "../common/GlassCard.jsx";
import DropZone from "../common/DropZone.jsx";
import Button from "../common/Button.jsx";
import Icon from "../common/Icon.jsx";
import ErrorMsg from "../common/ErrorMsg.jsx";
import Disclaimer from "../common/Disclaimer.jsx";
import AnalysisRunner from "../analysis/AnalysisRunner.jsx";
import CodeResultPanel from "../result/CodeResultPanel.jsx";
import { useAnalysisRun } from "../../lib/useAnalysisRun.js";
import { CODE_STAGES } from "../../data/stages.js";
import { postForm, postJSON } from "../../lib/api.js";
import { ACCEPT, FORMAT_CHIPS, SUPPORTED_LANGUAGES } from "../../data/constants.js";
import { SAMPLE_CODE_AI } from "../../data/samples.js";

const MODES = [
  { key: "paste", icon: "content_paste", title: "Paste snippet", blurb: "Paste source code directly." },
  { key: "file", icon: "upload_file", title: "Upload source", blurb: "A source file, or a document containing code." },
];

// Plain source extensions the browser can safely read as text client-side
// for the Code Optimizer (see CodeResultPanel's sourceCode prop) — NOT
// documents (PDF/DOCX/PPTX), whose extracted code the backend never
// echoes back, so there's nothing clean to send to the optimizer for those.
const CODE_FILE_EXTS = [
  ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cpp", ".cc", ".cxx", ".h",
  ".hpp", ".c", ".cs", ".php", ".go", ".rb", ".kt", ".swift", ".sql",
];

export default function CodeTab() {
  const [mode, setMode] = useState("paste");
  const [file, setFile] = useState(null);
  const [fileText, setFileText] = useState(null);
  const [code, setCode] = useState("");
  const [inputError, setInputError] = useState("");
  const run = useAnalysisRun(CODE_STAGES);

  const start = async () => {
    if (mode === "paste") {
      const c = code.trim();
      if (c.length < 10) {
        setInputError("Paste at least 10 characters of code.");
        return;
      }
      setInputError("");
      await run.run(({ signal }) => postJSON("/detect-code-text", { code: c, filename: "" }, { signal }));
      return;
    }
    if (!file) {
      setInputError("Select a source file to scan.");
      return;
    }
    setInputError("");
    const isPlainCodeFile = CODE_FILE_EXTS.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (isPlainCodeFile) {
      try {
        setFileText(await file.text());
      } catch {
        setFileText(null);
      }
    } else {
      setFileText(null); // a document (PDF/DOCX/PPTX) — no clean source text to optimize
    }
    const form = new FormData();
    form.append("file", file);
    await run.run(({ signal }) => postForm("/detect-code", form, { signal }));
  };

  const backToInput = () => run.reset();

  if (run.isBusy || run.phase === "error") {
    return (
      <>
        <PageHeader
          title="Code Analysis"
          subtitle={mode === "file" ? file?.name : "Pasted snippet"}
          status={run.phase === "error" ? "error" : "running"}
        />
        <AnalysisRunner
          kind="code"
          run={run}
          stages={CODE_STAGES}
          subject={{ name: file?.name }}
          onAbort={run.abort}
          onRetry={start}
          onCancel={backToInput}
        />
      </>
    );
  }

  if (run.phase === "done" && run.result) {
    return (
      <>
        <PageHeader
          title="Code Report"
          subtitle={mode === "file" ? file?.name : "Pasted snippet"}
          status="done"
          action={
            <Button onClick={backToInput} variant="ghost" size="sm" icon="arrow_back">
              New scan
            </Button>
          }
        />
        <CodeResultPanel result={run.result} sourceCode={mode === "paste" ? code : fileText} />
      </>
    );
  }

  const canRun = mode === "paste" ? code.trim().length >= 10 : !!file;

  return (
    <>
      <PageHeader
        title="Code Analysis"
        subtitle="Paste a snippet or upload a source file to assess whether it reads as AI-assisted."
        status={canRun ? "ready" : "idle"}
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        {MODES.map((m) => {
          const active = mode === m.key;
          return (
            <button
              key={m.key}
              type="button"
              onClick={() => { setMode(m.key); setInputError(""); }}
              className={`rounded-xl border p-5 text-left transition-colors ${
                active
                  ? "border-primary/50 bg-primary-container/6"
                  : "border-outline-variant/40 bg-surface hover:border-primary/30 hover:bg-primary-container/4"
              }`}
            >
              <div
                className={`mb-3 flex h-10 w-10 items-center justify-center rounded-lg ${
                  active ? "bg-primary-container/12 text-primary" : "bg-surface-high text-on-surface-variant"
                }`}
              >
                <Icon name={m.icon} size={20} />
              </div>
              <h3 className={`text-[15px] font-semibold ${active ? "text-primary" : "text-on-surface"}`}>
                {m.title}
              </h3>
              <p className="mt-1 text-[13px] leading-relaxed text-on-surface-variant">{m.blurb}</p>
            </button>
          );
        })}
      </div>

      {mode === "paste" ? (
        <GlassCard bodyClassName="p-0">
          <div className="flex items-center justify-between border-b border-outline-variant/40 px-4 py-2.5">
            <span className="text-[12.5px] font-medium text-on-surface-variant">Source code</span>
            <button
              type="button"
              onClick={() => { setCode(SAMPLE_CODE_AI); setInputError(""); }}
              className="text-[12.5px] font-medium text-primary hover:underline"
            >
              Load sample
            </button>
          </div>
          <textarea
            value={code}
            onChange={(e) => { setCode(e.target.value); setInputError(""); }}
            rows={16}
            spellCheck="false"
            placeholder="// paste source here — .py .js .ts .java .cpp .go .rb .sql …"
            aria-label="Source code to analyze"
            className="w-full resize-none rounded-b-xl border-0 bg-surface-lowest/50 p-5 font-mono text-[12.5px] leading-[1.8] text-on-surface outline-none placeholder:text-outline/60 focus:ring-0"
          />
          <div className="flex items-center justify-between border-t border-outline-variant/40 px-5 py-3.5">
            <span className="text-[13px] text-on-surface-variant">
              {code.split("\n").length} lines · {code.length.toLocaleString()} chars
            </span>
            <Button onClick={() => setCode("")} variant="quiet" size="sm" icon="delete" disabled={!code}>
              Clear
            </Button>
          </div>
        </GlassCard>
      ) : (
        <DropZone
          file={file}
          setFile={setFile}
          accept={ACCEPT.code}
          formats={FORMAT_CHIPS.code}
          title="Drag & drop a source file here"
          hint="Source files scan directly. PDF, DOCX and PPTX are searched for embedded code blocks."
          onReset={() => { run.reset(); setInputError(""); }}
        />
      )}

      <ErrorMsg msg={inputError} />

      <div className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-2.5 rounded-xl border border-outline-variant/40 bg-surface-lowest/50 px-5 py-4">
        <span className="text-[12.5px] font-medium text-on-surface-variant">Supported languages:</span>
        <div className="flex flex-wrap gap-1.5">
          {SUPPORTED_LANGUAGES.map((l) => (
            <span
              key={l}
              className="rounded-full border border-outline-variant/50 bg-surface px-2.5 py-1 text-[11.5px] text-on-surface-variant"
            >
              {l}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-7 flex justify-center">
        <Button onClick={start} icon="search" size="lg" disabled={!canRun}>
          Analyze code
        </Button>
      </div>

      <div className="mt-8">
        <Disclaimer>
          Code detection reads structural habits — comment style, docstring coverage, naming
          uniformity, edge-case handling. Formatters and linters push human code toward the same
          profile, so treat the result as a weak indicator only.
        </Disclaimer>
      </div>
    </>
  );
}
