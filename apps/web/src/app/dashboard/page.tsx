"use client";
import Link from "next/link";
import { ProfileView } from "@/components/ProfileView";
import { EmptyState, VerdictBadge } from "@/components/ui";
import { useApi, useUser } from "@/lib/hooks";
import type { Submission } from "@/lib/types";

export default function Dashboard() {
  const { user, ready } = useUser();
  const recent = useApi<Submission[]>(user ? "/submissions?limit=8" : null);
  if (!ready) return null;
  if (!user) return <EmptyState title="Sign in to see your dashboard" hint="Your stats, streaks and recent submissions live here." />;
  return (
    <div className="space-y-8">
      {user.is_public ? <ProfileView handle={user.handle} /> : <p className="card p-4 text-sm text-muted">Your profile is private, so charts are hidden. Change this in <Link className="text-cyan" href="/settings">settings</Link>.</p>}
      <section>
        <h2 className="mb-3 font-semibold">Recent submissions</h2>
        {!recent.data?.length ? <EmptyState title="No submissions yet" hint="Solve your first problem to see it here." /> : (
          <ul className="card divide-y divide-line">{recent.data.map((s) => (
            <li key={s.id} className="flex items-center justify-between px-4 py-3 text-sm"><span className="text-muted">{new Date(s.created_at).toLocaleString()} · {s.language}</span><VerdictBadge status={s.status} /></li>))}</ul>
        )}
      </section>
    </div>
  );
}
