"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { authApi } from "@/lib/api";
import { useUser } from "@/lib/hooks";

const LINKS = [["/problems", "Problems"], ["/contests", "Contests"], ["/leaderboard", "Leaderboard"]] as const;

export function BrandMark() {
  return (
    <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="8" fill="rgb(var(--raised))" />
      <path d="M12 11l-5 5 5 5M20 11l5 5-5 5" fill="none" stroke="rgb(var(--violet))" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M17.5 9l-3 14" stroke="rgb(var(--cyan))" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  );
}

export function Nav() {
  const path = usePathname();
  const router = useRouter();
  const { user } = useUser();
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  useEffect(() => {
    let saved: string | null = null;
    try { saved = localStorage.getItem("codearena.theme"); } catch { /* ignore */ }
    const t = saved === "light" ? "light" : "dark";
    setTheme(t); document.documentElement.dataset.theme = t;
  }, []);
  const toggle = () => {
    const t = theme === "dark" ? "light" : "dark";
    setTheme(t); document.documentElement.dataset.theme = t;
    try { localStorage.setItem("codearena.theme", t); } catch { /* ignore */ }
  };
  const staff = user && ["admin", "contest_admin", "setter"].includes(user.role);
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-bg/90 backdrop-blur">
      <nav aria-label="Main" className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold"><BrandMark /> CodeArena</Link>
        <ul className="hidden items-center gap-1 sm:flex">
          {LINKS.map(([href, label]) => (
            <li key={href}><Link href={href} aria-current={path.startsWith(href) ? "page" : undefined}
              className={`rounded px-3 py-1.5 text-sm ${path.startsWith(href) ? "bg-raised text-ink" : "text-muted hover:text-ink"}`}>{label}</Link></li>
          ))}
          {staff && <li><Link href="/admin" className="rounded px-3 py-1.5 text-sm text-muted hover:text-ink">Admin</Link></li>}
        </ul>
        <div className="ml-auto flex items-center gap-2">
          <button className="btn btn-ghost !px-2.5" onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>{theme === "dark" ? "☀" : "☾"}</button>
          {user ? (
            <>
              <Link className="btn btn-ghost" href="/dashboard">{user.handle}</Link>
              <button className="btn btn-ghost" onClick={async () => { await authApi.logout(); router.push("/"); }}>Sign out</button>
            </>
          ) : (
            <>
              <Link className="btn btn-ghost" href="/login">Sign in</Link>
              <Link className="btn btn-primary" href="/register">Sign up</Link>
            </>
          )}
        </div>
      </nav>
      <ul className="flex gap-1 overflow-x-auto px-4 pb-2 sm:hidden">
        {LINKS.map(([href, label]) => <li key={href}><Link href={href} className="rounded bg-raised px-3 py-1 text-xs">{label}</Link></li>)}
      </ul>
    </header>
  );
}
