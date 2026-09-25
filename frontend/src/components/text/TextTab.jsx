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
import WebCheckToggle from "../common/WebCheckToggle.jsx";
import { usePref } from "../../lib/prefs.js";
import { postJSON } from "../../lib/api.js";
import { countWords } from "../../lib/format.js";
import { SAMPLE_AI, SAMPLE_HUMAN } from "../../data/samples.js";

const TERMINAL_STATUSES = ["unanalyzable", "insufficient_text", "insufficient", "extraction_failure"];

export default function TextTab() {
  const [text, setText] = useState("");
  const [inputError, setInputError] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [checkWeb, setCheckWeb] = usePref("checkWeb", false);
  const run = useAnalysisRun(TEXT_STAGES);

  const start = async (value) => {
    const t = (value ?? text).trim();
    if (!t) {
      setInputError("Enter some text to analyze.");
      return;
    }
    setInputError("");
    setSubmitted(t);
    await run.run(({ signal }) => postJSON("/analyze", { text: t, check_web: checkWeb }, { signal }));
  };

  const backToInput = () => run.reset();

  if (run.isBusy || run.phase === "error") {
    return (
      <>
        <PageHeader
          title="Text Analysis"
          subtitle="Checking your text for AI-generated writing and overlap with prior submissions."
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

  if (run.phase === "done" && run.result) {
    const result = run.result;
    const declined = TERMINAL_STATUSES.includes(result.status);
    return (
      <>
        <PageHeader
          title="Analysis Report"
          subtitle="Pasted text"
          status={declined ? "idle" : "done"}
          statusLabel={declined ? "Not assessed" : undefined}
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
            <StatusNotice status={result.status} message={result.message} />
            <Disclaimer />
          </div>
        )}
      </>
    );
  }

  const chars = text.length;
  const words = countWords(text);

  return (
    <>
      <PageHeader
        title="Text Analysis"
        subtitle="Paste text below to estimate AI-generated writing and check overlap with documents you've analyzed before."
        status={text.trim() ? "ready" : "idle"}
      />

      <GlassCard bodyClassName="p-0">
        <textarea
          value={text}
          onChange={(e) => { setText(e.target.value); setInputError(""); }}
          rows={12}
          spellCheck="false"
          placeholder="Paste your text here…"
          aria-label="Text to analyze"
          className="w-full resize-none rounded-t-xl border-0 bg-transparent p-6 text-[15px] leading-[1.7] text-on-surface outline-none placeholder:text-outline/60 focus:ring-0"
        />

        <div className="flex flex-col gap-4 border-t border-outline-variant/40 bg-surface-lowest/60 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-5 text-[13px] text-on-surface-variant">
            <span className="flex items-center gap-1.5">
              <Icon name="text_fields" size={16} className="text-outline" />
              <span className="tabular-nums">{chars.toLocaleString()}</span> characters
            </span>
            <span className="flex items-center gap-1.5">
              <Icon name="segment" size={16} className="text-outline" />
              <span className="tabular-nums">{words.toLocaleString()}</span> words
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

      <div className="mt-4">
        <WebCheckToggle checked={checkWeb} onChange={setCheckWeb} />
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <span className="text-[13px] font-medium text-on-surface-variant">Try a sample:</span>
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
