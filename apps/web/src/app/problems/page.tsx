"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { DifficultyBadge, EmptyState, ErrorState, PageHeader, Skeleton } from "@/components/ui";
import { useApi, useUser } from "@/lib/hooks";
import type { ProblemPage } from "@/lib/types";

export default function ProblemsPage() {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [tag, setTag] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("difficulty");
  const [page, setPage] = useState(1);
  const { user } = useUser();
  const tags = useApi<string[]>("/problems/tags");
  useEffect(() => { const t = setTimeout(() => { setDebounced(q); setPage(1); }, 250); return () => clearTimeout(t); }, [q]);
  const qs = new URLSearchParams({ sort, page: String(page), page_size: "15" });
  if (debounced) qs.set("q", debounced);
  if (difficulty) qs.set("difficulty", difficulty);
  if (tag) qs.set("tag", tag);
  if (status && user) qs.set("status", status);
  const { data, error, loading, reload } = useApi<ProblemPage>(`/problems?${qs}`);
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const reset = (fn: (v: string) => void) => (e: React.ChangeEvent<HTMLSelectElement>) => { fn(e.target.value); setPage(1); };

  return (
    <>
      <PageHeader title="Problems" subtitle="Practice with hidden-test judging." />
      <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <input className="input lg:col-span-2" placeholder="Search by title…" aria-label="Search problems" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input" aria-label="Difficulty" value={difficulty} onChange={reset(setDifficulty)}><option value="">All difficulties</option><option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option></select>
        <select className="input" aria-label="Topic" value={tag} onChange={reset(setTag)}><option value="">All topics</option>{tags.data?.map((t) => <option key={t}>{t}</option>)}</select>
        <select className="input" aria-label="Sort" value={sort} onChange={reset(setSort)}><option value="difficulty">Sort: difficulty</option><option value="title">Sort: title</option><option value="newest">Sort: newest</option></select>
        {user && <select className="input" aria-label="Status" value={status} onChange={reset(setStatus)}><option value="">Any status</option><option value="solved">Solved</option><option value="attempted">Attempted</option><option value="unsolved">Unsolved</option></select>}
      </div>
      {loading && !data ? <Skeleton rows={8} /> : error ? <ErrorState error={error} retry={reload} /> : !data?.items.length ? <EmptyState title="No problems match your filters" hint="Try clearing a filter." /> : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-line text-left text-xs uppercase text-muted"><tr><th className="px-4 py-3">Status</th><th>Title</th><th>Difficulty</th><th className="hidden md:table-cell">Topics</th><th className="px-4 text-right">Acceptance</th></tr></thead>
            <tbody>
              {data.items.map((p) => (
                <tr key={p.id} className="border-b border-line last:border-0 hover:bg-raised">
                  <td className="px-4 py-3" aria-label={p.status ?? "not attempted"}>{p.status === "solved" ? <span className="text-ok">✔</span> : p.status === "attempted" ? <span className="text-warn">●</span> : <span className="text-muted">–</span>}</td>
                  <td><Link className="font-medium hover:text-cyan" href={`/problems/${p.slug}`}>{p.title}</Link></td>
                  <td><DifficultyBadge level={p.difficulty} /></td>
                  <td className="hidden md:table-cell"><div className="flex flex-wrap gap-1">{p.tags.map((t) => <span key={t} className="rounded bg-raised px-2 py-0.5 text-xs text-muted">{t}</span>)}</div></td>
                  <td className="px-4 text-right tabular-nums text-muted">{p.acceptance_rate != null ? `${p.acceptance_rate}%` : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && data.total > data.page_size && (
        <div className="mt-4 flex items-center justify-center gap-3 text-sm">
          <button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span className="text-muted">Page {page} of {pages}</span>
          <button className="btn btn-ghost" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      )}
    </>
  );
}
