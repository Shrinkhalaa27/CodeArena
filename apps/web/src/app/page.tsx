"use client";
import Link from "next/link";
import { Countdown, DifficultyBadge, EmptyState, Skeleton, Stat } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import type { Contest, LeaderboardRow, ProblemPage } from "@/lib/types";

export default function Landing() {
  const problems = useApi<ProblemPage>("/problems?page_size=4&sort=difficulty");
  const contests = useApi<Contest[]>("/contests");
  const board = useApi<LeaderboardRow[]>("/leaderboard?limit=100");
  const upcoming = (contests.data ?? []).filter((c) => c.phase === "scheduled" || c.phase === "running" || c.phase === "frozen");
  return (
    <div className="space-y-12">
      <section className="py-8">
        <p className="font-mono text-sm text-cyan">Compete. Code. Conquer.</p>
        <h1 className="mt-3 max-w-2xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">Sharpen your algorithms. Climb the ranks.</h1>
        <p className="mt-4 max-w-xl text-muted">Solve problems in a browser editor, get judged against hidden tests in an isolated sandbox, and compete in timed contests with live scoreboards.</p>
        <div className="mt-6 flex gap-3">
          <Link href="/problems" className="btn btn-primary">Start solving</Link>
          <Link href="/contests" className="btn btn-ghost">View contests</Link>
        </div>
      </section>

      <section aria-label="Platform stats" className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Stat label="Problems" value={problems.data?.total ?? "–"} />
        <Stat label="Contests" value={contests.data?.length ?? "–"} />
        <Stat label="Ranked coders" value={board.data?.length ?? "–"} />
      </section>

      <div className="grid gap-8 lg:grid-cols-2">
        <section>
          <div className="mb-3 flex items-center justify-between"><h2 className="font-semibold">Featured problems</h2><Link className="text-sm text-cyan" href="/problems">All problems →</Link></div>
          {problems.loading ? <Skeleton rows={4} /> : !problems.data?.items.length ? <EmptyState title="No problems yet" hint="Run the seed command to add sample problems." /> : (
            <ul className="card divide-y divide-line">
              {problems.data.items.map((p) => (
                <li key={p.id}><Link href={`/problems/${p.slug}`} className="flex items-center justify-between px-4 py-3 hover:bg-raised"><span>{p.title}</span><DifficultyBadge level={p.difficulty} /></Link></li>
              ))}
            </ul>
          )}
        </section>
        <section>
          <div className="mb-3 flex items-center justify-between"><h2 className="font-semibold">Upcoming contests</h2><Link className="text-sm text-cyan" href="/contests">All contests →</Link></div>
          {contests.loading ? <Skeleton rows={2} /> : upcoming.length === 0 ? <EmptyState title="No upcoming contests" /> : (
            <ul className="card divide-y divide-line">
              {upcoming.slice(0, 3).map((c) => (
                <li key={c.id}><Link href={`/contests/${c.slug}`} className="flex items-center justify-between px-4 py-3 hover:bg-raised">
                  <span>{c.title}</span>
                  <span className="text-xs text-muted">{c.phase === "scheduled" ? <>starts in <Countdown to={c.start_at} label="Time until start" /></> : "live now"}</span>
                </Link></li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
