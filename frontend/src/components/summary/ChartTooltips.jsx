function Shell({ children }) {
  return (
    <div className="rounded border border-outline-variant/50 bg-surface-lowest/95 px-3.5 py-2.5 shadow-neon backdrop-blur">
      {children}
    </div>
  );
}

function Line({ label, value, hex }) {
  return (
    <div className="flex items-baseline justify-between gap-6">
      <span className="font-mono text-[11px] uppercase tracking-[0.1em] text-outline">{label}</span>
      <span className="font-mono text-[13px] font-medium tabular-nums" style={{ color: hex || "#e5e1e4" }}>
        {value}
      </span>
    </div>
  );
}

export function BarTooltip({ active, payload, label, valueLabel = "Value" }) {
  if (!active || !payload?.length) return null;
  return (
    <Shell>
      <div className="mb-1.5 font-mono text-[12px] text-on-surface">{label}</div>
      <Line label={valueLabel} value={payload[0].value?.toLocaleString()} hex={payload[0].payload?.fill} />
    </Shell>
  );
}

export function HBarTooltip({ active, payload, label, valueLabel = "Value", suffix = "" }) {
  if (!active || !payload?.length) return null;
  return (
    <Shell>
      <div className="mb-1.5 font-mono text-[12px] text-on-surface">{label}</div>
      <Line label={valueLabel} value={`${payload[0].value?.toLocaleString()}${suffix}`} />
    </Shell>
  );
}

export function LineTooltip({ active, payload, label, valueLabel = "Value", suffix = "" }) {
  if (!active || !payload?.length) return null;
  return (
    <Shell>
      <div className="mb-1.5 font-mono text-[12px] text-on-surface">{label}</div>
      <Line label={valueLabel} value={`${payload[0].value?.toLocaleString()}${suffix}`} hex={payload[0].stroke} />
    </Shell>
  );
}

export function PieTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const pct = d.total ? ((d.value / d.total) * 100).toFixed(1) : null;
  return (
    <Shell>
      <div className="mb-1.5 font-mono text-[12px] text-on-surface">{d.name}</div>
      <Line label="Value" value={d.value?.toLocaleString()} hex={payload[0].payload?.fill} />
      {pct && <Line label="Share" value={`${pct}%`} />}
    </Shell>
  );
}

export function GroupedTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <Shell>
      <div className="mb-1.5 font-mono text-[12px] text-on-surface">{label}</div>
      {payload.map((p) => (
        <Line key={p.dataKey} label={p.name} value={p.value?.toLocaleString()} hex={p.fill} />
      ))}
    </Shell>
  );
}
