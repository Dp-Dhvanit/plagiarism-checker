import { formatSeconds } from "../../lib/format.js";

/**
 * The headline progress bar. Its fill is driven by useAnalysisRun, which
 * never lets it park: it eases through the scripted stages, then creeps
 * while the real request is still out, and only completes when the
 * response actually lands.
 */
export default function ProgressRail({ progress, phase, elapsedMs, overrunning, tone = "live" }) {
  const fill =
    phase === "error" ? "progress-failed"
    : phase === "done" || phase === "finishing" ? "progress-done"
    : "progress-live";

  return (
    <div>
      <div className="h-2 overflow-hidden rounded-full border border-outline-variant/40 bg-surface-high">
        {/*
          No CSS width transition here. `progress` is already advanced every
          frame by useAnalysisRun's rAF loop; layering a transition on top
          restarts it each frame, so the bar renders a fraction of the real
          value and appears frozen near zero while the label climbs.
        */}
        <div
          className={`h-full rounded-full ${fill}`}
          style={{ width: `${Math.max(progress, 1.5)}%` }}
        />
      </div>

      <div className="mt-2.5 flex items-center justify-between font-mono text-[11px] tracking-[0.08em]">
        <span className={phase === "error" ? "text-error" : "text-outline"}>
          {phase === "error"
            ? "SEQUENCE HALTED"
            : phase === "done" || phase === "finishing"
            ? "SEQUENCE COMPLETE"
            : overrunning
            ? "STILL PROCESSING — LARGER INPUTS TAKE LONGER"
            : "SEQUENCE RUNNING"}
        </span>
        <span className="tabular-nums text-outline">
          {Math.round(progress)}% · {formatSeconds(elapsedMs)}
        </span>
      </div>
    </div>
  );
}
