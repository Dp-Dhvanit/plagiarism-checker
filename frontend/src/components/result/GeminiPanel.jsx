import GlassCard from "../common/GlassCard.jsx";
import Icon from "../common/Icon.jsx";
import ScoreBar from "../common/ScoreBar.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import { toneForScore } from "../../data/constants.js";

/**
 * The AI-assisted second opinion.
 *
 * Two states, deliberately asymmetric in weight:
 *
 *  • Ran      → a full panel carrying what it actually returned (its own
 *               probability estimate, its reasoning, any flagged passages).
 *  • Did not  → nothing here at all. Its absence is reported by the
 *               one-line <AiAssistStatus/> note in the headline instead,
 *               because a missing optional second opinion is not a fault
 *               and must not look like one next to a valid local result.
 *
 * Confidence is intentionally not repeated here — the headline already
 * carries it as a primary field.
 */
export default function GeminiPanel({ gemini }) {
  if (!gemini) return null;

  const pct = Math.round(gemini.ai_probability);
  const tone = toneForScore(pct);

  return (
    <GlassCard code="SEC // AI_ASSIST">
      <SectionTitle icon="neurology">AI-assisted check</SectionTitle>

      <ScoreBar label="Second-opinion AI probability" pct={pct} hex={tone.hex} />

      <p className="mt-4 text-[13.5px] leading-relaxed text-on-surface-variant/85">
        {gemini.explanation}
      </p>
      <p className="mt-2.5 text-[12.5px] leading-relaxed text-outline">
        A model-assisted estimate that runs alongside the local statistical detector. The two can
        disagree — where they do, treat the result as less certain, not more.
      </p>

      {gemini.flagged_sections?.length > 0 && (
        <div className="mt-5 border-t border-outline-variant/20 pt-5">
          <h3 className="mb-3 font-mono text-label-caps uppercase tracking-[0.14em] text-secondary">
            Flagged passages ({gemini.flagged_sections.length})
          </h3>
          <div className="space-y-2.5">
            {gemini.flagged_sections.map((s, i) => (
              <div
                key={i}
                className="rounded border-l-2 border-secondary/60 bg-secondary-container/10 px-4 py-3"
              >
                <p className="text-[13px] italic leading-relaxed text-on-surface">“{s.text}”</p>
                {s.reason && (
                  <p className="mt-1.5 text-[12px] leading-relaxed text-secondary/85">{s.reason}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </GlassCard>
  );
}

/**
 * One-line provenance note for the headline: which detectors produced the
 * score on screen. Informational in both states — never an error.
 */
export function AiAssistStatus({ gemini }) {
  const ran = Boolean(gemini);

  return (
    <div
      className={`flex items-start gap-2.5 border-l-2 py-1 pl-3 ${
        ran ? "border-tertiary/50" : "border-outline-variant/50"
      }`}
    >
      <Icon
        name={ran ? "task_alt" : "info"}
        size={15}
        className={`mt-px shrink-0 ${ran ? "text-tertiary" : "text-outline"}`}
      />
      <p className="text-[12.5px] leading-relaxed text-outline">
        {ran ? (
          <>
            Scored by the local statistical detector, with an
            <span className="text-tertiary"> AI-assisted check completed</span> as a second opinion.
          </>
        ) : (
          <>
            Scored by the local statistical detector. The optional AI-assisted second opinion
            didn&rsquo;t run for this analysis — the figures above are unaffected.
          </>
        )}
      </p>
    </div>
  );
}
