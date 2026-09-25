import { useEffect, useRef, useState } from "react";
import { getJSON } from "../../lib/api.js";

/**
 * Entry screen. Genuinely probes GET /health so an unreachable backend is
 * reported immediately — this isn't decorative, the progress bar is tied
 * to a real check. Holds for a short readable minimum, then hands off; it
 * can never trap the user (a hard ceiling always releases it).
 */

const MIN_MS = 700;
const MAX_MS = 6000;

export default function BootScreen({ onReady }) {
  const [progress, setProgress] = useState(0);
  const [health, setHealth] = useState("pending"); // pending | online | offline
  const doneRef = useRef(false);
  const startRef = useRef(performance.now());

  useEffect(() => {
    let cancelled = false;
    getJSON("/health")
      .then(() => !cancelled && setHealth("online"))
      .catch(() => !cancelled && setHealth("offline"));
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let raf = 0;
    const step = () => {
      const t = performance.now() - startRef.current;
      const resolved = health !== "pending" && t >= MIN_MS;
      const timedOut = t >= MAX_MS;

      if (resolved || timedOut) {
        setProgress((p) => {
          const next = p + (100 - p) * 0.22;
          if (next > 99.4 && !doneRef.current) {
            doneRef.current = true;
            setTimeout(() => onReady(health === "offline" ? false : health === "online"), 200);
            return 100;
          }
          return next;
        });
      } else {
        setProgress((p) => Math.min(p + (78 - p) * 0.05, 78));
      }
      if (!doneRef.current) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [health, onReady]);

  const skip = () => {
    if (doneRef.current) return;
    doneRef.current = true;
    onReady(health === "offline" ? false : health === "online" ? true : null);
  };

  useEffect(() => {
    window.addEventListener("keydown", skip);
    return () => window.removeEventListener("keydown", skip);
  });

  return (
    <div
      className="fixed inset-0 z-[100] flex animate-fade-in flex-col items-center justify-center bg-surface px-4"
      onClick={skip}
      role="status"
      aria-live="polite"
    >
      <img src="/logo-96.png" alt="" className="mb-8 h-16 w-16 object-contain dark:hidden" />
      <img src="/logo-dark-96.png" alt="" className="mb-8 hidden h-16 w-16 object-contain dark:block" />

      <div className="h-1.5 w-52 overflow-hidden rounded-full bg-surface-high">
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-150 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      <p className="mt-4 text-[13.5px] text-on-surface-variant">
        {health === "pending" ? "Starting up…" : health === "online" ? "Ready." : "Backend unreachable — continuing anyway."}
      </p>
    </div>
  );
}
