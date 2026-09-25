import Icon from "../common/Icon.jsx";
import Button from "../common/Button.jsx";
import GlassCard from "../common/GlassCard.jsx";
import StageList from "./StageList.jsx";
import ProgressRail from "./ProgressRail.jsx";
import { RUN_COPY } from "../../data/stages.js";

/**
 * The processing experience — one consistent layout for every analysis
 * type (text/document/code/image), so the app doesn't feel like four
 * different products. Progress and stages are driven entirely by
 * useAnalysisRun, which is tied to the real request; nothing here invents
 * stages the backend doesn't actually perform.
 */
export default function AnalysisRunner({ kind, run, stages, subject, onAbort, onRetry, onCancel }) {
  const copy = RUN_COPY[kind] || RUN_COPY.text;
  const { phase, progress, stageStates, elapsedMs, overrunning, error } = run;
  const failed = phase === "error";

  return (
    <GlassCard strong className="mx-auto max-w-2xl">
      <div className="py-2">
        <div className="mb-7 text-center">
          <div
            className={`mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full ${
              failed ? "bg-error-container/10 text-error" : "bg-primary-container/10 text-primary"
            }`}
          >
            <Icon
              name={failed ? "error" : "progress_activity"}
              size={22}
              className={failed ? "" : "animate-spin-slow"}
            />
          </div>
          <h2 className={`font-display text-[22px] font-semibold ${failed ? "text-error" : "text-on-surface"}`}>
            {failed ? "Analysis failed" : `${copy.title}…`}
          </h2>
          <p className="mt-1.5 text-[13.5px] text-on-surface-variant">
            {failed ? "The sequence stopped before it could finish." : copy.subtitle}
          </p>
        </div>

        {subject?.name && (
          <div className="mb-6 flex items-center gap-3 rounded-lg border border-outline-variant/40 bg-surface-lowest/60 px-4 py-3">
            {subject.previewUrl ? (
              <img src={subject.previewUrl} alt="" className="h-10 w-10 shrink-0 rounded-md object-cover" />
            ) : (
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-surface-high text-on-surface-variant">
                <Icon name="description" size={18} />
              </span>
            )}
            <span className="min-w-0 truncate text-[13.5px] font-medium text-on-surface">{subject.name}</span>
          </div>
        )}

        <div className="mb-7">
          <ProgressRail progress={progress} phase={phase} elapsedMs={elapsedMs} overrunning={overrunning} />
        </div>

        <StageList stages={stages} states={stageStates} />

        {failed && (
          <div className="mt-5 flex items-start gap-3 rounded-lg border border-error/30 bg-error-container/6 px-4 py-3.5">
            <Icon name="report" size={18} className="mt-px shrink-0 text-error" />
            <p className="text-[13px] leading-relaxed text-on-surface">{error}</p>
          </div>
        )}

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          {failed ? (
            <>
              <Button onClick={onRetry} icon="refresh" variant="primary">Retry analysis</Button>
              <Button onClick={onCancel} icon="arrow_back" variant="ghost">Back to input</Button>
            </>
          ) : (
            <Button onClick={onAbort} variant="ghost" size="sm">Cancel</Button>
          )}
        </div>
      </div>
    </GlassCard>
  );
}
