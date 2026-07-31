"use client";

import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { HeatmapDay } from "@/lib/dashboard-data";
import { cn } from "@/lib/utils";

function intensityClass(count: number, max: number): string {
  if (count === 0) return "bg-muted";
  const ratio = count / Math.max(max, 1);
  if (ratio > 0.75) return "bg-primary";
  if (ratio > 0.5) return "bg-primary/70";
  if (ratio > 0.25) return "bg-primary/45";
  return "bg-primary/25";
}

export function ExecutionHeatmap({ days }: { days: HeatmapDay[] }) {
  const [hovered, setHovered] = useState<HeatmapDay | null>(null);
  const max = useMemo(() => days.reduce((m, d) => Math.max(m, d.count), 0), [days]);

  // Group into weeks (columns), 7 rows each, oldest first.
  const weeks: HeatmapDay[][] = [];
  for (let i = 0; i < days.length; i += 7) {
    weeks.push(days.slice(i, i + 7));
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">Execution activity — last 8 weeks</CardTitle>
        {hovered && (
          <span className="text-xs text-muted-foreground">
            {hovered.count} run{hovered.count === 1 ? "" : "s"} · {hovered.date}
          </span>
        )}
      </CardHeader>
      <CardContent>
        <div className="flex gap-1 overflow-x-auto pb-1">
          {weeks.map((week, wi) => (
            <div key={wi} className="flex flex-col gap-1">
              {week.map((day) => (
                <div
                  key={day.date}
                  onMouseEnter={() => setHovered(day)}
                  onMouseLeave={() => setHovered(null)}
                  className={cn("h-3 w-3 rounded-[3px] transition-colors", intensityClass(day.count, max))}
                  title={`${day.date}: ${day.count} run${day.count === 1 ? "" : "s"}`}
                />
              ))}
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
          Less
          <span className="h-2.5 w-2.5 rounded-[3px] bg-muted" />
          <span className="h-2.5 w-2.5 rounded-[3px] bg-primary/25" />
          <span className="h-2.5 w-2.5 rounded-[3px] bg-primary/45" />
          <span className="h-2.5 w-2.5 rounded-[3px] bg-primary/70" />
          <span className="h-2.5 w-2.5 rounded-[3px] bg-primary" />
          More
        </div>
      </CardContent>
    </Card>
  );
}
