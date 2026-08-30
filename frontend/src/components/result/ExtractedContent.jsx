import { useState } from "react";
import GlassCard from "../common/GlassCard.jsx";
import Button from "../common/Button.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";

/**
 * Extracted document text (reference screen-6, "CONTENT_VIEW").
 *
 * The reference highlights individual sentences by classification. The
 * backend returns a plain extraction preview with no per-sentence spans
 * for uploads, so this renders the text faithfully rather than inventing
 * highlight bands the analysis did not produce.
 */
const COLLAPSED = 1400;

export default function ExtractedContent({ text, title = "Extracted content" }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;

  const long = text.length > COLLAPSED;
  const shown = open || !long ? text : `${text.slice(0, COLLAPSED)}…`;

  return (
    <GlassCard code="SEC // CONTENT_VIEW">
      <SectionTitle
        icon="article"
        right={
          <span className="font-mono text-[11px] text-outline">
            {text.length.toLocaleString()} chars extracted
          </span>
        }
      >
        {title}
      </SectionTitle>

      <div className="max-h-[460px] overflow-y-auto rounded border border-outline-variant/25 bg-surface-lowest/50 p-4">
        <p className="whitespace-pre-wrap font-mono text-[12.5px] leading-[1.9] text-on-surface-variant/80">
          {shown}
        </p>
      </div>

      {long && (
        <div className="mt-3">
          <Button onClick={() => setOpen(!open)} size="sm" variant="quiet" icon={open ? "expand_less" : "expand_more"}>
            {open ? "Collapse" : "Show full extraction"}
          </Button>
        </div>
      )}
    </GlassCard>
  );
}
