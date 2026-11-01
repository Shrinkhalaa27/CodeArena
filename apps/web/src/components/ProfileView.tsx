"use client";
import { ErrorState, PageHeader, Skeleton, Stat } from "@/components/ui";
import { Bars, Heatmap, RatingChart } from "@/components/charts";
import { useApi } from "@/lib/hooks";
import type { Profile } from "@/lib/types";

export function ProfileView({ handle }: { handle: string }) {
  const { data: p, error, loading, reload } = useApi<Profile>(`/users/${encodeURIComponent(handle)}`);
  if (loading) return <Skeleton rows={6} />;
  if (error || !p) return <ErrorState error={error!} retry={reload} />;
  const solved = Object.values(p.solved_by_difficulty).reduce((a, b) => a + b, 0);
  const points = [{ rating: p.rating_history[0]?.old ?? p.rating, label: "Start" }, ...p.rating_history.map((h, i) => ({ rating: h.new, label: `Contest ${i + 1}${h.provisional ? " (provisional)" : ""}` }))];
  return (
    <>
      <PageHeader title={p.handle} subtitle={p.bio || `Joined ${new Date(p.joined).toLocaleDateString()}`} />
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Rating" value={p.rating} /><Stat label="Solved" value={solved} />
        <Stat label="Accepted" value={p.accepted_submissions} /><Stat label="Submissions" value={p.total_submissions} />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card p-5"><h2 className="mb-3 font-semibold">Rating history</h2><RatingChart points={points} /></section>
        <section className="card p-5"><h2 className="mb-3 font-semibold">Solved by difficulty</h2><Bars data={p.solved_by_difficulty} colors={{ easy: "bg-ok", medium: "bg-warn", hard: "bg-bad" }} /></section>
        <section className="card p-5 lg:col-span-2"><h2 className="mb-3 font-semibold">Activity</h2><Heatmap activity={p.activity} /></section>
        <section className="card p-5"><h2 className="mb-3 font-semibold">Languages</h2>{Object.keys(p.languages).length ? <Bars data={p.languages} /> : <p className="text-sm text-muted">No submissions yet.</p>}</section>
      </div>
    </>
  );
}
