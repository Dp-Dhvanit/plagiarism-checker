import { useId, useState } from "react";
import Icon from "../common/Icon.jsx";

/**
 * Progressive disclosure for the deep statistics.
 *
 * The headline figures answer "what did it find". Perplexity, burstiness,
 * the four signal weights and the per-sentence map answer "how did it get
 * there" — kept one click away so they stay available without competing
 * with the primary result.
 */
export default function TechnicalDetail({ summary, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={id}
        className="group flex w-full items-center gap-3 rounded-lg border border-outline-variant/30 bg-surface-low/40 px-5 py-4 text-left transition-all duration-200 hover:border-primary/35 hover:bg-surface-low/70"
      >
        <Icon name="analytics" size={18} className="shrink-0 text-outline transition-colors group-hover:text-primary" />

        <span className="min-w-0 flex-1">
          <span className="block font-display text-[14.5px] font-bold text-on-surface">
            Technical detail
          </span>
          {summary && (
            <span className="mt-0.5 block text-[12.5px] leading-snug text-outline">{summary}</span>
          )}
        </span>

        <span className="flex shrink-0 items-center gap-2">
          <span className="hidden font-mono text-label-caps uppercase tracking-[0.12em] text-outline sm:inline">
            {open ? "Hide" : "Show"}
          </span>
          <Icon
            name="expand_more"
            size={20}
            className={`text-outline transition-transform duration-300 group-hover:text-primary ${
              open ? "rotate-180" : ""
            }`}
          />
        </span>
      </button>

      {open && (
        <div id={id} className="stagger mt-4 space-y-4">
          {children}
        </div>
      )}
    </div>
  );
}
