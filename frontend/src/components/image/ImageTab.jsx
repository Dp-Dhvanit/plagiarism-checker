import { useEffect, useState } from "react";
import PageHeader from "../common/PageHeader.jsx";
import GlassCard from "../common/GlassCard.jsx";
import DropZone from "../common/DropZone.jsx";
import Button from "../common/Button.jsx";
import Icon from "../common/Icon.jsx";
import ErrorMsg from "../common/ErrorMsg.jsx";
import Disclaimer from "../common/Disclaimer.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import AnalysisRunner from "../analysis/AnalysisRunner.jsx";
import ImageResultPanel from "../result/ImageResultPanel.jsx";
import { useAnalysisRun } from "../../lib/useAnalysisRun.js";
import { IMAGE_STAGES } from "../../data/stages.js";
import { postForm } from "../../lib/api.js";
import { ACCEPT, FORMAT_CHIPS } from "../../data/constants.js";
import { formatBytes } from "../../lib/format.js";

export default function ImageTab() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [dimensions, setDimensions] = useState(null);
  const [inputError, setInputError] = useState("");
  const run = useAnalysisRun(IMAGE_STAGES);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      setDimensions(null);
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    const img = new Image();
    img.onload = () => setDimensions({ w: img.naturalWidth, h: img.naturalHeight });
    img.src = url;
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const start = async () => {
    if (!file) {
      setInputError("Select an image to analyze.");
      return;
    }
    setInputError("");
    const form = new FormData();
    form.append("file", file);
    await run.run(({ signal }) => postForm("/analyze/image", form, { signal }));
  };

  const backToInput = () => run.reset();

  if (run.isBusy || run.phase === "error") {
    return (
      <>
        <PageHeader
          eyebrow="SEC_04 // IMG_PROC"
          title="Image Analysis"
          subtitle={file?.name}
          status={run.phase === "error" ? "error" : "running"}
        />
        <AnalysisRunner
          kind="image"
          run={run}
          stages={IMAGE_STAGES}
          subject={{ previewUrl, name: file?.name }}
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
          eyebrow="SEC_04 // IMG_PROC"
          title="Image Report"
          subtitle={file?.name}
          status="done"
          action={
            <Button onClick={backToInput} variant="ghost" size="sm" icon="arrow_back">
              New analysis
            </Button>
          }
        />
        <ImageResultPanel result={run.result} previewUrl={previewUrl} onRetry={start} />
      </>
    );
  }

  // ── Intake (reference screen-12) ─────────────────────────────────────
  return (
    <>
      <PageHeader
        eyebrow="ANALYSIS_MODULE // IMG_PROC"
        title="Visual Data Intake"
        subtitle="Initialize a deep scanning sequence for supported visual formats."
        status={file ? "ready" : "idle"}
      />

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <DropZone
          file={file}
          setFile={setFile}
          accept={ACCEPT.image}
          formats={FORMAT_CHIPS.image}
          zoneCode="ZONE_ALPHA"
          icon="add_photo_alternate"
          title="Drop an image here"
          hint="Maximum payload size: 10 MB."
          onReset={() => { run.reset(); setInputError(""); }}
          preview={
            previewUrl && (
              <div className="relative w-full max-w-sm overflow-hidden rounded border border-tertiary/30">
                <img src={previewUrl} alt="Selected" className="max-h-56 w-full object-contain bg-surface-lowest" />
              </div>
            )
          }
        />

        {/* Buffer status (reference screen-12) */}
        <div className="flex flex-col gap-4">
          <GlassCard className="flex-1" bodyClassName="p-5">
            <SectionTitle icon="memory">Buffer status</SectionTitle>

            {file ? (
              <dl className="space-y-3">
                <Row label="File" value={file.name} mono truncate />
                <Row label="Payload" value={formatBytes(file.size)} />
                <Row label="Type" value={file.type || "—"} />
                <Row
                  label="Resolution"
                  value={dimensions ? `${dimensions.w} × ${dimensions.h}` : "reading…"}
                />
                <div className="mt-4 flex items-center gap-2 border-t border-outline-variant/20 pt-4">
                  <span className="h-1.5 w-1.5 rounded-full bg-tertiary" />
                  <span className="font-mono text-label-caps uppercase tracking-[0.14em] text-tertiary">
                    Ready for analysis
                  </span>
                </div>
              </dl>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <Icon name="hourglass_empty" size={30} className="mb-3 text-outline/50" />
                <p className="font-mono text-[12px] text-outline">Awaiting image data stream…</p>
              </div>
            )}
          </GlassCard>

          <div className="flex flex-col gap-3">
            {file && (
              <Button onClick={() => setFile(null)} variant="quiet" icon="delete" full>
                Clear buffer
              </Button>
            )}
            <Button onClick={start} icon="radar" size="lg" disabled={!file} full>
              Execute analysis
            </Button>
          </div>
        </div>
      </div>

      <ErrorMsg msg={inputError} />

      <div className="mt-8">
        <Disclaimer>
          Image detection is a model-assisted visual estimate performed on the server. If the
          service is not configured or the request fails, you will see a clear unavailable notice
          rather than an invented score.
        </Disclaimer>
      </div>
    </>
  );
}

function Row({ label, value, mono, truncate }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="shrink-0 font-mono text-label-caps uppercase tracking-[0.12em] text-outline">{label}</dt>
      <dd
        className={`min-w-0 text-right font-mono text-[12px] text-on-surface-variant ${
          truncate ? "truncate" : ""
        } ${mono ? "" : "tabular-nums"}`}
      >
        {value}
      </dd>
    </div>
  );
}
