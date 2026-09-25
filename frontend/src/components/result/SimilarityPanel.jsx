import { useState } from "react";
import GlassCard from "../common/GlassCard.jsx";
import Icon from "../common/Icon.jsx";
import ScoreBar from "../common/ScoreBar.jsx";
import StatusBadge, { MetaChip } from "../common/StatusBadge.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import { TONE, toneForSimilarity } from "../../data/constants.js";
import { formatDateTime } from "../../lib/format.js";

/**
 * Overlap against previously analyzed documents.
 *
 * A passage only counts toward "verified" when embedding similarity is
 * corroborated by shared wording (word/n-gram overlap) — semantic closeness
 * alone is not enough, because independently written text on the same
 * subject can score just as high on embeddings as a genuine paraphrase.
 * Framed throughout as an overlap indicator, not a plagiarism verdict.
 */
export default function SimilarityPanel({ similarity }) {
  const [expanded, setExpanded] = useState(null);
  if (!similarity) return null;

  const verifiedPortion = Math.round(similarity.matched_portion ?? 0);
  const possiblePortion = Math.round(similarity.possible_portion ?? 0);
  const top = Math.round(similarity.top_match ?? similarity.overall_similarity);
  const topVerified = Boolean(similarity.top_match_verified);

  const tone = verifiedPortion > 0 ? toneForSimilarity(verifiedPortion) : TONE.human;

  const verifiedMatches = similarity.matches?.filter((m) => m.verified) || [];
  const possibleMatches = similarity.matches?.filter((m) => !m.verified) || [];

  return (
    <GlassCard>
      <SectionTitle
        icon="compare_arrows"
        right={<MetaChip icon="database">{similarity.corpus_size} passages on file</MetaChip>}
      >
        Similarity indicator
      </SectionTitle>

      {similarity.external && <ExternalNote external={similarity.external} />}

      <ScoreBar label="Verified overlap — corroborated by shared wording" pct={verifiedPortion} hex={tone.hex} />
      <ScoreBar label="Topical overlap only — semantic, unverified" pct={possiblePortion} hex="#7C6EEA" />

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-[12.5px] text-on-surface-variant">Closest passage found:</span>
        <StatusBadge
          label={`${top}% ${topVerified ? "verified" : "semantic only"}`}
          tone={topVerified ? toneForSimilarity(top) : TONE.muted}
          icon={topVerified ? "verified" : "help"}
        />
      </div>

      <div className="mt-4 grid gap-3 rounded-lg bg-surface-lowest/60 p-4 sm:grid-cols-2">
        <div className="flex items-start gap-2">
          <Icon name="check_circle" size={16} className="mt-0.5 shrink-0 text-tertiary" />
          <p className="text-[12.5px] leading-relaxed text-on-surface-variant">
            <strong className="font-medium text-on-surface">Verified overlap</strong> — shared wording
            or phrasing backs up the similarity.
          </p>
        </div>
        <div className="flex items-start gap-2">
          <Icon name="help" size={16} className="mt-0.5 shrink-0 text-outline" />
          <p className="text-[12.5px] leading-relaxed text-on-surface-variant">
            <strong className="font-medium text-on-surface">Semantic similarity</strong> — similar
            topic or meaning, but not automatically copied content.
          </p>
        </div>
      </div>

      {verifiedMatches.length > 0 && (
        <div className="mt-5 border-t border-outline-variant/30 pt-5">
          <h3 className="mb-3 flex items-center gap-2 text-[12.5px] font-semibold text-on-surface">
            <Icon name="verified" size={14} className="text-tertiary" />
            Verified matches ({verifiedMatches.length})
          </h3>
          <div className="space-y-2.5">
            {verifiedMatches.map((m, i) => (
              <MatchCard key={`v${i}`} m={m} id={`v${i}`} expanded={expanded} setExpanded={setExpanded} />
            ))}
          </div>
        </div>
      )}

      {possibleMatches.length > 0 && (
        <div className="mt-5 border-t border-outline-variant/30 pt-5">
          <h3 className="mb-3 flex items-center gap-2 text-[12.5px] font-semibold text-on-surface-variant">
            <Icon name="help" size={14} />
            Topical overlap, unverified ({possibleMatches.length})
          </h3>
          <p className="mb-3 text-[12px] leading-relaxed text-outline">
            These passages are semantically close to something on file, but share too little
            wording to confirm copying — this often means the same general subject, not the same
            source text.
          </p>
          <div className="space-y-2.5">
            {possibleMatches.map((m, i) => (
              <MatchCard key={`p${i}`} m={m} id={`p${i}`} expanded={expanded} setExpanded={setExpanded} muted />
            ))}
          </div>
        </div>
      )}

      {verifiedMatches.length === 0 && possibleMatches.length === 0 && (
        <p className="mt-5 border-t border-outline-variant/30 pt-5 text-[13.5px] leading-relaxed text-on-surface-variant">
          {similarity.note || "No closely matching passages were found."}
        </p>
      )}
    </GlassCard>
  );
}

