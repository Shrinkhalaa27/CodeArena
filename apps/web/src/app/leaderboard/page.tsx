"use client";
import Link from "next/link";
import { EmptyState, ErrorState, PageHeader, Skeleton } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import type { LeaderboardRow } from "@/lib/types";

export default function GlobalLeaderboard() {
  const { data, error, loading, reload } = useApi<LeaderboardRow[]>("/leaderboard?limit=100");
  return (
    <>
      <PageHeader title="Global leaderboard" subtitle="Ranked by contest rating. New accounts start at 1200 (provisional until 5 rated contests)." />
      {loading ? <Skeleton rows={8} /> : error ? <ErrorState error={error} retry={reload} /> : !data?.length ? <EmptyState title="Nobody ranked yet" /> : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-line text-left text-xs uppercase text-muted"><tr><th className="px-4 py-3">#</th><th>Handle</th><th className="text-right">Rating</th><th className="px-4 text-right">Solved</th></tr></thead>
            <tbody>{data.map((r) => (
              <tr key={r.handle} className="border-b border-line last:border-0 hover:bg-raised">
                <td className="px-4 py-3 tabular-nums">{r.rank}</td><td><Link className="font-medium hover:text-cyan" href={`/profile/${r.handle}`}>{r.handle}</Link></td>
                <td className="text-right tabular-nums">{r.rating}</td><td className="px-4 text-right tabular-nums text-muted">{r.solved}</td>
              </tr>))}</tbody>
          </table>
        </div>
      )}
    </>
  );
}
