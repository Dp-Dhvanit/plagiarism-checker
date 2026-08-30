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

/** Reference screen-9: two real intake routes, presented as OP_ cards. */
const MODES = [
  { key: "paste", code: "OP_01", icon: "content_paste", title: "Paste Snippet", blurb: "Direct source injection." },
  { key: "file", code: "OP_02", icon: "upload_file", title: "Upload Source", blurb: "Source files, or a PDF/DOCX/PPTX containing code." },
];

export default function CodeTab() {
  const [mode, setMode] = useState("paste");
  const [file, setFile] = useState(null);
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
    const form = new FormData();
    form.append("file", file);
    await run.run(({ signal }) => postForm("/detect-code", form, { signal }));
  };

  const backToInput = () => run.reset();

  if (run.isBusy || run.phase === "error") {
    return (
      <>
        <PageHeader
          eyebrow="SEC_03 // CODE"
          title="Code Analysis"
          subtitle={mode === "file" ? file?.name : "Pasted snippet"}
          status={run.phase === "error" ? "error" : "running"}
        />
        <AnalysisRunner
          kind="code"
          run={run}
          stages={CODE_STAGES}
          subject={{ source: mode === "paste" ? code : null, name: file?.name }}
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
          eyebrow="SEC_03 // CODE"
          title="Code Report"
          subtitle={mode === "file" ? file?.name : "Pasted snippet"}
          status="done"
          action={
            <Button onClick={backToInput} variant="ghost" size="sm" icon="arrow_back">
              New scan
            </Button>
          }
        />
        <CodeResultPanel result={run.result} />
      </>
    );
  }

  const canRun = mode === "paste" ? code.trim().length >= 10 : !!file;

  return (
    <>
      <PageHeader
        eyebrow="MODULE_INIT // READY"
        title="Initialize Analysis"
        subtitle="Provide target source via paste or file upload to begin the deep-scan protocol."
        status={canRun ? "ready" : "idle"}
      />

      {/* Intake mode selector */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        {MODES.map((m) => {
          const active = mode === m.key;
          return (
            <button
              key={m.key}
              type="button"
              onClick={() => { setMode(m.key); setInputError(""); }}
              className={`relative overflow-hidden rounded-lg border p-6 text-left transition-all duration-200 ${
                active
                  ? "border-primary/60 bg-primary-container/10 shadow-[0_0_20px_rgba(37,99,235,0.18)]"
                  : "border-outline-variant/35 bg-surface-low/40 hover:border-primary/35 hover:bg-surface-low/70"
              }`}
            >
              <span className="absolute left-4 top-3 font-mono text-label-caps uppercase tracking-[0.14em] text-outline/60">
                {m.code}
              </span>
              <div
                className={`mb-4 mt-5 flex h-12 w-12 items-center justify-center rounded border ${
                  active
                    ? "border-primary/45 bg-primary-container/20 text-primary"
                    : "border-outline-variant/40 bg-surface-high/50 text-on-surface-variant"
                }`}
              >
                <Icon name={m.icon} size={24} />
              </div>
              <h3 className={`font-mono text-[16px] font-medium ${active ? "text-primary" : "text-on-surface"}`}>
                {m.title}
              </h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-outline">{m.blurb}</p>
            </button>
          );
        })}
      </div>

      {mode === "paste" ? (
        <GlassCard brackets bodyClassName="p-0">
          <div className="flex items-center justify-between border-b border-outline-variant/20 bg-surface/50 px-4 py-2.5">
            <span className="font-mono text-label-caps uppercase tracking-[0.14em] text-primary">
              SRC_IN // RAW
            </span>
            <button
              type="button"
              onClick={() => { setCode(SAMPLE_CODE_AI); setInputError(""); }}
              className="font-mono text-label-caps uppercase tracking-[0.14em] text-outline transition-colors hover:text-primary"
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
            className="w-full resize-none border-0 bg-transparent p-5 font-mono text-[12.5px] leading-[1.8] text-on-surface outline-none placeholder:text-outline/50 focus:ring-0"
          />
          <div className="flex items-center justify-between border-t border-outline-variant/20 bg-surface-low/70 px-5 py-3.5">
            <span className="font-mono text-data-sm text-outline">
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
          zoneCode="ZONE_03 // SOURCE"
          title="Drag & drop a source file here"
          hint="Source files scan directly. PDF, DOCX and PPTX are searched for embedded code blocks."
          onReset={() => { run.reset(); setInputError(""); }}
        />
      )}

      <ErrorMsg msg={inputError} />

      {/* Supported syntax rail (reference screen-9) */}
      <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-3 rounded-lg border border-outline-variant/30 bg-surface-low/40 px-5 py-4">
        <span className="font-mono text-label-caps uppercase tracking-[0.14em] text-outline">
          Supported syntax:
        </span>
        <div className="flex flex-wrap gap-2">
          {SUPPORTED_LANGUAGES.map((l) => (
            <span
              key={l}
              className="rounded border border-outline-variant/35 bg-surface-high/50 px-2.5 py-1 font-mono text-[11px] text-on-surface-variant"
            >
              {l}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-7 flex justify-center">
        <Button onClick={start} icon="target" size="lg" disabled={!canRun}>
          Initiate code scan
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
