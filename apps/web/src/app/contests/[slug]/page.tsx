"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Countdown, DifficultyBadge, ErrorState, PageHeader, Skeleton } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useApi, useUser } from "@/lib/hooks";
import type { ContestDetail } from "@/lib/types";

export default function ContestPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data: c, error, loading, reload } = useApi<ContestDetail>(`/contests/${slug}`);
  const { user } = useUser();
  const [msg, setMsg] = useState<string | null>(null);
  if (loading) return <Skeleton rows={5} />;
  if (error || !c) return <ErrorState error={error!} retry={reload} />;

  const toggle = async () => {
    setMsg(null);
    try { await api(`/contests/${slug}/register`, { method: c.registered ? "DELETE" : "POST" }); reload(); }
    catch (e) { setMsg((e as ApiError).message); }
  };
  const open = c.phase === "running" || c.phase === "frozen";
  return (
    <>
      <PageHeader title={c.title} subtitle={`${fmtDate(c.start_at)} → ${fmtDate(c.end_at)} · ${c.penalty_minutes} min penalty per wrong attempt`}
        action={<Link className="btn btn-ghost" href={`/contests/${slug}/leaderboard`}>Scoreboard</Link>} />
      <div className="card mb-6 flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <p className="text-xs uppercase text-muted">{c.phase === "scheduled" ? "Starts in" : open ? "Ends in" : "Status"}</p>
          <p className="text-2xl font-semibold">{c.phase === "scheduled" ? <Countdown to={c.start_at} label="Time until start" /> : open ? <Countdown to={c.end_at} label="Time remaining" /> : "Finished"}</p>
        </div>
        {(c.phase === "scheduled" || open) && (
          user ? <button className={`btn ${c.registered ? "btn-ghost" : "btn-primary"}`} onClick={toggle} disabled={c.registered && c.phase !== "scheduled"}>{c.registered ? (c.phase === "scheduled" ? "Unregister" : "Registered") : "Register"}</button>
               : <Link className="btn btn-primary" href="/login">Sign in to register</Link>
        )}
      </div>
      {msg && <p role="alert" className="mb-4 text-sm text-bad">{msg}</p>}
      {c.description && <p className="mb-6 text-sm text-muted">{c.description}</p>}
      <h2 className="mb-3 font-semibold">Problems</h2>
      {c.problems.length === 0 ? <p className="card p-6 text-center text-sm text-muted">Problems are revealed when the contest starts.</p> : (
        <ul className="card divide-y divide-line">
          {c.problems.map((p) => (
            <li key={p.label}><Link href={`/contests/${slug}/problems/${p.slug}`} className="flex items-center gap-4 px-4 py-3 hover:bg-raised">
              <span className="w-6 font-mono font-semibold text-violet">{p.label}</span><span className="flex-1">{p.title}</span><DifficultyBadge level={p.difficulty} /><span className="w-12 text-right text-xs text-muted">{p.points} pt</span>
            </Link></li>
          ))}
        </ul>
      )}
    </>
  );
}
