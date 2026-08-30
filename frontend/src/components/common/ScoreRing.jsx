import { useEffect, useRef, useState } from "react";

/**
 * The headline probability ring (reference screen-3 / screen-6).
 *
 * Counts up from zero on mount so the number *arrives* rather than
 * appearing — the visual continuation of the analysis sweep.
 */
export default function ScoreRing({
  value,
  label = "AI CONTENT\nPROBABILITY",
  hex = "#ddb8ff",
  size = 232,
  stroke = 4,
  suffix = "%",
  duration = 1300,
}) {
  const [shown, setShown] = useState(0);
  const raf = useRef(0);

  useEffect(() => {
    const target = Number(value) || 0;
    const t0 = performance.now();
    const step = (ts) => {
      const r = Math.min((ts - t0) / duration, 1);
      setShown(target * (1 - Math.pow(1 - r, 3)));
      if (r < 1) raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf.current);
  }, [value, duration]);

  const r = 45;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - Math.min(Math.max(shown, 0), 100) / 100);

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
        <circle cx="50" cy="50" r={r} fill="transparent" stroke="#2a2a2c" strokeWidth={stroke / 2} />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="transparent"
          stroke={hex}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ filter: `drop-shadow(0 0 6px ${hex}66)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-display text-[44px] font-extrabold leading-none tracking-tight"
          style={{ color: hex }}
        >
          {Math.round(shown)}
          <span className="text-[26px]">{suffix}</span>
        </span>
        <span className="mt-2 whitespace-pre-line text-center font-mono text-label-caps uppercase leading-[1.5] tracking-[0.14em] text-on-surface-variant/70">
          {label}
        </span>
      </div>
    </div>
  );
}
