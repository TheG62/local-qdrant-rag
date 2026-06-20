import { create } from 'zustand';
import { api, setToken } from './api';
import type { User } from './types';

interface AuthState {
  user: User | null;
  loading: boolean;
  init: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  init: async () => {
    try {
      const { user } = await api.me();
      set({ user, loading: false });
    } catch {
      setToken(null);
      set({ user: null, loading: false });
    }
  },
  login: async (email, password) => {
    const { token, user } = await api.login(email, password);
    setToken(token);
    set({ user });
  },
  register: async (name, email, password) => {
    const { token, user } = await api.register(name, email, password);
    setToken(token);
    set({ user });
  },
  logout: () => {
    setToken(null);
    set({ user: null });
  },
}));
