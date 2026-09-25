import { useState } from "react";
import GlassCard from "../common/GlassCard.jsx";
import Icon from "../common/Icon.jsx";
import Button from "../common/Button.jsx";
import StatTile from "../common/StatTile.jsx";
import StatusBadge from "../common/StatusBadge.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import ChartCard from "./ChartCard.jsx";
import { DOC_TYPE_META, TONE } from "../../data/constants.js";

export default function SummaryResultPanel({ result, fileName }) {
  const [copied, setCopied] = useState(false);
  const meta = DOC_TYPE_META[result.document_type] || DOC_TYPE_META.General;
  const charts = result.charts || [];
  const numbers = result.important_numbers || [];

  const copy = () => {
    const text = [result.title, result.overview, "", ...result.summary_points.map((p, i) => `${i + 1}. ${p}`)]
      .filter(Boolean)
      .join("\n");
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="stagger space-y-6">
      <GlassCard strong>
        <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-container/10 text-primary">
              <Icon name={meta.icon} size={20} />
            </span>
            <div>
              <StatusBadge label={result.document_type} tone={TONE.neutral} />
              {fileName && <p className="mt-1.5 truncate text-[12px] text-outline">{fileName}</p>}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {result.ai_enhanced ? (
              <StatusBadge label="Semantic layer applied" tone={TONE.human} icon="auto_awesome" />
            ) : (
              <StatusBadge label="Extractive summary" tone={TONE.muted} icon="functions" />
            )}
            <Button onClick={copy} size="sm" variant="ghost" icon={copied ? "check" : "content_copy"}>
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>
        </div>

        {result.title && <h2 className="font-display text-[22px] font-semibold leading-tight text-on-surface">{result.title}</h2>}
        {result.overview && <p className="mt-3 text-[14px] leading-relaxed text-on-surface-variant">{result.overview}</p>}
      </GlassCard>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Words" icon="text_fields" value={result.word_count.toLocaleString()} hex="#7C6EEA" />
        <StatTile label="Takeaways" icon="format_list_bulleted" value={result.summary_points.length} hex="#6FAF7C" />
        <StatTile label="Charts" icon="bar_chart" value={charts.length} hex="#D99A3C" />
        <StatTile label="Key figures" icon="tag" value={numbers.length} hex="rgb(var(--on-surface))" />
      </div>

      <div className={`grid gap-6 ${numbers.length > 0 ? "lg:grid-cols-2" : ""}`}>
        <GlassCard>
          <SectionTitle icon="lightbulb">Key takeaways</SectionTitle>
          <div className="space-y-4 border-l-2 border-primary/25 pl-4">
            {result.summary_points.map((point, i) => (
              <p key={i} className="text-[14px] leading-[1.75] text-on-surface-variant">
                <span className="mr-2 font-mono text-[11px] font-semibold text-primary">
                  {String(i + 1).padStart(2, "0")}
                </span>
                {point}
              </p>
            ))}
          </div>
        </GlassCard>

        {numbers.length > 0 && (
          <GlassCard>
            <SectionTitle icon="tag">Key figures</SectionTitle>
            <div className="grid gap-3 sm:grid-cols-2">
              {numbers.map((n, i) => (
                <div key={i} className="rounded-lg border border-outline-variant/40 bg-surface-lowest/60 p-3.5">
                  <div className="text-[11px] font-medium uppercase tracking-[0.02em] text-on-surface-variant">{n.label}</div>
                  <div className="mt-1.5 text-[17px] font-semibold text-primary">{n.value}</div>
                  {n.context && <p className="mt-1.5 text-[11.5px] leading-snug text-outline">{n.context}</p>}
                </div>
              ))}
            </div>
          </GlassCard>
        )}
      </div>

      {charts.length === 0 && (
        <GlassCard>
          <div className="flex flex-col items-center py-8 text-center">
            <Icon name="bar_chart_off" size={28} className="mb-3 text-outline/60" />
            <p className="text-[13px] text-on-surface-variant">No chartable series were found in this document.</p>
          </div>
        </GlassCard>
      )}

      {charts.length > 0 && (
        <>
          <SectionTitle icon="insights">Visual breakdown</SectionTitle>
          <div className="grid gap-6 xl:grid-cols-2">
            {charts.map((chart, i) => (
              <ChartCard key={i} chart={chart} index={i} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
