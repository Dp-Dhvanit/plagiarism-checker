import { useEffect, useState } from "react";
import PageHeader, { SectionTitle } from "../common/PageHeader.jsx";
import ErrorMsg from "../common/ErrorMsg.jsx";
import EmptyState from "../common/EmptyState.jsx";
import StatTile from "../common/StatTile.jsx";
import GlassCard from "../common/GlassCard.jsx";
import Button from "../common/Button.jsx";
import Icon from "../common/Icon.jsx";
import ScoreRing from "../common/ScoreRing.jsx";
import StatusBadge from "../common/StatusBadge.jsx";
import OriginalityImprovePanel from "./OriginalityImprovePanel.jsx";
import { AGREEMENT_TONE, DetectorList } from "../result/DetectorBreakdown.jsx";
import { getJSON } from "../../lib/api.js";
import { formatRelative, formatDateTime } from "../../lib/format.js";
import { TONE, toneForScore, toneForSimilarity } from "../../data/constants.js";

const TYPE_META = {
  text: { icon: "description", label: "Text" },
  image: { icon: "image", label: "Image" },
};

function greeting() {
  const h = new Date().getHours();
  if (h < 5) return "Still up?";
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

/** Week-over-week change. `invert` = a decrease is the good direction. */
function WeekDelta({ current, previous, invert = false, suffix = "%" }) {
  if (current == null || previous == null) {
    return <span className="text-outline">Not enough history yet</span>;
  }
  const diff = Math.round((current - previous) * 10) / 10;
  if (diff === 0) return <span className="text-outline">No change this week</span>;
  const rising = diff > 0;
  const good = invert ? !rising : rising;
  return (
    <span className={`inline-flex items-center gap-1 font-medium ${good ? "text-tertiary" : "text-secondary"}`}>
      <Icon name={rising ? "arrow_upward" : "arrow_downward"} size={13} />
      {Math.abs(diff)}
      {suffix} this week
    </span>
  );
}

export default function Dashboard({ onNavigate }) {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState(null);
  const [latestDetail, setLatestDetail] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([getJSON("/dashboard"), getJSON("/history?sort=newest")])
      .then(([statsRes, historyRes]) => {
        if (cancelled) return;
        setStats(statsRes);
        setRecent(historyRes);
      })
      .catch((e) => !cancelled && setError(e.message || "Could not load overview data."));
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!recent) return;
    const latestText = recent.find((r) => r.analysis_type === "text");
    if (!latestText) return;
    let cancelled = false;
    getJSON(`/history/${latestText.id}`)
      .then((d) => !cancelled && setLatestDetail(d))
      .catch(() => {}); // non-critical — the breakdown cards just stay hidden
    return () => { cancelled = true; };
  }, [recent]);

  const loading = !stats || !recent;
  const latestTextItem = recent?.find((r) => r.analysis_type === "text") || null;
  const sim = latestDetail?.result_json?.similarity;
  const detectors = latestDetail?.result_json?.detectors || [];
  const consensus = latestDetail?.result_json?.consensus;
  const preview = latestDetail?.result_json?.extracted_text_preview || "";
  const ranDetectors = detectors.filter((d) => d.verdict !== "unavailable");
  const hasOverlapToImprove = Math.round(sim?.matched_portion ?? latestTextItem?.similarity_score ?? 0) > 0;

  return (
    <>
      <PageHeader
        title={`${greeting()}!`}
        subtitle="Let's make sure your content is original and AI-free."
        status={null}
      />
      <ErrorMsg msg={error} />

      {/* ── Stat cards ─────────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {loading ? (
          [0, 1, 2, 3].map((i) => (
            <div key={i} className="h-[132px] animate-pulse rounded-xl border border-outline-variant/30 bg-surface-low" />
          ))
        ) : (
          <>
            <StatTile
              size="lg" label="Documents scanned" icon="description" value={stats.total_analyses}
              iconBg="bg-primary-container/12" iconColor="text-primary"
              sub={
                stats.scans_this_week > 0
                  ? <span className="font-medium text-tertiary">+{stats.scans_this_week} this week</span>
                  : "No new scans this week"
              }
            />
            <StatTile
              size="lg" label="AI detection (avg.)" icon="psychology"
              value={`${Math.round(stats.average_ai_probability)}%`}
              hex={toneForScore(stats.average_ai_probability).hex}
              iconBg="bg-secondary-container/12" iconColor="text-secondary"
              sub={<WeekDelta current={stats.avg_ai_this_week} previous={stats.avg_ai_prev_week} invert />}
            />
            <StatTile
              size="lg" label="Plagiarism (avg.)" icon="link"
              value={`${Math.round(stats.average_similarity)}%`}
              hex={toneForSimilarity(stats.average_similarity).hex}
              iconBg="bg-tertiary-container/12" iconColor="text-tertiary"
              sub={<WeekDelta current={stats.avg_similarity_this_week} previous={stats.avg_similarity_prev_week} invert />}
            />
            <StatTile
              size="lg" label="Scans this week" icon="calendar_today" value={stats.scans_this_week}
              iconBg="bg-warning-container/12" iconColor="text-warning"
              sub={`${stats.scans_prev_week} scanned the week before`}
            />
          </>
        )}
      </div>

      {/* ── Quick action + recent scans ────────────────────────────── */}
      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        <GlassCard className="lg:col-span-2">
          <div className="flex h-full flex-col items-center justify-center py-4 text-center">
            <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary-container/10 text-primary">
              <Icon name="note_add" size={26} />
            </span>
            <h3 className="font-display text-[16px] font-semibold text-on-surface">Scan new content</h3>
            <p className="mt-1.5 max-w-[26ch] text-[13px] leading-relaxed text-on-surface-variant">
              Paste text or upload a document to check for AI writing and overlap.
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-2.5">
              <Button icon="upload_file" variant="ghost" onClick={() => onNavigate("file")}>Upload file</Button>
              <Button icon="edit_note" onClick={() => onNavigate("text")}>Paste text</Button>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="lg:col-span-3" bodyClassName="p-5 sm:p-6">
          <SectionTitle
            icon="history"
            right={<Button size="sm" variant="quiet" onClick={() => onNavigate("history")}>View all</Button>}
          >
            Recent scans
          </SectionTitle>

          {loading ? (
            <div className="space-y-2.5">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-[60px] animate-pulse rounded-lg border border-outline-variant/30 bg-surface-low" />
              ))}
            </div>
          ) : recent.length === 0 ? (
            <EmptyState icon="history" title="No scans yet" message="Your analyzed documents will show up here." />
          ) : (
            <ul className="space-y-2">
              {recent.slice(0, 4).map((item) => {
                const type = TYPE_META[item.analysis_type] || TYPE_META.text;
                const aiTone = toneForScore(item.ai_probability);
                const simTone = toneForSimilarity(item.similarity_score);
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => onNavigate("history")}
                      className="flex w-full items-center gap-3 rounded-lg border border-outline-variant/40 bg-surface p-3 text-left transition-colors hover:border-primary/30 hover:bg-primary-container/4"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-container/10 text-primary">
                        <Icon name={type.icon} size={17} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[13.5px] font-medium text-on-surface">{item.file_name}</span>
                        <span className="text-[11.5px] text-on-surface-variant" title={formatDateTime(item.created_at)}>
                          {formatRelative(item.created_at)}
                        </span>
                      </span>
                      {item.ai_probability != null && (
                        <span className="shrink-0 text-right">
                          <span className="block text-[10px] uppercase tracking-wide text-on-surface-variant/70">AI</span>
                          <span className="font-mono text-[13px] font-semibold" style={{ color: aiTone.hex }}>
                            {Math.round(item.ai_probability)}%
                          </span>
                        </span>
                      )}
                      {item.similarity_score != null && (
                        <span className="hidden shrink-0 text-right sm:block">
                          <span className="block text-[10px] uppercase tracking-wide text-on-surface-variant/70">Overlap</span>
                          <span className="font-mono text-[13px] font-semibold" style={{ color: simTone.hex }}>
                            {Math.round(item.similarity_score)}%
                          </span>
                        </span>
                      )}
                      <Icon name="chevron_right" size={18} className="shrink-0 text-outline" />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </GlassCard>
      </div>

      {/* ── Detection summary + AI provider breakdown, latest text scan ── */}
      {latestTextItem && (
        <div className="mt-4 grid gap-4 lg:grid-cols-5">
          <GlassCard className="lg:col-span-2">
            <SectionTitle icon="donut_large">Detection summary</SectionTitle>
            <p className="mb-4 text-[12px] text-on-surface-variant">Latest scan — {latestTextItem.file_name}</p>
            <div className="flex flex-col items-center">
              <ScoreRing
                value={latestTextItem.ai_probability ?? 0}
                hex={toneForScore(latestTextItem.ai_probability).hex}
                label="AI GENERATED"
                size={168}
                stroke={7}
              />
              <div className="mt-5 flex w-full items-center justify-center gap-6">
                <Legend hex="#D97862" label="AI generated" value={Math.round(latestTextItem.ai_probability ?? 0)} />
                <Legend hex="#6FAF7C" label="Human written" value={100 - Math.round(latestTextItem.ai_probability ?? 0)} />
              </div>
            </div>
            <p className="mt-4 border-t border-outline-variant/30 pt-3 text-[11.5px] leading-relaxed text-outline">
              Results are probabilistic and should be reviewed carefully.
            </p>
          </GlassCard>

          <GlassCard className="lg:col-span-3">
            <SectionTitle
              icon="hub"
              right={
                consensus && (
                  <StatusBadge
                    label={consensus.agreement}
                    tone={AGREEMENT_TONE[consensus.agreement] || TONE.muted}
                  />
                )
              }
            >
              AI detection breakdown
            </SectionTitle>

            {!latestDetail ? (
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-[52px] animate-pulse rounded-lg border border-outline-variant/30 bg-surface-low" />
                ))}
              </div>
            ) : ranDetectors.length === 0 ? (
              <p className="text-[13.5px] leading-relaxed text-on-surface-variant">
                No AI-assisted providers were configured or available for this scan — only the local
                statistical detector ran.
              </p>
            ) : (
              <>
                {consensus?.summary && (
                  <p className="mb-3 text-[12.5px] leading-relaxed text-on-surface-variant">{consensus.summary}</p>
                )}
                <DetectorList detectors={detectors} />
              </>
            )}
          </GlassCard>
        </div>
      )}

      {/* ── Closest matches + originality improvement, latest text scan ── */}
      {latestTextItem && latestDetail && (
        <div className={`mt-4 grid gap-4 ${hasOverlapToImprove ? "lg:grid-cols-2" : ""}`}>
          <GlassCard>
            <SectionTitle
              icon="find_in_page"
              right={<Button size="sm" variant="quiet" onClick={() => onNavigate("history")}>View all</Button>}
            >
              Closest matches on file
            </SectionTitle>
            {!sim?.matches?.length ? (
              <p className="text-[13.5px] leading-relaxed text-on-surface-variant">
                {sim?.note || "No closely matching passages were found for this scan."}
              </p>
            ) : (
              <div className="space-y-2.5">
                {[...sim.matches]
                  .sort((a, b) => b.score - a.score)
                  .slice(0, 3)
                  .map((m, i) => (
                    <div key={i} className="rounded-lg border border-outline-variant/40 bg-surface p-3.5">
                      <div className="flex items-center justify-between gap-3">
                        <span className="flex min-w-0 items-center gap-2 text-[12.5px] text-on-surface-variant">
                          <Icon name="description" size={14} className="shrink-0 text-outline" />
                          <span className="truncate">{m.source_name || m.source_file}</span>
                        </span>
                        <span className="shrink-0 flex items-center gap-1.5">
                          {m.verified && <Icon name="verified" size={13} className="text-secondary" />}
                          <span
                            className="text-[12.5px] font-semibold"
                            style={{ color: m.verified ? "#D97862" : "#8F8A80" }}
                          >
                            {Math.round(m.score)}%
                          </span>
                        </span>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </GlassCard>

          <OriginalityImprovePanel
            scan={{
              fileName: latestTextItem.file_name,
              matchedPortion: sim?.matched_portion ?? latestTextItem.similarity_score,
              textPreview: preview,
              truncated: preview.length >= 3000,
            }}
          />
        </div>
      )}
    </>
  );
}

function Legend({ hex, label, value }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: hex }} />
      <span className="text-[12.5px] text-on-surface-variant">
        {label} <strong className="font-semibold text-on-surface">{value}%</strong>
      </span>
    </div>
  );
}
