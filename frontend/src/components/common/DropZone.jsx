import { useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { formatBytes } from "../../lib/format.js";

/**
 * Ingest zone (reference screens 5 and 12). Dashed technical boundary,
 * corner brackets, and a scan sweep once a payload is buffered.
 */
export default function DropZone({
  file,
  setFile,
  accept,
  formats = [],
  title = "Drag & drop a file here",
  hint,
  zoneCode = "ZONE_01 // UPLOAD",
  icon = "cloud_upload",
  onReset,
  preview,
  disabled = false,
}) {
  const [drag, setDrag] = useState(false);
  const inputRef = useRef(null);

  const pick = (f) => {
    if (!f || disabled) return;
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
      className={`brackets relative overflow-hidden rounded-lg border border-dashed p-8 text-center transition-all duration-300 sm:p-12 ${
        disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"
      } ${
        drag
          ? "border-primary bg-primary-container/10 shadow-[0_0_28px_rgba(37,99,235,0.25)]"
          : file
          ? "border-tertiary/45 bg-tertiary-container/[0.07]"
          : "border-outline-variant/60 bg-surface-lowest/40 hover:border-primary/45 hover:bg-surface-low/40"
      }`}
    >
      {/* A buffered file is not being analyzed yet, so no scan sweep here —
          the static BUFFERED indicator carries that state instead. */}
      <div className="pointer-events-none absolute left-4 top-3 font-mono text-label-caps uppercase tracking-[0.14em] text-outline/60">
        {zoneCode}
      </div>
      <div className="pointer-events-none absolute right-4 top-3 flex items-center gap-1.5">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            file ? "bg-tertiary" : "animate-pulse bg-secondary"
          }`}
        />
        <span
          className={`font-mono text-label-caps uppercase tracking-[0.14em] ${
            file ? "text-tertiary" : "text-secondary/80"
          }`}
        >
          {file ? "BUFFERED" : "AWAITING_INPUT"}
        </span>
      </div>

      {preview && file ? (
        <div className="mt-4 flex flex-col items-center gap-4">
          {preview}
          <FileLine file={file} />
        </div>
      ) : (
        <div className="mt-4 flex flex-col items-center">
          <div
            className={`mb-5 flex h-16 w-16 items-center justify-center rounded-lg border transition-colors ${
              file
                ? "border-tertiary/40 bg-tertiary-container/15 text-tertiary"
                : "border-outline-variant/40 bg-surface-high/60 text-primary"
            }`}
          >
            <Icon name={file ? "description" : icon} size={30} />
          </div>

          {file ? (
            <FileLine file={file} />
          ) : (
            <>
              <p className="font-display text-[19px] font-bold text-on-surface sm:text-[22px]">
                {title} or <span className="text-primary underline decoration-primary/40 underline-offset-4">Browse</span>
              </p>
              {hint && <p className="mx-auto mt-2 max-w-md text-[13.5px] leading-relaxed text-on-surface-variant/70">{hint}</p>}
            </>
          )}
        </div>
      )}

      {formats.length > 0 && !file && (
        <div className="mt-7 flex flex-wrap items-center justify-center gap-x-6 gap-y-3">
          {formats.map((f) => (
            <span key={f} className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-outline/70">
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
        onChange={(e) => pick(e.target.files?.[0])}
      />
    </div>
  );
}

function FileLine({ file }) {
  return (
    <>
      <p className="max-w-full truncate font-mono text-[15px] font-medium text-on-surface">{file.name}</p>
      <p className="mt-1.5 font-mono text-data-sm text-outline">
        {formatBytes(file.size)} · click to replace
      </p>
    </>
  );
}
