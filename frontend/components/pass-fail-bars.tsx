"use client";

import { motion } from "framer-motion";
import { RunStatus } from "@/lib/types";
import type { RunOut } from "@/lib/types";
import { cn } from "@/lib/utils";

const COLOR_MAP: Record<string, string> = {
  [RunStatus.PASSED]: "bg-success",
  [RunStatus.FAILED]: "bg-destructive",
  [RunStatus.ERRORED]: "bg-destructive/60",
  [RunStatus.CANCELLED]: "bg-muted-foreground/40",
};

export function PassFailBars({ runs }: { runs: RunOut[] }) {
  const chronological = [...runs].sort(
    (a, b) => new Date(a.started_at ?? a.finished_at ?? 0).getTime() - new Date(b.started_at ?? b.finished_at ?? 0).getTime(),
  );

  if (chronological.length === 0) {
    return <p className="text-sm text-muted-foreground">No run history yet.</p>;
  }

  return (
    <div className="flex h-24 items-end gap-1">
      {chronological.map((run, idx) => {
        const heightPct = run.duration_ms != null ? Math.max(15, Math.min(100, (run.duration_ms / 1000 / 30) * 100)) : 40;
        return (
          <motion.div
            key={run.id}
            initial={{ height: 0 }}
            animate={{ height: `${heightPct}%` }}
            transition={{ delay: idx * 0.01 }}
            title={`${run.status} · ${new Date(run.started_at ?? run.finished_at ?? "").toLocaleDateString()}`}
            className={cn("w-1.5 min-w-[3px] rounded-sm", COLOR_MAP[run.status] ?? "bg-muted")}
          />
        );
      })}
    </div>
  );
}
