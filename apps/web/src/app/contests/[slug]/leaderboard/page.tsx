"use client";
import { useParams } from "next/navigation";
import { useEffect } from "react";
import { EmptyState, ErrorState, PageHeader, Skeleton } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import type { Scoreboard } from "@/lib/types";

export default function ScoreboardPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data, error, loading, reload } = useApi<Scoreboard>(`/contests/${slug}/scoreboard`);
  const live = data && (data.phase === "running" || data.phase === "frozen");
  useEffect(() => { if (!live) return; const t = setInterval(reload, 5000); return () => clearInterval(t); }, [live, reload]);
  if (loading && !data) return <Skeleton rows={6} />;
  if (error || !data) return <ErrorState error={error!} retry={reload} />;
  const labels = data.rows[0]?.cells.map((c) => c.label) ?? [];
  return (
    <>
      <PageHeader title="Scoreboard" subtitle={data.frozen ? "Frozen: recent submissions are hidden until the contest ends." : live ? "Updates every few seconds." : data.full_view ? "Staff view." : undefined} />
      {data.rows.length === 0 ? <EmptyState title="No participants yet" /> : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-line text-left text-xs uppercase text-muted"><tr><th className="px-4 py-3">#</th><th>Handle</th><th className="text-right">Score</th><th className="text-right">Penalty</th>{labels.map((l) => <th key={l} className="px-3 text-center">{l}</th>)}</tr></thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.handle} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 tabular-nums">{r.rank}</td><td className="font-medium">{r.handle}</td>
                  <td className="text-right tabular-nums">{r.score}</td><td className="text-right tabular-nums text-muted">{r.penalty}</td>
                  {r.cells.map((c) => <td key={c.label} className={`px-3 text-center text-xs ${c.solved ? "text-ok" : c.wrong_attempts ? "text-bad" : "text-muted"}`}>{c.solved ? `+${c.wrong_attempts || ""} (${c.minutes}m)` : c.wrong_attempts ? `−${c.wrong_attempts}` : "·"}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
