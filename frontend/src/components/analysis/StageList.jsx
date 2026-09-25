import Icon from "../common/Icon.jsx";

/**
 * The stage sequence. Exactly one stage is active at a time; completed
 * stages show a check, pending stages sit dimmed.
 */

const STATE_META = {
  done: {
    ring: "bg-tertiary-container/12 text-tertiary",
    label: "text-on-surface",
    tag: "text-tertiary",
    tagText: "Done",
    icon: "check",
    row: "opacity-70",
  },
  active: {
    ring: "bg-primary-container/12 text-primary",
    label: "text-on-surface font-medium",
    tag: "text-primary",
    tagText: "In progress",
    icon: "progress_activity",
    row: "",
  },
  pending: {
    ring: "bg-surface-high text-outline",
    label: "text-on-surface-variant",
    tag: "text-outline",
    tagText: "Waiting",
    icon: "hourglass_empty",
    row: "opacity-45",
  },
  failed: {
    // The stage the sequence had *reached* when the request failed —
    // labelled "Halted" rather than "Failed": the request errored, which
    // is not necessarily this specific stage's fault.
    ring: "bg-error-container/12 text-error",
    label: "text-error font-medium",
    tag: "text-error",
    tagText: "Halted",
    icon: "error",
    row: "",
  },
};

export default function StageList({ stages, states, showNotes = true }) {
  return (
    <ol className="space-y-1">
      {stages.map((stage, i) => {
        const state = states[i] || "pending";
        const m = STATE_META[state];
        return (
          <li
            key={stage.id}
            className={`flex items-center gap-3.5 rounded-lg px-2 py-2.5 transition-opacity duration-300 ${m.row}`}
          >
            <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${m.ring}`}>
              <Icon name={m.icon} size={16} className={state === "active" ? "animate-spin-slow" : ""} />
            </span>

            <span className="min-w-0 flex-1">
              <span className={`block text-[14px] leading-tight ${m.label}`}>{stage.label}</span>
              {showNotes && stage.note && (
                <span className="mt-0.5 block text-[12px] leading-tight text-on-surface-variant">
                  {stage.note}
                </span>
              )}
            </span>

            <span className={`shrink-0 text-[12px] font-medium ${m.tag}`}>{m.tagText}</span>
          </li>
        );
      })}
    </ol>
  );
}
