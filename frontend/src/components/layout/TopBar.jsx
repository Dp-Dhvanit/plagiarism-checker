import Icon from "../common/Icon.jsx";
import { BRAND } from "../../data/constants.js";

export default function TopBar({ onToggleNav, navOpen, backendOnline }) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 flex h-16 items-center justify-between border-b border-outline-variant/30 bg-surface/70 px-4 shadow-[0_0_18px_rgba(37,99,235,0.12)] backdrop-blur-xl sm:px-6 lg:px-page">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleNav}
          aria-label={navOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={navOpen}
          className="-ml-1 flex h-9 w-9 items-center justify-center rounded text-on-surface-variant transition-colors hover:text-primary lg:hidden"
        >
          <Icon name={navOpen ? "close" : "menu"} size={22} />
        </button>

        <span className="font-display text-[21px] font-extrabold tracking-tight text-primary sm:text-[24px]">
          {BRAND}
        </span>

        <span className="ml-2 hidden items-center gap-2 rounded border border-outline-variant/35 bg-surface-high/50 px-2.5 py-1 md:flex">
          {/* Static: a steady lime dot reads as "online" without adding
              perpetual motion to every screen. */}
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              backendOnline === false ? "bg-error" : backendOnline ? "bg-tertiary" : "bg-outline"
            }`}
          />
          <span
            className={`font-mono text-label-caps uppercase tracking-[0.14em] ${
              backendOnline === false ? "text-error" : backendOnline ? "text-tertiary" : "text-outline"
            }`}
          >
            {backendOnline === false ? "ENGINE OFFLINE" : backendOnline ? "ENGINE ONLINE" : "CONNECTING"}
          </span>
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="mr-2 hidden font-mono text-[11px] tracking-[0.12em] text-outline lg:inline">
          NODE: LOCAL_01
        </span>
        <a
          href="http://127.0.0.1:8000/docs"
          target="_blank"
          rel="noreferrer"
          title="Open the backend API reference"
          className="flex h-9 w-9 items-center justify-center rounded text-on-surface-variant transition-colors hover:text-primary"
        >
          <Icon name="api" size={20} />
        </a>
      </div>
    </header>
  );
}
