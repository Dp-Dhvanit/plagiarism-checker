import Icon from "./Icon.jsx";

/**
 * Metric tile (reference screens 6 and 13). A monospaced ID, an optional
 * icon/label row, then the figure itself.
 *
 * `size="lg"` is a bigger variant for surfaces where the stats ARE the
 * page's main content (the Overview) rather than a secondary strip.
 */
export default function StatTile({ code, label, value, icon, hex = "#e5e1e4", sub, size = "md", className = "" }) {
  const lg = size === "lg";
  return (
    <div
      className={`relative overflow-hidden rounded-lg border border-outline-variant/35 bg-surface-low/50 ${
        lg ? "p-6" : "p-4"
      } ${className}`}
    >
      {code && (
        <div
          className={`font-mono uppercase tracking-[0.14em] text-outline/60 ${
            lg ? "mb-4 text-[11px]" : "mb-3 text-label-caps"
          }`}
        >
          {code}
        </div>
      )}
      <div className={`flex items-center justify-between gap-2 ${lg ? "mb-3" : "mb-2"}`}>
        {icon ? <Icon name={icon} size={lg ? 22 : 17} className="text-outline" /> : <span />}
        <span
          className={`font-mono uppercase text-on-surface-variant/70 ${
            lg ? "tracking-[0.1em] text-[11.5px]" : "tracking-[0.12em] text-label-caps"
          }`}
        >
          {label}
        </span>
      </div>
      <div
        className={`font-display font-extrabold leading-none tracking-tight ${lg ? "text-[42px]" : "text-[30px]"}`}
        style={{ color: hex }}
      >
        {value}
      </div>
      {sub && <div className="mt-2 font-mono text-[11px] text-outline">{sub}</div>}
    </div>
  );
}

/** Compact variant for dense grids. */
export function MiniStat({ label, value, hex = "#e5e1e4", icon }) {
  return (
    <div className="rounded-lg border border-outline-variant/35 bg-surface-low/50 p-3.5">
      <div className="mb-1.5 flex items-center gap-1.5">
        {icon && <Icon name={icon} size={13} className="text-outline" />}
        <span className="font-mono text-label-caps uppercase tracking-[0.12em] text-on-surface-variant/70">
          {label}
        </span>
      </div>
      <div className="font-mono text-[19px] font-medium leading-none tabular-nums" style={{ color: hex }}>
        {value}
      </div>
    </div>
  );
}
