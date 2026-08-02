"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Search } from "lucide-react";
import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { NAV_ITEMS } from "@/components/sidebar";
import { useCommandPalette } from "@/components/command-palette";
import { cn } from "@/lib/utils";

/**
 * Sidebar (components/sidebar.tsx) is `hidden md:flex` — below that breakpoint
 * there was previously no way to navigate between Dashboard/Projects at all
 * except browser back/forward, since ⌘K is a keyboard shortcut with no
 * touch-discoverable affordance. This is the mobile equivalent, shown only
 * below md.
 */
export function MobileNav() {
  const pathname = usePathname();
  const palette = useCommandPalette();
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
          <span className="sr-only">Open navigation</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64 p-0">
        <SheetTitle className="sr-only">Navigation</SheetTitle>
        <div className="flex h-16 items-center px-5">
          <Logo />
        </div>

        <div className="px-3">
          <Button
            variant="outline"
            className="w-full justify-start text-muted-foreground"
            onClick={() => {
              setOpen(false);
              palette.open();
            }}
          >
            <Search className="h-3.5 w-3.5" />
            Search…
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
                onClick={() => setOpen(false)}
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
      </SheetContent>
    </Sheet>
  );
}
