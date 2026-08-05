"use client";

import { BrainCircuit, Globe, Terminal } from "lucide-react";
import { CollapsiblePanel } from "@/components/collapsible-panel";
import { cn } from "@/lib/utils";
import type { ConsoleEntry, NetworkEntry, ReasoningEntry } from "@/lib/run-events";

/** AI Reasoning panel — streams the narration the executor emits as it works each step. */
export function ReasoningPanel({ entries }: { entries: ReasoningEntry[] }) {
  return (
    <CollapsiblePanel icon={<BrainCircuit className="h-4 w-4" />} title="AI reasoning" contentClassName="max-h-[420px]">
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
    </CollapsiblePanel>
  );
}

/** Live Console panel — every console message as it's emitted, not just the last 50 bundled at step-end. */
export function LiveConsolePanel({ entries }: { entries: ConsoleEntry[] }) {
  return (
    <CollapsiblePanel
      icon={<Terminal className="h-4 w-4" />}
      title="Live console"
      contentClassName="max-h-64 font-mono text-xs"
    >
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
    </CollapsiblePanel>
  );
}

/** Live Network panel — every finished request as it happens, not just the last 50 bundled at step-end. */
export function LiveNetworkPanel({ entries }: { entries: NetworkEntry[] }) {
  return (
    <CollapsiblePanel icon={<Globe className="h-4 w-4" />} title="Live network" contentClassName="max-h-64">
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
    </CollapsiblePanel>
  );
}
