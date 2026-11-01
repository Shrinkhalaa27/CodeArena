"use client";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError, getTokens } from "./api";
import type { User } from "./types";

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(path !== null);
  const load = useCallback(() => {
    if (path === null) return;
    setLoading(true);
    api<T>(path).then((d) => { setData(d); setError(null); })
      .catch((e: ApiError) => setError(e)).finally(() => setLoading(false));
  }, [path]);
  useEffect(load, [load]);
  return { data, error, loading, reload: load };
}

export function useUser() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const sync = () => {
      if (!getTokens()) { setUser(null); setReady(true); return; }
      api<User>("/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setReady(true));
    };
    sync();
    window.addEventListener("codearena:auth", sync);
    return () => window.removeEventListener("codearena:auth", sync);
  }, []);
  return { user, ready };
}
