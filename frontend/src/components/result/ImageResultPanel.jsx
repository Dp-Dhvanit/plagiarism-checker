import GlassCard from "../common/GlassCard.jsx";
import Icon from "../common/Icon.jsx";
import Button from "../common/Button.jsx";
import Disclaimer from "../common/Disclaimer.jsx";
import StatusBadge, { MetaChip } from "../common/StatusBadge.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import ResultHeadline from "./ResultHeadline.jsx";
import ReportButton from "./ReportButton.jsx";
import { CONFIDENCE_TONE, IMAGE_CLASSIFICATION_META, TONE } from "../../data/constants.js";

const PROVIDER_LABEL = { gemini: "Gemini", openrouter: "OpenRouter" };

export default function ImageResultPanel({ result, previewUrl, onRetry }) {
  // No local fallback exists for images, so an unavailable service is
  // reported plainly — but in plain end-user language. The backend's own
  // message can carry technical detail (env var names, provider errors)
  // that is meant for logs/API consumers, not shown here.
  if (result.status === "unavailable") {
    return (
      <div className="stagger space-y-6">
        <GlassCard>
          <div className="flex items-start gap-3.5">
            <Icon name="cloud_off" size={22} className="mt-0.5 shrink-0 text-outline" />
            <div className="min-w-0">
              <p className="font-display text-[15px] font-semibold text-on-surface">
                AI image analysis is currently unavailable
              </p>
              <p className="mt-1.5 text-[13.5px] leading-relaxed text-on-surface-variant">
                Please try again in a little while. Nothing was saved to your history for this
                attempt. Image checks are performed by an external AI provider, so the image is sent
                to it whenever a check is attempted.
              </p>
            </div>
          </div>
          {onRetry && (
            <div className="mt-5">
              <Button onClick={onRetry} variant="ghost" icon="refresh">Try again</Button>
            </div>
          )}
        </GlassCard>

        {previewUrl && (
          <GlassCard bodyClassName="p-3">
            <div className="overflow-hidden rounded-lg bg-surface-lowest">
              <img src={previewUrl} alt="Submitted" className="max-h-[380px] w-full object-contain" />
            </div>
          </GlassCard>
        )}
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
        aiLabel="AI-generated"
        altLabel="Authentic capture"
        rows={[
          {
            label: "Confidence level",
            value: result.confidence[0].toUpperCase() + result.confidence.slice(1),
            icon: "verified_user",
            hex: (CONFIDENCE_TONE[result.confidence] || TONE.muted).hex,
          },
          { label: "Indicators observed", value: String(result.indicators?.length || 0), icon: "troubleshoot" },
        ]}
        actions={<ReportButton historyId={result.history_id} />}
      >
        <StatusBadge label={meta.label} tone={meta.tone} dot />
      </ResultHeadline>

      {previewUrl && (
        <GlassCard bodyClassName="p-3">
          <div className="overflow-hidden rounded-lg bg-surface-lowest">
            <img src={previewUrl} alt="Analyzed" className="max-h-[440px] w-full object-contain" />
          </div>
        </GlassCard>
      )}

      <GlassCard>
        <SectionTitle
          icon="visibility"
          right={
            result.provider && (
              <MetaChip icon="cloud">{PROVIDER_LABEL[result.provider] || result.provider}</MetaChip>
            )
          }
        >
          Visual assessment
        </SectionTitle>
        <p className="text-[13.5px] leading-relaxed text-on-surface-variant">{result.explanation}</p>
      </GlassCard>

      {result.indicators?.length > 0 && (
        <GlassCard>
          <SectionTitle icon="troubleshoot">Observed indicators</SectionTitle>
          <ul className="space-y-2.5">
            {result.indicators.map((ind, i) => (
              <li key={i} className="flex items-start gap-3 rounded-lg border-l-[3px] border-secondary/50 bg-secondary-container/6 px-4 py-3">
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
