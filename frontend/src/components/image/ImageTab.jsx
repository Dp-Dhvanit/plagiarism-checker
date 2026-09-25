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

  return (
    <>
      <PageHeader
        title="Image Analysis"
        subtitle="Upload a JPG, PNG or WEBP image to estimate whether it shows signs of AI generation."
        status={file ? "ready" : "idle"}
      />

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <DropZone
          file={file}
          setFile={setFile}
          accept={ACCEPT.image}
          formats={FORMAT_CHIPS.image}
          icon="add_photo_alternate"
          title="Drop an image here"
          hint="Maximum payload size: 10 MB."
          onReset={() => { run.reset(); setInputError(""); }}
          preview={
            previewUrl && (
              <div className="w-full max-w-sm overflow-hidden rounded-lg border border-outline-variant/40">
                <img src={previewUrl} alt="Selected" className="max-h-56 w-full bg-surface-lowest object-contain" />
              </div>
            )
          }
        />

        <div className="flex flex-col gap-4">
          <GlassCard className="flex-1" bodyClassName="p-5">
            <SectionTitle icon="info">Image details</SectionTitle>

            {file ? (
              <dl className="space-y-3">
                <Row label="File" value={file.name} truncate />
                <Row label="Size" value={formatBytes(file.size)} />
                <Row label="Type" value={file.type || "—"} />
                <Row label="Resolution" value={dimensions ? `${dimensions.w} × ${dimensions.h}` : "reading…"} />
              </dl>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <Icon name="image" size={28} className="mb-3 text-outline/60" />
                <p className="text-[13px] text-on-surface-variant">No image selected yet.</p>
              </div>
            )}
          </GlassCard>

          <div className="flex flex-col gap-3">
            {file && (
              <Button onClick={() => setFile(null)} variant="quiet" icon="delete" full>
                Clear
              </Button>
            )}
            <Button onClick={start} icon="search" size="lg" disabled={!file} full>
              Analyze image
            </Button>
          </div>
        </div>
      </div>

      <ErrorMsg msg={inputError} />

      <div className="mt-8">
        <Disclaimer>
          Image detection is a model-assisted visual estimate performed on the server. If the
          service is not configured or the request fails, you'll see a clear message rather than an
          invented score.
        </Disclaimer>
      </div>
    </>
  );
}

function Row({ label, value, truncate }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="shrink-0 text-[12.5px] text-on-surface-variant">{label}</dt>
      <dd className={`min-w-0 text-right text-[13px] font-medium text-on-surface ${truncate ? "truncate" : ""}`}>
        {value}
      </dd>
    </div>
  );
}
