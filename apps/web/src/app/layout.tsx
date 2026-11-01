import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "CodeArena — Compete. Code. Conquer.", template: "%s · CodeArena" },
  description: "A competitive programming platform with sandboxed judging, contests and rankings.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <body>
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:rounded focus:bg-surface focus:p-2">Skip to content</a>
        <Nav />
        <main id="main" className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 pb-10 text-xs text-muted">CodeArena · Compete. Code. Conquer.</footer>
      </body>
    </html>
  );
}
