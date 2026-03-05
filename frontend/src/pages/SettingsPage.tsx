/**
 * Settings page - displays org info, API docs, and developer tools.
 *
 * Shows:
 * - Organization name, slug, and UUID
 * - Example curl commands for single and batch event ingestion
 * - Developer mode toggle with a "Seed Demo Data" button
 *
 * Developer mode:
 * - A checkbox toggle reveals the seed button
 * - Clicking "Seed Demo Data" calls POST /api/v1/events/seed
 * - The backend generates randomized events (same logic as seed.py)
 * - On success, shows the count and event type distribution
 * - devMode is local state (useState) — resets on page refresh, which is fine
 */

import { useState } from "react";
import { api } from "../api/client";
import { useAuthStore } from "../stores/authStore";

interface SeedResult {
  inserted: number;
  distribution: Record<string, number>;
}

export default function SettingsPage() {
  const { orgId, orgName, orgSlug } = useAuthStore();

  // Developer mode state (local to this page, not persisted)
  const [devMode, setDevMode] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<SeedResult | null>(null);
  const [seedError, setSeedError] = useState("");

  const handleSeed = async () => {
    setSeeding(true);
    setSeedError("");
    setSeedResult(null);
    try {
      const res = await api.seedDemoData(1000, 30);
      setSeedResult({ inserted: res.inserted, distribution: res.distribution });
    } catch (err: any) {
      setSeedError(err.message);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Settings</h2>
        <p className="text-sm text-gray-500 mt-1">
          Organization details and API configuration.
        </p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <h3 className="font-semibold text-gray-900">Organization</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Name</span>
            <p className="font-medium text-gray-900">{orgName}</p>
          </div>
          <div>
            <span className="text-gray-500">Slug</span>
            <p className="font-medium text-gray-900">{orgSlug}</p>
          </div>
          <div className="col-span-2">
            <span className="text-gray-500">Organization ID</span>
            <p className="font-mono text-xs text-gray-700 mt-1">{orgId}</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <h3 className="font-semibold text-gray-900">Event Ingestion</h3>
        <p className="text-sm text-gray-500">
          Send events to your analytics platform using the API.
        </p>
        <div className="bg-gray-900 rounded-lg p-4">
          <pre className="text-sm text-green-400 whitespace-pre-wrap">{`curl -X POST http://localhost:8000/api/v1/events \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -d '{
    "event": "page_view",
    "distinct_id": "user-123",
    "properties": {
      "page": "/home",
      "referrer": "google"
    }
  }'`}</pre>
        </div>
        <div className="bg-gray-900 rounded-lg p-4">
          <p className="text-xs text-gray-400 mb-2">Batch ingestion (up to 1000 events):</p>
          <pre className="text-sm text-green-400 whitespace-pre-wrap">{`curl -X POST http://localhost:8000/api/v1/events/batch \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -d '{
    "events": [
      {"event": "signup", "distinct_id": "user-1"},
      {"event": "purchase", "distinct_id": "user-2", "properties": {"amount": 99.99}}
    ]
  }'`}</pre>
        </div>
      </div>

      {/* Developer Tools section */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Developer Tools</h3>
          <label className="flex items-center gap-2 cursor-pointer">
            <span className="text-xs text-gray-500">Developer mode</span>
            <div
              className={`relative w-9 h-5 rounded-full transition-colors ${
                devMode ? "bg-indigo-600" : "bg-gray-300"
              }`}
              onClick={() => setDevMode(!devMode)}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                  devMode ? "translate-x-4" : "translate-x-0.5"
                }`}
              />
            </div>
          </label>
        </div>

        {devMode && (
          <div className="space-y-4 pt-2">
            <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
              <p className="text-sm text-amber-800">
                Seed 1,000 randomized events across 7 event types (page_view, signup,
                login, button_click, purchase, feature_used, error) spread over the
                last 30 days with realistic property distributions.
              </p>
            </div>

            <button
              onClick={handleSeed}
              disabled={seeding}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {seeding ? "Seeding..." : "Seed Demo Data"}
            </button>

            {seedError && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">
                {seedError}
              </div>
            )}

            {seedResult && (
              <div className="bg-green-50 border border-green-200 rounded-md p-4 space-y-3">
                <p className="text-sm font-medium text-green-800">
                  Successfully seeded {seedResult.inserted.toLocaleString()} events!
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {Object.entries(seedResult.distribution)
                    .sort(([, a], [, b]) => b - a)
                    .map(([name, count]) => (
                      <div
                        key={name}
                        className="bg-white rounded-md px-3 py-2 border border-green-100"
                      >
                        <p className="text-xs text-gray-500">{name}</p>
                        <p className="text-sm font-semibold text-gray-900">{count}</p>
                      </div>
                    ))}
                </div>
                <p className="text-xs text-green-600">
                  Head to the Dashboard to query your new data.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
