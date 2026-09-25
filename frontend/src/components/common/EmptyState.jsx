import Icon from "./Icon.jsx";

export default function EmptyState({ icon = "inbox", title, message, action }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-surface-high text-outline">
        <Icon name={icon} size={26} />
      </div>
      <p className="font-display text-[16px] font-semibold text-on-surface">{title}</p>
      {message && <p className="mt-2 max-w-md text-[13.5px] leading-relaxed text-on-surface-variant">{message}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
