import { useState } from "react";
import PageHeader from "../common/PageHeader.jsx";
import DropZone from "../common/DropZone.jsx";
import Button from "../common/Button.jsx";
import ErrorMsg from "../common/ErrorMsg.jsx";
import StatusNotice from "../common/StatusNotice.jsx";
import Disclaimer from "../common/Disclaimer.jsx";
import FilePreview from "../common/FilePreview.jsx";
import AnalysisRunner from "../analysis/AnalysisRunner.jsx";
import TextResultPanel from "../result/TextResultPanel.jsx";
import CodeResultPanel from "../result/CodeResultPanel.jsx";
import { useAnalysisRun } from "../../lib/useAnalysisRun.js";
import { DOCUMENT_STAGES } from "../../data/stages.js";
import WebCheckToggle from "../common/WebCheckToggle.jsx";
import { usePref } from "../../lib/prefs.js";
import { postForm } from "../../lib/api.js";
import { ACCEPT, FORMAT_CHIPS } from "../../data/constants.js";

const TERMINAL_STATUSES = ["unanalyzable", "insufficient_text", "insufficient", "extraction_failure"];

export default function FileTab() {
  const [file, setFile] = useState(null);
  const [inputError, setInputError] = useState("");
  const [checkWeb, setCheckWeb] = usePref("checkWeb", false);
  const run = useAnalysisRun(DOCUMENT_STAGES);

  const start = async (f = file) => {
    if (!f) {
      setInputError("Select a document to analyze.");
      return;
    }
    setInputError("");
    const form = new FormData();
    form.append("file", f);
    form.append("check_web", checkWeb ? "true" : "false");
    await run.run(({ signal }) => postForm("/upload", form, { signal }));
  };

  const backToInput = () => run.reset();

  if (run.isBusy || run.phase === "error") {
    return (
      <>
        <PageHeader
          title="Document Analysis"
          subtitle="Extracting content and checking for AI writing and overlap."
          status={run.phase === "error" ? "error" : "running"}
        />
        <AnalysisRunner
          kind="document"
          run={run}
          stages={DOCUMENT_STAGES}
          subject={{ name: file?.name }}
          onAbort={run.abort}
          onRetry={() => start()}
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
          subtitle={file?.name}
          status={declined ? "idle" : "done"}
          statusLabel={declined ? "Not assessed" : undefined}
          action={
            <Button onClick={backToInput} variant="ghost" size="sm" icon="arrow_back">
              New analysis
            </Button>
          }
        />

        <div className="mb-6">
          <FilePreview
            name={file?.name}
            size={file?.size}
            meta={result.document_class || undefined}
            status={declined ? "Not assessed" : "Analyzed"}
            tone={declined ? "primary" : "lime"}
          />
        </div>

        {result.status === "analyzed" && (
          <TextResultPanel result={result} originalText={result.extracted_text || ""} showExtracted />
        )}

        {result.status === "code" && (
          <div className="space-y-6">
            <StatusNotice
              status="mixed"
              message="This document was mostly source code, so it was routed to the code detector."
            />
            {result.code_result && <CodeResultPanel result={result.code_result} />}
          </div>
        )}

        {result.status === "mixed" && (
          <div className="space-y-6">
            <StatusNotice
              status="mixed"
              message={result.message || "This document contains both prose and code — each was analyzed separately below."}
            />
            {result.code_result && <CodeResultPanel result={result.code_result} />}
            {result.sentence_breakdown?.length > 0 && (
              <TextResultPanel result={result} originalText={result.extracted_text || ""} showExtracted />
            )}
          </div>
        )}

        {TERMINAL_STATUSES.includes(result.status) && (
          <div className="space-y-6">
            <StatusNotice status={result.status} message={result.message} />
            {result.extracted_text && (
              <TextResultPanel
                result={{ ...result, signals: null, sentence_breakdown: [] }}
                originalText={result.extracted_text}
                showExtracted
              />
            )}
          </div>
        )}
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Document Analysis"
        subtitle="Upload a document to extract its text and check for AI writing and overlap."
        status={file ? "ready" : "idle"}
      />

      <DropZone
        file={file}
        setFile={setFile}
        accept={ACCEPT.document}
        formats={FORMAT_CHIPS.document}
        title="Drag & drop a document here"
        hint="The file must contain selectable text — scanned page images cannot be read."
        onReset={() => { run.reset(); setInputError(""); }}
      />

      <ErrorMsg msg={inputError} />

      <div className="mt-4">
        <WebCheckToggle checked={checkWeb} onChange={setCheckWeb} />
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
        <p className="text-[12.5px] text-outline">Maximum upload size: 15 MB</p>
        <div className="flex gap-3">
          {file && (
            <Button onClick={() => setFile(null)} variant="quiet" size="md" icon="delete">
              Clear
            </Button>
          )}
          <Button onClick={() => start()} icon="search" disabled={!file}>
            {file ? "Analyze document" : "Select a document"}
          </Button>
        </div>
      </div>

      <div className="mt-8">
        <Disclaimer>
          Documents are read on this server. Extracted prose is scored with the same statistical
          detector used for pasted text — and, if AI-assisted checks are configured, sent to those
          providers too — then stored so later uploads can be compared against it.
        </Disclaimer>
      </div>
    </>
  );
}
