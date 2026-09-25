import GlassCard from "../common/GlassCard.jsx";
import Icon from "../common/Icon.jsx";
import StatusBadge from "../common/StatusBadge.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import { TONE, toneForScore } from "../../data/constants.js";

export const AGREEMENT_TONE = {
  unanimous: TONE.human,
  mixed: TONE.uncertain,
  conflicted: TONE.ai,
  single: TONE.muted,
  none: TONE.muted,
};

// CSS `capitalize` turns "likely_ai" into "Likely Ai".
const VERDICT_LABEL = {
  likely_ai: "Likely AI",
  likely_human: "Likely Human",
  uncertain: "Uncertain",
};

const AGREEMENT_LABEL = {
  unanimous: "Detectors agree",
  mixed: "Partial agreement",
  conflicted: "Detectors disagree",
  single: "One detector",
  none: "No detector ran",
};

/**
 * One row per detector that produced a score, then a single line naming the
 * ones that couldn't run. The reason a detector was unavailable is
 * deliberately not shown: the backend's message can name server settings
 * (env vars), which don't belong in the browser.
 */
export function DetectorList({ detectors = [] }) {
  const ran = detectors.filter((d) => d.verdict !== "unavailable" && d.ai_probability != null);
  const unavailable = detectors.filter((d) => d.verdict === "unavailable" || d.ai_probability == null);

  return (
    <>
      <div className="space-y-2">
        {ran.map((d) => {
          const tone = toneForScore(d.ai_probability);
          const pct = Math.max(0, Math.min(100, Math.round(d.ai_probability)));
          return (
            <div
              key={d.provider}
              className="flex items-center gap-3 rounded-lg border-l-[3px] bg-surface-lowest/50 py-2.5 pl-3.5 pr-4"
              style={{ borderLeftColor: tone.hex }}
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface text-on-surface-variant">
                <Icon name={d.local ? "computer" : "cloud"} size={16} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[13.5px] font-medium text-on-surface">{d.label}</span>
                {d.explanation && (
                  <span className="block truncate text-[11.5px] text-on-surface-variant" title={d.explanation}>
                    {d.explanation}
                  </span>
                )}
                <span
                  className="mt-1.5 block h-1.5 w-full overflow-hidden rounded-full bg-surface-high/70"
                  role="img"
                  aria-label={`${d.label}: ${pct}% AI likelihood`}
                >
                  <span className="block h-full rounded-full" style={{ width: `${pct}%`, background: tone.hex }} />
                </span>
              </span>
              <span className="shrink-0 text-right">
                <span className="block text-[12px] font-medium" style={{ color: tone.hex }}>
                  {VERDICT_LABEL[d.verdict] || d.verdict.replace(/_/g, " ")}
                </span>
                <span className="block font-mono text-[11.5px] text-on-surface-variant">{pct}%</span>
              </span>
            </div>
          );
        })}
      </div>
      {unavailable.length > 0 && (
        <p className="mt-3 text-[11.5px] text-outline">
          {unavailable.length} more provider{unavailable.length !== 1 ? "s" : ""} not configured or
          unavailable: {unavailable.map((d) => d.label).join(", ")}.
        </p>
      )}
    </>
  );
}

/** Card wrapper: every detector's opinion side by side, and whether they agree. */
export default function DetectorBreakdown({ detectors = [], consensus }) {
  return (
    <GlassCard>
      <SectionTitle
        icon="hub"
        right={
          consensus && (
            <StatusBadge
              label={AGREEMENT_LABEL[consensus.agreement] || consensus.agreement}
              tone={AGREEMENT_TONE[consensus.agreement] || TONE.muted}
            />
          )
        }
      >
        Detector breakdown
      </SectionTitle>
      {consensus?.summary && (
        <p className="mb-3 text-[12.5px] leading-relaxed text-on-surface-variant">{consensus.summary}</p>
      )}
      <DetectorList detectors={detectors} />
      <p className="mt-4 border-t border-outline-variant/30 pt-3 text-[11.5px] leading-relaxed text-outline">
        Each detector scores the text independently and the scores are not averaged: when they disagree,
        that disagreement is the finding.
      </p>
    </GlassCard>
  );
}
