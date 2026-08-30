import GlassCard from "../common/GlassCard.jsx";
import Icon from "../common/Icon.jsx";
import Button from "../common/Button.jsx";
import Disclaimer from "../common/Disclaimer.jsx";
import StatusNotice from "../common/StatusNotice.jsx";
import StatusBadge from "../common/StatusBadge.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import ResultHeadline from "./ResultHeadline.jsx";
import ReportButton from "./ReportButton.jsx";
import { CONFIDENCE_TONE, IMAGE_CLASSIFICATION_META, TONE } from "../../data/constants.js";

export default function ImageResultPanel({ result, previewUrl, onRetry }) {
  // No local fallback exists for images, so an unavailable service is
  // reported plainly rather than filled in with a fabricated score.
  if (result.status === "unavailable") {
    return (
      <div className="stagger space-y-6">
        <StatusNotice status="unavailable" message={result.message} code="SEC // IMG_PROC" />

        {previewUrl && (
          <GlassCard code="SEC // SOURCE_IMAGE" bodyClassName="px-4 pb-4 pt-11">
            <div className="overflow-hidden rounded border border-outline-variant/35 bg-surface-lowest">
              <img src={previewUrl} alt="Submitted" className="max-h-[380px] w-full object-contain" />
            </div>
          </GlassCard>
        )}

        <GlassCard code="SEC // NEXT_STEPS">
          <SectionTitle icon="build">Getting image detection running</SectionTitle>
          <ul className="space-y-2.5 text-[13.5px] leading-relaxed text-on-surface-variant/85">
            {[
              "Image detection needs GEMINI_API_KEY set in the backend environment — see backend/.env.example.",
              "Restart the backend after setting it so the key is picked up.",
              "Text, document, code and summary analysis all work without it.",
            ].map((line) => (
              <li key={line} className="flex gap-3">
                <Icon name="chevron_right" size={16} className="mt-px shrink-0 text-primary/70" />
                <span>{line}</span>
              </li>
            ))}
          </ul>
          {onRetry && (
            <div className="mt-5">
              <Button onClick={onRetry} variant="ghost" icon="refresh">
                Try again
              </Button>
            </div>
          )}
        </GlassCard>
      </div>
    );
  }

  const meta = IMAGE_CLASSIFICATION_META[result.classification] || IMAGE_CLASSIFICATION_META.uncertain;
  const score = result.ai_probability;

  return (
    <div className="stagger space-y-6">
      <ResultHeadline
        score={score}
        ringLabel={"AI GENERATION\nLIKELIHOOD"}
        verdict={meta.label}
        blurb="A visual assessment of how closely this image matches the artefacts typical of AI image generators."
        code="RES // IMG_PROB"
        aiLabel="AI-GENERATED"
        altLabel="AUTHENTIC CAPTURE"
        rows={[
          {
            label: "Confidence level",
            value: result.confidence[0].toUpperCase() + result.confidence.slice(1),
            icon: "verified_user",
            hex: (CONFIDENCE_TONE[result.confidence] || TONE.muted).hex,
          },
          {
            label: "Indicators observed",
            value: String(result.indicators?.length || 0),
            icon: "troubleshoot",
          },
        ]}
        actions={<ReportButton historyId={result.history_id} />}
      >
        <StatusBadge label={meta.label} tone={meta.tone} chamfer dot />
      </ResultHeadline>

      {previewUrl && (
        <GlassCard code="SEC // SOURCE_IMAGE" bodyClassName="px-4 pb-4 pt-11">
          <div className="overflow-hidden rounded border border-outline-variant/35 bg-surface-lowest">
            <img src={previewUrl} alt="Analyzed" className="max-h-[440px] w-full object-contain" />
          </div>
        </GlassCard>
      )}

      <GlassCard code="SEC // EXPLANATION">
        <SectionTitle icon="visibility">Visual assessment</SectionTitle>
        <p className="text-[13.5px] leading-relaxed text-on-surface-variant/85">{result.explanation}</p>
      </GlassCard>

      {result.indicators?.length > 0 && (
        <GlassCard code="SEC // INDICATORS">
          <SectionTitle icon="troubleshoot">Observed indicators</SectionTitle>
          <ul className="space-y-2.5">
            {result.indicators.map((ind, i) => (
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

      <Disclaimer>
        This is an AI-assisted visual estimate. Photo editing, heavy compression, upscaling and
        stylised photography all produce artefacts that resemble generation. It is not proof that
        an image was or was not AI-generated.
      </Disclaimer>
    </div>
  );
}
