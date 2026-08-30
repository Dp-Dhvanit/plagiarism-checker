import Icon from "./Icon.jsx";

export default function ErrorMsg({ msg, className = "" }) {
  if (!msg) return null;
  return (
    <div
      role="alert"
      className={`mt-3 flex items-start gap-2.5 rounded border border-error/35 bg-error-container/15 px-3.5 py-2.5 ${className}`}
    >
      <Icon name="error" size={16} className="mt-px shrink-0 text-error" />
      <p className="font-mono text-data-sm leading-relaxed text-error">{msg}</p>
    </div>
  );
}
