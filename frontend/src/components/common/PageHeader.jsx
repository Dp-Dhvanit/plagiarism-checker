import Icon from "./Icon.jsx";

/**
 * Page title block used at the top of every feature surface, with a status
 * pill on the right ("Idle" / "Ready" / "Analyzing" / "Complete").
 */

const STATUS_STYLE = {
  idle: { dot: "bg-outline-variant", text: "text-on-surface-variant", bg: "bg-surface-low", label: "Idle" },
  ready: { dot: "bg-primary", text: "text-primary", bg: "bg-primary-container/10", label: "Ready" },
  running: { dot: "bg-primary animate-pulse", text: "text-primary", bg: "bg-primary-container/10", label: "Analyzing" },
  done: { dot: "bg-tertiary", text: "text-tertiary", bg: "bg-tertiary-container/10", label: "Complete" },
  error: { dot: "bg-error", text: "text-error", bg: "bg-error-container/10", label: "Attention" },
};

/** Pass `status={null}` to show no status pill at all. */
export default function PageHeader({ eyebrow, title, subtitle, status = "idle", statusLabel, action }) {
  const s = status === null ? null : STATUS_STYLE[status] || STATUS_STYLE.idle;
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && (
          <p className="mb-1.5 text-[13px] font-medium text-on-surface-variant/80">{eyebrow}</p>
        )}
        <h1 className="font-display text-[26px] font-semibold leading-tight tracking-tight text-on-surface sm:text-[30px]">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-1.5 text-[14.5px] leading-relaxed text-on-surface-variant">{subtitle}</p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-3">
        {action}
        {s && (
          <span
            className={`hidden items-center gap-2 rounded-full px-3 py-1.5 md:flex ${s.bg}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
            <span className={`text-[12.5px] font-medium ${s.text}`}>{statusLabel || s.label}</span>
          </span>
        )}
      </div>
    </header>
  );
}

/** Inline section heading used inside cards. */
export function SectionTitle({ icon, children, right }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h2 className="flex items-center gap-2 font-display text-[15.5px] font-semibold text-on-surface">
        {icon && <Icon name={icon} size={18} className="text-primary" />}
        {children}
      </h2>
      {right}
    </div>
  );
}
