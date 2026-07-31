"use client";

import { useParams, useRouter } from "next/navigation";
import { PlayCircle } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRuns } from "@/lib/queries";
import { formatConfidence, formatDate, formatDuration } from "@/lib/utils";

const SEVERITY_VARIANT: Record<string, "destructive" | "warning" | "secondary" | "outline"> = {
  critical: "destructive",
  high: "destructive",
  medium: "warning",
  low: "secondary",
};

export default function RunsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const router = useRouter();
  const { data: runs, isLoading } = useRuns(projectId);

  const sorted = [...(runs ?? [])].sort(
    (a, b) => new Date(b.started_at ?? b.finished_at ?? 0).getTime() - new Date(a.started_at ?? a.finished_at ?? 0).getTime(),
  );

  return (
    <div className="space-y-6">
      <PageHeader title="Runs" description="Every execution Stryker has kicked off for this project." />

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 rounded-lg" />
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <EmptyState icon={PlayCircle} title="No runs yet" description="Start one from the Requirements tab." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Status</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Started</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((run) => (
                <TableRow
                  key={run.id}
                  className="cursor-pointer"
                  onClick={() => router.push(`/projects/${projectId}/runs/${run.id}`)}
                >
                  <TableCell>
                    <StatusBadge status={run.status} />
                  </TableCell>
                  <TableCell>{formatConfidence(run.confidence_score)}</TableCell>
                  <TableCell>
                    {run.severity ? (
                      <Badge variant={SEVERITY_VARIANT[run.severity] ?? "outline"} className="capitalize">
                        {run.severity}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell>{formatDuration(run.duration_ms)}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(run.started_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
