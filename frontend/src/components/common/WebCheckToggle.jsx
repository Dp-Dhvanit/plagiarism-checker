import Icon from "./Icon.jsx";

/**
 * Opt-in for the external-source comparison (Wikipedia and arXiv). Off by
 * default and worded plainly, because ticking it sends a few short excerpts of
 * the user's text to those sites as search queries.
 */
export default function WebCheckToggle({ checked, onChange, disabled = false }) {
  return (
    <label
      className={`flex items-start gap-3 rounded-lg border border-outline-variant/40 bg-surface-lowest/60 px-4 py-3.5 ${
        disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:border-primary/30"
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 shrink-0 accent-primary"
      />
      <span className="min-w-0">
        <span className="flex items-center gap-2 text-[13.5px] font-medium text-on-surface">
          <Icon name="travel_explore" size={16} className="text-primary" />
          Also compare against Wikipedia and arXiv
        </span>
        <span className="mt-1 block text-[12px] leading-relaxed text-on-surface-variant">
          Finds text copied from those sources. This sends a few short excerpts of your text to
          wikipedia.org and arxiv.org as search queries; the rest never leaves this server. Sources
          outside those two are not checked.
        </span>
      </span>
    </label>
  );
}
