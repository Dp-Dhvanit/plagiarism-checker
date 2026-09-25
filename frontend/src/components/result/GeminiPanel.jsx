import GlassCard from "../common/GlassCard.jsx";
import Icon from "../common/Icon.jsx";
import ScoreBar from "../common/ScoreBar.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import { toneForScore } from "../../data/constants.js";

/**
 * The AI-assisted second opinion. Renders nothing when it didn't run — its
 * absence is reported by the one-line <AiAssistStatus/> instead, because a
 * missing optional second opinion is not a fault and shouldn't look like
 * one next to a valid local result.
 */
export default function GeminiPanel({ gemini }) {
  if (!gemini) return null;

  const pct = Math.round(gemini.ai_probability);
  const tone = toneForScore(pct);

  return (
    <GlassCard>
      <SectionTitle icon="neurology">AI-assisted check</SectionTitle>

      <ScoreBar label="Second-opinion AI probability" pct={pct} hex={tone.hex} />

      <p className="mt-4 text-[13.5px] leading-relaxed text-on-surface-variant">{gemini.explanation}</p>
      <p className="mt-2.5 text-[12px] leading-relaxed text-outline">
        A model-assisted estimate that runs alongside the local statistical detector. The two can
        disagree — where they do, treat the result as less certain, not more.
      </p>

      {gemini.flagged_sections?.length > 0 && (
        <div className="mt-5 border-t border-outline-variant/30 pt-5">
          <h3 className="mb-3 text-[12.5px] font-semibold text-on-surface">
            Flagged passages ({gemini.flagged_sections.length})
          </h3>
          <div className="space-y-2.5">
            {gemini.flagged_sections.map((s, i) => (
              <div key={i} className="rounded-lg border-l-[3px] border-secondary/50 bg-secondary-container/6 px-4 py-3">
                <p className="text-[13px] italic leading-relaxed text-on-surface">"{s.text}"</p>
                {s.reason && <p className="mt-1.5 text-[12px] leading-relaxed text-secondary">{s.reason}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </GlassCard>
  );
}

/**
 * One-line provenance note: which detectors produced the score on screen.
 *
 * "Ran" is decided from the full detector list, not just the legacy Gemini
 * field — Gemini can be rate-limited while Groq answers, and the old check
 * then claimed no second opinion had run when one had (and disagreed).
 */
export function AiAssistStatus({ gemini, detectors = [] }) {
  const hosted = detectors.filter((d) => !d.local && d.verdict !== "unavailable" && d.ai_probability != null);
  const count = detectors.length ? hosted.length : gemini ? 1 : 0;
  const ran = count > 0;

  return (
    <div className={`flex items-start gap-2.5 border-l-[3px] py-1 pl-3 ${ran ? "border-tertiary/60" : "border-outline-variant"}`}>
      <Icon name={ran ? "task_alt" : "info"} size={15} className={`mt-px shrink-0 ${ran ? "text-tertiary" : "text-outline"}`} />
      <p className="text-[12.5px] leading-relaxed text-on-surface-variant">
        {ran ? (
          <>
            Scored by the local statistical detector, with{" "}
            <span className="font-medium text-tertiary">
              {count} AI-assisted check{count !== 1 ? "s" : ""} completed
            </span>{" "}
            as {count !== 1 ? "second opinions" : "a second opinion"}.
          </>
        ) : (
          <>
            Only the local statistical detector ran — no AI-assisted second opinion was available for this
            analysis, so nothing corroborates this score.
          </>
        )}
      </p>
    </div>
  );
}
