import { create } from "zustand";
import { api } from "../api/client";

interface AuthState {
  orgId: string | null;
  orgName: string | null;
  orgSlug: string | null;
  isLoading: boolean;
  login: (apiKey: string) => Promise<void>;
  logout: () => Promise<void>;
  checkSession: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  orgId: null,
  orgName: null,
  orgSlug: null,
  isLoading: true,

  login: async (apiKey: string) => {
    const res = await api.login(apiKey);
    set({ orgId: res.org_id, orgName: res.org_name });
  },

  logout: async () => {
    await api.logout();
    set({ orgId: null, orgName: null, orgSlug: null });
  },

  checkSession: async () => {
    try {
      const res = await api.getMe();
      set({ orgId: res.org_id, orgName: res.org_name, orgSlug: res.org_slug, isLoading: false });
    } catch {
      set({ orgId: null, orgName: null, orgSlug: null, isLoading: false });
    }
  },
}));
