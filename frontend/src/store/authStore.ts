import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User } from '@/types/travel';
import { api } from '@/services/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  logout: () => void;
  initAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      
      setToken: (token) => {
        set({ token });
        if (token) {
          localStorage.setItem('token', token);
        } else {
          localStorage.removeItem('token');
        }
      },
      
      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
        localStorage.removeItem('token');
        api.logout();
      },
      
      initAuth: async () => {
        const token = localStorage.getItem('token');
        if (token) {
          try {
            const user = await api.getMe();
            set({ user, token, isAuthenticated: true });
          } catch {
            set({ user: null, token: null, isAuthenticated: false });
            localStorage.removeItem('token');
          }
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated }),
    }
  )
);