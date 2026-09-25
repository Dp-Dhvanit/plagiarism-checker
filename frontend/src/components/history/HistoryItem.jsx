import Icon from "../common/Icon.jsx";
import StatusBadge from "../common/StatusBadge.jsx";
import { TONE, toneForScore, toneForSimilarity } from "../../data/constants.js";
import { fileExtension, formatDateTime, formatRelative } from "../../lib/format.js";

const TYPE_META = {
  text: { icon: "description", label: "Text" },
  image: { icon: "image", label: "Image" },
  code: { icon: "code", label: "Code" },
};

/** One stored analysis row. */
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
  const rawExt = fileExtension(item.file_name);
  const ext = rawExt === "FILE" ? null : rawExt;

  return (
    <li className="rounded-xl border border-outline-variant/40 bg-surface transition-colors hover:border-primary/30">
      <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
        <div className="flex min-w-0 flex-1 items-center gap-3.5">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-container/10 text-primary">
            <Icon name={type.icon} size={19} />
          </span>
          <div className="min-w-0">
            <p className="truncate text-[14px] font-medium text-on-surface" title={item.file_name}>
              {item.file_name}
            </p>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-on-surface-variant">
              <span>{type.label}</span>
              {ext && ext !== type.label && (
                <>
                  <span className="text-outline">·</span>
                  <span>{ext}</span>
                </>
              )}
              <span className="text-outline">·</span>
              <span title={formatDateTime(item.created_at)}>{formatRelative(item.created_at)}</span>
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-6 sm:gap-8">
          <Metric label="AI likelihood" value={item.ai_probability} hex={aiTone.hex} />
          <Metric label="Overlap" value={item.similarity_score} hex={simTone.hex} />
          <div className="hidden md:block">
            <StatusBadge label={item.status} tone={item.status === "analyzed" ? TONE.human : TONE.muted} />
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {confirming ? (
            <>
              <span className="mr-1 hidden text-[12.5px] text-error sm:inline">Delete?</span>
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
      <div className="text-[11px] text-on-surface-variant/80">{label}</div>
      <div className="mt-0.5 text-[15px] font-semibold tabular-nums" style={{ color: has ? hex : "#8F8A80" }}>
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
      className={`flex h-9 w-9 items-center justify-center rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
        tone === "error"
          ? "text-outline hover:bg-error-container/10 hover:text-error"
          : "text-outline hover:bg-primary-container/10 hover:text-primary"
      }`}
    >
      <Icon name={icon} size={18} />
    </button>
  );
}