const isWebUrl = (u) => typeof u === "string" && /^https?:\/\//i.test(u);

const EXTERNAL_ICON = { wikipedia: "public", arxiv: "article" };

/** What the opt-in Wikipedia/arXiv check did, including when it could not run. */
function ExternalNote({ external }) {
  const ok = external.status === "ok";
  const failed = external.status === "unavailable";
  return (
    <div
      className={`mb-4 rounded-lg border px-4 py-3 ${
        failed ? "border-warning/35 bg-warning-container/10" : "border-outline-variant/40 bg-surface-lowest/60"
      }`}
    >
      <p className="flex items-start gap-2 text-[12.5px] leading-relaxed text-on-surface-variant">
        <Icon
          name={failed ? "cloud_off" : "travel_explore"}
          size={15}
          className={`mt-px shrink-0 ${failed ? "text-warning" : "text-primary"}`}
        />
        <span>{external.note}</span>
      </p>
      {ok && external.sources?.length > 0 && (
        <ul className="mt-2 space-y-1 pl-6">
          {external.sources.map((s) => (
            <li key={s.url} className="truncate text-[12px]">
              {isWebUrl(s.url) ? (
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  {s.title}
                </a>
              ) : (
                s.title
              )}
              <span className="text-outline"> — {s.kind === "arxiv" ? "arXiv" : "Wikipedia"}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * Where a matched passage came from: an external page (linked out) or an
 * earlier submission (dated, and linked back to its history entry). The
 * backend's internal storage tag is never shown — `source_name` is the
 * display name; `source_file` is only a fallback for records that predate it.
 */
function SourceLabel({ m }) {
  const external = m.source_kind === "wikipedia" || m.source_kind === "arxiv";
  // Records saved before `source_name` existed only have the internal storage
  // tag, "Pasted text (<12-hex content hash>)"; drop the hash for display.
  const name = m.source_name || (m.source_file || "").replace(/ \([0-9a-f]{12}\)$/, "");

  if (external) {
    return (
      <span className="flex min-w-0 items-center gap-2 text-[12px] text-on-surface-variant">
        <Icon name={EXTERNAL_ICON[m.source_kind]} size={14} className="shrink-0 text-primary" />
        {isWebUrl(m.source_url) ? (
          <a
            href={m.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex min-w-0 items-center gap-1 text-primary hover:underline"
            title={m.source_url}
          >
            <span className="truncate">{name}</span>
            <Icon name="open_in_new" size={12} className="shrink-0" />
          </a>
        ) : (
          <span className="truncate">{name}</span>
        )}
      </span>
    );
  }

  return (
    <span className="flex min-w-0 items-center gap-2 text-[12px] text-on-surface-variant">
      <Icon name="description" size={14} className="shrink-0 text-outline" />
      <span className="truncate">
        Earlier submission · {name}
        {m.source_created_at && <span className="text-outline"> · analysed {formatDateTime(m.source_created_at)}</span>}
      </span>
      {m.source_history_id != null && (
        <a href={`#history/${m.source_history_id}`} className="shrink-0 font-medium text-primary hover:underline">
          View
        </a>
      )}
    </span>
  );
}

function MatchCard({ m, id, expanded, setExpanded, muted = false }) {
  const long = m.query_excerpt.length > 150;
  const open = expanded === id;
  const tone = muted ? TONE.muted : toneForSimilarity(m.score);

  return (
    <div className={`rounded-lg border p-4 ${muted ? "border-outline-variant/30 bg-surface-lowest/50" : "border-outline-variant/40 bg-surface"}`}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <SourceLabel m={m} />
        <span className="shrink-0 text-[12px] font-semibold" style={{ color: tone.hex }}>
          {m.score}% semantic
        </span>
      </div>
      <p className={`text-[12.5px] leading-relaxed ${muted ? "text-outline" : "text-on-surface-variant"}`}>
        {open || !long ? m.query_excerpt : `${m.query_excerpt.slice(0, 150)}…`}
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1">
        {long && (
          <button
            type="button"
            onClick={() => setExpanded(open ? null : id)}
            className="text-[11.5px] font-medium text-primary hover:underline"
          >
            {open ? "Show less" : "Show more"}
          </button>
        )}
        <span className="text-[11px] text-outline">
          word overlap {m.word_overlap}% · phrase overlap {m.ngram_overlap}%
        </span>
      </div>
    </div>
  );
}
