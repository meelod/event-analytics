/**
 * Centralized API client for all backend communication.
 *
 * Design: One thin wrapper around fetch, then each endpoint is a one-liner.
 * This keeps API calls consistent and makes it easy to add new endpoints.
 *
 * Key details:
 * - BASE = "/api/v1" works because Vite's dev proxy (vite.config.ts) forwards
 *   all /api/* requests to localhost:8000. In production you'd point this at
 *   the real backend URL.
 * - credentials: "include" ensures the session cookie is sent with every request.
 *   Without this, the browser won't attach HttpOnly cookies to fetch() calls.
 * - Error handling: extracts the `detail` field from FastAPI's error responses
 *   (FastAPI's HTTPException returns {"detail": "message"}).
 */

const BASE = "/api/v1";

/**
 * Generic fetch wrapper. All API methods go through this.
 *
 * - Always sends JSON content type
 * - Always includes credentials (session cookie)
 * - On error, tries to parse FastAPI's error JSON for a readable message
 * - Returns parsed JSON typed as T
 */
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    // FastAPI returns {"detail": "error message"} for HTTPException
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

/**
 * API methods - each maps to one backend endpoint.
 *
 * Auth patterns:
 * - createOrg: no auth needed (creates new org + API key)
 * - login/logout: no auth needed (login validates key, creates session)
 * - getMe: uses session cookie (set by login)
 * - ingestEvent: uses API key header (same as curl/SDK ingestion)
 * - query, visualizations: use session cookie (dashboard features)
 */
export const api = {
  // POST /api/v1/orgs - Create org, returns raw API key (shown once)
  createOrg: (name: string, slug: string) =>
    request<any>("/orgs", {
      method: "POST",
      body: JSON.stringify({ name, slug }),
    }),

  // POST /api/v1/auth/login - Exchange API key for session cookie
  login: (api_key: string) =>
    request<{ status: string; org_id: string; org_name: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ api_key }),
    }),

  // POST /api/v1/auth/logout - Clear session cookie
  logout: () => request<any>("/auth/logout", { method: "POST" }),

  // GET /api/v1/auth/me - Check if session is valid, get org info
  getMe: () =>
    request<{ org_id: string; org_name: string; org_slug: string }>("/auth/me"),

  // POST /api/v1/events - Ingest single event (uses API key, not session)
  ingestEvent: (event: any, apiKey: string) =>
    request<any>("/events", {
      method: "POST",
      body: JSON.stringify(event),
      headers: { "X-API-Key": apiKey },
    }),

  // POST /api/v1/query - Send NL question, get SQL + data + chart config
  query: (question: string) =>
    request<any>("/query", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  // GET /api/v1/visualizations - List all saved visualizations for this org
  listVisualizations: () => request<any[]>("/visualizations"),

  // POST /api/v1/visualizations - Save query result + chart config for later
  saveVisualization: (data: any) =>
    request<any>("/visualizations", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // GET /api/v1/visualizations/:id - Load a specific saved visualization
  getVisualization: (id: string) => request<any>(`/visualizations/${id}`),

  // DELETE /api/v1/visualizations/:id - Remove a saved visualization
  deleteVisualization: (id: string) =>
    request<any>(`/visualizations/${id}`, { method: "DELETE" }),

  // POST /api/v1/events/seed - Seed randomized demo data (developer mode)
  seedDemoData: (count: number = 1000, daysBack: number = 30) =>
    request<{ status: string; inserted: number; distribution: Record<string, number> }>(
      "/events/seed",
      {
        method: "POST",
        body: JSON.stringify({ count, days_back: daysBack }),
      }
    ),

  // GET /api/v1/auth/dev/orgs - List all orgs (dev mode, no auth needed)
  listOrgs: () =>
    request<{ id: string; name: string; slug: string }[]>("/auth/dev/orgs"),

  // POST /api/v1/auth/dev/login - Login by org ID without API key (dev mode)
  devLogin: (orgId: string) =>
    request<{ status: string; org_id: string; org_name: string }>("/auth/dev/login", {
      method: "POST",
      body: JSON.stringify({ org_id: orgId }),
    }),
};
