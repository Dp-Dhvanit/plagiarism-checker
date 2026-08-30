import { useState } from "react";
import GlassCard from "../common/GlassCard.jsx";
import Icon from "../common/Icon.jsx";
import ScoreBar from "../common/ScoreBar.jsx";
import { MetaChip } from "../common/StatusBadge.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import { toneForSimilarity } from "../../data/constants.js";

/**
 * Overlap against previously analyzed documents. Framed as a similarity
 * indicator — overlap is evidence to review, not a plagiarism finding.
 */
export default function SimilarityPanel({ similarity }) {
  const [expanded, setExpanded] = useState(null);
  if (!similarity) return null;

  // Headline is the strongest single passage, not the mean: the mean drifts
  // upward purely as the archive grows, so it isn't comparable over time.
  const top = Math.round(similarity.top_match ?? similarity.overall_similarity);
  const portion = Math.round(similarity.matched_portion ?? 0);
  const mean = Math.round(similarity.overall_similarity);
  const tone = toneForSimilarity(top);

  return (
    <GlassCard code="SEC // SIMILARITY">
      <SectionTitle
        icon="compare_arrows"
        right={<MetaChip icon="database">{similarity.corpus_size} passages on file</MetaChip>}
      >
        Similarity indicator
      </SectionTitle>

      <ScoreBar label="Strongest passage match" pct={top} hex={tone.hex} />
      <ScoreBar label="Share of document matched" pct={portion} hex={tone.hex} />

      <p className="mt-3 text-[12.5px] leading-relaxed text-outline">
        This document was split into {similarity.chunks_compared || 0} passage
        {similarity.chunks_compared === 1 ? "" : "s"} and each was compared against the stored
        corpus. The figures above are the single closest match and the proportion of passages that
        crossed the reporting threshold (mean across all passages: {mean}%). Overlap is not
        automatically plagiarism — quotations, shared sources and common phrasing all raise it.
      </p>

      {similarity.matches?.length > 0 ? (
        <div className="mt-5 border-t border-outline-variant/20 pt-5">
          <h3 className="mb-3 font-mono text-label-caps uppercase tracking-[0.14em] text-primary">
            Matching passages ({similarity.matches.length})
          </h3>
          <div className="space-y-2.5">
            {similarity.matches.map((m, i) => {
              const long = m.query_excerpt.length > 150;
              const open = expanded === i;
              return (
                <div key={i} className="rounded border border-outline-variant/30 bg-surface-low/50 p-4">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <span className="flex min-w-0 items-center gap-2 font-mono text-[12px] text-on-surface-variant">
                      <Icon name="description" size={14} className="shrink-0 text-outline" />
                      <span className="truncate">{m.source_file}</span>
                    </span>
                    <span
                      className="shrink-0 font-mono text-[12px] font-bold"
                      style={{ color: toneForSimilarity(m.score).hex }}
                    >
                      {m.score}% match
                    </span>
                  </div>
                  <p className="text-[12.5px] leading-relaxed text-on-surface-variant/75">
                    {open || !long ? m.query_excerpt : `${m.query_excerpt.slice(0, 150)}…`}
                  </p>
                  {long && (
                    <button
                      type="button"
                      onClick={() => setExpanded(open ? null : i)}
                      className="mt-2 font-mono text-[11px] uppercase tracking-[0.1em] text-primary hover:underline"
                    >
                      {open ? "Show less" : "Show more"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="mt-5 border-t border-outline-variant/20 pt-5 text-[13.5px] leading-relaxed text-on-surface-variant/70">
          {similarity.note || "No closely matching passages were found."}
        </p>
      )}
    </GlassCard>
  );
}
