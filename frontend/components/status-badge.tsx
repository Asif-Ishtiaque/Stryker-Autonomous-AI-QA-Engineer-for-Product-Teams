import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Clock,
  Loader2,
  RotateCw,
  SkipForward,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { KnowledgeIndexStatus, RunStatus, StepStatus } from "@/lib/types";

type AnyStatus = RunStatus | StepStatus | KnowledgeIndexStatus | string;

interface StatusMeta {
  label: string;
  className: string;
  icon: React.ComponentType<{ className?: string }>;
  spin?: boolean;
}

const STATUS_META: Record<string, StatusMeta> = {
  // run + shared terminal states
  queued: { label: "Queued", className: "bg-muted text-muted-foreground border-border", icon: Clock },
  planning: { label: "Planning", className: "bg-primary/15 text-primary border-primary/30", icon: Loader2, spin: true },
  running: { label: "Running", className: "bg-primary/15 text-primary border-primary/30", icon: Loader2, spin: true },
  retrying: { label: "Retrying", className: "bg-warning/15 text-warning border-warning/30", icon: RotateCw, spin: true },
  validating: { label: "Validating", className: "bg-primary/15 text-primary border-primary/30", icon: Loader2, spin: true },
  passed: { label: "Passed", className: "bg-success/15 text-success border-success/30", icon: CheckCircle2 },
  failed: { label: "Failed", className: "bg-destructive/15 text-destructive border-destructive/30", icon: XCircle },
  errored: { label: "Errored", className: "bg-destructive/15 text-destructive border-destructive/30", icon: AlertTriangle },
  cancelled: { label: "Cancelled", className: "bg-muted text-muted-foreground border-border", icon: XCircle },
  // step-only
  waiting: { label: "Waiting", className: "bg-muted text-muted-foreground border-border", icon: CircleDashed },
  skipped: { label: "Skipped", className: "bg-muted text-muted-foreground border-border", icon: SkipForward },
  // knowledge-only
  pending: { label: "Pending", className: "bg-muted text-muted-foreground border-border", icon: Clock },
  processing: { label: "Processing", className: "bg-primary/15 text-primary border-primary/30", icon: Loader2, spin: true },
  indexed: { label: "Indexed", className: "bg-success/15 text-success border-success/30", icon: CheckCircle2 },
};

export function statusMeta(status: AnyStatus): StatusMeta {
  return STATUS_META[status] ?? { label: status, className: "bg-muted text-muted-foreground border-border", icon: CircleDashed };
}

export function StatusBadge({ status, className }: { status: AnyStatus; className?: string }) {
  const meta = statusMeta(status);
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
        meta.className,
        className,
      )}
    >
      <Icon className={cn("h-3 w-3", meta.spin && "animate-spin")} />
      {meta.label}
    </span>
  );
}
