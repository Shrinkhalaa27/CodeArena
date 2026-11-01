"use client";
import { useEffect, useState } from "react";
import { EmptyState, PageHeader } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useUser } from "@/lib/hooks";

export default function Settings() {
  const { user, ready } = useUser();
  const [bio, setBio] = useState("");
  const [country, setCountry] = useState("");
  const [isPublic, setPublic] = useState(true);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  useEffect(() => { if (user) { setBio(user.bio); setCountry(user.country ?? ""); setPublic(user.is_public); } }, [user]);
  if (!ready) return null;
  if (!user) return <EmptyState title="Sign in to edit settings" />;
  async function save(e: React.FormEvent) {
    e.preventDefault(); setMsg(null);
    try { await api("/auth/me", { method: "PATCH", json: { bio, country: country || null, is_public: isPublic } }); setMsg({ ok: true, text: "Saved." }); }
    catch (err) { setMsg({ ok: false, text: (err as ApiError).message }); }
  }
  return (
    <>
      <PageHeader title="Settings" />
      <form onSubmit={save} className="card max-w-lg space-y-4 p-6">
        <div><label htmlFor="bio" className="mb-1 block text-sm">Bio</label><textarea id="bio" maxLength={280} className="input h-24" value={bio} onChange={(e) => setBio(e.target.value)} /></div>
        <div><label htmlFor="country" className="mb-1 block text-sm">Country code (optional)</label><input id="country" maxLength={2} className="input !w-24 uppercase" value={country} onChange={(e) => setCountry(e.target.value)} /></div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={isPublic} onChange={(e) => setPublic(e.target.checked)} /> Make my profile and activity public</label>
        <button className="btn btn-primary">Save changes</button>
        {msg && <p role="status" className={`text-sm ${msg.ok ? "text-ok" : "text-bad"}`}>{msg.text}</p>}
      </form>
    </>
  );
}
