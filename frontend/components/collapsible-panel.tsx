"use client";

import { useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Card with a collapsible, internally-scrollable body. Used for the Mission Control
 * live panels (AI reasoning, live network, live console, execution timeline), which
 * otherwise grow unbounded as events stream in instead of scrolling in place.
 */
export function CollapsiblePanel({
  icon,
  title,
  children,
  className,
  contentClassName,
  defaultCollapsed = false,
}: {
  icon?: ReactNode;
  title: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  defaultCollapsed?: boolean;
}) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="pb-2">
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="flex w-full items-center justify-between gap-2 text-left"
          aria-expanded={!collapsed}
        >
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            {icon}
            {title}
          </CardTitle>
          <ChevronDown
            className={cn("h-4 w-4 shrink-0 text-muted-foreground transition-transform", collapsed && "-rotate-90")}
          />
        </button>
      </CardHeader>
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <CardContent className={cn("overflow-y-auto pt-0", contentClassName)}>{children}</CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
