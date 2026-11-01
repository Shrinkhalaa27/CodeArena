"use client";
import { useState } from "react";
import { EmptyState, ErrorState, PageHeader, Skeleton } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useApi, useUser } from "@/lib/hooks";

interface AdminProblem { id: string; slug: string; title: string; status: string; difficulty: string; tests: number }

export default function AdminPage() {
  const { user, ready } = useUser();
  const staff = !!user && ["admin", "contest_admin", "setter"].includes(user.role);
  const problems = useApi<AdminProblem[]>(staff ? "/admin/problems" : null);
  const health = useApi<{ queue_depth: number | null; judge_backend: string; judge_ok: boolean }>(staff ? "/admin/judge-health" : null);
  const audit = useApi<{ id: string; action: string; target: string; at: string }[]>(user?.role === "admin" ? "/admin/audit?limit=10" : null);
  const [msg, setMsg] = useState<string | null>(null);
  if (!ready) return null;
  // UI gating is cosmetic. Every endpoint below enforces roles on the server.
  if (!staff) return <EmptyState title="Restricted area" hint="You need a staff role to view this page." />;
  const publish = async (slug: string) => {
    setMsg(null);
    try { await api(`/admin/problems/${slug}/publish`, { method: "POST" }); problems.reload(); } catch (e) { setMsg((e as ApiError).message); }
  };
  return (
    <>
      <PageHeader title="Admin" subtitle="Judge health, problems and audit trail." />
      <section className="mb-8 grid gap-3 sm:grid-cols-3" aria-label="Judge health">
        <div className="card p-4"><p className="text-xs text-muted">Judge</p><p className={`text-lg font-semibold ${health.data?.judge_ok ? "text-ok" : "text-bad"}`}>{health.loading ? "…" : health.data?.judge_ok ? "Healthy" : "Unreachable"}</p></div>
        <div className="card p-4"><p className="text-xs text-muted">Queue depth</p><p className="text-lg font-semibold">{health.data?.queue_depth ?? "–"}</p></div>
        <div className="card p-4"><p className="text-xs text-muted">Backend</p><p className="text-lg font-semibold">{health.data?.judge_backend ?? "–"}</p></div>
      </section>
      {msg && <p role="alert" className="mb-3 text-sm text-bad">{msg}</p>}
      <h2 className="mb-3 font-semibold">Problems</h2>
      {problems.loading ? <Skeleton rows={4} /> : problems.error ? <ErrorState error={problems.error} retry={problems.reload} /> : (
        <div className="card mb-8 overflow-x-auto"><table className="w-full text-sm"><thead className="border-b border-line text-left text-xs uppercase text-muted"><tr><th className="px-4 py-3">Title</th><th>Status</th><th>Tests</th><th className="px-4" /></tr></thead>
          <tbody>{problems.data?.map((p) => <tr key={p.id} className="border-b border-line last:border-0"><td className="px-4 py-3">{p.title}</td><td>{p.status}</td><td>{p.tests}</td>
            <td className="px-4 text-right">{p.status !== "published" && user?.role === "admin" && <button className="btn btn-ghost !py-1" onClick={() => publish(p.slug)}>Publish</button>}</td></tr>)}</tbody></table></div>
      )}
      {audit.data && (<><h2 className="mb-3 font-semibold">Recent audit log</h2><ul className="card divide-y divide-line text-sm">{audit.data.map((a) => <li key={a.id} className="flex justify-between px-4 py-2"><span>{a.action} <span className="text-muted">{a.target}</span></span><span className="text-xs text-muted">{new Date(a.at).toLocaleString()}</span></li>)}</ul></>)}
      <p className="mt-6 text-xs text-muted">Creating problems and contests is available via the documented admin API (see docs/API.md); a full authoring UI is on the roadmap.</p>
    </>
  );
}
