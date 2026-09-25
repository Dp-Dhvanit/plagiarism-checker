import Icon from "./Icon.jsx";

/**
 * Buttons.
 *  primary — solid lavender, the main call to action.
 *  ghost   — outlined neutral, for secondary actions.
 *  accent  — soft-tinted lavender, for a secondary-but-notable action.
 *  danger  — outlined red, for destructive/abort actions.
 *  quiet   — text-only.
 */

const VARIANTS = {
  primary:
    "bg-primary-container text-on-primary-container border border-primary-container shadow-soft hover:bg-primary-dim hover:border-primary-dim hover:shadow-card",
  ghost:
    "bg-surface text-on-surface border border-outline-variant/60 hover:border-primary/50 hover:text-primary hover:bg-primary-container/5",
  accent:
    "bg-primary-container/10 text-primary border border-primary/30 hover:bg-primary-container/16",
  danger:
    "bg-surface text-error border border-error/40 hover:bg-error/8",
  quiet:
    "bg-transparent text-on-surface-variant border border-transparent hover:text-primary hover:bg-primary-container/6",
};

const SIZES = {
  sm: "px-3 py-1.5 text-[13px]",
  md: "px-4 py-2.5 text-[14px]",
  lg: "px-5 py-3 text-[15px]",
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
  const DISABLED = "cursor-not-allowed border border-outline-variant/30 bg-surface-low text-outline/70 shadow-none";

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      className={`btn-scan inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors ${
        isDisabled ? DISABLED : `${VARIANTS[variant]} active:scale-[0.98]`
      } ${SIZES[size]} ${full ? "w-full" : ""} ${className}`}
      {...rest}
    >
      {loading ? (
        <Icon name="progress_activity" size={17} className="animate-spin" />
      ) : (
        icon && <Icon name={icon} size={17} />
      )}
      {children}
      {iconRight && !loading && <Icon name={iconRight} size={17} />}
    </button>
  );
}
