import { create } from "zustand";

import { api } from "@/api/client";

export type Permissions = {
  manage_users: boolean;
  manage_groups: boolean;
  manage_cameras: boolean;
};

export type Me = {
  id: number;
  username: string;
  language: string;
  must_change_password: boolean;
  permissions: Permissions;
};

type AuthState = {
  me: Me | null;
  loading: boolean;
  refresh: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuth = create<AuthState>((set) => ({
  me: null,
  loading: true,
  refresh: async () => {
    try {
      const me = await api.get<Me>("/api/auth/me");
      set({ me, loading: false });
    } catch {
      set({ me: null, loading: false });
    }
  },
  login: async (username, password) => {
    await api.post("/api/auth/login", { username, password });
    const me = await api.get<Me>("/api/auth/me");
    set({ me });
  },
  logout: async () => {
    await api.post("/api/auth/logout");
    set({ me: null });
  },
}));
