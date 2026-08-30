import PageHeader from "../common/PageHeader.jsx";
import GlassCard from "../common/GlassCard.jsx";
import Button from "../common/Button.jsx";
import Icon from "../common/Icon.jsx";
import Disclaimer from "../common/Disclaimer.jsx";
import StatusBadge, { MetaChip } from "../common/StatusBadge.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import { MiniStat } from "../common/StatTile.jsx";
import ResultHeadline from "../result/ResultHeadline.jsx";
import GeminiPanel, { AiAssistStatus } from "../result/GeminiPanel.jsx";
import SimilarityPanel from "../result/SimilarityPanel.jsx";
import ExtractedContent from "../result/ExtractedContent.jsx";
import ReportButton from "../result/ReportButton.jsx";
import TechnicalDetail from "../result/TechnicalDetail.jsx";
import {
  CONFIDENCE_TONE, IMAGE_CLASSIFICATION_META, TONE, toneForSimilarity,
} from "../../data/constants.js";
import { formatDateTime } from "../../lib/format.js";

/** Full view of one archived analysis. */
export default function HistoryDetailPanel({ detail, onClose }) {
  const r = detail.result_json || {};
  const isImage = detail.analysis_type === "image";
  const img = r.image_result;
  const score = detail.ai_probability ?? r.heuristic?.ai_likelihood_score ?? 0;
  const simPct = detail.similarity_score != null ? Math.round(detail.similarity_score) : null;

  const rows = [
    {
      label: "Confidence level",
      value: detail.confidence
        ? detail.confidence[0].toUpperCase() + detail.confidence.slice(1)
        : "—",
      icon: "verified_user",
      hex: (CONFIDENCE_TONE[detail.confidence] || TONE.muted).hex,
    },
  ];
  if (simPct != null) {
    rows.push({
      label: "Similarity index",
      value: `${simPct}%`,
      icon: "compare_arrows",
      hex: toneForSimilarity(simPct).hex,
    });
  }
  rows.push({ label: "Recorded", value: formatDateTime(detail.created_at), icon: "schedule" });

  return (
    <>
      <PageHeader
        eyebrow={`ARCHIVE // REF_${String(detail.id).padStart(4, "0")}`}
        title={detail.file_name}
        subtitle={`${detail.analysis_type.toUpperCase()} analysis · ${formatDateTime(detail.created_at)}`}
        status="done"
        action={
          <Button onClick={onClose} variant="ghost" size="sm" icon="arrow_back">
            Back to history
          </Button>
        }
      />

      <div className="stagger space-y-6">
        <ResultHeadline
          score={score}
          ringLabel={isImage ? "AI GENERATION\nLIKELIHOOD" : "AI LIKELIHOOD\nESTIMATE"}
          aiLabel={isImage ? "AI-GENERATED" : "AI LIKELIHOOD"}
          altLabel={isImage ? "AUTHENTIC CAPTURE" : "HUMAN LIKELIHOOD"}
          verdict={
            isImage
              ? (IMAGE_CLASSIFICATION_META[img?.classification] || IMAGE_CLASSIFICATION_META.uncertain).label
              : r.heuristic?.verdict
          }
          code={`RES_${detail.id} // ARCHIVED`}
          rows={rows}
          actions={<ReportButton historyId={detail.id} label="Download PDF report" />}
        >
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={detail.analysis_type} tone={TONE.neutral} />
            <StatusBadge
              label={detail.status}
              tone={detail.status === "analyzed" ? TONE.human : TONE.muted}
            />
            <MetaChip icon="draft">{detail.file_type}</MetaChip>
          </div>
          {!isImage && <AiAssistStatus gemini={r.gemini_text} />}
        </ResultHeadline>

        {!isImage && (
          <>
            <GeminiPanel gemini={r.gemini_text} />
            <SimilarityPanel similarity={r.similarity} />
          </>
        )}

        {isImage && img && (
          <>
            <GlassCard code="SEC // IMG_ASSESSMENT">
              <SectionTitle
                icon="visibility"
                right={
                  <StatusBadge
                    label={(IMAGE_CLASSIFICATION_META[img.classification] || IMAGE_CLASSIFICATION_META.uncertain).label}
                    tone={(IMAGE_CLASSIFICATION_META[img.classification] || IMAGE_CLASSIFICATION_META.uncertain).tone}
                  />
                }
              >
                Visual assessment
              </SectionTitle>
              <p className="text-[13.5px] leading-relaxed text-on-surface-variant/85">{img.explanation}</p>
            </GlassCard>

            {img.indicators?.length > 0 && (
              <GlassCard code="SEC // INDICATORS">
                <SectionTitle icon="troubleshoot">Observed indicators</SectionTitle>
                <ul className="space-y-2.5">
                  {img.indicators.map((ind, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-3 rounded border-l-2 border-secondary/50 bg-secondary-container/[0.08] px-4 py-3"
                    >
                      <Icon name="chevron_right" size={16} className="mt-px shrink-0 text-secondary" />
                      <span className="text-[13.5px] leading-relaxed text-on-surface-variant">{ind}</span>
                    </li>
                  ))}
                </ul>
              </GlassCard>
            )}
          </>
        )}

        {/* Secondary by design, matching the live result page. */}
        {(r.heuristic || r.extracted_text_preview) && (
          <TechnicalDetail
            summary={
              r.heuristic
                ? "Local detector readings and the archived text excerpt."
                : "The archived text excerpt for this analysis."
            }
          >
            {r.heuristic && (
              <GlassCard code="SEC // LOCAL_HEURISTIC">
                <SectionTitle icon="functions">Local statistical detector</SectionTitle>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <MiniStat label="Verdict" value={r.heuristic.verdict} icon="gavel" />
                  <MiniStat
                    label="AI likelihood"
                    value={`${Math.round(r.heuristic.ai_likelihood_score)}%`}
                    icon="percent"
                  />
                  <MiniStat label="Perplexity" value={r.heuristic.perplexity?.toFixed(1)} icon="show_chart" />
                  <MiniStat label="Burstiness" value={r.heuristic.burstiness?.toFixed(1)} icon="ssid_chart" />
                </div>
              </GlassCard>
            )}

            {r.extracted_text_preview && (
              <ExtractedContent text={r.extracted_text_preview} title="Archived text excerpt" />
            )}
          </TechnicalDetail>
        )}

        <Disclaimer />
      </div>
    </>
  );
}
