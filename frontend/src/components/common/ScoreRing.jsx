import { useEffect, useRef, useState } from "react";

/**
 * The headline probability ring. Counts up from zero on mount so the
 * number arrives rather than appearing instantly — a meaningful, restrained
 * use of animation (communicates "this was just computed").
 */
export default function ScoreRing({
  value,
  label = "AI LIKELIHOOD\nESTIMATE",
  hex = "#D97862",
  size = 220,
  stroke = 8,
  suffix = "%",
  duration = 1100,
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
        <circle cx="50" cy="50" r={r} fill="transparent" stroke="rgb(var(--surface-container))" strokeWidth={stroke / 2} />
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
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-display text-[42px] font-bold leading-none tracking-tight"
          style={{ color: hex }}
        >
          {Math.round(shown)}
          <span className="text-[24px]">{suffix}</span>
        </span>
        <span className="mt-2.5 whitespace-pre-line text-center text-[11.5px] font-medium uppercase leading-[1.5] tracking-[0.08em] text-outline">
          {label}
        </span>
      </div>
    </div>
  );
}
