import Icon from "./Icon.jsx";
import { fileExtension, formatBytes } from "../../lib/format.js";

const EXT_ICON = {
  PDF: "picture_as_pdf", DOCX: "description", DOC: "description",
  PPTX: "slideshow", PPT: "slideshow", TXT: "article", CSV: "table_chart",
  XLSX: "table_chart", XLS: "table_chart",
  JPG: "image", JPEG: "image", PNG: "image", WEBP: "image",
};

/**
 * The buffered-payload card shown above an in-flight run (reference
 * screens 7 and 8) and in file-analysis results.
 */
export default function FilePreview({ name, size, meta, status, tone = "primary", right, thumb }) {
  const ext = fileExtension(name);
  const toneClass =
    tone === "lime" ? "text-tertiary" : tone === "purple" ? "text-secondary" : "text-primary";

  return (
    <div className="relative overflow-hidden rounded-lg border border-outline-variant/35 bg-surface-low/60">
      <div className="flex items-center gap-4 p-4">
        {thumb ? (
          <div className="h-12 w-12 shrink-0 overflow-hidden rounded border border-outline-variant/40">
            {thumb}
          </div>
        ) : (
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded border border-outline-variant/40 bg-surface-high/60">
            <Icon name={EXT_ICON[ext] || "draft"} size={22} className={toneClass} />
          </div>
        )}

        <div className="min-w-0 flex-1">
          <p className="truncate font-mono text-[14.5px] font-medium text-on-surface">{name}</p>
          <p className="mt-1 font-mono text-data-sm text-outline">
            {[ext, size != null ? formatBytes(size) : null, meta].filter(Boolean).join(" · ")}
          </p>
        </div>

        {right ??
          (status && (
            <span className={`shrink-0 font-mono text-label-caps uppercase tracking-[0.14em] ${toneClass}`}>
              {status}
            </span>
          ))}
      </div>
    </div>
  );
}
