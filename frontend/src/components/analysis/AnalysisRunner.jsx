import Icon from "../common/Icon.jsx";
import Button from "../common/Button.jsx";
import GlassCard from "../common/GlassCard.jsx";
import StageList from "./StageList.jsx";
import ProgressRail from "./ProgressRail.jsx";
import LogStream from "./LogStream.jsx";
import FilePreview from "../common/FilePreview.jsx";
import { RUN_COPY } from "../../data/stages.js";

/**
 * The processing experience. One component, four shapes — chosen by the
 * kind of content being analyzed, following the reference screens:
 *
 *   text     → screen-4  : centred HUD, linear stage list
 *   document → screen-7/8: payload card + stages + live log
 *   code     → screen-10 : source map + analysis sequence + log
 *   image    → screen-11 : scanned preview + sequence log
 *
 * All four are driven by the same run state, so progress can never diverge
 * from the real request.
 */
export default function AnalysisRunner({ kind, run, stages, subject, onAbort, onRetry, onCancel }) {
  const copy = RUN_COPY[kind] || RUN_COPY.text;
  const { phase, progress, stageIndex, stageStates, elapsedMs, overrunning, error } = run;
  const failed = phase === "error";

  const header = (
    <div className="mb-8 text-center">
      <h2
        className={`font-display text-[26px] font-bold tracking-tight sm:text-[30px] ${
          failed ? "text-error" : "text-primary"
        }`}
      >
        {failed ? "Analysis failed" : `${copy.title}…`}
      </h2>
      <p className="mt-2 font-mono text-[13.5px] text-outline">
        {failed ? "The sequence stopped before it could finish." : copy.subtitle}
      </p>
    </div>
  );

  const controls = (
    <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
      {failed ? (
        <>
          <Button onClick={onRetry} icon="refresh" variant="primary">Retry analysis</Button>
          <Button onClick={onCancel} icon="arrow_back" variant="ghost">Back to input</Button>
        </>
      ) : (
        <Button onClick={onAbort} variant="danger" size="sm">Abort sequence</Button>
      )}
    </div>
  );

  const errorBlock = failed && (
    <div className="mt-6 flex items-start gap-3 rounded border border-error/35 bg-error-container/15 px-4 py-3.5">
      <Icon name="report" size={18} className="mt-px shrink-0 text-error" />
      <p className="font-mono text-[12.5px] leading-relaxed text-error">{error}</p>
    </div>
  );

  // ── Text: centred HUD ──────────────────────────────────────────────────
  if (kind === "text") {
    return (
      <GlassCard strong brackets scanner={failed ? null : "primary"} code={`${copy.code} // ${failed ? "HALTED" : "LIVE"}`}>
        <div className="mx-auto max-w-2xl py-2">
          {header}
          <div className="mb-9">
            <ProgressRail progress={progress} phase={phase} elapsedMs={elapsedMs} overrunning={overrunning} />
          </div>
          <StageList stages={stages} states={stageStates} />
          {errorBlock}
          {controls}
        </div>
      </GlassCard>
    );
  }

  // ── Image: scanned preview beside the sequence log ─────────────────────
  if (kind === "image") {
    return (
      <div className="space-y-6">
        {header}
        <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
          <GlassCard code="SEC_PREVIEW // SCAN" bodyClassName="px-4 pb-4 pt-11">
            <div className="relative overflow-hidden rounded border border-outline-variant/40 bg-surface-lowest">
              {!failed && <div className="scanner" />}
              {subject?.previewUrl ? (
                <img
                  src={subject.previewUrl}
                  alt="Image being analyzed"
                  className="max-h-[420px] w-full object-contain"
                />
              ) : (
                <div className="flex h-64 items-center justify-center text-outline">
                  <Icon name="image" size={40} />
                </div>
              )}
              {/* Reticle framing, purely as a viewport treatment */}
              <div className="pointer-events-none absolute inset-4 border border-primary/20" />
              <div className="pointer-events-none absolute left-3 top-3 h-5 w-5 border-l border-t border-primary/60" />
              <div className="pointer-events-none absolute right-3 top-3 h-5 w-5 border-r border-t border-primary/60" />
              <div className="pointer-events-none absolute bottom-3 left-3 h-5 w-5 border-b border-l border-primary/60" />
              <div className="pointer-events-none absolute bottom-3 right-3 h-5 w-5 border-b border-r border-primary/60" />
            </div>
            {subject?.name && (
              <p className="mt-3 truncate font-mono text-[11.5px] text-outline">{subject.name}</p>
            )}
          </GlassCard>

          <GlassCard code="SEQUENCE_LOG">
            <div className="mb-6">
              <ProgressRail progress={progress} phase={phase} elapsedMs={elapsedMs} overrunning={overrunning} />
            </div>
            <StageList stages={stages} states={stageStates} />
            {errorBlock}
            {controls}
          </GlassCard>
        </div>
      </div>
    );
  }

  // ── Code: source map beside sequence + log ─────────────────────────────
  if (kind === "code") {
    return (
      <div className="space-y-6">
        {header}
        <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
          <GlassCard code="SEC_01 // VISUAL_MAP" bodyClassName="px-0 pb-0 pt-11">
            <div className="relative max-h-[420px] overflow-auto px-5 pb-5">
              {!failed && <div className="scanner scanner-purple" />}
              <pre className="whitespace-pre-wrap break-words font-mono text-[11.5px] leading-[1.75] text-on-surface-variant/60">
                {subject?.source?.slice(0, 4000) || "// no inline source — analyzing uploaded file"}
              </pre>
            </div>
          </GlassCard>

          <div className="space-y-6">
            <GlassCard code="ANALYSIS_SEQUENCE">
              <div className="mb-6">
                <ProgressRail progress={progress} phase={phase} elapsedMs={elapsedMs} overrunning={overrunning} />
              </div>
              <StageList stages={stages} states={stageStates} showNotes={false} />
              {errorBlock}
              {controls}
            </GlassCard>
            <LogStream stages={stages} stageIndex={stageIndex} phase={phase} error={error} height="h-52" />
          </div>
        </div>
      </div>
    );
  }

  // ── Document / summary: payload card + stages + live log ───────────────
  return (
    <div className="space-y-6">
      {header}

      {subject?.name && (
        <FilePreview
          name={subject.name}
          size={subject.size}
          meta={subject.meta}
          status={failed ? "HALTED" : phase === "done" ? "COMPLETE" : "PROCESSING…"}
          tone={failed ? "purple" : "primary"}
        />
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <GlassCard code={`${copy.code} // ${failed ? "HALTED" : "IN_PROGRESS"}`} scanner={failed ? null : "primary"}>
          <div className="mb-7">
            <ProgressRail progress={progress} phase={phase} elapsedMs={elapsedMs} overrunning={overrunning} />
          </div>
          <StageList stages={stages} states={stageStates} showNotes={false} />
          {errorBlock}
          {controls}
        </GlassCard>

        <LogStream stages={stages} stageIndex={stageIndex} phase={phase} error={error} height="h-[420px]" />
      </div>
    </div>
  );
}
