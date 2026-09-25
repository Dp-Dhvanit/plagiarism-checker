import Icon from "./Icon.jsx";
import { TONE } from "../../data/constants.js";

/**
 * Status pill. `chamfer` (the old sci-fi clipped-corner shape) is retired —
 * the prop is still accepted so call sites don't need to change, but every
 * badge now renders as a simple rounded pill.
 */
export default function StatusBadge({
  label,
  tone = TONE.neutral,
  icon,
  chamfer, // eslint-disable-line no-unused-vars -- accepted for API compatibility
  dot = false,
  className = "",
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[12px] font-medium leading-none ${
        tone.bg
      } ${tone.border} ${tone.text} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full" style={{ background: tone.hex }} />}
      {icon && <Icon name={icon} size={14} />}
      {label}
    </span>
  );
}

/** Neutral key/value chip — file type, size, counts. */
export function MetaChip({ icon, children }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-outline-variant/50 bg-surface-low px-2.5 py-1 text-[12px] text-on-surface-variant">
      {icon && <Icon name={icon} size={14} className="text-outline" />}
      {children}
    </span>
  );
}
