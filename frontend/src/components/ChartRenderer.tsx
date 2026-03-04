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

const COLORS = ["#8884d8", "#82ca9d", "#ffc658", "#ff7300", "#0088fe", "#00C49F", "#FFBB28", "#FF8042"];

interface ChartConfig {
  chart_type: "line" | "bar" | "area" | "pie" | "number";
  title: string;
  x_axis: string | null;
  y_axis: string | null;
  series: Array<{ dataKey: string; name: string; color?: string }>;
}

interface Props {
  config: ChartConfig;
  data: Record<string, unknown>[];
}

export default function ChartRenderer({ config, data }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        No data to display
      </div>
    );
  }

  if (config.chart_type === "number") {
    const value = data[0]?.[config.series[0]?.dataKey];
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="text-5xl font-bold text-indigo-600">{String(value)}</div>
        <div className="text-gray-500 mt-3 text-lg">{config.title}</div>
      </div>
    );
  }

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

  const ChartComponent = {
    line: LineChart,
    bar: BarChart,
    area: AreaChart,
  }[config.chart_type] || LineChart;

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
          angle={-45}
          textAnchor="end"
          height={80}
        />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        {config.series.map((s, i) => (
          <SeriesComponent
            key={s.dataKey}
            type="monotone"
            dataKey={s.dataKey}
            name={s.name}
            stroke={s.color || COLORS[i % COLORS.length]}
            fill={s.color || COLORS[i % COLORS.length]}
            fillOpacity={config.chart_type === "area" ? 0.3 : 1}
          />
        ))}
      </ChartComponent>
    </ResponsiveContainer>
  );
}
