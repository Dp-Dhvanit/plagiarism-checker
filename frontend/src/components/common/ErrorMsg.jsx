import Icon from "./Icon.jsx";

export default function ErrorMsg({ msg, className = "" }) {
  if (!msg) return null;
  return (
    <div
      role="alert"
      className={`mt-3 flex items-start gap-2.5 rounded-lg border border-error/30 bg-error-container/6 px-3.5 py-3 ${className}`}
    >
      <Icon name="error" size={16} className="mt-px shrink-0 text-error" />
      <p className="text-[13px] leading-relaxed text-on-surface">{msg}</p>
    </div>
  );
}
