import { useState } from "react";
import GlassCard from "../common/GlassCard.jsx";
import Button from "../common/Button.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";

const COLLAPSED = 1400;

export default function ExtractedContent({ text, title = "Extracted content" }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;

  const long = text.length > COLLAPSED;
  const shown = open || !long ? text : `${text.slice(0, COLLAPSED)}…`;

  return (
    <GlassCard>
      <SectionTitle
        icon="article"
        right={<span className="text-[12px] text-outline">{text.length.toLocaleString()} chars extracted</span>}
      >
        {title}
      </SectionTitle>

      <div className="max-h-[460px] overflow-y-auto rounded-lg bg-surface-lowest/60 p-4">
        <p className="whitespace-pre-wrap font-mono text-[12.5px] leading-[1.85] text-on-surface-variant">{shown}</p>
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
