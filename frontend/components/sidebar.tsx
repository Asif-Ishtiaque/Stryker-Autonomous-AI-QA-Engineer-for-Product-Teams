"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FolderKanban, LayoutDashboard, Search } from "lucide-react";
import { Logo } from "@/components/logo";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useCommandPalette } from "@/components/command-palette";

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
];

export function Sidebar() {
  const pathname = usePathname();
  const palette = useCommandPalette();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card/40 md:flex">
      <div className="flex h-16 items-center px-5">
        <Link href="/dashboard">
          <Logo />
        </Link>
      </div>

      <div className="px-3">
        <Button
          variant="outline"
          className="w-full justify-between text-muted-foreground"
          onClick={() => palette.open()}
        >
          <span className="flex items-center gap-2">
            <Search className="h-3.5 w-3.5" />
            Search…
          </span>
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium">⌘K</kbd>
        </Button>
      </div>

      <nav className="mt-4 flex flex-col gap-0.5 px-3">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto p-4">
        <p className="text-xs text-muted-foreground">Stryker v0.1 · self-hosted</p>
      </div>
    </aside>
  );
}
