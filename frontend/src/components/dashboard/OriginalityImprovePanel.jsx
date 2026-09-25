import { useState } from "react";
import GlassCard from "../common/GlassCard.jsx";
import Button from "../common/Button.jsx";
import ScoreBar from "../common/ScoreBar.jsx";
import StatusBadge from "../common/StatusBadge.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import { TONE, toneForSimilarity } from "../../data/constants.js";
import { postJSON, ApiError } from "../../lib/api.js";

const SOURCE_LABEL = { local: "Local", groq: "Groq", openrouter: "OpenRouter", gemini: "Gemini" };

/**
 * Entry point for the verified-overlap rewrite loop (`POST /reduce-overlap`,
 * see app/originality_rewriter.py). Operates on the most recent text scan's
 * saved excerpt — for a pasted-text scan longer than the 3,000-character
 * preview the app stores, the rewrite runs on that saved excerpt rather than
 * the full original, which is disclosed in the copy below rather than
 * silently assumed.
 */
export default function OriginalityImprovePanel({ scan }) {
  const [state, setState] = useState("idle"); // idle | loading | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const matchedPortion = Math.round(scan?.matchedPortion ?? 0);
  if (!scan || matchedPortion <= 0) return null;

  const isPasted = !scan.fileName || scan.fileName === "Pasted text";

  const run = async () => {
    setState("loading");
    setError("");
    try {
      const res = await postJSON("/reduce-overlap", {
        text: scan.textPreview,
        file_name: isPasted ? null : scan.fileName,
      });
      setResult(res);
      setState("done");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not run the rewrite.");
      setState("error");
    }
  };

  const copy = () => {
    navigator.clipboard?.writeText(result.rewritten);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <GlassCard className="border-primary/25">
      <SectionTitle
        icon="auto_awesome"
        right={<StatusBadge label="New" tone={TONE.neutral} />}
      >
        Originality improvement
      </SectionTitle>

      {state !== "done" && (
        <>
          <p className="text-[13.5px] leading-relaxed text-on-surface-variant">
            Your latest scan (<strong className="font-medium text-on-surface">{scan.fileName}</strong>) has{" "}
            <strong className="font-medium text-secondary">{matchedPortion}% verified overlap</strong>. This
            rewrites only the passages verified as copied — reordering and rephrasing them — then re-checks
            overlap for real before keeping anything, never on a guess.
            {isPasted && scan.truncated && (
              <> Runs on the saved 3,000-character excerpt from that scan, not the full original text.</>
            )}
          </p>
          <div className="mt-4 flex items-center gap-3">
            <Button icon="auto_awesome" loading={state === "loading"} onClick={run}>
              {state === "loading" ? "Rewriting…" : "Improve now"}
            </Button>
            {state === "error" && <span className="text-[12.5px] text-error">{error}</span>}
          </div>
        </>
      )}

      {state === "done" && result && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <ScoreBar
              label="Verified overlap — before"
              pct={Math.round(result.before?.matched_portion ?? 0)}
              hex={toneForSimilarity(result.before?.matched_portion).hex}
            />
            <ScoreBar
              label="Verified overlap — after"
              pct={Math.round(result.after?.matched_portion ?? 0)}
              hex={toneForSimilarity(result.after?.matched_portion).hex}
            />
            <ScoreBar
              label="Closest single match — before"
              pct={Math.round(result.before?.top_match ?? 0)}
              hex={toneForSimilarity(result.before?.top_match).hex}
              compact
            />
            <ScoreBar
              label="Closest single match — after"
              pct={Math.round(result.after?.top_match ?? 0)}
              hex={toneForSimilarity(result.after?.top_match).hex}
              compact
            />
          </div>

          {result.improved && Math.round(result.before?.matched_portion) === Math.round(result.after?.matched_portion) && (
            <p className="rounded-lg bg-warning-container/8 px-3.5 py-2.5 text-[12.5px] leading-relaxed text-on-surface-variant">
              The verified share of the document didn't shrink — this passage is short enough that it's
              essentially all one verified span. Its closest-match score still dropped, which is the honest
              limit for a fully-copied passage: restructuring can improve phrasing, but it can't make
              wholesale copying disappear.
            </p>
          )}

          {result.changed ? (
            <>
              <div className="rounded-lg border border-tertiary/25 bg-tertiary-container/5 p-4">
                <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-on-surface">
                  {result.rewritten}
                </p>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-[12px] text-outline">
                  {result.sentences_rewritten} sentence{result.sentences_rewritten !== 1 ? "s" : ""} rewritten ·{" "}
                  {result.attempts_tried} attempt{result.attempts_tried !== 1 ? "s" : ""} tried
                  {result.source && result.source !== "none" && (
                    <> · via {SOURCE_LABEL[result.source] || result.source}</>
                  )}
                </span>
                <div className="flex gap-2">
                  <Button onClick={copy} size="sm" variant="ghost" icon={copied ? "check" : "content_copy"}>
                    {copied ? "Copied" : "Copy rewritten text"}
                  </Button>
                  <Button onClick={() => setState("idle")} size="sm" variant="quiet" icon="close">
                    Close
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <p className="text-[13.5px] leading-relaxed text-on-surface-variant">{result.note}</p>
          )}
        </div>
      )}
    </GlassCard>
  );
}
