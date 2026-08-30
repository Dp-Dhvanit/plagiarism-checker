import { useCallback, useEffect, useRef, useState } from "react";
import { isAbort } from "./api.js";

/**
 * Drives the staged analysis experience against a *real* request.
 *
 * The contract this hook exists to keep:
 *
 *  • The visual sequence is paced by the stage script, but it can never
 *    finish on its own. Progress eases toward — and asymptotically creeps
 *    below — 100%, so it stays visibly alive without ever parking on a
 *    number and pretending to be done.
 *  • The moment the real request resolves, remaining stages complete and
 *    progress runs cleanly to 100% before the result is revealed.
 *  • If the request fails, the sequence stops on the stage it reached and
 *    the caller renders an error state. No endless spinner.
 *  • Abort is real: it cancels the in-flight fetch via AbortController.
 *
 * Phases: idle → running → finishing → done | error | aborted
 */

const FINISH_MS = 480; // time to sweep the bar from wherever it is to 100%
const CREEP_CEILING = 97; // never reach 100 until the response actually lands

export function useAnalysisRun(stages) {
  const [phase, setPhase] = useState("idle");
  const [progress, setProgress] = useState(0);
  const [stageIndex, setStageIndex] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const rafRef = useRef(0);
  const startRef = useRef(0);
  const abortRef = useRef(null);
  const phaseRef = useRef("idle");
  const mountedRef = useRef(true);
  // Mirrors `progress` so the finish sweep can read it without re-binding.
  const progressRef = useRef(0);

  useEffect(() => {
    progressRef.current = progress;
  }, [progress]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cancelAnimationFrame(rafRef.current);
      abortRef.current?.abort();
    };
  }, []);

  const setPhaseSafe = (p) => {
    phaseRef.current = p;
    if (mountedRef.current) setPhase(p);
  };

  const totalMs = stages.reduce((sum, s) => sum + s.ms, 0);

  /** Cumulative planned time → which stage should be active right now. */
  const stageAt = useCallback(
    (t) => {
      let acc = 0;
      for (let i = 0; i < stages.length; i += 1) {
        acc += stages[i].ms;
        if (t < acc) return i;
      }
      return stages.length - 1; // hold on the last stage
    },
    [stages]
  );

  const tick = useCallback(() => {
    if (phaseRef.current !== "running") return;
    const t = performance.now() - startRef.current;

    let p;
    if (t < totalMs) {
      // Ease-out across the scripted sequence, capped well short of done.
      const r = t / totalMs;
      p = 92 * (1 - Math.pow(1 - r, 2.2));
    } else {
      // Overrun: the backend is taking longer than the script. Creep, never
      // stall, never arrive.
      const over = t - totalMs;
      p = 92 + (CREEP_CEILING - 92) * (1 - Math.exp(-over / (totalMs || 1000)));
    }

    if (mountedRef.current) {
      setProgress(p);
      setStageIndex(stageAt(t));
      setElapsed(t);
    }
    rafRef.current = requestAnimationFrame(tick);
  }, [stageAt, totalMs]);

  /** Sweep the bar to 100% and settle into `done`. */
  const finish = useCallback((payload) => {
    cancelAnimationFrame(rafRef.current);
    setPhaseSafe("finishing");
    if (mountedRef.current) setStageIndex(stages.length - 1);

    const from = progressRef.current;
    const t0 = performance.now();
    const sweep = () => {
      const r = Math.min((performance.now() - t0) / FINISH_MS, 1);
      const eased = 1 - Math.pow(1 - r, 3);
      if (mountedRef.current) setProgress(from + (100 - from) * eased);
      if (r < 1) {
        rafRef.current = requestAnimationFrame(sweep);
      } else if (mountedRef.current) {
        setResult(payload);
        setPhaseSafe("done");
      }
    };
    rafRef.current = requestAnimationFrame(sweep);
  }, [stages.length]);

  /**
   * @param {(opts: {signal: AbortSignal}) => Promise<any>} requestFn
   * @returns {Promise<any|null>} the payload, or null if it failed/aborted
   */
  const run = useCallback(
    async (requestFn) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setError("");
      setResult(null);
      setProgress(0);
      progressRef.current = 0;
      setStageIndex(0);
      setElapsed(0);
      setPhaseSafe("running");
      startRef.current = performance.now();
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(tick);

      try {
        const payload = await requestFn({ signal: controller.signal });
        if (!mountedRef.current || controller.signal.aborted) return null;
        finish(payload);
        return payload;
      } catch (err) {
        cancelAnimationFrame(rafRef.current);
        if (!mountedRef.current) return null;
        if (isAbort(err)) {
          setPhaseSafe("aborted");
          setProgress(0);
          return null;
        }
        setError(err?.message || "The analysis could not be completed.");
        setPhaseSafe("error");
        return null;
      }
    },
    [finish, tick]
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    cancelAnimationFrame(rafRef.current);
    setPhaseSafe("aborted");
    setProgress(0);
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    cancelAnimationFrame(rafRef.current);
    setPhaseSafe("idle");
    setProgress(0);
    progressRef.current = 0;
    setStageIndex(0);
    setElapsed(0);
    setError("");
    setResult(null);
  }, []);

  /** "done" | "active" | "pending" | "failed" for each stage. */
  const stageStates = stages.map((_, i) => {
    if (phase === "done" || phase === "finishing") return "done";
    if (phase === "error") {
      if (i < stageIndex) return "done";
      if (i === stageIndex) return "failed";
      return "pending";
    }
    if (i < stageIndex) return "done";
    if (i === stageIndex) return "active";
    return "pending";
  });

  return {
    phase,
    progress,
    stageIndex,
    stageStates,
    elapsedMs: elapsed,
    /** True once the script has run out but the request is still in flight. */
    overrunning: phase === "running" && elapsed > totalMs,
    error,
    result,
    isBusy: phase === "running" || phase === "finishing",
    run,
    abort,
    reset,
    setResult,
  };
}
