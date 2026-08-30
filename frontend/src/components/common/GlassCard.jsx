/**
 * The Glass Layer. Every panel in the app is one of these.
 *
 * `code` renders the small monospaced section ID in the top-left corner
 * ("SEC_04 // AI_PROB") that the reference design uses to keep the
 * technical narrative consistent across surfaces.
 */
export default function GlassCard({
  children,
  code,
  strong = false,
  brackets = false,
  scanner = null, // null | "primary" | "lime" | "purple"
  className = "",
  bodyClassName,
  ...rest
}) {
  const scannerClass =
    scanner === "lime" ? "scanner scanner-lime"
    : scanner === "purple" ? "scanner scanner-purple"
    : scanner ? "scanner"
    : null;

  const padding =
    bodyClassName ?? (code ? "px-5 pb-5 pt-11 sm:px-6 sm:pb-6" : "p-5 sm:p-6");

  return (
    <section
      className={`relative overflow-hidden rounded-lg ${strong ? "glass-strong" : "glass"} ${
        brackets ? "brackets" : ""
      } ${className}`}
      {...rest}
    >
      {scannerClass && <div className={scannerClass} />}
      {code && (
        <div className="pointer-events-none absolute left-5 top-4 z-10 font-mono text-label-caps uppercase tracking-[0.14em] text-outline/70 sm:left-6">
          {code}
        </div>
      )}
      <div className={padding}>{children}</div>
    </section>
  );
}
