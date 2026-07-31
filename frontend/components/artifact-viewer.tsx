"use client";

import { useMemo, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EvidenceImage, EvidenceVideo } from "@/components/evidence-media";
import { EvidenceType } from "@/lib/types";
import type { EvidenceOut } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ArtifactViewerProps {
  projectId: string;
  runId: string;
  evidence: EvidenceOut[];
  className?: string;
}

type TabKey = "screenshot" | "video" | "console" | "network" | "dom" | "api" | "timeline";

const TAB_LABELS: Record<TabKey, string> = {
  screenshot: "Screenshot",
  video: "Video",
  console: "Console",
  network: "Network",
  dom: "DOM",
  api: "API",
  timeline: "Timeline",
};

function groupEvidence(evidence: EvidenceOut[]): Partial<Record<TabKey, EvidenceOut[]>> {
  const groups: Partial<Record<TabKey, EvidenceOut[]>> = {};
  const push = (key: TabKey, item: EvidenceOut) => {
    groups[key] = [...(groups[key] ?? []), item];
  };
  for (const item of evidence) {
    switch (item.evidence_type) {
      case EvidenceType.SCREENSHOT:
        push("screenshot", item);
        break;
      case EvidenceType.VIDEO:
        push("video", item);
        break;
      case EvidenceType.CONSOLE_LOG:
        push("console", item);
        break;
      case EvidenceType.NETWORK_LOG:
        push("network", item);
        break;
      case EvidenceType.DOM_SNAPSHOT:
      case EvidenceType.ACCESSIBILITY_TREE:
        push("dom", item);
        break;
      case EvidenceType.API_REQUEST:
      case EvidenceType.API_RESPONSE:
        push("api", item);
        break;
      case EvidenceType.TIMING:
        push("timeline", item);
        break;
    }
  }
  return groups;
}

export function ArtifactViewer({ projectId, runId, evidence, className }: ArtifactViewerProps) {
  const groups = useMemo(() => groupEvidence(evidence), [evidence]);
  const availableTabs = useMemo(
    () => (Object.keys(groups) as TabKey[]).filter((key) => (groups[key]?.length ?? 0) > 0),
    [groups],
  );
  const [active, setActive] = useState<TabKey | "">(() => availableTabs[0] ?? "");
  const [opened, setOpened] = useState<Set<TabKey>>(() => new Set(availableTabs[0] ? [availableTabs[0]] : []));

  if (availableTabs.length === 0) {
    return <p className={cn("text-sm text-muted-foreground", className)}>No evidence captured for this step.</p>;
  }

  function handleTabChange(value: string) {
    const key = value as TabKey;
    setActive(key);
    setOpened((prev) => new Set(prev).add(key));
  }

  return (
    <Tabs value={active} onValueChange={handleTabChange} className={className}>
      <TabsList>
        {availableTabs.map((tab) => (
          <TabsTrigger key={tab} value={tab}>
            {TAB_LABELS[tab]}
          </TabsTrigger>
        ))}
      </TabsList>

      {availableTabs.map((tab) => (
        <TabsContent key={tab} value={tab} className="pt-3">
          <TabContent
            tab={tab}
            items={groups[tab] ?? []}
            projectId={projectId}
            runId={runId}
            enabled={opened.has(tab)}
          />
        </TabsContent>
      ))}
    </Tabs>
  );
}

function TabContent({
  tab,
  items,
  projectId,
  runId,
  enabled,
}: {
  tab: TabKey;
  items: EvidenceOut[];
  projectId: string;
  runId: string;
  enabled: boolean;
}) {
  switch (tab) {
    case "screenshot":
      return (
        <div className="space-y-3">
          {items.map((item) => (
            <EvidenceImage key={item.id} projectId={projectId} runId={runId} evidenceId={item.id} enabled={enabled} />
          ))}
        </div>
      );
    case "video":
      return (
        <div className="space-y-3">
          {items.map((item) => (
            <EvidenceVideo key={item.id} projectId={projectId} runId={runId} evidenceId={item.id} enabled={enabled} />
          ))}
        </div>
      );
    case "dom":
      return (
        <div className="space-y-3">
          {items.map((item) =>
            item.storage_key ? (
              <EvidenceImage key={item.id} projectId={projectId} runId={runId} evidenceId={item.id} enabled={enabled} alt="DOM snapshot" />
            ) : (
              <InlineDataView key={item.id} data={item.inline_data} />
            ),
          )}
        </div>
      );
    case "console":
      return <ConsoleLogView items={items} />;
    case "network":
      return <NetworkLogView items={items} />;
    case "api":
      return <ApiLogView items={items} />;
    case "timeline":
      return <TimelineView items={items} />;
    default:
      return null;
  }
}

