/**
 * Login page with three modes: login, org creation, and developer quick-login.
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
 * Developer mode (gear icon):
 * - Since API keys are SHA-256 hashed, they can't be retrieved after creation
 * - The gear icon toggles a list of existing orgs
 * - Clicking an org logs you in directly via POST /auth/dev/login (no key needed)
 * - This is a local-only convenience — in production you'd remove these endpoints
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuthStore } from "../stores/authStore";

interface OrgItem {
  id: string;
  name: string;
  slug: string;
}

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "setup">("login");
  const [apiKey, setApiKey] = useState("");
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [error, setError] = useState("");
  const [createdKey, setCreatedKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Developer mode state
  const [devMode, setDevMode] = useState(false);
  const [orgs, setOrgs] = useState<OrgItem[]>([]);
  const [loadingOrgs, setLoadingOrgs] = useState(false);

  const login = useAuthStore((s) => s.login);
  const devLogin = useAuthStore((s) => s.devLogin);
  const navigate = useNavigate();

  // Fetch org list when dev mode is toggled on
  useEffect(() => {
    if (devMode) {
      setLoadingOrgs(true);
      api
        .listOrgs()
        .then(setOrgs)
        .catch(() => setOrgs([]))
        .finally(() => setLoadingOrgs(false));
    }
  }, [devMode]);

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

  const handleDevLogin = async (orgId: string) => {
    setError("");
    setIsLoading(true);
    try {
      await devLogin(orgId);
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
        <div className="text-center relative">
          <h2 className="text-2xl font-bold text-gray-900">Event Analytics</h2>
          <p className="text-sm text-gray-500 mt-1">
            Lightweight open-source analytics
          </p>
          {/* Gear icon toggle for developer mode */}
          <button
            onClick={() => setDevMode(!devMode)}
            className={`absolute top-0 right-0 p-1 rounded-md transition-colors ${
              devMode
                ? "text-indigo-600 bg-indigo-50"
                : "text-gray-300 hover:text-gray-500"
            }`}
            title="Developer mode"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                clipRule="evenodd"
              />
            </svg>
          </button>
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

        {/* Developer mode: show existing orgs for quick login */}
        {devMode && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-md p-4 space-y-3">
            <p className="text-xs font-medium text-indigo-700 uppercase tracking-wide">
              Developer Quick Login
            </p>
            {loadingOrgs ? (
              <p className="text-sm text-indigo-500">Loading organizations...</p>
            ) : orgs.length === 0 ? (
              <p className="text-sm text-indigo-500">
                No organizations yet. Create one below.
              </p>
            ) : (
              <div className="space-y-2">
                {orgs.map((org) => (
                  <button
                    key={org.id}
                    onClick={() => handleDevLogin(org.id)}
                    disabled={isLoading}
                    className="w-full flex items-center justify-between px-3 py-2 bg-white border border-indigo-100 rounded-md hover:border-indigo-300 hover:bg-indigo-50/50 transition-colors disabled:opacity-50 text-left"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {org.name}
                      </p>
                      <p className="text-xs text-gray-500">{org.slug}</p>
                    </div>
                    <span className="text-xs text-indigo-600 font-medium">
                      Login &rarr;
                    </span>
                  </button>
                ))}
              </div>
            )}
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
