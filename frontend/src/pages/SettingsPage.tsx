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

// Property config: options = clickable tags, no options = text input.
// Values match seeding.py exactly so the data looks consistent.
interface PropConfig {
  default: string;
  options?: string[];
}

const EVENT_TEMPLATES: Record<string, Record<string, PropConfig>> = {
  page_view: {
    page:     { default: "/pricing", options: ["/home", "/pricing", "/features", "/blog", "/about", "/docs", "/signup", "/login"] },
    referrer: { default: "google",   options: ["google", "twitter", "direct", "github", "hackernews"] },
    browser:  { default: "Chrome",   options: ["Chrome", "Firefox", "Safari", "Edge"] },
  },
  signup: {
    plan:   { default: "pro",     options: ["free", "pro", "enterprise"] },
    source: { default: "organic", options: ["organic", "referral", "ad", "blog"] },
  },
  login: {
    method: { default: "google", options: ["email", "google", "github"] },
  },
  button_click: {
    button_id: { default: "cta_hero", options: ["cta_hero", "nav_signup", "pricing_pro", "pricing_enterprise", "docs_link"] },
    page:      { default: "/home",    options: ["/home", "/pricing", "/features"] },
  },
  purchase: {
    amount:   { default: "99.99" },
    plan:     { default: "enterprise", options: ["pro", "enterprise"] },
    currency: { default: "USD",        options: ["USD"] },
  },
  feature_used: {
    feature: { default: "dashboard", options: ["dashboard", "export", "api", "webhook", "integration", "report"] },
  },
  error: {
    error_code: { default: "500", options: ["400", "401", "403", "404", "500"] },
    page:       { default: "/api/query", options: ["/api/events", "/api/query", "/dashboard"] },
  },
};

export default function SettingsPage() {
  const { orgId, orgName, orgSlug } = useAuthStore();

  // Developer mode state (local to this page, not persisted)
  const [devMode, setDevMode] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<SeedResult | null>(null);
  const [seedError, setSeedError] = useState("");

  // Manual event form state
  const [eventName, setEventName] = useState("");
  const [eventProps, setEventProps] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);
  const [sendSuccess, setSendSuccess] = useState("");
  const [sendError, setSendError] = useState("");

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

  const selectEventType = (tag: string) => {
    setEventName(tag);
    // Pull default values from the template configs
    const template = EVENT_TEMPLATES[tag] || {};
    const defaults: Record<string, string> = {};
    for (const [key, config] of Object.entries(template)) {
      defaults[key] = config.default;
    }
    setEventProps(defaults);
    setSendSuccess("");
    setSendError("");
  };

  const handleSendEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    setSending(true);
    setSendError("");
    setSendSuccess("");
    try {
      // Parse numbers so they're stored as numbers in JSON (e.g., amount: 99.99)
      const props: Record<string, any> = {};
      for (const [key, value] of Object.entries(eventProps)) {
        const trimmed = value.trim();
        if (!trimmed) continue;
        if (!isNaN(Number(trimmed))) props[key] = Number(trimmed);
        else props[key] = trimmed;
      }
      const res = await api.sendEvent(eventName, "dashboard-user", props);
      setSendSuccess(`Sent "${eventName}" with ${Object.keys(props).length} properties`);
    } catch (err: any) {
      setSendError(err.message);
    } finally {
      setSending(false);
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

            {/* Manual event creation form */}
            <div className="border-t border-gray-200 pt-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">
                Send Event
              </h4>

              <form onSubmit={handleSendEvent} className="space-y-3">
                {/* Event type tags — click to select + auto-fill properties */}
                <div className="flex flex-wrap gap-1.5">
                  {Object.keys(EVENT_TEMPLATES).map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => selectEventType(tag)}
                      className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                        eventName === tag
                          ? "bg-indigo-100 border-indigo-300 text-indigo-700 font-medium"
                          : "bg-gray-50 border-gray-200 text-gray-600 hover:border-indigo-300 hover:text-indigo-600"
                      }`}
                    >
                      {tag}
                    </button>
                  ))}
                </div>

                {/* Auto-filled properties — tags or text input per field */}
                {eventName && EVENT_TEMPLATES[eventName] && (
                  <div className="bg-gray-50 rounded-md p-3 space-y-3">
                    {Object.entries(EVENT_TEMPLATES[eventName]).map(([key, config]) => (
                      <div key={key}>
                        <p className="text-xs font-medium text-gray-500 mb-1">{key}</p>
                        {config.options ? (
                          <div className="flex flex-wrap gap-1.5">
                            {config.options.map((opt) => (
                              <button
                                key={opt}
                                type="button"
                                onClick={() => setEventProps({ ...eventProps, [key]: opt })}
                                className={`px-2 py-0.5 text-xs rounded-full border transition-colors ${
                                  eventProps[key] === opt
                                    ? "bg-indigo-100 border-indigo-300 text-indigo-700 font-medium"
                                    : "bg-white border-gray-200 text-gray-600 hover:border-indigo-300"
                                }`}
                              >
                                {opt}
                              </button>
                            ))}
                          </div>
                        ) : (
                          <input
                            type="text"
                            value={eventProps[key] || ""}
                            onChange={(e) =>
                              setEventProps({ ...eventProps, [key]: e.target.value })
                            }
                            className="w-40 px-2 py-1 border border-gray-300 rounded text-sm focus:ring-indigo-500 focus:border-indigo-500"
                          />
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Send button + feedback */}
                <div className="flex items-center gap-3">
                  <button
                    type="submit"
                    disabled={sending || !eventName.trim()}
                    className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    {sending ? "Sending..." : "Send Event"}
                  </button>
                  {sendSuccess && (
                    <span className="text-sm text-green-600">{sendSuccess}</span>
                  )}
                  {sendError && (
                    <span className="text-sm text-red-600">{sendError}</span>
                  )}
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
