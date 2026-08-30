import { useState } from "react";
import PageHeader from "../common/PageHeader.jsx";
import GlassCard from "../common/GlassCard.jsx";
import Button from "../common/Button.jsx";
import Icon from "../common/Icon.jsx";
import ErrorMsg from "../common/ErrorMsg.jsx";
import StatusNotice from "../common/StatusNotice.jsx";
import Disclaimer from "../common/Disclaimer.jsx";
import AnalysisRunner from "../analysis/AnalysisRunner.jsx";
import TextResultPanel from "../result/TextResultPanel.jsx";
import CodeResultPanel from "../result/CodeResultPanel.jsx";
import { useAnalysisRun } from "../../lib/useAnalysisRun.js";
import { TEXT_STAGES } from "../../data/stages.js";
import { postJSON } from "../../lib/api.js";
import { countWords } from "../../lib/format.js";
import { SAMPLE_AI, SAMPLE_HUMAN } from "../../data/samples.js";

const TERMINAL_STATUSES = ["unanalyzable", "insufficient_text", "insufficient", "extraction_failure"];

export default function TextTab() {
  const [text, setText] = useState("");
  const [inputError, setInputError] = useState("");
  const [submitted, setSubmitted] = useState("");
  const run = useAnalysisRun(TEXT_STAGES);

  const start = async (value) => {
    const t = (value ?? text).trim();
    if (!t) {
      setInputError("Enter some text to analyze.");
      return;
    }
    setInputError("");
    setSubmitted(t);
    await run.run(({ signal }) => postJSON("/analyze", { text: t }, { signal }));
  };

  const backToInput = () => run.reset();

  // ── Processing / failed ──────────────────────────────────────────────
  if (run.isBusy || run.phase === "error") {
    return (
      <>
        <PageHeader
          eyebrow="SEC_01 // TEXT"
          title="Text Analysis Engine"
          subtitle={run.phase === "error" ? "Sequence halted" : "Linguistic decryption in progress"}
          status={run.phase === "error" ? "error" : "running"}
        />
        <AnalysisRunner
          kind="text"
          run={run}
          stages={TEXT_STAGES}
          onAbort={run.abort}
          onRetry={() => start(submitted)}
          onCancel={backToInput}
        />
      </>
    );
  }

  // ── Result ───────────────────────────────────────────────────────────
  if (run.phase === "done" && run.result) {
    const result = run.result;
    // A declined input (too short, unscoreable) finished the request but did
    // not produce an assessment — badging it "COMPLETE" would overstate it.
    const declined = TERMINAL_STATUSES.includes(result.status);
    return (
      <>
        <PageHeader
          eyebrow="SEC_01 // TEXT"
          title="Analysis Report"
          subtitle="Pasted text"
          status={declined ? "idle" : "done"}
          statusLabel={declined ? "NOT ASSESSED" : undefined}
          action={
            <Button onClick={backToInput} variant="ghost" size="sm" icon="arrow_back">
              New analysis
            </Button>
          }
        />

        {result.status === "analyzed" && <TextResultPanel result={result} originalText={submitted} />}

        {result.status === "code" && (
          <div className="space-y-6">
            <StatusNotice
              status="mixed"
              message="This looked like source code rather than prose, so it was routed to the code detector instead."
            />
            {result.code_result && <CodeResultPanel result={result.code_result} />}
          </div>
        )}

        {result.status === "mixed" && (
          <div className="space-y-6">
            <StatusNotice
              status="mixed"
              message={result.message || "Prose and code were both detected — each was analyzed separately below."}
            />
            {result.code_result && <CodeResultPanel result={result.code_result} />}
            {result.sentence_breakdown?.length > 0 && (
              <TextResultPanel result={result} originalText={submitted} />
            )}
          </div>
        )}

        {TERMINAL_STATUSES.includes(result.status) && (
          <div className="space-y-6">
            <StatusNotice status={result.status} message={result.message} code="SEC_01 // TEXT" />
            <Disclaimer />
          </div>
        )}
      </>
    );
  }

  // ── Input (reference screen-2) ───────────────────────────────────────
  const chars = text.length;
  const words = countWords(text);

  return (
    <>
      <PageHeader
        eyebrow="SEC_01 // TEXT"
        title="Text Analysis Engine"
        subtitle="Awaiting input stream for linguistic decryption."
        status={text.trim() ? "ready" : "idle"}
      />

      <div className="mb-2 flex items-center gap-2 px-1">
        <span className="h-1 w-1 animate-pulse rounded-full bg-primary" />
        <span className="font-mono text-label-caps uppercase tracking-[0.2em] text-primary/60">
          Input_Stream // SEC_01
        </span>
      </div>

      <GlassCard brackets bodyClassName="p-0" className="group">
        <div className="flex items-center justify-between border-b border-outline-variant/20 bg-surface/50 px-4 py-2.5">
          <span className="font-mono text-label-caps uppercase tracking-[0.14em] text-primary">
            TXT_IN // 00
          </span>
          <span className="flex items-center gap-2">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                text.trim() ? "bg-tertiary" : "animate-pulse bg-tertiary/60"
              }`}
            />
            <span className="font-mono text-label-caps uppercase tracking-[0.14em] text-tertiary">
              {text.trim() ? "STREAM BUFFERED" : "AWAITING STREAM"}
            </span>
          </span>
        </div>

        <div className="relative">
          <textarea
            value={text}
            onChange={(e) => { setText(e.target.value); setInputError(""); }}
            rows={12}
            spellCheck="false"
            placeholder="Paste your text here…"
            aria-label="Text to analyze"
            className="w-full resize-none border-0 bg-transparent p-6 font-mono text-[14.5px] leading-[1.85] text-on-surface outline-none placeholder:text-outline/50 focus:ring-0"
          />
        </div>

        <div className="flex flex-col gap-4 border-t border-outline-variant/20 bg-surface-low/70 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-6 font-mono text-data-sm text-on-surface-variant">
            <span className="flex items-center gap-2">
              <Icon name="text_fields" size={15} className="text-outline" />
              Chars: <span className="font-medium text-on-surface tabular-nums">{chars.toLocaleString()}</span>
            </span>
            <span className="flex items-center gap-2">
              <Icon name="segment" size={15} className="text-outline" />
              Words: <span className="font-medium text-on-surface tabular-nums">{words.toLocaleString()}</span>
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Button
              onClick={() => { setText(""); setInputError(""); }}
              variant="quiet"
              size="sm"
              icon="delete"
              disabled={!text}
            >
              Clear
            </Button>
            <Button onClick={() => start()} icon="psychology" disabled={!text.trim()}>
              Analyze text
            </Button>
          </div>
        </div>
      </GlassCard>

      <ErrorMsg msg={inputError} />

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <span className="font-mono text-label-caps uppercase tracking-[0.14em] text-outline">
          Load sample:
        </span>
        <Button onClick={() => { setText(SAMPLE_AI); setInputError(""); }} variant="ghost" size="sm" icon="smart_toy">
          Machine-style
        </Button>
        <Button onClick={() => { setText(SAMPLE_HUMAN); setInputError(""); }} variant="ghost" size="sm" icon="person">
          Human-style
        </Button>
      </div>

      <div className="mt-8">
        <Disclaimer>
          Scoring combines perplexity, burstiness, marker density and sentence uniformity into a
          likelihood estimate. It is a heuristic indicator, not a certified detector.
        </Disclaimer>
      </div>
    </>
  );
}
