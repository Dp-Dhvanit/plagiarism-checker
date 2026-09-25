function Shell({ children }) {
  return (
    <div className="rounded-lg border border-outline-variant/40 bg-surface px-3.5 py-2.5 shadow-dropdown">
      {children}
    </div>
  );
}

function Line({ label, value, hex }) {
  return (
    <div className="flex items-baseline justify-between gap-6">
      <span className="text-[11px] text-on-surface-variant">{label}</span>
      <span className="text-[13px] font-semibold tabular-nums" style={{ color: hex || "rgb(var(--on-surface))" }}>{value}</span>
    </div>
  );
}

export function BarTooltip({ active, payload, label, valueLabel = "Value" }) {
  if (!active || !payload?.length) return null;
  return (
    <Shell>
      <div className="mb-1.5 text-[12px] font-medium text-on-surface">{label}</div>
      <Line label={valueLabel} value={payload[0].value?.toLocaleString()} hex={payload[0].payload?.fill} />
    </Shell>
  );
}

export function HBarTooltip({ active, payload, label, valueLabel = "Value", suffix = "" }) {
  if (!active || !payload?.length) return null;
  return (
    <Shell>
      <div className="mb-1.5 text-[12px] font-medium text-on-surface">{label}</div>
      <Line label={valueLabel} value={`${payload[0].value?.toLocaleString()}${suffix}`} />
    </Shell>
  );
}

export function LineTooltip({ active, payload, label, valueLabel = "Value", suffix = "" }) {
  if (!active || !payload?.length) return null;
  return (
    <Shell>
      <div className="mb-1.5 text-[12px] font-medium text-on-surface">{label}</div>
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
      <div className="mb-1.5 text-[12px] font-medium text-on-surface">{d.name}</div>
      <Line label="Value" value={d.value?.toLocaleString()} hex={payload[0].payload?.fill} />
      {pct && <Line label="Share" value={`${pct}%`} />}
    </Shell>
  );
}

export function GroupedTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <Shell>
      <div className="mb-1.5 text-[12px] font-medium text-on-surface">{label}</div>
      {payload.map((p) => (
        <Line key={p.dataKey} label={p.name} value={p.value?.toLocaleString()} hex={p.fill} />
      ))}
    </Shell>
  );
}
