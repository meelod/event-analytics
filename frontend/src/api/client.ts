const BASE = "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  createOrg: (name: string, slug: string) =>
    request<any>("/orgs", {
      method: "POST",
      body: JSON.stringify({ name, slug }),
    }),

  login: (api_key: string) =>
    request<{ status: string; org_id: string; org_name: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ api_key }),
    }),

  logout: () => request<any>("/auth/logout", { method: "POST" }),

  getMe: () =>
    request<{ org_id: string; org_name: string; org_slug: string }>("/auth/me"),

  ingestEvent: (event: any, apiKey: string) =>
    request<any>("/events", {
      method: "POST",
      body: JSON.stringify(event),
      headers: { "X-API-Key": apiKey },
    }),

  query: (question: string) =>
    request<any>("/query", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  listVisualizations: () => request<any[]>("/visualizations"),

  saveVisualization: (data: any) =>
    request<any>("/visualizations", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getVisualization: (id: string) => request<any>(`/visualizations/${id}`),

  deleteVisualization: (id: string) =>
    request<any>(`/visualizations/${id}`, { method: "DELETE" }),
};
