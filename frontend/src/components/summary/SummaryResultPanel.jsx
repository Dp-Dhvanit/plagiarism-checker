import { useState } from "react";
import GlassCard from "../common/GlassCard.jsx";
import Icon from "../common/Icon.jsx";
import Button from "../common/Button.jsx";
import StatTile from "../common/StatTile.jsx";
import StatusBadge from "../common/StatusBadge.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import ChartCard from "./ChartCard.jsx";
import { DOC_TYPE_META, TONE } from "../../data/constants.js";

/** Reference screen-13: metric tiles, key takeaways, chart panel. */
export default function SummaryResultPanel({ result, fileName }) {
  const [copied, setCopied] = useState(false);
  const meta = DOC_TYPE_META[result.document_type] || DOC_TYPE_META.General;
  const charts = result.charts || [];
  const numbers = result.important_numbers || [];

  const copy = () => {
    const text = [
      result.title,
      result.overview,
      "",
      ...result.summary_points.map((p, i) => `${i + 1}. ${p}`),
    ]
      .filter(Boolean)
      .join("\n");
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="stagger space-y-6">
      {/* Header strip */}
      <GlassCard strong code="SUM // OVERVIEW">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded border border-outline-variant/40 bg-surface-high/50">
              <Icon name={meta.icon} size={20} className="text-primary" />
            </span>
            <div>
              <StatusBadge label={result.document_type} tone={TONE.neutral} />
              {fileName && (
                <p className="mt-1.5 truncate font-mono text-[11.5px] text-outline">{fileName}</p>
              )}
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

        {result.title && (
          <h2 className="font-display text-[24px] font-bold leading-tight text-on-surface">{result.title}</h2>
        )}
        {result.overview && (
          <p className="mt-3 text-[14px] leading-relaxed text-on-surface-variant/85">{result.overview}</p>
        )}
      </GlassCard>

      {/* Metric tiles */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          code="MTR_01"
          label="Words"
          icon="text_fields"
          value={result.word_count.toLocaleString()}
          hex="#b4c5ff"
        />
        <StatTile
          code="MTR_02"
          label="Takeaways"
          icon="format_list_bulleted"
          value={result.summary_points.length}
          hex="#ddb8ff"
        />
        <StatTile code="MTR_03" label="Charts" icon="bar_chart" value={charts.length} hex="#b3d17a" />
        <StatTile code="MTR_04" label="Key figures" icon="tag" value={numbers.length} hex="#e5e1e4" />
      </div>

      {/* Takeaways share the row with key figures only when there are any;
          otherwise they take the full width instead of leaving a void. */}
      <div className={`grid gap-6 ${numbers.length > 0 ? "lg:grid-cols-2" : ""}`}>
        <GlassCard code="TXT_01 // INSIGHTS">
          <SectionTitle icon="lightbulb">Key takeaways</SectionTitle>
          <ul className={`grid gap-3 ${numbers.length > 0 ? "" : "md:grid-cols-2"}`}>
            {result.summary_points.map((point, i) => (
              <li
                key={i}
                className="flex gap-3 rounded border-l-2 border-primary/50 bg-surface-low/45 px-4 py-3"
              >
                <span className="mt-0.5 shrink-0 font-mono text-[11px] font-bold text-primary">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <p className="text-[13.5px] leading-relaxed text-on-surface-variant">{point}</p>
              </li>
            ))}
          </ul>
        </GlassCard>

        {numbers.length > 0 && (
          <GlassCard code="NUM_01 // FIGURES">
            <SectionTitle icon="tag">Key figures</SectionTitle>
            <div className="grid gap-3 sm:grid-cols-2">
              {numbers.map((n, i) => (
                <div key={i} className="rounded border border-outline-variant/30 bg-surface-low/50 p-3.5">
                  <div className="font-mono text-label-caps uppercase tracking-[0.12em] text-outline">
                    {n.label}
                  </div>
                  <div className="mt-1.5 font-mono text-[17px] font-medium text-secondary">{n.value}</div>
                  {n.context && (
                    <p className="mt-1.5 text-[11.5px] leading-snug text-outline">{n.context}</p>
                  )}
                </div>
              ))}
            </div>
          </GlassCard>
        )}
      </div>

      {charts.length === 0 && (
        <GlassCard code="VIZ_01 // EMPTY">
          <div className="flex flex-col items-center py-8 text-center">
            <Icon name="bar_chart_off" size={28} className="mb-3 text-outline/50" />
            <p className="font-mono text-[12px] text-outline">
              No chartable series were found in this document.
            </p>
          </div>
        </GlassCard>
      )}

      {charts.length > 0 && (
        <>
          <div className="flex items-center gap-3 pt-2">
            <span className="h-px flex-1 bg-outline-variant/25" />
            <span className="font-mono text-label-caps uppercase tracking-[0.16em] text-primary">
              Visual breakdown
            </span>
            <span className="h-px flex-1 bg-outline-variant/25" />
          </div>
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
