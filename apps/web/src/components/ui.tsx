"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { VERDICT_LABEL, isFinal, timeUntil } from "@/lib/format";
import type { ApiError } from "@/lib/api";

const DIFF: Record<string, string> = { easy: "text-ok", medium: "text-warn", hard: "text-bad" };
export function DifficultyBadge({ level }: { level: string }) {
  return <span className={`text-xs font-medium capitalize ${DIFF[level] ?? ""}`}>{level}</span>;
}

export function VerdictBadge({ status }: { status: string }) {
  const tone = status === "ACCEPTED" ? "text-ok border-ok/40 bg-ok/10"
    : !isFinal(status) ? "text-cyan border-cyan/40 bg-cyan/10"
    : status === "INTERNAL_ERROR" ? "text-muted border-line bg-raised" : "text-bad border-bad/40 bg-bad/10";
  return (
    <span role="status" data-testid="verdict" data-verdict={status}
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-semibold ${tone}`}>
      {!isFinal(status) && <span aria-hidden className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan" />}
      {VERDICT_LABEL[status] ?? status}
    </span>
  );
}

export function Skeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading" className="space-y-2">
      {Array.from({ length: rows }, (_, i) => <div key={i} className="skeleton h-10 w-full" />)}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: ApiError; retry?: () => void }) {
  return (
    <div role="alert" className="card p-6 text-center">
      <p className="font-medium text-bad">{error.message}</p>
      {error.requestId && <p className="mt-1 font-mono text-xs text-muted">request {error.requestId}</p>}
      {retry && <button className="btn btn-ghost mt-4" onClick={retry}>Try again</button>}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="card p-10 text-center">
      <p className="font-medium">{title}</p>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </div>
  );
}

export function Countdown({ to, label }: { to: string; label: string }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  // Display only: the server clock is authoritative for every contest rule.
  return <span className="font-mono tabular-nums" aria-label={label}>{timeUntil(to, now)}</span>;
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="card p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

export function TextLink({ href, children }: { href: string; children: React.ReactNode }) {
  return <Link href={href} className="text-cyan hover:underline">{children}</Link>;
}

/** Tiny, safe inline formatter: **bold** and `code` only. Renders React nodes, never HTML. */
export function RichText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*\n]+\*\*|`[^`\n]+`)/g);
  return (
    <p className="whitespace-pre-wrap">
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**") && part.length > 4 ? (
          <strong key={i}>{part.slice(2, -2)}</strong>
        ) : part.startsWith("`") && part.endsWith("`") && part.length > 2 ? (
          <code key={i} className="rounded bg-raised px-1 font-mono text-xs">{part.slice(1, -1)}</code>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </p>
  );
}
