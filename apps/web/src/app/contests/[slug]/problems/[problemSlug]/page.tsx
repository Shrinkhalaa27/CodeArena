"use client";
import { useParams } from "next/navigation";
import { Workspace } from "@/components/Workspace";
import { ErrorState, Skeleton } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import type { ContestDetail } from "@/lib/types";

export default function ContestProblemPage() {
  const { slug, problemSlug } = useParams<{ slug: string; problemSlug: string }>();
  const { data, error, loading, reload } = useApi<ContestDetail>(`/contests/${slug}`);
  if (loading) return <Skeleton rows={6} />;
  if (error || !data) return <ErrorState error={error!} retry={reload} />;
  return <Workspace slug={problemSlug} contestId={data.id} contestSlug={slug} />;
}
