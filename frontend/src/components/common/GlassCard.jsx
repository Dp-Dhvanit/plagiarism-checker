/**
 * The app's card primitive. Every panel in the app is one of these.
 *
 * `code` used to render a small monospaced terminal-style tag in the
 * corner ("SEC_04 // AI_PROB"). Removed as part of the clean-SaaS redesign
 * — the prop is still accepted (so none of the ~40 call sites across the
 * app need to change) but no longer renders anything.
 *
 * `scanner` used to draw a moving highlight line, mimicking a security-
 * terminal scan. Removed for the same reason: it was decorative motion
 * with no informational value. The prop is still accepted and ignored.
 */
export default function GlassCard({
  children,
  code, // eslint-disable-line no-unused-vars -- accepted for API compatibility, no longer rendered
  strong = false,
  brackets = false, // eslint-disable-line no-unused-vars -- accepted for API compatibility
  scanner = null, // eslint-disable-line no-unused-vars -- accepted for API compatibility
  className = "",
  bodyClassName,
  ...rest
}) {
  return (
    <section
      className={`relative overflow-hidden rounded-xl ${strong ? "glass-strong" : "glass"} ${className}`}
      {...rest}
    >
      <div className={bodyClassName ?? "p-5 sm:p-6"}>{children}</div>
    </section>
  );
}
