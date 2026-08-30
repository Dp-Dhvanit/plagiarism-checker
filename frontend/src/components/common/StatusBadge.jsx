import Icon from "./Icon.jsx";
import { TONE } from "../../data/constants.js";

/**
 * Technical status flag. `chamfer` clips the corners for high-level
 * verdict flags, matching the "military-grade hardware" shape language.
 */
export default function StatusBadge({
  label,
  tone = TONE.neutral,
  icon,
  chamfer = false,
  dot = false,
  className = "",
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 border px-2.5 py-1 font-mono text-[10.5px] font-bold uppercase leading-none tracking-[0.09em] ${
        tone.bg
      } ${tone.border} ${tone.text} ${chamfer ? "chamfer" : "rounded"} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full" style={{ background: tone.hex }} />}
      {icon && <Icon name={icon} size={13} />}
      {label}
    </span>
  );
}

/** Neutral key/value chip — file type, size, counts. */
export function MetaChip({ icon, children }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded border border-outline-variant/40 bg-surface-high/50 px-2.5 py-1 font-mono text-[11px] text-on-surface-variant">
      {icon && <Icon name={icon} size={13} className="text-outline" />}
      {children}
    </span>
  );
}
