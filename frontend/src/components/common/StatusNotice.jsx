import Icon from "./Icon.jsx";

/**
 * Non-error outcomes the backend can legitimately return — content that
 * cannot be scored, extraction failures, or an unavailable service. These
 * are informational, not faults.
 */
const COPY = {
  unanalyzable: { icon: "block", title: "Not suitable for AI detection", tone: "warn" },
  insufficient_text: { icon: "notes", title: "Not enough text to assess", tone: "warn" },
  insufficient: { icon: "notes", title: "Not enough text to assess", tone: "warn" },
  extraction_failure: { icon: "description_off", title: "Could not read this file", tone: "muted" },
  unavailable: { icon: "cloud_off", title: "This check is currently unavailable", tone: "muted" },
  mixed: { icon: "call_split", title: "Prose and code both detected", tone: "info" },
  aborted: { icon: "cancel", title: "Analysis stopped", tone: "muted" },
};

const TONES = {
  warn: "border-warning/30 bg-warning-container/8 text-on-surface",
  muted: "border-outline-variant/50 bg-surface-low text-on-surface",
  info: "border-primary/25 bg-primary-container/6 text-on-surface",
};

const ICON_TONES = {
  warn: "text-warning",
  muted: "text-outline",
  info: "text-primary",
};

export default function StatusNotice({ status, message, code }) {
  const meta = COPY[status] || COPY.unanalyzable;
  return (
    <div className={`rounded-xl border p-5 ${TONES[meta.tone]}`}>
      <div className="flex items-start gap-3.5">
        <Icon name={meta.icon} size={22} className={`mt-0.5 shrink-0 ${ICON_TONES[meta.tone]}`} />
        <div className="min-w-0">
          <p className="font-display text-[15px] font-semibold">{meta.title}</p>
          {message && (
            <p className="mt-1.5 text-[13.5px] leading-relaxed text-on-surface-variant">{message}</p>
          )}
        </div>
      </div>
    </div>
  );
}
