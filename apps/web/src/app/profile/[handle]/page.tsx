"use client";
import { useParams } from "next/navigation";
import { ProfileView } from "@/components/ProfileView";

export default function ProfilePage() {
  const { handle } = useParams<{ handle: string }>();
  return <ProfileView handle={handle} />;
}
