import { useEffect, useState } from "react";
import TopBar from "./TopBar.jsx";
import SideNav from "./SideNav.jsx";
import { useTheme } from "../../lib/theme.js";

export default function AppShell({ active, onNavigate, children }) {
  const [navOpen, setNavOpen] = useState(false);
  const { isDark, toggle: toggleTheme } = useTheme();

  useEffect(() => { setNavOpen(false); }, [active]);

  return (
    <div className="min-h-screen bg-void">
      <TopBar
        navOpen={navOpen}
        onToggleNav={() => setNavOpen((v) => !v)}
        isDark={isDark}
        onToggleTheme={toggleTheme}
        onHome={() => onNavigate("dashboard")}
      />
      <SideNav
        active={active}
        onNavigate={onNavigate}
        open={navOpen}
        onClose={() => setNavOpen(false)}
      />

      <div className="flex flex-col pt-16 lg:pl-64">
        <main className="flex-1 px-4 py-8 sm:px-6 sm:py-10 lg:px-page lg:py-12">
          <div className="mx-auto w-full max-w-content">{children}</div>
        </main>

        <footer className="border-t border-outline-variant/30 px-4 py-6 sm:px-6 lg:px-page">
          <div className="mx-auto max-w-content text-center">
            <span className="text-[12.5px] text-on-surface-variant/70">
              Results are estimates, not proof of authorship or plagiarism.
            </span>
          </div>
        </footer>
      </div>
    </div>
  );
}
