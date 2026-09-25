import Icon from "./Icon.jsx";

/**
 * Metric tile. An optional icon/label row, then the figure itself.
 *
 * `size="lg"` is a bigger variant for surfaces where the stats ARE the
 * page's main content (the Overview) rather than a secondary strip.
 */
export default function StatTile({
  label, value, icon, hex = "rgb(var(--on-surface))", sub, size = "md", className = "",
  iconBg = "bg-surface-high", iconColor = "text-on-surface-variant",
}) {
  const lg = size === "lg";
  return (
    <div
      className={`rounded-xl border border-outline-variant/40 bg-surface ${lg ? "p-6" : "p-4"} ${className}`}
    >
      <div className={`flex items-center justify-between gap-2 ${lg ? "mb-3" : "mb-2"}`}>
        {icon ? (
          <span className={`flex items-center justify-center rounded-lg ${iconBg} ${iconColor} ${lg ? "h-9 w-9" : "h-7 w-7"}`}>
            <Icon name={icon} size={lg ? 19 : 15} />
          </span>
        ) : (
          <span />
        )}
        <span className={`font-medium uppercase tracking-[0.04em] text-on-surface-variant/80 ${lg ? "text-[11.5px]" : "text-[10.5px]"}`}>
          {label}
        </span>
      </div>
      <div
        className={`font-display font-bold leading-none tracking-tight ${lg ? "text-[38px]" : "text-[26px]"}`}
        style={{ color: hex }}
      >
        {value}
      </div>
      {sub && <div className="mt-2 text-[11.5px] text-outline">{sub}</div>}
    </div>
  );
}

/** Compact variant for dense grids. */
export function MiniStat({ label, value, hex = "rgb(var(--on-surface))", icon }) {
  return (
    <div className="rounded-lg border border-outline-variant/40 bg-surface p-3.5">
      <div className="mb-1.5 flex items-center gap-1.5">
        {icon && <Icon name={icon} size={13} className="text-outline" />}
        <span className="text-[10.5px] font-medium uppercase tracking-[0.04em] text-on-surface-variant/80">
          {label}
        </span>
      </div>
      <div className="font-mono text-[18px] font-medium leading-none tabular-nums" style={{ color: hex }}>
        {value}
      </div>
    </div>
  );
}
