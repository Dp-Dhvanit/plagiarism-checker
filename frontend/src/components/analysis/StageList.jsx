import Icon from "../common/Icon.jsx";

/**
 * The stage sequence (reference screen-4). Exactly one stage is active at a
 * time; completed stages recede, pending stages sit at low opacity.
 */

const STATE_META = {
  done: {
    ring: "border-tertiary/50 bg-tertiary-container/20 text-tertiary",
    label: "text-on-surface",
    tag: "text-tertiary",
    tagText: "DONE",
    icon: "check_circle",
    row: "opacity-70",
  },
  active: {
    ring: "border-transparent bg-secondary-container text-on-secondary-container animate-pulse-ring shadow-[0_0_12px_#7c03d3]",
    label: "text-secondary font-semibold",
    tag: "text-secondary animate-pulse",
    tagText: "PROCESSING",
    icon: "sync",
    row: "bg-secondary-container/10 border border-secondary/20 rounded -mx-3 px-3",
  },
  pending: {
    ring: "border-outline-variant/60 text-outline",
    label: "text-on-surface-variant",
    tag: "text-outline-variant",
    tagText: "PENDING",
    icon: "hourglass_empty",
    row: "opacity-40",
  },
  // The stage the sequence had *reached* when the request failed. Labelled
  // "HALTED" rather than "FAILED": the request errored, which is not the
  // same as this particular stage being the thing that broke.
  failed: {
    ring: "border-error/50 bg-error-container/25 text-error",
    label: "text-error font-semibold",
    tag: "text-error",
    tagText: "HALTED",
    icon: "error",
    row: "bg-error-container/10 border border-error/25 rounded -mx-3 px-3",
  },
};

export default function StageList({ stages, states, showNotes = true }) {
  return (
    <ol className="space-y-3.5">
      {stages.map((stage, i) => {
        const state = states[i] || "pending";
        const m = STATE_META[state];
        return (
          <li key={stage.id} className={`flex items-center gap-4 py-2 transition-all duration-300 ${m.row}`}>
            <span
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${m.ring}`}
            >
              <Icon
                name={m.icon}
                size={17}
                fill={state === "done"}
                className={state === "active" ? "animate-spin-slow" : ""}
              />
            </span>

            <span className="min-w-0 flex-1">
              <span className={`block font-mono text-[14px] leading-tight ${m.label}`}>{stage.label}</span>
              {showNotes && stage.note && (
                <span className="mt-1 block font-mono text-[11px] leading-tight text-outline">
                  {stage.note}
                </span>
              )}
            </span>

            <span className={`shrink-0 font-mono text-label-caps uppercase tracking-[0.12em] ${m.tag}`}>
              {state === "done" ? "100%" : m.tagText}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
