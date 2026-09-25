/**
 * Horizontal signal meter. Used for detection signals, similarity, and the
 * signal-distribution block.
 *
 * `value` is 0–1 unless `pct` is given (0–100).
 */
export default function ScoreBar({ label, value, pct, description, hex = "#7C6EEA", compact = false }) {
  const percent = Math.round(pct != null ? pct : (Number(value) || 0) * 100);
  const clamped = Math.min(Math.max(percent, 0), 100);

  return (
    <div className={compact ? "mb-2.5" : "mb-4"}>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <span className="truncate text-[13.5px] font-medium text-on-surface-variant">{label}</span>
        <span className="shrink-0 font-mono text-[13px] font-medium tabular-nums" style={{ color: hex }}>
          {clamped}%
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-surface-high">
        <div
          className="h-full rounded-full"
          style={{
            width: `${clamped}%`,
            background: hex,
            transition: "width 0.9s cubic-bezier(0.22,1,0.36,1)",
          }}
        />
      </div>
      {description && !compact && (
        <p className="mt-1.5 text-[12.5px] leading-snug text-outline">{description}</p>
      )}
    </div>
  );
}
