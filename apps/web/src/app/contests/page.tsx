"use client";
import Link from "next/link";
import { Countdown, EmptyState, ErrorState, PageHeader, Skeleton } from "@/components/ui";
import { fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Contest } from "@/lib/types";

const PHASE: Record<string, string> = { scheduled: "Upcoming", running: "Live", frozen: "Live (frozen)", ended: "Finished" };

export default function ContestsPage() {
  const { data, error, loading, reload } = useApi<Contest[]>("/contests");
  return (
    <>
      <PageHeader title="Contests" subtitle="Timed rounds with live scoreboards. Server time is authoritative." />
      {loading ? <Skeleton rows={3} /> : error ? <ErrorState error={error} retry={reload} /> : !data?.length ? <EmptyState title="No contests yet" /> : (
        <ul className="space-y-3">
          {data.map((c) => (
            <li key={c.id}>
              <Link href={`/contests/${c.slug}`} className="card flex flex-wrap items-center justify-between gap-3 p-4 hover:bg-raised">
                <div>
                  <p className="font-medium">{c.title}</p>
                  <p className="text-xs text-muted">{fmtDate(c.start_at)} → {fmtDate(c.end_at)} · {c.participants} registered{c.is_rated && " · rated"}</p>
                </div>
                <div className="text-right text-sm">
                  <span className={c.phase === "running" || c.phase === "frozen" ? "text-ok" : "text-muted"}>{PHASE[c.phase] ?? c.phase}</span>
                  {c.phase === "scheduled" && <p className="text-xs text-muted">in <Countdown to={c.start_at} label="Time until start" /></p>}
                  {c.registered && <p className="text-xs text-cyan">Registered</p>}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
