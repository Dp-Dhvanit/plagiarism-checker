import { useState } from "react";
import PageHeader from "../common/PageHeader.jsx";
import DropZone from "../common/DropZone.jsx";
import Button from "../common/Button.jsx";
import ErrorMsg from "../common/ErrorMsg.jsx";
import Disclaimer from "../common/Disclaimer.jsx";
import AnalysisRunner from "../analysis/AnalysisRunner.jsx";
import SummaryResultPanel from "./SummaryResultPanel.jsx";
import { useAnalysisRun } from "../../lib/useAnalysisRun.js";
import { SUMMARY_STAGES } from "../../data/stages.js";
import { postForm } from "../../lib/api.js";
import { ACCEPT, FORMAT_CHIPS } from "../../data/constants.js";

export default function SummaryTab() {
  const [file, setFile] = useState(null);
  const [inputError, setInputError] = useState("");
  const run = useAnalysisRun(SUMMARY_STAGES);

  const start = async () => {
    if (!file) {
      setInputError("Select a document to summarize.");
      return;
    }
    setInputError("");
    const form = new FormData();
    form.append("file", file);
    await run.run(({ signal }) => postForm("/summarize", form, { signal }));
  };

  const backToInput = () => run.reset();

  if (run.isBusy || run.phase === "error") {
    return (
      <>
        <PageHeader
          eyebrow="SEC_05 // SUMMARY"
          title="Document Summary"
          subtitle={run.phase === "error" ? "Sequence halted" : "Semantic extraction in progress"}
          status={run.phase === "error" ? "error" : "running"}
        />
        <AnalysisRunner
          kind="summary"
          run={run}
          stages={SUMMARY_STAGES}
          subject={{ name: file?.name, size: file?.size }}
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
          eyebrow="SEC_05 // SUMMARY"
          title="Analysis Complete"
          subtitle={file?.name}
          status="done"
          action={
            <Button onClick={backToInput} variant="ghost" size="sm" icon="arrow_back">
              New summary
            </Button>
          }
        />
        <SummaryResultPanel result={run.result} fileName={file?.name} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="SEC_05 // SUMMARY"
        title="Document Summary"
        subtitle="Extract key points and chartable figures from a document or dataset."
        status={file ? "ready" : "idle"}
      />

      <DropZone
        file={file}
        setFile={setFile}
        accept={ACCEPT.summary}
        formats={FORMAT_CHIPS.summary}
        zoneCode="ZONE_05 // INGEST"
        icon="summarize"
        title="Drag & drop a document here"
        hint="Prose documents produce key takeaways. CSV and spreadsheet files produce data breakdowns."
        onReset={() => { run.reset(); setInputError(""); }}
      />

      <ErrorMsg msg={inputError} />

      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
        <p className="font-mono text-[11px] text-outline">Documents need at least 50 characters of readable text.</p>
        <div className="flex gap-3">
          {file && (
            <Button onClick={() => setFile(null)} variant="quiet" icon="delete">
              Clear
            </Button>
          )}
          <Button onClick={start} icon="auto_awesome" disabled={!file}>
            {file ? "Summarize document" : "Select a document"}
          </Button>
        </div>
      </div>

      <div className="mt-8">
        <Disclaimer>
          Summaries are extractive by default. When the server-side semantic layer is available it
          rewrites the takeaways and selects charts; when it is not, you get the deterministic
          summary and the panel says so.
        </Disclaimer>
      </div>
    </>
  );
}
