/**
 * Per-sentence perplexity row. Low perplexity = highly predictable =
 * leans machine; high perplexity leans human.
 */
export default function HeatmapBar({ sentence, perplexity, maxPpl }) {
  const hex = perplexity < 25 ? "#D97862" : perplexity > 50 ? "#6FAF7C" : "#D99A3C";
  const verdict = perplexity < 25 ? "AI-leaning" : perplexity > 50 ? "Human-leaning" : "Uncertain";

  return (
    <div className="mb-2 rounded-lg border-l-[3px] bg-surface-lowest/70 py-2.5 pl-3.5 pr-3" style={{ borderColor: hex }}>
      <div className="mb-1 flex items-baseline justify-between gap-3">
        <span className="text-[10.5px] font-semibold uppercase tracking-[0.04em]" style={{ color: hex }}>
          {verdict}
        </span>
        <span className="shrink-0 font-mono text-[10.5px] tabular-nums text-outline">
          PPL {perplexity.toFixed(1)}
        </span>
      </div>
      <p className="text-[13.5px] leading-relaxed text-on-surface-variant">{sentence}</p>
    </div>
  );
}
