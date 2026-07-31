"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, ChevronDown, CircleDashed, Loader2, RotateCw, XCircle } from "lucide-react";
import { statusMeta } from "@/components/status-badge";
import { ArtifactViewer } from "@/components/artifact-viewer";
import { cn } from "@/lib/utils";
import type { LiveStepView } from "@/lib/run-events";
import type { EvidenceOut, StepOut } from "@/lib/types";

interface TimelineEntry {
  key: string;
  sequence: number;
  name: string;
  status: string;
  errorMessage?: string | null;
  message?: string | null;
  retryCount?: number;
  evidence?: EvidenceOut[];
}

function fromStepOut(step: StepOut): TimelineEntry {
  return {
    key: step.id,
    sequence: step.sequence,
    name: step.name,
    status: step.status,
    errorMessage: step.error_message,
    retryCount: step.retry_count,
    evidence: step.evidence,
  };
}

function fromLiveStep(step: LiveStepView): TimelineEntry {
  return {
    key: step.key,
    sequence: step.sequence,
    name: step.name,
    status: step.status,
    message: step.message,
  };
}

export function StepTimeline({
  projectId,
  runId,
  steps,
  liveSteps,
}: {
  projectId: string;
  runId: string;
  steps?: StepOut[];
  liveSteps?: LiveStepView[];
}) {
  const entries: TimelineEntry[] = steps ? steps.map(fromStepOut) : (liveSteps ?? []).map(fromLiveStep);

  if (entries.length === 0) {
    return (
      <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Waiting for the first step to start…
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="absolute bottom-0 left-[15px] top-2 w-px bg-border" />
      <ul className="space-y-1">
        <AnimatePresence initial={false}>
          {entries.map((entry, idx) => (
            <TimelineRow key={entry.key} entry={entry} index={idx} projectId={projectId} runId={runId} />
          ))}
        </AnimatePresence>
      </ul>
    </div>
  );
}

function TimelineRow({
  entry,
  index,
  projectId,
  runId,
}: {
  entry: TimelineEntry;
  index: number;
  projectId: string;
  runId: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const meta = statusMeta(entry.status);
  const hasEvidence = (entry.evidence?.length ?? 0) > 0;
  const isRunning = entry.status === "running" || entry.status === "retrying";

  return (
    <motion.li
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.03 }}
      className="relative pl-9"
    >
      <span
        className={cn(
          "absolute left-0 top-1 flex h-7 w-7 items-center justify-center rounded-full border bg-background",
          meta.className,
          isRunning && "animate-pulse-ring",
        )}
      >
        <StepIcon status={entry.status} />
      </span>

      <div
        className={cn(
          "flex items-center justify-between gap-3 rounded-lg py-1.5",
          hasEvidence && "cursor-pointer hover:bg-secondary/40 px-2 -mx-2",
        )}
        onClick={() => hasEvidence && setExpanded((e) => !e)}
      >
        <div>
          <p className="text-sm font-medium leading-tight">
            {entry.sequence != null && <span className="mr-1.5 text-muted-foreground">#{entry.sequence}</span>}
            {entry.name}
          </p>
          {(entry.errorMessage || entry.message) && (
            <p className={cn("mt-0.5 text-xs", entry.errorMessage ? "text-destructive" : "text-muted-foreground")}>
              {entry.errorMessage ?? entry.message}
            </p>
          )}
          {!!entry.retryCount && entry.retryCount > 0 && (
            <p className="mt-0.5 text-xs text-warning">Retried {entry.retryCount}×</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={cn("rounded-full border px-2 py-0.5 text-xs font-medium capitalize", meta.className)}>{meta.label}</span>
          {hasEvidence && <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", expanded && "rotate-180")} />}
        </div>
      </div>

      <AnimatePresence initial={false}>
        {expanded && hasEvidence && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="my-3 rounded-lg border border-border bg-card/40 p-3">
              <ArtifactViewer projectId={projectId} runId={runId} evidence={entry.evidence ?? []} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  );
}

function StepIcon({ status }: { status: string }) {
  switch (status) {
    case "passed":
      return <CheckCircle2 className="h-3.5 w-3.5" />;
    case "failed":
      return <XCircle className="h-3.5 w-3.5" />;
    case "running":
      return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
    case "retrying":
      return <RotateCw className="h-3.5 w-3.5 animate-spin" />;
    default:
      return <CircleDashed className="h-3.5 w-3.5" />;
  }
}
