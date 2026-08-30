import GlassCard from "../common/GlassCard.jsx";
import ScoreBar from "../common/ScoreBar.jsx";
import Disclaimer from "../common/Disclaimer.jsx";
import StatusBadge, { MetaChip } from "../common/StatusBadge.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import ResultHeadline from "./ResultHeadline.jsx";
import TechnicalDetail from "./TechnicalDetail.jsx";
import { CONFIDENCE_TONE, LANG_ICON, TONE } from "../../data/constants.js";

const VERDICT = (score) =>
  score >= 60
    ? { label: "Leans AI-generated", blurb: "The structural signals in this source resemble output from AI coding assistants more than hand-written code." }
    : score <= 40
    ? { label: "Leans human-written", blurb: "The structural signals in this source resemble hand-written code more than assistant output." }
    : { label: "Inconclusive", blurb: "The signals point both ways. Modern human-written code often looks like this too." };

export default function CodeResultPanel({ result }) {
  const score = result.ai_code_probability;
  const verdict = VERDICT(score);
  const sig = result.signals;
  const langKey = (result.detected_language || "unknown").toLowerCase();

  const signalRows = [
    { label: "Code cleanness", value: sig.cleanness_score, description: "Absence of debug artifacts and TODOs", hex: "#ddb8ff" },
    { label: "Edge-case handling", value: sig.edge_case_density, description: "Null checks, validation, explicit raises", hex: "#ddb8ff" },
    { label: "Docstring coverage", value: sig.docstring_coverage, description: "Functions carrying full docstrings", hex: "#ddb8ff" },
    { label: "Generic comments", value: sig.generic_comment_ratio, description: "Template-like comment phrasing", hex: "#ddb8ff" },
    { label: "Naming consistency", value: sig.naming_consistency, description: "Convention uniformity across identifiers", hex: "#b4c5ff" },
    { label: "Line uniformity", value: sig.line_uniformity, description: "Evenness of line-length distribution", hex: "#b4c5ff" },
    { label: "Function uniformity", value: sig.func_length_uniformity, description: "Evenness of function lengths", hex: "#b4c5ff" },
    { label: "Comment density", value: Math.min(sig.comment_density / 0.3, 1), description: "Comments per line of code", hex: "#b4c5ff" },
    { label: "Error handling", value: sig.error_handling_density, description: "try/catch coverage", hex: "#b4c5ff" },
    { label: "Verbose naming", value: Math.min(Math.max(sig.avg_identifier_length - 4, 0) / 7, 1), description: `Average identifier: ${sig.avg_identifier_length.toFixed(1)} chars`, hex: "#b4c5ff" },
  ];

  return (
    <div className="stagger space-y-6">
      <ResultHeadline
        score={score}
        ringLabel={"AI CODE\nLIKELIHOOD"}
        verdict={verdict.label}
        blurb={verdict.blurb}
        code="RES // CODE_PROB"
        aiLabel="AI-ASSISTED"
        altLabel="HAND-WRITTEN"
        altValue={result.human_code_probability}
        rows={[
          { label: "Detected language", value: result.detected_language, icon: LANG_ICON[langKey] || "code", hex: "#b4c5ff" },
          { label: "Code blocks found", value: String(result.code_blocks_found), icon: "data_object" },
          { label: "Lines analyzed", value: result.lines_analyzed.toLocaleString(), icon: "format_list_numbered" },
        ]}
      >
        <div className="flex flex-wrap gap-2">
          <StatusBadge
            label={`Confidence ${result.confidence}`}
            tone={CONFIDENCE_TONE[result.confidence] || TONE.muted}
          />
          {result.languages_detected?.length > 1 && (
            <MetaChip icon="language">{result.languages_detected.join(", ")}</MetaChip>
          )}
        </div>
      </ResultHeadline>

      <GlassCard code="SEC // EXPLANATION">
        <SectionTitle icon="lightbulb">What drove this estimate</SectionTitle>
        <p className="text-[13.5px] leading-relaxed text-on-surface-variant/85">{result.explanation}</p>
      </GlassCard>

      {/* Secondary by design, matching the text result page. */}
      <TechnicalDetail summary="The ten structural signals behind the score, and the extracted code chunks.">
        <GlassCard code="SEC // CODE_SIGNALS">
          <SectionTitle icon="equalizer">Structural signals</SectionTitle>
          <div className="grid gap-x-8 gap-y-1 sm:grid-cols-2">
            {signalRows.map((r) => (
              <ScoreBar key={r.label} label={r.label} value={r.value} hex={r.hex} description={r.description} />
            ))}
          </div>
        </GlassCard>

        {result.chunks?.length > 0 && (
          <GlassCard code="SEC // BLOCK_BREAKDOWN">
            <SectionTitle
              icon="view_agenda"
              right={
                <span className="font-mono text-[11px] text-outline">
                  {result.chunks.length} chunk{result.chunks.length === 1 ? "" : "s"}
                </span>
              }
            >
              Extracted code chunks
            </SectionTitle>
            <p className="mb-4 text-[12.5px] leading-relaxed text-outline">
              The score above is a line-weighted aggregate across these chunks. The engine reports
              chunk coverage, not a separate score per chunk.
            </p>
            <div className="max-h-80 overflow-x-auto overflow-y-auto">
              <table className="w-full min-w-[420px] text-left">
                <thead className="sticky top-0 bg-surface-low/95 backdrop-blur">
                  <tr className="border-b border-outline-variant/30">
                    {["Chunk", "Source pages / slides", "Lines"].map((h) => (
                      <th key={h} className="px-3 py-2.5 font-mono text-label-caps uppercase tracking-[0.12em] text-outline">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.chunks.map((c, i) => (
                    <tr key={i} className="border-b border-outline-variant/15">
                      <td className="px-3 py-2.5 font-mono text-[12px] text-on-surface-variant">
                        {String(i + 1).padStart(2, "0")}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-[12px] text-outline">
                        {Array.isArray(c.units) && c.units.length
                          ? c.units.map((u) => u + 1).join(", ")
                          : "—"}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-[12px] tabular-nums text-outline">
                        {c.lines ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        )}
      </TechnicalDetail>

      <Disclaimer>
        Code-authorship detection is weaker than prose detection: linters, formatters and house
        style all push human code toward the same signals. Read this as an indicator, never as
        proof that code was AI-generated.
      </Disclaimer>
    </div>
  );
}
