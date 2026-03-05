/**
 * Login page with two modes: login and org creation.
 *
 * Login flow:
 * 1. User enters their API key (e.g., ea_live_abc123...)
 * 2. POST /auth/login validates the key and sets a session cookie
 * 3. On success, navigate to "/" (dashboard)
 *
 * Org creation flow:
 * 1. User clicks "Create new organization"
 * 2. Enters org name + slug
 * 3. POST /api/v1/orgs creates the org and returns a raw API key
 * 4. The key is displayed in a green box (shown only once - it's hashed in the DB)
 * 5. The key is also auto-filled into the login input for convenience
 *
 * Slug input: auto-lowercases and replaces non-alphanumeric chars with hyphens
 * for URL-friendly organization identifiers.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuthStore } from "../stores/authStore";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "setup">("login");
  const [apiKey, setApiKey] = useState("");
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [error, setError] = useState("");
  const [createdKey, setCreatedKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      await login(apiKey);
      navigate("/");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const res = await api.createOrg(orgName, orgSlug);
      setCreatedKey(res.api_key);
      setApiKey(res.api_key);
      setMode("login");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-6 p-8 bg-white rounded-lg shadow-md">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900">Event Analytics</h2>
          <p className="text-sm text-gray-500 mt-1">
            Lightweight open-source analytics
          </p>
        </div>

        {createdKey && (
          <div className="bg-green-50 border border-green-200 rounded-md p-4">
            <p className="text-sm font-medium text-green-800">
              Organization created! Save your API key:
            </p>
            <code className="block mt-2 text-xs bg-green-100 p-2 rounded break-all">
              {createdKey}
            </code>
            <p className="text-xs text-green-600 mt-2">
              This key won't be shown again. Use it for event ingestion and login.
            </p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {mode === "login" ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Key
              </label>
              <input
                type="text"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="ea_live_..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                required
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2 px-4 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {isLoading ? "Logging in..." : "Login"}
            </button>
            <button
              type="button"
              onClick={() => setMode("setup")}
              className="w-full py-2 px-4 text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              Create new organization
            </button>
          </form>
        ) : (
          <form onSubmit={handleSetup} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Organization Name
              </label>
              <input
                type="text"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="My Company"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Slug
              </label>
              <input
                type="text"
                value={orgSlug}
                onChange={(e) =>
                  setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-"))
                }
                placeholder="my-company"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                required
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2 px-4 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {isLoading ? "Creating..." : "Create Organization"}
            </button>
            <button
              type="button"
              onClick={() => setMode("login")}
              className="w-full py-2 px-4 text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              Back to login
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
