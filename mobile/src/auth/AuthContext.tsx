import { createContext, useContext, useEffect, useState } from "react";
import { api, tokens } from "@/api/client";
import type { User } from "@/api/types";

type AuthState = {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (u: User) => void;
};

const AuthContext = createContext<AuthState | null>(null);

/** Restore the signed-in user from the keychain on app start (null when signed out or the session expired). */
async function restoreSession(): Promise<User | null> {
  try {
    return (await tokens.get()) ? await api.me() : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    restoreSession().then((u) => {
      if (!alive) return;
      setUser(u);
      setReady(true);
    });
    const unsubscribe = tokens.subscribe((signedIn) => {
      if (!signedIn) setUser(null);
    });
    return () => {
      alive = false;
      unsubscribe();
    };
  }, []);

  const value: AuthState = {
    user,
    ready,
    setUser,
    login: async (email, password) => {
      const res = await api.login({ email, password });
      await tokens.set(res.tokens);
      setUser(res.user);
    },
    register: async (name, email, password) => {
      const res = await api.register({ name, email, password });
      await tokens.set(res.tokens);
      setUser(res.user);
    },
    logout: async () => {
      const t = await tokens.get();
      if (t) await api.logout(t.refresh_token).catch(() => undefined);
      await tokens.set(null);
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
