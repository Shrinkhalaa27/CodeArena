"use client";
import { useParams } from "next/navigation";
import { Workspace } from "@/components/Workspace";

export default function ProblemPage() {
  const { slug } = useParams<{ slug: string }>();
  return <Workspace slug={slug} />;
}
