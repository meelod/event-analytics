/**
 * Config-driven chart renderer.
 *
 * This component takes a ChartConfig JSON (from the backend's GPT-4o-mini call)
 * and an array of data rows, and renders the appropriate Recharts chart.
 *
 * The key design pattern is "config-driven rendering":
 * - The backend decides WHAT to render (chart type, axes, series)
 * - This component just maps config → React components
 * - No business logic here - it's purely a presentation layer
 *
 * Supports 5 chart types:
 * - "number": Single big metric (e.g., "Total Users: 1,234")
 * - "pie": Proportional data (e.g., "Events by type")
 * - "line": Time series (e.g., "DAU over 30 days")
 * - "bar": Categorical comparison (e.g., "Top 5 events")
 * - "area": Time series with filled area (e.g., "Revenue over time")
 *
 * The component lookup pattern (lines 79-89) avoids a big switch statement:
 * instead of if/else for each chart type, we use an object as a map from
 * chart_type string → React component class.
 */

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Color palette for chart series. Cycles if there are more series than colors.
const COLORS = ["#8884d8", "#82ca9d", "#ffc658", "#ff7300", "#0088fe", "#00C49F", "#FFBB28", "#FF8042"];

// This interface matches the JSON shape returned by chart_config.py on the backend
interface ChartConfig {
  chart_type: "line" | "bar" | "area" | "pie" | "number";
  title: string;
  x_axis: string | null;   // Column name for X axis (e.g., "day")
  y_axis: string | null;   // Column name for Y axis (e.g., "daily_users")
  series: Array<{ dataKey: string; name: string; color?: string }>;
}

interface Props {
  config: ChartConfig;
  data: Record<string, unknown>[];  // Array of row objects from the SQL query
}

export default function ChartRenderer({ config, data }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        No data to display
      </div>
    );
  }

  // ── "number" type: single metric display ───────────────────────────
  // Used for queries like "How many users signed up?" → shows "1,234" big
  if (config.chart_type === "number") {
    const value = data[0]?.[config.series[0]?.dataKey];
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="text-5xl font-bold text-indigo-600">{String(value)}</div>
        <div className="text-gray-500 mt-3 text-lg">{config.title}</div>
      </div>
    );
  }

  // ── "pie" type: needs special Recharts components ──────────────────
  // PieChart uses Pie + Cell (for colors) instead of XAxis/YAxis
  if (config.chart_type === "pie") {
    const dataKey = config.series[0]?.dataKey || config.y_axis || "";
    const nameKey = config.x_axis || "";
    return (
      <ResponsiveContainer width="100%" height={400}>
        <PieChart>
          <Pie
            data={data}
            dataKey={dataKey}
            nameKey={nameKey}
            cx="50%"
            cy="50%"
            outerRadius={150}
            label={(entry) => entry[nameKey] || ""}
          >
            {/* Each slice gets a color from the palette */}
            {data.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  // ── line/bar/area: share the same XAxis/YAxis/CartesianGrid structure ──
  // We use object lookup to pick the right Recharts component class
  const ChartComponent = {
    line: LineChart,
    bar: BarChart,
    area: AreaChart,
  }[config.chart_type] || LineChart;

  // The "series element" differs: Line for line charts, Bar for bar charts, etc.
  const SeriesComponent = {
    line: Line,
    bar: Bar,
    area: Area,
  }[config.chart_type] || Line;

  return (
    <ResponsiveContainer width="100%" height={400}>
      <ChartComponent data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey={config.x_axis || undefined}
          tick={{ fontSize: 12 }}
          angle={-45}        // Rotate labels to prevent overlap on date axes
          textAnchor="end"
          height={80}
        />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        {/* Render one series element per data series in the config */}
        {config.series.map((s, i) => (
          <SeriesComponent
            key={s.dataKey}
            type="monotone"       // Smooth interpolation for line/area
            dataKey={s.dataKey}   // Which column to plot
            name={s.name}         // Legend label
            stroke={s.color || COLORS[i % COLORS.length]}
            fill={s.color || COLORS[i % COLORS.length]}
            fillOpacity={config.chart_type === "area" ? 0.3 : 1}
          />
        ))}
      </ChartComponent>
    </ResponsiveContainer>
  );
}
