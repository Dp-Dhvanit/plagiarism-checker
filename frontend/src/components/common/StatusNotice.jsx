import Icon from "./Icon.jsx";

/**
 * Non-error outcomes the backend can legitimately return — content that
 * cannot be scored, extraction failures, or an unavailable service. These
 * are informational, not faults.
 */
const COPY = {
  unanalyzable: {
    icon: "block",
    title: "Not suitable for AI detection",
    tone: "warn",
  },
  insufficient_text: { icon: "notes", title: "Not enough text to assess", tone: "warn" },
  insufficient: { icon: "notes", title: "Not enough text to assess", tone: "warn" },
  extraction_failure: { icon: "description_off", title: "Could not read this file", tone: "muted" },
  unavailable: { icon: "cloud_off", title: "AI analysis unavailable", tone: "muted" },
  mixed: { icon: "call_split", title: "Prose and code both detected", tone: "info" },
  aborted: { icon: "cancel", title: "Analysis aborted", tone: "muted" },
};

const TONES = {
  warn: "border-primary/30 bg-primary-container/10 text-primary",
  muted: "border-outline-variant/40 bg-surface-high/40 text-on-surface-variant",
  info: "border-secondary/30 bg-secondary-container/10 text-secondary",
};

export default function StatusNotice({ status, message, code }) {
  const meta = COPY[status] || COPY.unanalyzable;
  return (
    <div className={`relative overflow-hidden rounded-lg border p-5 ${TONES[meta.tone]}`}>
      {code && (
        <div className="absolute right-4 top-3 font-mono text-label-caps uppercase tracking-[0.14em] opacity-50">
          {code}
        </div>
      )}
      <div className="flex items-start gap-3.5">
        <Icon name={meta.icon} size={22} className="mt-0.5 shrink-0" />
        <div className="min-w-0">
          <p className="font-display text-[15px] font-bold">{meta.title}</p>
          {message && (
            <p className="mt-1.5 text-[13.5px] leading-relaxed text-on-surface-variant/85">{message}</p>
          )}
        </div>
      </div>
    </div>
  );
}
