/**
 * Saved visualizations page - browse and reload previously saved analytics.
 *
 * Data flow:
 * 1. On mount, fetches the list (GET /api/v1/visualizations) - just metadata, no chart data
 * 2. When user clicks a card, fetches full detail (GET /api/v1/visualizations/:id)
 *    which includes the snapshot of result_data + chart_config
 * 3. ChartRenderer renders the chart from the saved data - no LLM call needed
 *
 * Trade-off: Saved visualizations store a SNAPSHOT of the data at save time.
 * They don't re-run the query, so the chart is instant but may be stale.
 * This is intentional - it avoids burning LLM tokens on every reload.
 *
 * Delete: removes the visualization from the backend and optimistically
 * removes it from the local list (no need to re-fetch).
 */

import { useEffect, useState } from "react";
import { api } from "../api/client";
import ChartRenderer from "../components/ChartRenderer";

interface VizListItem {
  id: string;
  title: string;
  nl_question: string;
  chart_type: string | null;
  created_at: string;
}

interface VizDetail {
  id: string;
  title: string;
  nl_question: string;
  generated_sql: string;
  result_data: Record<string, unknown>[];
  chart_config: any;
  created_at: string;
}

export default function SavedVisualizationsPage() {
  const [items, setItems] = useState<VizListItem[]>([]);
  const [selected, setSelected] = useState<VizDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    loadList();
  }, []);

  const loadList = async () => {
    setLoading(true);
    try {
      const res = await api.listVisualizations();
      setItems(res);
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (id: string) => {
    setLoadingDetail(true);
    try {
      const res = await api.getVisualization(id);
      setSelected(res);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDelete = async (id: string) => {
    await api.deleteVisualization(id);
    setItems(items.filter((i) => i.id !== id));
    if (selected?.id === id) setSelected(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Saved Visualizations</h2>
        <p className="text-sm text-gray-500 mt-1">
          View and reload your saved analytics.
        </p>
      </div>

      {loading ? (
        <div className="text-gray-400 text-sm">Loading...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">No saved visualizations yet</p>
          <p className="text-sm mt-1">
            Ask a question on the Dashboard and save the result.
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {items.map((item) => (
            <div
              key={item.id}
              className={`bg-white rounded-lg border p-4 cursor-pointer transition-all ${
                selected?.id === item.id
                  ? "border-indigo-300 ring-2 ring-indigo-100"
                  : "border-gray-200 hover:border-gray-300"
              }`}
              onClick={() => loadDetail(item.id)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">{item.title}</h3>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {item.nl_question}
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                    {item.chart_type && (
                      <span className="px-2 py-0.5 bg-gray-100 rounded-full">
                        {item.chart_type}
                      </span>
                    )}
                    <span>
                      {new Date(item.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(item.id);
                  }}
                  className="text-xs text-red-400 hover:text-red-600 px-2 py-1"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {loadingDetail && (
        <div className="text-gray-400 text-sm">Loading visualization...</div>
      )}

      {selected && !loadingDetail && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">{selected.title}</h3>
            <button
              onClick={() => setSelected(null)}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              Close
            </button>
          </div>
          <p className="text-sm text-gray-500">{selected.nl_question}</p>
          <ChartRenderer
            config={selected.chart_config}
            data={selected.result_data}
          />
          <div className="bg-gray-900 rounded-lg p-4">
            <pre className="text-sm text-green-400 whitespace-pre-wrap">
              {selected.generated_sql}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
