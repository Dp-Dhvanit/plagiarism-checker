/**
 * Per-sentence perplexity row. Low perplexity = highly predictable =
 * leans machine (purple); high perplexity leans human (lime).
 */
export default function HeatmapBar({ sentence, perplexity, maxPpl }) {
  const ratio = Math.min(perplexity / (maxPpl || 80), 1);
  const aiLean = 1 - ratio; // 1 = most AI-like

  const hex = perplexity < 25 ? "#ddb8ff" : perplexity > 50 ? "#b3d17a" : "#b4c5ff";
  const verdict = perplexity < 25 ? "AI-leaning" : perplexity > 50 ? "Human-leaning" : "Uncertain";

  return (
    <div
      className="relative mb-2 overflow-hidden rounded border-l-2 bg-surface-low/50 py-2.5 pl-3.5 pr-3"
      style={{ borderColor: hex }}
    >
      <div
        className="absolute inset-y-0 left-0 pointer-events-none"
        style={{ width: `${aiLean * 100}%`, background: `linear-gradient(90deg, ${hex}1f, transparent)` }}
      />
      <div className="relative mb-1 flex items-baseline justify-between gap-3">
        <span className="font-mono text-[10.5px] font-bold uppercase tracking-[0.1em]" style={{ color: hex }}>
          {verdict}
        </span>
        <span className="shrink-0 font-mono text-[10.5px] tabular-nums text-outline">
          PPL {perplexity.toFixed(1)}
        </span>
      </div>
      <p className="relative text-[13.5px] leading-relaxed text-on-surface-variant">{sentence}</p>
    </div>
  );
}
