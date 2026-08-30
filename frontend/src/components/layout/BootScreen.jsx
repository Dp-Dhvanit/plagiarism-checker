import { useEffect, useRef, useState } from "react";
import Icon from "../common/Icon.jsx";
import { BRAND } from "../../data/constants.js";
import { getJSON } from "../../lib/api.js";

/**
 * Entry sequence (reference screen-1).
 *
 * This is not decorative: the boot genuinely probes GET /health, so the
 * progress bar is tied to a real check and the user learns immediately if
 * the detection engine is not running. It holds for a minimum readable
 * beat, then hands off — it can never trap the user.
 */

const MIN_MS = 1700; // long enough to read the sequence
const MAX_MS = 6000; // hard ceiling — never hold the app hostage

const LOG = [
  { t: "> INITIATING DETECTION_CORE/OS_V2...", tone: "dim" },
  { t: "> ALLOCATING MEMORY SECTORS... [OK]", tone: "dim" },
  { t: "> MOUNTING ANALYSIS MODULES... [6/6]", tone: "dim" },
  { t: "> LOADING PERPLEXITY MODEL...", tone: "dim" },
  { t: "> LOADING BURSTINESS HEURISTICS...", tone: "dim" },
  { t: "> OPENING HISTORY STORE... [OK]", tone: "dim" },
  { t: "> PROBING ANALYSIS ENGINE // :8000", tone: "primary" },
];

export default function BootScreen({ onReady }) {
  const [progress, setProgress] = useState(0);
  const [health, setHealth] = useState("pending"); // pending | online | offline
  const [lines, setLines] = useState([]);
  const doneRef = useRef(false);
  const startRef = useRef(performance.now());

  // Reveal the log lines one at a time.
  useEffect(() => {
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setLines(LOG.slice(0, i));
      if (i >= LOG.length) clearInterval(id);
    }, 150);
    return () => clearInterval(id);
  }, []);

  // Real health probe.
  useEffect(() => {
    let cancelled = false;
    getJSON("/health")
      .then(() => !cancelled && setHealth("online"))
      .catch(() => !cancelled && setHealth("offline"));
    return () => { cancelled = true; };
  }, []);

  // Progress creeps to 88% while the probe is out, then completes.
  useEffect(() => {
    let raf = 0;
    const step = () => {
      const t = performance.now() - startRef.current;
      const resolved = health !== "pending" && t >= MIN_MS;
      const timedOut = t >= MAX_MS;

      if (resolved || timedOut) {
        setProgress((p) => {
          const next = p + (100 - p) * 0.18;
          if (next > 99.4 && !doneRef.current) {
            doneRef.current = true;
            setTimeout(() => onReady(health === "offline" ? false : health === "online"), 260);
            return 100;
          }
          return next;
        });
      } else {
        setProgress((p) => Math.min(p + (88 - p) * 0.035, 88));
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

  // Any key or click gets you straight in.
  useEffect(() => {
    window.addEventListener("keydown", skip);
    return () => window.removeEventListener("keydown", skip);
  });

  const statusLine =
    health === "online" ? { text: "> ENGINE ONLINE. HANDING OFF TO TERMINAL.", cls: "text-tertiary" }
    : health === "offline" ? { text: "> ENGINE UNREACHABLE ON :8000 — START THE BACKEND.", cls: "text-error" }
    : { text: "> AWAITING ENGINE RESPONSE...", cls: "text-primary" };

  return (
    <div
      className="fixed inset-0 z-[100] flex animate-fade-in flex-col items-center justify-center overflow-hidden bg-void px-4"
      onClick={skip}
      role="status"
      aria-live="polite"
    >
      {/* Wordmark behind the terminal, deliberately soft-focused */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 flex select-none items-center justify-center"
      >
        <span className="whitespace-nowrap font-display text-[16vw] font-extrabold tracking-tighter text-on-surface/[0.055] blur-[3px]">
          {BRAND}
        </span>
      </div>

      {/* Terminal */}
      <div className="relative z-10 w-full max-w-2xl rounded-lg border border-outline-variant/30 bg-surface-lowest/60 p-6 backdrop-blur-sm">
        <div className="mb-6 flex items-center gap-2">
          <span className="h-2 w-2 animate-pulse rounded-full bg-tertiary" />
          <span className="font-mono text-label-caps uppercase tracking-[0.16em] text-tertiary">
            SYS_BOOT_SEQ
          </span>
        </div>

        <div className="min-h-[172px] font-mono text-data-sm leading-[1.9] text-primary/60">
          {lines.map((l, i) => (
            <div key={i} className={`animate-fade-in ${l.tone === "primary" ? "text-primary" : ""}`}>
              {l.t}
            </div>
          ))}
          {lines.length >= LOG.length && (
            <div className={`animate-fade-in ${statusLine.cls}`}>{statusLine.text}</div>
          )}
        </div>
      </div>

      {/* Bottom status rail */}
      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-primary/25 bg-surface-lowest/85 backdrop-blur-sm">
        {/* rAF-driven width — no CSS transition (see ProgressRail). */}
        <div className="progress-live h-0.5" style={{ width: `${progress}%` }} />
        <div className="mx-auto flex max-w-shell flex-col gap-2 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-page">
          <div className="flex items-center gap-4">
            <Icon name="data_usage" size={24} className="animate-spin-slow text-primary" />
            <div className="flex flex-col sm:flex-row sm:items-baseline sm:gap-4">
              <h1 className="font-mono text-label-caps uppercase tracking-[0.16em] text-on-surface">
                SYSTEM INITIALIZATION:
                <span className="ml-2 font-mono text-[17px] font-medium tracking-[0.05em] text-primary">
                  {Math.round(progress)}%
                </span>
                <span className="animate-blink text-primary">_</span>
              </h1>
              <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-on-surface-variant/60">
                {health === "pending" ? "CONTACTING ANALYSIS ENGINE" : "MODULES RESOLVED"} // SEC_00
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-outline">
            press any key to skip
          </span>
        </div>
      </div>
    </div>
  );
}
