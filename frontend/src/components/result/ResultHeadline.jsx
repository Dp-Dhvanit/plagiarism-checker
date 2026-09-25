import Icon from "../common/Icon.jsx";
import GlassCard from "../common/GlassCard.jsx";
import ScoreRing from "../common/ScoreRing.jsx";
import { toneForScore } from "../../data/constants.js";

/**
 * The headline verdict block — the first thing a user sees on any result
 * page. Deliberately worded as a likelihood, never a determination.
 */
export default function ResultHeadline({
  score,
  ringLabel = "AI LIKELIHOOD\nESTIMATE",
  verdict,
  verdictTone, // colours the verdict when it isn't simply the score's band (e.g. detectors disagree)
  blurb,
  reason,
  rows = [],
  actions,
  children,
  aiLabel = "AI likelihood",
  altLabel = "Human likelihood",
  altValue,
}) {
  const tone = toneForScore(score);
  const verdictHex = (verdictTone || tone).hex;
  const alt = altValue != null ? Math.round(altValue) : Math.max(0, Math.round(100 - score));

  return (
    <GlassCard strong>
      <div className="flex flex-col items-center gap-10 lg:flex-row lg:items-stretch lg:gap-12">
        <div className="flex shrink-0 items-center justify-center">
          <ScoreRing value={score} hex={tone.hex} label={ringLabel} />
        </div>

        <div className="flex w-full flex-col justify-center gap-6">
          {verdict && (
            <div>
              <h2 className="font-display text-[22px] font-semibold leading-tight" style={{ color: verdictHex }}>
                {verdict}
              </h2>
              {blurb && <p className="mt-2 text-[13.5px] leading-relaxed text-on-surface-variant">{blurb}</p>}
              {reason && <p className="mt-1.5 text-[12.5px] leading-relaxed text-outline">{reason}</p>}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <SplitTile label={aiLabel} value={`${Math.round(score)}%`} hex="#D97862" />
            <SplitTile label={altLabel} value={`${alt}%`} hex="#6FAF7C" />
          </div>

          {rows.length > 0 && (
            <div className="space-y-2.5">
              {rows.map((r) => (
                <div
                  key={r.label}
                  className="flex items-center justify-between gap-4 border-b border-outline-variant/30 pb-2.5"
                >
                  <span className="flex items-center gap-2 text-[13px] text-on-surface-variant">
                    {r.icon && <Icon name={r.icon} size={15} className="text-outline" />}
                    {r.label}
                  </span>
                  <span className="shrink-0 text-[14px] font-medium" style={{ color: r.hex || "rgb(var(--on-surface))" }}>
                    {r.value}
                  </span>
                </div>
              ))}
            </div>
          )}

          {children}
          {actions && <div className="flex flex-wrap gap-3">{actions}</div>}
        </div>
      </div>
    </GlassCard>
  );
}

function SplitTile({ label, value, hex }) {
  return (
    <div className="rounded-lg border border-outline-variant/40 bg-surface-lowest/60 p-4">
      <div className="mb-1.5 text-[11.5px] font-medium uppercase tracking-[0.03em] text-on-surface-variant">
        {label}
      </div>
      <div className="text-[19px] font-semibold" style={{ color: hex }}>
        {value}
      </div>
    </div>
  );
}
