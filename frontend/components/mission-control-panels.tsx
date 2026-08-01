"use client";

import { BrainCircuit, Globe, Terminal } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ConsoleEntry, NetworkEntry, ReasoningEntry } from "@/lib/run-events";

/** AI Reasoning panel — streams the narration the executor emits as it works each step. */
export function ReasoningPanel({ entries }: { entries: ReasoningEntry[] }) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <BrainCircuit className="h-4 w-4" />
          AI reasoning
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto pt-0">
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">Waiting for the run to start…</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {entries.map((entry) => (
              <li key={entry.key} className="leading-relaxed">
                {entry.sequence != null && <span className="mr-1.5 text-muted-foreground">#{entry.sequence}</span>}
                {entry.text}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

/** Live Console panel — every console message as it's emitted, not just the last 50 bundled at step-end. */
export function LiveConsolePanel({ entries }: { entries: ConsoleEntry[] }) {
  return (
    <Card className="flex h-64 flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Terminal className="h-4 w-4" />
          Live console
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto pt-0 font-mono text-xs">
        {entries.length === 0 ? (
          <p className="font-sans text-sm text-muted-foreground">No console output yet.</p>
        ) : (
          <div className="space-y-1">
            {entries.map((entry) => (
              <div
                key={entry.key}
                className={cn(
                  "flex gap-2 rounded px-2 py-1",
                  entry.type === "error" && "bg-destructive/10 text-destructive",
                  (entry.type === "warning" || entry.type === "warn") && "bg-warning/10 text-warning",
                )}
              >
                <span className="shrink-0 uppercase text-muted-foreground">{entry.type}</span>
                <span className="break-all">{entry.text}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** Live Network panel — every finished request as it happens, not just the last 50 bundled at step-end. */
export function LiveNetworkPanel({ entries }: { entries: NetworkEntry[] }) {
  return (
    <Card className="flex h-64 flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Globe className="h-4 w-4" />
          Live network
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto pt-0">
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">No requests captured yet.</p>
        ) : (
          <div className="space-y-1.5">
            {entries.map((entry) => (
              <div key={entry.key} className="flex items-center gap-2 rounded-lg border border-border px-2 py-1.5 text-xs">
                <span className="shrink-0 font-mono text-muted-foreground">{entry.method}</span>
                <span className="truncate">{entry.url}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
