import { useEffect, useRef, useState } from "react";

/**
 * Terminal log (reference screens 8 and 10).
 *
 * Lines are generated from the *actual* stage transitions of the run — one
 * entry per stage the pipeline enters, plus the real terminal outcome. It
 * reports the sequence rather than inventing telemetry.
 */
export default function LogStream({ stages, stageIndex, phase, error, height = "h-64" }) {
  const [lines, setLines] = useState([]);
  const lastIndex = useRef(-1);
  const closed = useRef(false);
  const prevPhase = useRef("idle");
  const scrollRef = useRef(null);

  const stamp = () =>
    new Date().toLocaleTimeString("en-GB", { hour12: false }) +
    "." +
    String(Math.floor((Date.now() % 1000) / 10)).padStart(2, "0");

  // Start a fresh log on every entry into "running" — including a retry
  // after a failed run, which must not inherit the previous run's lines.
  useEffect(() => {
    if (phase === "running" && prevPhase.current !== "running") {
      lastIndex.current = -1;
      closed.current = false;
      setLines([{ ts: stamp(), tag: "SYS", text: "Analysis sequence started.", tone: "primary" }]);
    }
    if (phase === "idle") {
      lastIndex.current = -1;
      closed.current = false;
      setLines([]);
    }
    prevPhase.current = phase;
  }, [phase]);

  // One line per stage entered.
  useEffect(() => {
    if (phase !== "running" && phase !== "finishing") return;
    if (stageIndex === lastIndex.current) return;

    const entered = [];
    for (let i = lastIndex.current + 1; i <= stageIndex; i += 1) {
      const s = stages[i];
      if (!s) continue;
      if (i > 0 && stages[i - 1]) {
        entered.push({ ts: stamp(), tag: "OK", text: `${stages[i - 1].label} — complete.`, tone: "lime" });
      }
      entered.push({ ts: stamp(), tag: "RUN", text: `${s.label}: ${s.note?.toLowerCase() || "working"}…`, tone: "dim" });
    }
    lastIndex.current = stageIndex;
    if (entered.length) setLines((prev) => [...prev, ...entered]);
  }, [stageIndex, phase, stages]);

  // Terminal outcome.
  useEffect(() => {
    if (closed.current) return;
    if (phase === "done") {
      closed.current = true;
      setLines((prev) => [
        ...prev,
        { ts: stamp(), tag: "OK", text: `${stages[stages.length - 1]?.label} — complete.`, tone: "lime" },
        { ts: stamp(), tag: "DONE", text: "Result received. Rendering report.", tone: "lime" },
      ]);
    } else if (phase === "error") {
      closed.current = true;
      setLines((prev) => [
        ...prev,
        { ts: stamp(), tag: "FAIL", text: error || "Request failed.", tone: "error" },
      ]);
    } else if (phase === "aborted") {
      closed.current = true;
      setLines((prev) => [...prev, { ts: stamp(), tag: "ABRT", text: "Sequence aborted by operator.", tone: "error" }]);
    }
  }, [phase, error, stages]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [lines]);

  const TONE = { lime: "text-tertiary", error: "text-error", primary: "text-primary", dim: "text-on-surface-variant/70" };
  const TAG = { OK: "text-tertiary", FAIL: "text-error", ABRT: "text-error", DONE: "text-tertiary", RUN: "text-primary", SYS: "text-primary" };

  return (
    <div className="relative overflow-hidden rounded-lg border border-outline-variant/35 bg-surface-lowest/60">
      <div className="flex items-center justify-between border-b border-outline-variant/25 px-4 py-2.5">
        <span className="font-mono text-label-caps uppercase tracking-[0.14em] text-primary">LOG_STREAM</span>
        <span className="flex items-center gap-1.5">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              phase === "running" ? "animate-pulse bg-secondary" : phase === "error" ? "bg-error" : "bg-tertiary"
            }`}
          />
          <span className="font-mono text-label-caps uppercase tracking-[0.14em] text-on-surface-variant/70">
            {phase === "running" ? "LIVE" : "CLOSED"}
          </span>
        </span>
      </div>

      <div ref={scrollRef} className={`${height} overflow-y-auto px-4 py-3.5 font-mono text-[11.5px] leading-[1.85]`}>
        {lines.map((l, i) => (
          <div key={i} className="flex animate-fade-in gap-2">
            <span className="shrink-0 text-outline/60">[{l.ts}]</span>
            <span className={`shrink-0 font-bold ${TAG[l.tag] || "text-outline"}`}>{l.tag}:</span>
            <span className={TONE[l.tone]}>{l.text}</span>
          </div>
        ))}
        {(phase === "running" || phase === "finishing") && (
          <div className="flex gap-2 text-primary">
            <span>&gt;</span>
            <span className="animate-blink">_</span>
          </div>
        )}
      </div>
    </div>
  );
}
