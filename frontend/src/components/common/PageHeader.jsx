import Icon from "./Icon.jsx";

/**
 * Page title block used at the top of every feature surface, with the
 * status chip on the right ("SYSTEM IDLE" / "ANALYZING" / "COMPLETE").
 */

const STATUS_STYLE = {
  idle: { dot: "bg-outline-variant", text: "text-outline", label: "SYSTEM IDLE" },
  ready: { dot: "bg-primary animate-pulse", text: "text-primary", label: "READY" },
  running: { dot: "bg-secondary animate-pulse", text: "text-secondary", label: "ANALYZING" },
  done: { dot: "bg-tertiary", text: "text-tertiary", label: "COMPLETE" },
  error: { dot: "bg-error", text: "text-error", label: "FAULT" },
};

export default function PageHeader({ eyebrow, title, subtitle, status = "idle", statusLabel, action }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.idle;
  return (
    <header className="mb-7 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && (
          <div className="mb-2 flex items-center gap-2">
            <span className="h-1 w-1 rounded-full bg-primary" />
            <span className="font-mono text-label-caps uppercase tracking-[0.18em] text-primary/70">
              {eyebrow}
            </span>
          </div>
        )}
        <h1 className="font-display text-[28px] font-extrabold leading-[1.1] tracking-tight text-on-surface sm:text-[36px]">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-2 font-mono text-data-md text-on-surface-variant/80">{subtitle}</p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-3">
        {action}
        <div className="hidden items-center gap-2 rounded border border-outline-variant/40 bg-surface-high/60 px-3 py-1.5 md:flex">
          <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
          <span className={`font-mono text-label-caps uppercase tracking-[0.14em] ${s.text}`}>
            {statusLabel || s.label}
          </span>
        </div>
      </div>
    </header>
  );
}

/** Small inline section heading used inside cards. */
export function SectionTitle({ icon, children, right }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h2 className="flex items-center gap-2 font-display text-[15px] font-bold text-on-surface">
        {icon && <Icon name={icon} size={17} className="text-primary" />}
        {children}
      </h2>
      {right}
    </div>
  );
}
