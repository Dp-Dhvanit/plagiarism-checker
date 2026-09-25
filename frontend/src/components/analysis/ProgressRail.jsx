import { formatSeconds } from "../../lib/format.js";

/**
 * The headline progress bar. Its fill is driven by useAnalysisRun, which
 * never lets it park: it eases through the scripted stages, then creeps
 * while the real request is still out, and only completes when the
 * response actually lands — this bar always reflects genuine progress
 * information, never a fake animation invented to look busy.
 */
export default function ProgressRail({ progress, phase, elapsedMs, overrunning }) {
  const fill =
    phase === "error" ? "progress-failed"
    : phase === "done" || phase === "finishing" ? "progress-done"
    : "progress-live";

  return (
    <div>
      <div className="h-2 overflow-hidden rounded-full bg-surface-high">
        <div
          className={`h-full rounded-full ${fill}`}
          style={{ width: `${Math.max(progress, 1.5)}%` }}
        />
      </div>

      <div className="mt-2.5 flex items-center justify-between text-[12px]">
        <span className={phase === "error" ? "text-error" : "text-on-surface-variant"}>
          {phase === "error"
            ? "Stopped before finishing"
            : phase === "done" || phase === "finishing"
            ? "Complete"
            : overrunning
            ? "Still processing — larger inputs take longer"
            : "Processing…"}
        </span>
        <span className="tabular-nums text-outline">
          {Math.round(progress)}% · {formatSeconds(elapsedMs)}
        </span>
      </div>
    </div>
  );
}
