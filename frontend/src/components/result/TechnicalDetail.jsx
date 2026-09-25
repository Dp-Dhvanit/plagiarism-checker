import { useId, useState } from "react";
import Icon from "../common/Icon.jsx";

/**
 * Progressive disclosure for the deep statistics.
 *
 * The headline figures answer "what did it find". Perplexity, burstiness,
 * signal weights and the per-sentence map answer "how did it get there" —
 * kept one click away so they stay available without competing with the
 * primary result.
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
        className="group flex w-full items-center gap-3 rounded-xl border border-outline-variant/40 bg-surface px-5 py-4 text-left transition-colors hover:border-primary/40 hover:bg-primary-container/4"
      >
        <Icon name="analytics" size={19} className="shrink-0 text-outline transition-colors group-hover:text-primary" />

        <span className="min-w-0 flex-1">
          <span className="block font-display text-[14.5px] font-semibold text-on-surface">
            Technical detail
          </span>
          {summary && (
            <span className="mt-0.5 block text-[12.5px] leading-snug text-on-surface-variant">{summary}</span>
          )}
        </span>

        <span className="flex shrink-0 items-center gap-2">
          <span className="hidden text-[12.5px] font-medium text-outline sm:inline">
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
