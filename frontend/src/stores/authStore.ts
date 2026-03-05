/**
 * Global auth state using Zustand.
 *
 * Zustand is a lightweight state management library (alternative to Redux).
 * It uses a single `create()` call that returns a React hook.
 *
 * Auth flow:
 * 1. App mounts → calls checkSession() → hits GET /auth/me
 * 2. If valid session cookie exists → sets org info, isLoading = false
 * 3. If no session → clears state, isLoading = false → App redirects to /login
 * 4. User logs in → login() → POST /auth/login → sets org info
 * 5. User logs out → logout() → POST /auth/logout → clears state
 *
 * isLoading starts as `true` so the App shows a loading spinner
 * while checkSession() runs. This prevents a flash of the login page
 * on page refresh when the user does have a valid session.
 */

import { create } from "zustand";
import { api } from "../api/client";

interface AuthState {
  orgId: string | null;
  orgName: string | null;
  orgSlug: string | null;
  isLoading: boolean;      // true until checkSession completes
  login: (apiKey: string) => Promise<void>;
  devLogin: (orgId: string) => Promise<void>;  // Dev mode: login by org ID
  logout: () => Promise<void>;
  checkSession: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  orgId: null,
  orgName: null,
  orgSlug: null,
  isLoading: true,  // Start loading until session check completes

  login: async (apiKey: string) => {
    const res = await api.login(apiKey);
    // Backend sets HttpOnly cookie; we just need to store the org info
    set({ orgId: res.org_id, orgName: res.org_name });
  },

  // Dev mode: login by org ID without needing the API key
  devLogin: async (orgId: string) => {
    const res = await api.devLogin(orgId);
    set({ orgId: res.org_id, orgName: res.org_name });
  },

  logout: async () => {
    await api.logout();  // Backend deletes the session cookie
    set({ orgId: null, orgName: null, orgSlug: null });
  },

  /**
   * Called on app mount (App.tsx useEffect).
   * Tries GET /auth/me with the existing session cookie.
   * If it succeeds → user is authenticated.
   * If it fails (401) → user needs to log in.
   * Either way, isLoading becomes false so the UI can render.
   */
  checkSession: async () => {
    try {
      const res = await api.getMe();
      set({ orgId: res.org_id, orgName: res.org_name, orgSlug: res.org_slug, isLoading: false });
    } catch {
      // 401 or network error → not authenticated
      set({ orgId: null, orgName: null, orgSlug: null, isLoading: false });
    }
  },
}));
