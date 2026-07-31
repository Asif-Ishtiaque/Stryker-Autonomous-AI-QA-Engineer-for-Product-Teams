"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { slug: "", label: "Overview" },
  { slug: "requirements", label: "Requirements" },
  { slug: "knowledge", label: "Knowledge" },
  { slug: "credentials", label: "Credentials" },
  { slug: "runs", label: "Runs" },
  { slug: "evidence", label: "Evidence" },
  { slug: "history", label: "History" },
  { slug: "settings", label: "Settings" },
];

export function ProjectTabs({ projectId }: { projectId: string }) {
  const pathname = usePathname();
  const base = `/projects/${projectId}`;

  return (
    <div className="no-scrollbar -mx-6 flex gap-1 overflow-x-auto border-b border-border px-6">
      {TABS.map((tab) => {
        const href = tab.slug ? `${base}/${tab.slug}` : base;
        const active = tab.slug ? pathname.startsWith(href) : pathname === base;
        return (
          <Link
            key={tab.slug}
            href={href}
            className={cn(
              "relative whitespace-nowrap px-3 py-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground",
              active && "text-foreground",
            )}
          >
            {tab.label}
            {active && <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-primary" />}
          </Link>
        );
      })}
    </div>
  );
}
