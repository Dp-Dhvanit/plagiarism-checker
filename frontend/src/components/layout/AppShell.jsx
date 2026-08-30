import { useEffect, useState } from "react";
import TopBar from "./TopBar.jsx";
import SideNav from "./SideNav.jsx";

export default function AppShell({ active, onNavigate, backendOnline, children }) {
  const [navOpen, setNavOpen] = useState(false);

  // Close the mobile drawer whenever the surface changes.
  useEffect(() => { setNavOpen(false); }, [active]);

  return (
    <div className="min-h-screen">
      <TopBar
        navOpen={navOpen}
        onToggleNav={() => setNavOpen((v) => !v)}
        backendOnline={backendOnline}
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

        <footer className="border-t border-outline-variant/15 px-4 py-6 sm:px-6 lg:px-page">
          <div className="mx-auto flex max-w-content flex-col items-center gap-3 sm:flex-row sm:justify-between">
            <span className="font-mono text-label-caps uppercase tracking-[0.14em] text-outline">
              Local analysis terminal · results are estimates, not proof
            </span>
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-outline/60">
              engine :8000 · interface :5173
            </span>
          </div>
        </footer>
      </div>
    </div>
  );
}
