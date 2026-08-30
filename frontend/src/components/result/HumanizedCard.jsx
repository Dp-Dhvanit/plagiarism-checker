import { useState } from "react";
import GlassCard from "../common/GlassCard.jsx";
import Button from "../common/Button.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";

export default function HumanizedCard({ humanized, changed, onClose }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard?.writeText(humanized);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // No scanner: the rewrite has already finished by the time this renders.
  // Sweeping motion is reserved for work that is genuinely in flight.
  return (
    <GlassCard code="SEC // REWRITE">
      <SectionTitle
        icon="auto_fix_high"
        right={
          <div className="flex gap-2">
            <Button onClick={copy} size="sm" variant="ghost" icon={copied ? "check" : "content_copy"}>
              {copied ? "Copied" : "Copy"}
            </Button>
            <Button onClick={onClose} size="sm" variant="quiet" icon="close">
              Close
            </Button>
          </div>
        }
      >
        Rewritten draft — {changed} sentence{changed !== 1 ? "s" : ""} adjusted
      </SectionTitle>

      <div className="rounded border border-tertiary/25 bg-tertiary-container/[0.07] p-4">
        <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-on-surface">{humanized}</p>
      </div>

      <p className="mt-3 font-mono text-[11px] leading-relaxed text-outline">
        Stock phrasing replaced, contractions added, sentence rhythm varied. This changes the
        surface of the text, not its substance — read it before you use it.
      </p>
    </GlassCard>
  );
}