function InlineDataView({ data }: { data: Record<string, unknown> | null }) {
  if (!data) return <p className="text-sm text-muted-foreground">No data captured.</p>;
  return (
    <pre className="max-h-96 overflow-auto rounded-lg bg-black/30 p-3 text-xs leading-relaxed text-foreground/90">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function ConsoleLogView({ items }: { items: EvidenceOut[] }) {
  const entries = items.flatMap((item) => {
    const data = item.inline_data;
    if (!data) return [];
    const list = Array.isArray(data.entries) ? data.entries : Array.isArray(data) ? data : [data];
    return list as Record<string, unknown>[];
  });

  if (entries.length === 0) return <p className="text-sm text-muted-foreground">No console output captured.</p>;

  return (
    <div className="max-h-96 space-y-1 overflow-auto rounded-lg border border-border bg-black/20 p-2 font-mono text-xs">
      {entries.map((entry, idx) => {
        const level = String(entry.level ?? entry.type ?? "log");
        const message = String(entry.message ?? entry.text ?? JSON.stringify(entry));
        return (
          <div
            key={idx}
            className={cn(
              "flex gap-2 rounded px-2 py-1",
              level === "error" && "bg-destructive/10 text-destructive",
              level === "warning" || level === "warn" ? "bg-warning/10 text-warning" : "",
            )}
          >
            <span className="shrink-0 uppercase text-muted-foreground">{level}</span>
            <span className="break-all">{message}</span>
          </div>
        );
      })}
    </div>
  );
}

function NetworkLogView({ items }: { items: EvidenceOut[] }) {
  const entries = items.flatMap((item) => {
    const data = item.inline_data;
    if (!data) return [];
    const list = Array.isArray(data.requests) ? data.requests : Array.isArray(data) ? data : [data];
    return list as Record<string, unknown>[];
  });

  if (entries.length === 0) return <p className="text-sm text-muted-foreground">No network activity captured.</p>;

  return (
    <div className="max-h-96 space-y-1.5 overflow-auto">
      {entries.map((entry, idx) => {
        const status = Number(entry.status ?? entry.status_code ?? 0);
        const method = String(entry.method ?? "GET");
        const url = String(entry.url ?? entry.endpoint ?? "");
        return (
          <div key={idx} className="flex items-center gap-3 rounded-lg border border-border px-3 py-2 text-xs">
            <span
              className={cn(
                "shrink-0 rounded px-1.5 py-0.5 font-mono font-medium",
                status >= 400 ? "bg-destructive/15 text-destructive" : status >= 200 ? "bg-success/15 text-success" : "bg-muted text-muted-foreground",
              )}
            >
              {status || "—"}
            </span>
            <span className="shrink-0 font-mono text-muted-foreground">{method}</span>
            <span className="truncate">{url}</span>
            {typeof entry.duration_ms === "number" && (
              <span className="ml-auto shrink-0 text-muted-foreground">{entry.duration_ms}ms</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ApiLogView({ items }: { items: EvidenceOut[] }) {
  return (
    <div className="max-h-96 space-y-3 overflow-auto">
      {items.map((item) => (
        <div key={item.id} className="rounded-lg border border-border p-3">
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {item.evidence_type === EvidenceType.API_REQUEST ? "Request" : "Response"}
          </p>
          <InlineDataView data={item.inline_data} />
        </div>
      ))}
    </div>
  );
}

function TimelineView({ items }: { items: EvidenceOut[] }) {
  const entries = items.flatMap((item) => {
    const data = item.inline_data;
    if (!data) return [];
    const list = Array.isArray(data.events) ? data.events : Array.isArray(data) ? data : [data];
    return list as Record<string, unknown>[];
  });

  if (entries.length === 0) return <p className="text-sm text-muted-foreground">No timing data captured.</p>;

  const maxDuration = Math.max(...entries.map((e) => Number(e.duration_ms ?? 0)), 1);

  return (
    <div className="max-h-96 space-y-2 overflow-auto">
      {entries.map((entry, idx) => {
        const duration = Number(entry.duration_ms ?? 0);
        const label = String(entry.label ?? entry.name ?? `Step ${idx + 1}`);
        return (
          <div key={idx} className="text-xs">
            <div className="mb-1 flex justify-between text-muted-foreground">
              <span>{label}</span>
              <span>{duration}ms</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${Math.max((duration / maxDuration) * 100, 2)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
