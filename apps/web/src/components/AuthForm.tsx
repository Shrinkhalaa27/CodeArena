"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, authApi } from "@/lib/api";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [handle, setHandle] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null);
    try {
      if (mode === "login") await authApi.login(email, password); else await authApi.register(email, handle, password);
      router.push("/problems");
    } catch (err) { setError((err as ApiError).message); } finally { setBusy(false); }
  }
  return (
    <form onSubmit={submit} className="card mx-auto mt-8 max-w-sm space-y-4 p-6">
      <h1 className="text-xl font-semibold">{mode === "login" ? "Sign in" : "Create your account"}</h1>
      <div><label htmlFor="email" className="mb-1 block text-sm">Email</label><input id="email" type="email" required autoComplete="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
      {mode === "register" && <div><label htmlFor="handle" className="mb-1 block text-sm">Handle</label><input id="handle" required minLength={3} maxLength={24} pattern="[A-Za-z0-9_]+" className="input" value={handle} onChange={(e) => setHandle(e.target.value)} /><p className="mt-1 text-xs text-muted">3–24 letters, digits or underscores.</p></div>}
      <div><label htmlFor="password" className="mb-1 block text-sm">Password</label><input id="password" type="password" required minLength={8} autoComplete={mode === "login" ? "current-password" : "new-password"} className="input" value={password} onChange={(e) => setPassword(e.target.value)} /></div>
      {error && <p role="alert" className="text-sm text-bad">{error}</p>}
      <button className="btn btn-primary w-full" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Sign up"}</button>
      <p className="text-center text-sm text-muted">{mode === "login" ? <>New here? <Link className="text-cyan" href="/register">Create an account</Link></> : <>Have an account? <Link className="text-cyan" href="/login">Sign in</Link></>}</p>
    </form>
  );
}
