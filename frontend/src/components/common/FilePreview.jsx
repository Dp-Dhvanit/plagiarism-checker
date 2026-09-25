import Icon from "./Icon.jsx";
import { fileExtension, formatBytes } from "../../lib/format.js";

const EXT_ICON = {
  PDF: "picture_as_pdf", DOCX: "description", DOC: "description",
  PPTX: "slideshow", PPT: "slideshow", TXT: "article", CSV: "table_chart",
  XLSX: "table_chart", XLS: "table_chart",
  JPG: "image", JPEG: "image", PNG: "image", WEBP: "image",
};

const TONE_CLASS = {
  primary: "bg-primary-container/10 text-primary",
  lime: "bg-tertiary-container/10 text-tertiary",
  purple: "bg-secondary-container/10 text-secondary",
};

/** The buffered-payload card shown above an in-flight or completed run. */
export default function FilePreview({ name, size, meta, status, tone = "primary", right, thumb }) {
  const ext = fileExtension(name);
  const toneClass = TONE_CLASS[tone] || TONE_CLASS.primary;

  return (
    <div className="rounded-xl border border-outline-variant/40 bg-surface">
      <div className="flex items-center gap-4 p-4">
        {thumb ? (
          <div className="h-12 w-12 shrink-0 overflow-hidden rounded-lg border border-outline-variant/40">
            {thumb}
          </div>
        ) : (
          <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-lg ${toneClass}`}>
            <Icon name={EXT_ICON[ext] || "draft"} size={22} />
          </div>
        )}

        <div className="min-w-0 flex-1">
          <p className="truncate text-[14.5px] font-medium text-on-surface">{name}</p>
          <p className="mt-0.5 text-[13px] text-on-surface-variant">
            {[ext, size != null ? formatBytes(size) : null, meta].filter(Boolean).join(" · ")}
          </p>
        </div>

        {right ??
          (status && (
            <span className="shrink-0 rounded-full bg-surface-low px-2.5 py-1 text-[12px] font-medium text-on-surface-variant">
              {status}
            </span>
          ))}
      </div>
    </div>
  );
}
