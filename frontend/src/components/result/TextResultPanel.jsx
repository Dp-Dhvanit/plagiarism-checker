import { useState } from "react";
import GlassCard from "../common/GlassCard.jsx";
import Button from "../common/Button.jsx";
import ErrorMsg from "../common/ErrorMsg.jsx";
import HeatmapBar from "../common/HeatmapBar.jsx";
import Disclaimer from "../common/Disclaimer.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import ResultHeadline from "./ResultHeadline.jsx";
import SignalPanel from "./SignalPanel.jsx";
import GeminiPanel, { AiAssistStatus } from "./GeminiPanel.jsx";
import SimilarityPanel from "./SimilarityPanel.jsx";
import HumanizedCard from "./HumanizedCard.jsx";
import ReportButton from "./ReportButton.jsx";
import ExtractedContent from "./ExtractedContent.jsx";
import TechnicalDetail from "./TechnicalDetail.jsx";
import { postJSON } from "../../lib/api.js";
import { countWords } from "../../lib/format.js";
import { toneForSimilarity } from "../../data/constants.js";

const VERDICT_BLURB = {
  "Likely AI": "The statistical profile of this text resembles machine-generated writing more than human writing.",
  "Likely Human": "The statistical profile of this text resembles human writing more than machine-generated writing.",
  Uncertain: "The signals point both ways. Treat this as inconclusive rather than as evidence either way.",
};

export default function TextResultPanel({ result, originalText, showExtracted = false }) {
  const [humanizing, setHumanizing] = useState(false);
  const [humanized, setHumanized] = useState(null);
  const [hError, setHError] = useState("");

  const score = result.ai_likelihood_score;
  const sentences = result.sentence_breakdown || [];
  const maxPpl = sentences.length ? Math.max(...sentences.map((s) => s.perplexity), 80) : 80;
  const similarityPct =
    result.similarity != null
      ? Math.round(result.similarity.top_match ?? result.similarity.overall_similarity)
      : null;

  const doHumanize = async () => {
    setHumanizing(true);
    setHError("");
    setHumanized(null);
    try {
      setHumanized(
        await postJSON("/humanize", {
          text: originalText,
          sentence_breakdown: sentences,
          ai_score: score,
        })
      );
    } catch (e) {
      setHError(e.message || "The rewrite could not be completed.");
    } finally {
      setHumanizing(false);
    }
  };

  // Only surfaced when the AI-assisted check actually produced one — the
  // local detector does not report a confidence of its own.
  const rows = [];
  if (result.gemini?.confidence) {
    rows.push({
      label: "Confidence level",
      value: result.gemini.confidence[0].toUpperCase() + result.gemini.confidence.slice(1),
      icon: "verified_user",
      hex: "#b4c5ff",
    });
  }
  if (similarityPct != null) {
    rows.push({
      label: "Similarity index",
      value: `${similarityPct}%`,
      icon: "compare_arrows",
      hex: toneForSimilarity(similarityPct).hex,
    });
  }
  // Sentence/word counts deliberately stay out of the primary block — they
  // live in the technical detail panel alongside perplexity and burstiness.

  return (
    <div className="stagger space-y-6">
      <ResultHeadline
        score={score}
        verdict={result.verdict}
        blurb={VERDICT_BLURB[result.verdict]}
        code="RES // AI_PROB"
        rows={rows}
        actions={
          <>
            <ReportButton historyId={result.history_id} />
            {score > 20 && !humanized && (
              <Button
                onClick={doHumanize}
                loading={humanizing}
                variant="accent"
                icon="auto_fix_high"
              >
                {humanizing ? "Rewriting…" : "Reduce AI phrasing"}
              </Button>
            )}
          </>
        }
      >
        <AiAssistStatus gemini={result.gemini} />
        <ErrorMsg msg={hError} />
      </ResultHeadline>

      {humanized && (
        <HumanizedCard
          humanized={humanized.humanized}
          changed={humanized.sentences_changed}
          onClose={() => setHumanized(null)}
        />
      )}

      {/* Renders only when the AI-assisted check actually returned something. */}
      <GeminiPanel gemini={result.gemini} />

      <SimilarityPanel similarity={result.similarity} />

      {/* Secondary by design: the statistical internals stay one click away. */}
      <TechnicalDetail
        summary={
          sentences.length > 0
            ? `Signal breakdown, perplexity and burstiness readings, and a per-sentence map of all ${sentences.length} sentences.`
            : "Signal breakdown and the raw perplexity and burstiness readings."
        }
      >
        <SignalPanel
          signals={result.signals}
          perplexity={result.perplexity}
          burstiness={result.burstiness}
          sentenceCount={sentences.length}
          wordCount={countWords(originalText)}
        />

        {sentences.length > 0 && (
          <GlassCard code="SEC // SENTENCE_MAP">
            <SectionTitle icon="format_align_left">Sentence heatmap</SectionTitle>
            <div className="mb-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-[12px] text-outline">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-secondary" /> AI-leaning (low perplexity)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-primary" /> Uncertain
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-tertiary" /> Human-leaning
              </span>
            </div>
            <div className="max-h-[420px] overflow-y-auto pr-1">
              {sentences.map((s, i) => (
                <HeatmapBar key={i} sentence={s.sentence} perplexity={s.perplexity} maxPpl={maxPpl} />
              ))}
            </div>
          </GlassCard>
        )}

        {showExtracted && result.extracted_text && (
          <ExtractedContent text={result.extracted_text} />
        )}
      </TechnicalDetail>

      <Disclaimer />
    </div>
  );
}
