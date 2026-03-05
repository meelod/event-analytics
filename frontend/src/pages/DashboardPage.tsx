/**
 * Main dashboard page - the core feature of the application.
 *
 * This is where the NL-to-SQL pipeline is triggered from the frontend:
 * 1. User types a question in QueryBar
 * 2. handleQuery() sends it to POST /api/v1/query
 * 3. Backend generates SQL (GPT-4o) → validates (sandbox) → executes (DuckDB)
 *    → determines chart type (GPT-4o-mini) → returns everything
 * 4. Response contains: generated_sql, data (rows), chart_config, execution_time_ms
 * 5. ChartRenderer renders the chart based on chart_config
 * 6. Raw data is shown in a scrollable table below the chart
 *
 * Additional features:
 * - "Show SQL" toggle: reveals the LLM-generated SQL for transparency
 * - Save button: persists the visualization (question + SQL + data + chart config)
 *   to the backend for later viewing on the Saved page
 *
 * The data table shows max 100 rows (slice(0, 100)) to prevent DOM bloat,
 * even though the query may return up to 10000 rows (sandbox LIMIT).
 */

import { useState } from "react";
import { api } from "../api/client";
import ChartRenderer from "../components/ChartRenderer";
import QueryBar from "../components/QueryBar";

interface QueryResult {
  question: string;
  generated_sql: string;
  data: Record<string, unknown>[];
  chart_config: any;
  row_count: number;
  execution_time_ms: number;
}

export default function DashboardPage() {
  const [result, setResult] = useState<QueryResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [showSQL, setShowSQL] = useState(false);
  const [saveTitle, setSaveTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleQuery = async (question: string) => {
    setIsLoading(true);
    setError("");
    setResult(null);
    setSaved(false);
    try {
      const res = await api.query(question);
      setResult(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!result || !saveTitle.trim()) return;
    setSaving(true);
    try {
      await api.saveVisualization({
        title: saveTitle.trim(),
        nl_question: result.question,
        generated_sql: result.generated_sql,
        result_data: result.data,
        chart_config: result.chart_config,
      });
      setSaved(true);
      setSaveTitle("");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-sm text-gray-500 mt-1">
          Ask questions about your event data using natural language.
        </p>
      </div>

      <QueryBar onSubmit={handleQuery} isLoading={isLoading} />

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">
                {result.chart_config.title}
              </h3>
              <div className="flex items-center gap-3 text-xs text-gray-400">
                <span>{result.row_count} rows</span>
                <span>{result.execution_time_ms.toFixed(0)}ms</span>
              </div>
            </div>
            <ChartRenderer config={result.chart_config} data={result.data} />
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowSQL(!showSQL)}
              className="px-3 py-1.5 text-xs border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              {showSQL ? "Hide SQL" : "Show SQL"}
            </button>
            {!saved ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={saveTitle}
                  onChange={(e) => setSaveTitle(e.target.value)}
                  placeholder="Visualization title..."
                  className="px-3 py-1.5 border border-gray-300 rounded-md text-xs focus:ring-indigo-500 focus:border-indigo-500"
                />
                <button
                  onClick={handleSave}
                  disabled={saving || !saveTitle.trim()}
                  className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
              </div>
            ) : (
              <span className="text-xs text-green-600">Saved!</span>
            )}
          </div>

          {showSQL && (
            <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
              <pre className="text-sm text-green-400 whitespace-pre-wrap">
                {result.generated_sql}
              </pre>
            </div>
          )}

          {result.data.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200">
                <h4 className="text-sm font-medium text-gray-700">Raw Data</h4>
              </div>
              <div className="overflow-x-auto max-h-64">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      {Object.keys(result.data[0]).map((col) => (
                        <th
                          key={col}
                          className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {result.data.slice(0, 100).map((row, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        {Object.values(row).map((val, j) => (
                          <td key={j} className="px-4 py-2 text-gray-600 whitespace-nowrap">
                            {String(val ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
