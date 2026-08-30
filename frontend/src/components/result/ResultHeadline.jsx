import Icon from "../common/Icon.jsx";
import GlassCard from "../common/GlassCard.jsx";
import ScoreRing from "../common/ScoreRing.jsx";
import { toneForScore } from "../../data/constants.js";

/**
 * The headline verdict block (reference screen-3).
 *
 * Deliberately worded as a likelihood, never a determination: the ring is
 * labelled "AI LIKELIHOOD" and the verdict copy is hedged.
 */
export default function ResultHeadline({
  score,
  ringLabel = "AI LIKELIHOOD\nESTIMATE",
  verdict,
  blurb,
  code = "RES // AI_PROB",
  rows = [],
  actions,
  children,
  aiLabel = "AI LIKELIHOOD",
  altLabel = "HUMAN LIKELIHOOD",
  /** Explicit complement when the backend reports one; otherwise 100 − score. */
  altValue,
}) {
  const tone = toneForScore(score);
  const alt = altValue != null ? Math.round(altValue) : Math.max(0, Math.round(100 - score));

  return (
    <GlassCard strong code={code}>
      <div className="flex flex-col items-center gap-10 lg:flex-row lg:items-stretch lg:gap-12">
        <div className="flex shrink-0 items-center justify-center">
          <ScoreRing value={score} hex={tone.hex} label={ringLabel} />
        </div>

        <div className="flex w-full flex-col justify-center gap-6">
          {verdict && (
            <div>
              <h2 className="font-display text-[22px] font-bold leading-tight" style={{ color: tone.hex }}>
                {verdict}
              </h2>
              {blurb && (
                <p className="mt-2 text-[13.5px] leading-relaxed text-on-surface-variant/80">{blurb}</p>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <SplitTile label={aiLabel} value={`${Math.round(score)}%`} hex="#ddb8ff" />
            <SplitTile label={altLabel} value={`${alt}%`} hex="#b3d17a" />
          </div>

          {rows.length > 0 && (
            <div className="space-y-3">
              {rows.map((r) => (
                <div
                  key={r.label}
                  className="flex items-center justify-between gap-4 border-b border-outline-variant/20 pb-2.5"
                >
                  <span className="flex items-center gap-2 font-mono text-data-sm text-on-surface-variant">
                    {r.icon && <Icon name={r.icon} size={15} className="text-outline" />}
                    {r.label}
                  </span>
                  <span
                    className="shrink-0 font-mono text-[15px] font-medium tracking-[0.03em]"
                    style={{ color: r.hex || "#e5e1e4" }}
                  >
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
    <div className="relative overflow-hidden rounded border border-outline-variant/35 bg-surface-low/60 p-4">
      <span className="absolute inset-y-0 left-0 w-0.5" style={{ background: hex, opacity: 0.7 }} />
      <div className="mb-1.5 font-mono text-label-caps uppercase tracking-[0.12em] text-on-surface-variant/70">
        {label}
      </div>
      <div className="font-mono text-[19px] font-medium tracking-[0.03em]" style={{ color: hex }}>
        {value}
      </div>
    </div>
  );
}
