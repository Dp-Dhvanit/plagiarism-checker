import Icon from "../common/Icon.jsx";
import { NAV, NAV_BY_KEY, TERMINAL_NAME } from "../../data/constants.js";

export default function SideNav({ active, onNavigate, open, onClose }) {
  const activeMeta = NAV_BY_KEY[active];

  return (
    <>
      {/* Scrim for the mobile drawer */}
      {open && (
        <div
          className="fixed inset-0 top-16 z-40 bg-void/70 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <nav
        className={`fixed left-0 top-16 z-40 flex h-[calc(100vh-64px)] w-64 flex-col border-r border-outline-variant/25 bg-surface-low/70 backdrop-blur-md transition-transform duration-300 ease-out lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Analysis modules"
      >
        <div className="border-b border-outline-variant/20 px-5 py-5">
          <div className="mb-2 flex items-center gap-2.5">
            <span className="h-1.5 w-1.5 rounded-full bg-secondary shadow-glow-secondary" />
            <span className="font-mono text-label-caps uppercase tracking-[0.16em] text-on-surface-variant">
              {activeMeta?.code || "SEC_00"} // ACTIVE
            </span>
          </div>
          <h2 className="font-display text-[19px] font-bold text-on-surface">{TERMINAL_NAME}</h2>
        </div>

        <div className="flex-1 overflow-y-auto py-3">
          {NAV.map((item) => {
            const isActive = item.key === active;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => { onNavigate(item.key); onClose?.(); }}
                aria-current={isActive ? "page" : undefined}
                className={`group flex w-full items-center gap-3.5 border-r-2 px-5 py-3.5 text-left transition-all duration-200 ${
                  isActive
                    ? "border-secondary bg-secondary-container/25 text-secondary"
                    : "border-transparent text-on-surface-variant hover:bg-surface-variant/25 hover:text-on-surface"
                }`}
              >
                <Icon name={item.icon} size={20} fill={isActive} className="shrink-0" />
                <span className="font-mono text-[13.5px] transition-transform duration-200 group-hover:translate-x-0.5">
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>

        <div className="border-t border-outline-variant/20 px-5 py-4">
          <p className="font-mono text-[10px] leading-[1.7] tracking-[0.04em] text-outline/70">
            Statistical scoring runs locally.
          </p>
          <p className="mt-1.5 font-mono text-[10px] leading-[1.7] tracking-[0.04em] text-outline/70">
            AI-assisted checks run server-side; the browser never holds an API key.
          </p>
        </div>
      </nav>
    </>
  );
}
