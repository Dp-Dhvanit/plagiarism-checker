import Icon from "../common/Icon.jsx";

export default function TopBar({ onToggleNav, navOpen, isDark, onToggleTheme, onHome }) {
  const nextMode = isDark ? "light" : "dark";
  return (
    <header className="fixed inset-x-0 top-0 z-50 flex h-16 items-center justify-between border-b border-outline-variant/40 bg-surface/90 px-4 backdrop-blur-md sm:px-6 lg:px-page">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleNav}
          aria-label={navOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={navOpen}
          className="-ml-1 flex h-9 w-9 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-surface-low hover:text-on-surface lg:hidden"
        >
          <Icon name={navOpen ? "close" : "menu"} size={22} />
        </button>

        <button
          type="button"
          onClick={onHome}
          aria-label="Go to overview"
          title="Go to overview"
          className="rounded-lg lg:hidden"
        >
          <img src="/logo-48.png" alt="" className="h-8 w-8 object-contain dark:hidden" />
          <img src="/logo-dark-48.png" alt="" className="hidden h-8 w-8 object-contain dark:block" />
        </button>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleTheme}
          aria-label={`Switch to ${nextMode} mode`}
          title={`Switch to ${nextMode} mode`}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-surface-low hover:text-primary"
        >
          <Icon name={isDark ? "light_mode" : "dark_mode"} size={20} />
        </button>
        <a
          href={`${import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000"}/docs`}
          target="_blank"
          rel="noreferrer"
          title="Open the backend API reference"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-surface-low hover:text-primary"
        >
          <Icon name="api" size={20} />
        </a>
      </div>
    </header>
  );
}
