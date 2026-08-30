import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import GlassCard from "../common/GlassCard.jsx";
import { SectionTitle } from "../common/PageHeader.jsx";
import { BarTooltip, GroupedTooltip, HBarTooltip, LineTooltip, PieTooltip } from "./ChartTooltips.jsx";
import { CHART_COLORS } from "../../data/constants.js";

const AXIS = { fontSize: 11, fill: "#8d90a0", fontFamily: "JetBrains Mono, monospace" };
const GRID = "#2a2a2c";
const CURSOR = { fill: "rgba(180,197,255,0.06)" };

const CHART_ICON = { bar: "bar_chart", hbar: "bar_chart", pie: "pie_chart", line: "show_chart", "grouped-bar": "stacked_bar_chart" };

const legendStyle = (v) => (
  <span style={{ fontSize: 11, color: "#c3c6d7", fontFamily: "JetBrains Mono, monospace" }}>{v}</span>
);

export default function ChartCard({ chart, index = 0 }) {
  const data = chart.data || [];
  const total = data.reduce((s, d) => s + (d.value || 0), 0);
  const withTotal = data.map((d) => ({ ...d, total }));
  const suffix = chart.value_suffix || "";
  const valueLabel = chart.value_label || "Value";
  const hbarHeight = Math.max(180, data.length * 38);

  return (
    <GlassCard code={`VIZ_${String(index + 1).padStart(2, "0")} // ${(chart.type || "bar").toUpperCase()}`}>
      <SectionTitle icon={CHART_ICON[chart.type] || "bar_chart"}>{chart.title}</SectionTitle>

      {chart.type === "bar" && (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} margin={{ top: 4, right: 8, left: -12, bottom: 44 }}>
            <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" tick={AXIS} angle={-30} textAnchor="end" interval={0} tickLine={false} axisLine={{ stroke: GRID }} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} />
            <Tooltip content={<BarTooltip valueLabel={valueLabel} />} cursor={CURSOR} />
            <Bar dataKey="value" radius={[3, 3, 0, 0]} maxBarSize={48} animationDuration={900}>
              {data.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      {chart.type === "hbar" && (
        <ResponsiveContainer width="100%" height={hbarHeight}>
          <BarChart layout="vertical" data={data} margin={{ top: 4, right: 52, left: 4, bottom: 4 }}>
            <CartesianGrid stroke={GRID} strokeDasharray="3 3" horizontal={false} />
            <XAxis
              type="number" domain={[0, "dataMax"]} tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }}
              tickFormatter={(v) => `${v.toLocaleString()}${suffix}`}
            />
            <YAxis type="category" dataKey="name" tick={AXIS} width={64} tickLine={false} axisLine={false} />
            <Tooltip content={<HBarTooltip valueLabel={valueLabel} suffix={suffix} />} cursor={CURSOR} />
            <Bar
              dataKey="value" radius={[0, 3, 3, 0]} maxBarSize={22} animationDuration={900}
              label={{ position: "right", fontSize: 11, fill: "#8d90a0", formatter: (v) => `${v.toLocaleString()}${suffix}` }}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      {chart.type === "pie" && (
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={withTotal} cx="50%" cy="45%" innerRadius={58} outerRadius={94}
              paddingAngle={3} dataKey="value" animationDuration={900} labelLine={false}
              label={({ percent }) => (percent > 0.06 ? `${(percent * 100).toFixed(0)}%` : "")}
              stroke="#131315" strokeWidth={2}
            >
              {withTotal.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<PieTooltip />} />
            <Legend formatter={legendStyle} wrapperStyle={{ paddingTop: 14 }} />
          </PieChart>
        </ResponsiveContainer>
      )}

      {chart.type === "line" && (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data} margin={{ top: 4, right: 16, left: -12, bottom: 4 }}>
            <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} tickFormatter={(v) => `${v.toLocaleString()}${suffix}`} />
            <Tooltip content={<LineTooltip valueLabel={valueLabel} suffix={suffix} />} cursor={{ stroke: "#434655" }} />
            <Line
              type="monotone" dataKey="value" stroke={CHART_COLORS[0]} strokeWidth={2}
              dot={{ r: 3, fill: CHART_COLORS[0], strokeWidth: 0 }}
              activeDot={{ r: 5 }} animationDuration={900}
            />
          </LineChart>
        </ResponsiveContainer>
      )}

      {chart.type === "grouped-bar" && (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 4, right: 8, left: -12, bottom: 44 }}>
            <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" tick={AXIS} angle={-30} textAnchor="end" interval={0} tickLine={false} axisLine={{ stroke: GRID }} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} />
            <Tooltip content={<GroupedTooltip />} cursor={CURSOR} />
            <Legend formatter={legendStyle} />
            {(chart.series || []).map((s, i) => (
              <Bar
                key={s.key} dataKey={s.key} name={s.label}
                fill={CHART_COLORS[i % CHART_COLORS.length]}
                radius={[3, 3, 0, 0]} maxBarSize={26} animationDuration={900}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      )}
    </GlassCard>
  );
}
