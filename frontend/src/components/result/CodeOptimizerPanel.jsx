import { useState } from "react";
import GlassCard from "../common/GlassCard.jsx";
import Button from "../common/Button.jsx";
import Icon from "../common/Icon.jsx";
import StatTile from "../common/StatTile.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import { postJSON, ApiError } from "../../lib/api.js";

const SOURCE_LABEL = { groq: "Groq", openrouter: "OpenRouter", gemini: "Gemini" };

/** A code block with a line-number gutter, editor-style. */
function CodeWithLineNumbers({ code, className = "" }) {
  const lines = code.split("\n");
  return (
    <div
      className={`flex max-h-96 overflow-auto rounded-lg border p-3.5 font-mono text-[12px] leading-[1.7] ${className}`}
    >
      <div className="select-none border-r border-outline-variant/30 pr-3 text-right text-outline/50 tabular-nums">
        {lines.map((_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>
      <div className="min-w-0 flex-1 pl-3">
        {lines.map((line, i) => (
          <div key={i} className="whitespace-pre">
            {line || " "}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Addition to the Code Analysis result, not a separate screen — appears
 * only when the exact code that was analyzed is available client-side
 * (paste mode, or a plain source-file upload). Nothing is re-uploaded or
 * re-pasted: `code` is passed down from CodeTab's own existing state.
 */
export default function CodeOptimizerPanel({ code, language }) {
  const [state, setState] = useState("idle"); // idle | loading | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  if (!code) return null;

  const run = async () => {
    if (state === "loading") return; // no concurrent requests for the same code
    setState("loading");
    setError("");
    try {
      const res = await postJSON("/optimize-code", { code, language });
      if (!res.available) {
        setError(res.error || "Code analysis completed, but optimization is currently unavailable.");
        setState("error");
        return;
      }
      setResult(res);
      setState("done");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not optimize this code.");
      setState("error");
    }
  };

  const copy = () => {
    navigator.clipboard?.writeText(result.optimized_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const reduction =
    result && result.original.lines > 0
      ? Math.round(((result.original.lines - result.optimized.lines) / result.original.lines) * 100)
      : 0;

  return (
    <GlassCard className="border-primary/25">
      <SectionTitle icon="bolt">Code Optimizer</SectionTitle>

      {state !== "done" && (
        <>
          <p className="text-[13.5px] leading-relaxed text-on-surface-variant">
            Generate a more concise version of this code that preserves its behavior. Every result is
            validated locally (syntax/structure check) before it's shown — nothing here is taken on the
            model's word.
          </p>
          <div className="mt-4 flex items-center gap-3">
            <Button icon="bolt" loading={state === "loading"} onClick={run}>
              {state === "loading" ? "Optimizing…" : state === "error" ? "Try again" : "Optimize Code"}
            </Button>
            {state === "error" && <span className="text-[12.5px] text-error">{error}</span>}
          </div>
        </>
      )}

      {state === "done" && result && (
        <div className="space-y-5">
          {!result.changed ? (
            <p className="text-[13.5px] leading-relaxed text-on-surface-variant">
              {result.summary || "No safe optimization was found — the code is already reasonably concise."}
            </p>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-3">
                <StatTile label="Original" icon="description" value={`${result.original.lines}`} hex="rgb(var(--on-surface))" />
                <StatTile label="Optimized" icon="bolt" value={`${result.optimized.lines}`} hex="#6FAF7C" />
                <StatTile label="Reduction" icon="trending_down" value={`${reduction}%`} hex="#7C6EEA" />
              </div>

              <div>
                <p className="mb-2 text-[12.5px] font-medium text-on-surface">Optimized code</p>
                <div className="grid gap-4 lg:grid-cols-2">
                  <div>
                    <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.04em] text-outline">
                      Original · {result.original.lines} lines
                    </p>
                    <CodeWithLineNumbers
                      code={code}
                      className="border-outline-variant/40 bg-surface-lowest/50 text-on-surface-variant"
                    />
                  </div>
                  <div>
                    <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.04em] text-primary">
                      Optimized · {result.optimized.lines} lines
                    </p>
                    <CodeWithLineNumbers
                      code={result.optimized_code}
                      className="border-primary/25 bg-primary-container/5 text-on-surface"
                    />
                  </div>
                </div>
              </div>

              <div>
                <p className="mb-2 text-[12.5px] font-medium text-on-surface">Estimated complexity</p>
                <p className="mb-2.5 text-[11.5px] leading-relaxed text-outline">
                  The model's own estimate — not locally verified. {result.complexity.loop_nesting_before != null && (
                    <>The nested-loop depth numbers below (before {result.complexity.loop_nesting_before}, after{" "}
                    {result.complexity.loop_nesting_after}) ARE computed locally from the actual code, as a
                    sanity cross-check.</>
                  )}
                </p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-outline-variant/40 bg-surface-lowest/50 p-3.5">
                    <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.04em] text-outline">Before</p>
                    <p className="text-[13px] text-on-surface-variant">
                      Time <span className="font-mono text-on-surface">{result.complexity.before.time}</span>
                    </p>
                    <p className="text-[13px] text-on-surface-variant">
                      Space <span className="font-mono text-on-surface">{result.complexity.before.space}</span>
                    </p>
                  </div>
                  <div className="rounded-lg border border-primary/25 bg-primary-container/5 p-3.5">
                    <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.04em] text-primary">After</p>
                    <p className="text-[13px] text-on-surface-variant">
                      Time <span className="font-mono text-on-surface">{result.complexity.after.time}</span>
                    </p>
                    <p className="text-[13px] text-on-surface-variant">
                      Space <span className="font-mono text-on-surface">{result.complexity.after.space}</span>
                    </p>
                  </div>
                </div>
                {result.complexity.reasoning && (
                  <p className="mt-2 text-[12px] leading-relaxed text-outline">{result.complexity.reasoning}</p>
                )}
              </div>

              {result.changes.length > 0 && (
                <div>
                  <p className="mb-2 text-[12.5px] font-medium text-on-surface">What was changed</p>
                  <ul className="space-y-1.5">
                    {result.changes.map((c, i) => (
                      <li key={i} className="flex items-start gap-2 text-[13px] leading-relaxed text-on-surface-variant">
                        <Icon name="check" size={15} className="mt-0.5 shrink-0 text-tertiary" />
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="rounded-lg border border-outline-variant/40 bg-surface-lowest/50 p-3.5">
                <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.04em] text-on-surface-variant">
                  Validation
                </p>
                {result.validation_notes.map((n, i) => (
                  <p key={i} className="flex items-center gap-2 text-[12.5px] leading-relaxed text-on-surface-variant">
                    <Icon
                      name={result.validation_passed ? "check_circle" : "warning"}
                      size={14}
                      className={result.validation_passed ? "text-tertiary" : "text-secondary"}
                    />
                    {n}
                  </p>
                ))}
                <p className="mt-1.5 flex items-center gap-2 text-[12px] text-outline">
                  <Icon name="info" size={13} />
                  Runtime behavior was not executed.
                </p>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-[12px] text-outline">
                  via {SOURCE_LABEL[result.provider] || result.provider}
                </span>
                <div className="flex gap-2">
                  <Button onClick={copy} size="sm" variant="ghost" icon={copied ? "check" : "content_copy"}>
                    {copied ? "Copied" : "Copy optimized code"}
                  </Button>
                  <Button onClick={() => setState("idle")} size="sm" variant="quiet" icon="close">
                    Close
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </GlassCard>
  );
}
