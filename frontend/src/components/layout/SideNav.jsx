import Icon from "../common/Icon.jsx";
import Button from "../common/Button.jsx";
import { NAV } from "../../data/constants.js";

export default function SideNav({ active, onNavigate, open, onClose }) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 top-16 z-40 bg-black/30 backdrop-blur-[2px] lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <nav
        className={`fixed left-0 top-16 z-40 flex h-[calc(100vh-64px)] w-64 flex-col border-r border-outline-variant/40 bg-surface transition-transform duration-300 ease-out lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Analysis modules"
      >
        <div className="hidden items-center border-b border-outline-variant/30 px-5 py-5 lg:flex">
          <button
            type="button"
            onClick={() => { onNavigate("dashboard"); onClose?.(); }}
            aria-label="Go to overview"
            title="Go to overview"
            className="rounded-xl transition-opacity hover:opacity-80"
          >
            {/* Two artworks, one per theme: the light logo's black outlines vanish on dark. */}
            <img src="/logo-96.png" alt="Application logo" className="h-12 w-12 object-contain dark:hidden" />
            <img src="/logo-dark-96.png" alt="Application logo" className="hidden h-12 w-12 object-contain dark:block" />
          </button>
        </div>

        <div className="px-3 pb-1 pt-4">
          <Button
            full
            icon="add"
            onClick={() => { onNavigate("text"); onClose?.(); }}
          >
            New scan
          </Button>
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
                className={`group mx-3 mb-1 flex w-[calc(100%-1.5rem)] items-center gap-3 rounded-lg px-3.5 py-2.5 text-left transition-colors ${
                  isActive
                    ? "bg-primary-container/10 text-primary"
                    : "text-on-surface-variant hover:bg-surface-low hover:text-on-surface"
                }`}
              >
                <Icon name={item.icon} size={20} fill={isActive} className="shrink-0" />
                <span className="text-[14px] font-medium">{item.label}</span>
              </button>
            );
          })}
        </div>
      </nav>
    </>
  );
}
