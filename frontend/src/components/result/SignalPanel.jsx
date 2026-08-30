import GlassCard from "../common/GlassCard.jsx";
import ScoreBar from "../common/ScoreBar.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import { MiniStat } from "../common/StatTile.jsx";

/**
 * Signal distribution (reference screen-6). The four statistical inputs
 * behind the local score, plus the raw perplexity/burstiness readings.
 */
export default function SignalPanel({ signals, perplexity, burstiness, sentenceCount, wordCount }) {
  if (!signals) return null;

  const rows = [
    { label: "Predictability", value: signals.perplexity_signal, hex: "#ddb8ff", description: "How formulaic the wording is" },
    { label: "Style uniformity", value: signals.uniformity_signal, hex: "#ddb8ff", description: "Consistency of sentence length" },
    { label: "AI marker density", value: signals.marker_signal, hex: "#b4c5ff", description: "Frequency of stock AI phrasing" },
    { label: "Rhythm flatness", value: signals.burstiness_signal, hex: "#b4c5ff", description: "How monotone the flow is" },
  ];

  return (
    <GlassCard code="SEC // SIGNAL_DISTRIBUTION">
      <SectionTitle icon="equalizer">Detection signals</SectionTitle>

      <div className="grid gap-x-8 gap-y-1 sm:grid-cols-2">
        {rows.map((r) => (
          <ScoreBar key={r.label} label={r.label} value={r.value} hex={r.hex} description={r.description} />
        ))}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 border-t border-outline-variant/20 pt-5 sm:grid-cols-4">
        <MiniStat label="Perplexity" value={perplexity?.toFixed(1) ?? "—"} icon="show_chart" />
        <MiniStat label="Burstiness" value={burstiness?.toFixed(1) ?? "—"} icon="ssid_chart" />
        <MiniStat label="Sentences" value={sentenceCount ?? "—"} icon="segment" />
        <MiniStat label="Words" value={wordCount != null ? wordCount.toLocaleString() : "—"} icon="text_fields" />
      </div>

      <p className="mt-4 text-[12.5px] leading-relaxed text-outline">
        Lower perplexity and flatter rhythm are statistically more common in machine-generated
        prose, but plenty of human writing scores the same way.
      </p>
    </GlassCard>
  );
}
