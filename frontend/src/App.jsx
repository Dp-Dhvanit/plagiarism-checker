import { useCallback, useEffect, useState } from "react";
import BootScreen from "./components/layout/BootScreen.jsx";
import AppShell from "./components/layout/AppShell.jsx";
import Dashboard from "./components/dashboard/Dashboard.jsx";
import TextTab from "./components/text/TextTab.jsx";
import FileTab from "./components/file/FileTab.jsx";
import CodeTab from "./components/code/CodeTab.jsx";
import ImageTab from "./components/image/ImageTab.jsx";
import SummaryTab from "./components/summary/SummaryTab.jsx";
import HistoryTab from "./components/history/HistoryTab.jsx";
import Icon from "./components/common/Icon.jsx";

const SURFACES = {
  dashboard: Dashboard,
  text: TextTab,
  file: FileTab,
  code: CodeTab,
  image: ImageTab,
  summary: SummaryTab,
  history: HistoryTab,
};

/** Deep-link support: #text, #history, … so surfaces are addressable. */
function surfaceFromHash() {
  const key = window.location.hash.replace("#", "");
  return SURFACES[key] ? key : "dashboard";
}

export default function App() {
  const [booted, setBooted] = useState(false);
  const [backendOnline, setBackendOnline] = useState(null);
  const [surface, setSurface] = useState(surfaceFromHash);

  useEffect(() => {
    const onHash = () => setSurface(surfaceFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = useCallback((key) => {
    setSurface(key);
    window.location.hash = key;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const onReady = useCallback((online) => {
    setBackendOnline(online);
    setBooted(true);
  }, []);

  if (!booted) return <BootScreen onReady={onReady} />;

  const Surface = SURFACES[surface] || Dashboard;

  return (
    <AppShell active={surface} onNavigate={navigate} backendOnline={backendOnline}>
      {backendOnline === false && <OfflineBanner />}
      {/* Remount on surface change so each module starts from its input state. */}
      <div key={surface} className="animate-rise">
        <Surface onNavigate={navigate} />
      </div>
    </AppShell>
  );
}

function OfflineBanner() {
  return (
    <div className="mb-7 flex items-start gap-3.5 rounded-lg border border-error/35 bg-error-container/15 px-5 py-4">
      <Icon name="cloud_off" size={20} className="mt-px shrink-0 text-error" />
      <div>
        <p className="font-display text-[15px] font-bold text-error">Analysis engine unreachable</p>
        <p className="mt-1.5 text-[13.5px] leading-relaxed text-on-surface-variant/85">
          Nothing responded on <span className="font-mono text-error">127.0.0.1:8000</span>. Start
          the backend with{" "}
          <span className="font-mono text-on-surface">uvicorn app.main:app --reload --port 8000</span>{" "}
          from the <span className="font-mono text-on-surface">backend/</span> directory, then
          reload this page. You can browse the interface meanwhile, but analyses will fail.
        </p>
      </div>
    </div>
  );
}
