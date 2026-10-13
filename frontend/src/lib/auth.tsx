"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, tokens } from "./api";
import type { User } from "./types";

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (u: User) => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!tokens.get()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await api.me());
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const onChange = () => {
      if (!tokens.get()) setUser(null);
    };
    window.addEventListener("nomadiq:auth", onChange);
    return () => window.removeEventListener("nomadiq:auth", onChange);
  }, [load]);

  const login = async (email: string, password: string) => {
    const res = await api.login({ email, password });
    tokens.set(res.tokens);
    setUser(res.user);
  };
  const register = async (name: string, email: string, password: string) => {
    const res = await api.register({ name, email, password });
    tokens.set(res.tokens);
    setUser(res.user);
  };
  const logout = async () => {
    const t = tokens.get();
    if (t) await api.logout(t.refresh_token).catch(() => undefined);
    tokens.set(null);
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, login, register, logout, setUser }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

/** Redirects to /login?next=… when signed out. Returns the user once known. */
export function useRequireUser(): User | null {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (!loading && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [loading, user, router, pathname]);
  return user;
}
