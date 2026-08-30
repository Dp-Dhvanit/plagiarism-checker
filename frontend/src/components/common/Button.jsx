import Icon from "./Icon.jsx";

/**
 * Buttons.
 *  primary   — solid Tech Blue with the scanning light beam on hover.
 *  ghost     — outlined, for secondary actions.
 *  danger    — outlined error, for abort/delete.
 *  quiet     — text-only.
 */

const VARIANTS = {
  primary:
    "bg-primary-container text-on-primary-container border border-primary-container shadow-[0_0_14px_rgba(37,99,235,0.28)] hover:shadow-[0_0_22px_rgba(37,99,235,0.45)]",
  ghost:
    "bg-surface-high/40 text-on-surface border border-outline-variant/50 hover:border-primary/50 hover:text-primary",
  accent:
    "bg-secondary-container/20 text-secondary border border-secondary/40 hover:bg-secondary-container/30",
  danger:
    "bg-transparent text-error border border-error/45 hover:bg-error/10",
  quiet:
    "bg-transparent text-on-surface-variant border border-transparent hover:text-primary",
};

const SIZES = {
  sm: "px-3 py-1.5 text-[11px]",
  md: "px-5 py-2.5 text-[12px]",
  lg: "px-6 py-3.5 text-[12.5px]",
};

export default function Button({
  children,
  onClick,
  variant = "primary",
  size = "md",
  icon,
  iconRight,
  loading = false,
  disabled = false,
  full = false,
  type = "button",
  className = "",
  ...rest
}) {
  const isDisabled = disabled || loading;
  // A disabled control must not read as actionable, so the filled variants
  // drop to a flat surface rather than just fading.
  const DISABLED =
    "cursor-not-allowed border border-outline-variant/30 bg-surface-high/30 text-outline/60 shadow-none";

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      className={`btn-scan inline-flex items-center justify-center gap-2 rounded font-mono font-bold uppercase tracking-[0.1em] transition-all duration-200 ${
        isDisabled ? DISABLED : `${VARIANTS[variant]} active:scale-[0.985]`
      } ${SIZES[size]} ${full ? "w-full" : ""} ${className}`}
      {...rest}
    >
      {loading ? (
        <Icon name="progress_activity" size={16} className="animate-spin" />
      ) : (
        icon && <Icon name={icon} size={16} />
      )}
      {children}
      {iconRight && !loading && <Icon name={iconRight} size={16} />}
    </button>
  );
}
