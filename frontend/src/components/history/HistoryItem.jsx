import Icon from "../common/Icon.jsx";
import StatusBadge from "../common/StatusBadge.jsx";
import { TONE, toneForScore, toneForSimilarity } from "../../data/constants.js";
import { fileExtension, formatDateTime, formatRelative } from "../../lib/format.js";

const TYPE_META = {
  text: { icon: "description", label: "TEXT" },
  image: { icon: "image", label: "IMAGE" },
  code: { icon: "code", label: "CODE" },
};

/**
 * One stored analysis. Reads left-to-right: what it was → what came back →
 * what you can do with it.
 */
export default function HistoryItem({
  item,
  busy,
  confirming,
  onView,
  onDownload,
  onRequestDelete,
  onConfirmDelete,
  onCancelDelete,
}) {
  const type = TYPE_META[item.analysis_type] || TYPE_META.text;
  const aiTone = toneForScore(item.ai_probability);
  const simTone = toneForSimilarity(item.similarity_score);
  // "Pasted text" has no extension; fileExtension() falls back to "FILE",
  // which is noise next to the type label.
  const rawExt = fileExtension(item.file_name);
  const ext = rawExt === "FILE" ? null : rawExt;

  return (
    <li className="group relative overflow-hidden rounded-lg border border-outline-variant/30 bg-surface-low/45 transition-all duration-200 hover:border-primary/35 hover:bg-surface-low/70">
      <span
        className="absolute inset-y-0 left-0 w-0.5 opacity-60 transition-opacity group-hover:opacity-100"
        style={{ background: aiTone.hex }}
      />

      <div className="flex flex-col gap-4 p-4 pl-5 sm:flex-row sm:items-center">
        {/* Identity */}
        <div className="flex min-w-0 flex-1 items-center gap-3.5">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded border border-outline-variant/40 bg-surface-high/50">
            <Icon name={type.icon} size={19} className="text-primary" />
          </span>
          <div className="min-w-0">
            <p className="truncate font-mono text-[14px] text-on-surface" title={item.file_name}>
              {item.file_name}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-outline">
              <span>{type.label}</span>
              {ext && ext !== type.label && (
                <>
                  <span className="text-outline/40">·</span>
                  <span>{ext}</span>
                </>
              )}
              <span className="text-outline/40">·</span>
              <span title={formatDateTime(item.created_at)}>{formatRelative(item.created_at)}</span>
            </div>
          </div>
        </div>

        {/* Scores */}
        <div className="flex shrink-0 items-center gap-5 sm:gap-7">
          <Metric label="AI likelihood" value={item.ai_probability} hex={aiTone.hex} />
          <Metric label="Similarity" value={item.similarity_score} hex={simTone.hex} />
          <div className="hidden md:block">
            <StatusBadge
              label={item.status}
              tone={item.status === "analyzed" ? TONE.human : TONE.muted}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex shrink-0 items-center gap-1">
          {confirming ? (
            <>
              <span className="mr-1 hidden font-mono text-[11px] text-error sm:inline">Delete?</span>
              <ActionButton icon="check" label="Confirm delete" tone="error" onClick={onConfirmDelete} disabled={busy} />
              <ActionButton icon="close" label="Cancel delete" onClick={onCancelDelete} disabled={busy} />
            </>
          ) : (
            <>
              <ActionButton icon="visibility" label="View result" onClick={onView} disabled={busy} />
              <ActionButton icon="download" label="Download PDF report" onClick={onDownload} disabled={busy} />
              <ActionButton icon="delete" label="Delete" tone="error" onClick={onRequestDelete} disabled={busy} />
            </>
          )}
        </div>
      </div>
    </li>
  );
}

function Metric({ label, value, hex }) {
  const has = value != null;
  return (
    <div className="text-right">
      <div className="font-mono text-label-caps uppercase tracking-[0.1em] text-outline">{label}</div>
      <div
        className="mt-1 font-mono text-[16px] font-medium tabular-nums"
        style={{ color: has ? hex : "#8d90a0" }}
      >
        {has ? `${Math.round(value)}%` : "—"}
      </div>
    </div>
  );
}

function ActionButton({ icon, label, onClick, disabled, tone }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className={`flex h-9 w-9 items-center justify-center rounded transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
        tone === "error"
          ? "text-outline hover:bg-error/10 hover:text-error"
          : "text-outline hover:bg-primary/10 hover:text-primary"
      }`}
    >
      <Icon name={icon} size={18} />
    </button>
  );
}
