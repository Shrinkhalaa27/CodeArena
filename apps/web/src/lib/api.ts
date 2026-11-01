const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const KEY = "codearena.tokens";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public requestId?: string) {
    super(message);
  }
}

interface Tokens { access_token: string; refresh_token: string }

export function getTokens(): Tokens | null {
  try { return JSON.parse(localStorage.getItem(KEY) ?? "null"); } catch { return null; }
}
export function setTokens(t: Tokens | null) {
  try { t ? localStorage.setItem(KEY, JSON.stringify(t)) : localStorage.removeItem(KEY); } catch { /* storage unavailable */ }
  window.dispatchEvent(new Event("codearena:auth"));
}

let refreshing: Promise<boolean> | null = null;
async function refresh(): Promise<boolean> {
  const t = getTokens();
  if (!t) return false;
  refreshing ??= fetch(`${BASE}/api/v1/auth/refresh`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: t.refresh_token }),
  }).then(async (r) => { if (!r.ok) { setTokens(null); return false; } setTokens(await r.json()); return true; })
    .catch(() => false).finally(() => { refreshing = null; });
  return refreshing;
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown; retry?: boolean } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const tokens = getTokens();
  if (tokens) headers.set("Authorization", `Bearer ${tokens.access_token}`);
  if (init.json !== undefined) { headers.set("Content-Type", "application/json"); init.body = JSON.stringify(init.json); }
  let res: Response;
  try { res = await fetch(`${BASE}/api/v1${path}`, { ...init, headers }); }
  catch { throw new ApiError(0, "NETWORK", "Cannot reach the server. Is the API running?"); }
  if (res.status === 401 && tokens && init.retry !== false && (await refresh())) return api<T>(path, { ...init, retry: false });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const e = body?.error;
    throw new ApiError(res.status, e?.code ?? "ERROR", e?.message ?? "Request failed", e?.request_id);
  }
  return body as T;
}

export const authApi = {
  async login(email: string, password: string) { setTokens(await api("/auth/login", { method: "POST", json: { email, password } })); },
  async register(email: string, handle: string, password: string) { setTokens(await api("/auth/register", { method: "POST", json: { email, handle, password } })); },
  async logout() {
    const t = getTokens();
    if (t) await api("/auth/logout", { method: "POST", json: { refresh_token: t.refresh_token } }).catch(() => undefined);
    setTokens(null);
  },
};
