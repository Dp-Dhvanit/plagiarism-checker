import { useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { formatBytes } from "../../lib/format.js";

/**
 * File drop / browse area, shared by every upload surface.
 */
export default function DropZone({
  file,
  setFile,
  accept,
  formats = [],
  title = "Drag & drop a file here",
  hint,
  zoneCode, // eslint-disable-line no-unused-vars -- accepted for API compatibility, no longer shown
  icon = "cloud_upload",
  onReset,
  preview,
  disabled = false,
}) {
  const [drag, setDrag] = useState(false);
  const [rejection, setRejection] = useState("");
  const inputRef = useRef(null);

  // `accept` only filters the browse dialog; a dragged file bypasses it, and
  // the server would answer "unsupported" only after a fake upload stage.
  const allowed = (accept || "").split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
  const isAllowed = (f) => allowed.length === 0 || allowed.some((ext) => f.name.toLowerCase().endsWith(ext));

  const pick = (f) => {
    if (!f || disabled) return;
    if (!isAllowed(f)) {
      setRejection(`"${f.name}" isn't a supported file type. Accepted: ${formats.join(", ") || accept}.`);
      return;
    }
    setRejection("");
    setFile(f);
    onReset?.();
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !disabled) { e.preventDefault(); inputRef.current?.click(); }
      }}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label={title}
      className={`rounded-xl border-2 border-dashed p-8 text-center transition-all duration-200 sm:p-12 ${
        disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"
      } ${
        drag
          ? "border-primary bg-primary-container/6"
          : file
          ? "border-tertiary/50 bg-tertiary-container/5"
          : "border-outline-variant bg-surface-lowest/60 hover:border-primary/50 hover:bg-primary-container/4"
      }`}
    >
      {preview && file ? (
        <div className="flex flex-col items-center gap-4">
          {preview}
          <FileLine file={file} />
        </div>
      ) : (
        <div className="flex flex-col items-center">
          <div
            className={`mb-5 flex h-14 w-14 items-center justify-center rounded-full ${
              file ? "bg-tertiary-container/12 text-tertiary" : "bg-primary-container/10 text-primary"
            }`}
          >
            <Icon name={file ? "description" : icon} size={26} />
          </div>

          {file ? (
            <FileLine file={file} />
          ) : (
            <>
              <p className="font-display text-[18px] font-semibold text-on-surface sm:text-[20px]">
                {title}
              </p>
              <p className="mt-1.5 text-[13.5px] text-on-surface-variant">
                or <span className="font-medium text-primary underline decoration-primary/40 underline-offset-4">browse your files</span>
              </p>
              {hint && <p className="mx-auto mt-3 max-w-md text-[13px] leading-relaxed text-outline">{hint}</p>}
            </>
          )}
        </div>
      )}

      {rejection && (
        <p role="alert" className="mx-auto mt-4 max-w-md text-[13px] leading-relaxed text-error">
          {rejection}
        </p>
      )}

      {formats.length > 0 && !file && (
        <div className="mt-7 flex flex-wrap items-center justify-center gap-2">
          {formats.map((f) => (
            <span
              key={f}
              className="rounded-full border border-outline-variant/50 bg-surface px-2.5 py-1 text-[11px] font-medium text-on-surface-variant"
            >
              {f}
            </span>
          ))}
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          pick(e.target.files?.[0]);
          e.target.value = ""; // so choosing the same file again still fires onChange
        }}
      />
    </div>
  );
}

function FileLine({ file }) {
  return (
    <>
      <p className="max-w-full truncate text-[15px] font-medium text-on-surface">{file.name}</p>
      <p className="mt-1 text-[13px] text-outline">{formatBytes(file.size)} · click to replace</p>
    </>
  );
}
