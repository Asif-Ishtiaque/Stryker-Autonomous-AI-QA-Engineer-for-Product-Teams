"use client";

import { useParams, useRouter } from "next/navigation";
import { History } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PassFailBars } from "@/components/pass-fail-bars";
import { useRuns } from "@/lib/queries";
import { formatConfidence, formatDate, formatDuration } from "@/lib/utils";
import { RunStatus } from "@/lib/types";

export default function HistoryPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const router = useRouter();
  const { data: runs, isLoading } = useRuns(projectId);

  const chronologicalDesc = [...(runs ?? [])].sort(
    (a, b) => new Date(b.started_at ?? b.finished_at ?? 0).getTime() - new Date(a.started_at ?? a.finished_at ?? 0).getTime(),
  );

  const passed = (runs ?? []).filter((r) => r.status === RunStatus.PASSED).length;
  const failed = (runs ?? []).filter((r) => r.status === RunStatus.FAILED || r.status === RunStatus.ERRORED).length;

  return (
    <div className="space-y-6">
      <PageHeader title="History" description="Pass/fail trend over time for this project's runs." />

      {isLoading ? (
        <Skeleton className="h-32 rounded-xl" />
      ) : !runs || runs.length === 0 ? (
        <EmptyState icon={History} title="No history yet" description="Once runs execute, their pass/fail trend will appear here." />
      ) : (
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Run duration over time</CardTitle>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-success" /> {passed} passed
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-destructive" /> {failed} failed
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <PassFailBars runs={runs} />
          </CardContent>
        </Card>
      )}

      {!isLoading && runs && runs.length > 0 && (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Status</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {chronologicalDesc.map((run) => (
                <TableRow key={run.id} className="cursor-pointer" onClick={() => router.push(`/projects/${projectId}/runs/${run.id}`)}>
                  <TableCell>
                    <StatusBadge status={run.status} />
                  </TableCell>
                  <TableCell>{formatConfidence(run.confidence_score)}</TableCell>
                  <TableCell>{formatDuration(run.duration_ms)}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(run.started_at ?? run.finished_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
