import { useAuthStore } from "../stores/authStore";

export default function SettingsPage() {
  const { orgId, orgName, orgSlug } = useAuthStore();

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
    </div>
  );
}
