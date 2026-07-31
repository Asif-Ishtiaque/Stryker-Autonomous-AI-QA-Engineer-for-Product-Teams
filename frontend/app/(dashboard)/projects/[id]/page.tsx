"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, Clock, ListChecks, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { StatTile } from "@/components/dashboard/stat-tile";
import { EmptyState } from "@/components/empty-state";
import { useProjectStats, useRuns } from "@/lib/queries";
import { formatConfidence, formatDate, formatDuration } from "@/lib/utils";
import { PlayCircle } from "lucide-react";

export default function ProjectOverviewPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const { data: stats, isLoading: statsLoading } = useProjectStats(projectId);
  const { data: runs, isLoading: runsLoading } = useRuns(projectId);

  const recentRuns = [...(runs ?? [])]
    .sort((a, b) => new Date(b.finished_at ?? b.started_at ?? 0).getTime() - new Date(a.finished_at ?? a.started_at ?? 0).getTime())
    .slice(0, 10);

  return (
    <div className="space-y-6">
      {statsLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile label="Requirements" value={stats?.requirement_count ?? 0} icon={ListChecks} />
          <StatTile
            label="Pass rate"
            value={stats?.pass_rate != null ? formatConfidence(stats.pass_rate) : "—"}
            icon={CheckCircle2}
            hint={`${stats?.run_count ?? 0} total runs`}
          />
          <StatTile label="Avg. duration" value={formatDuration(stats?.average_duration_ms)} icon={Clock} />
          <StatTile
            label="Open bugs"
            value={stats?.open_bugs ?? 0}
            icon={ShieldAlert}
            hint={stats?.average_confidence != null ? `${formatConfidence(stats.average_confidence)} avg. confidence` : undefined}
          />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Recent runs</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {runsLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 rounded-lg" />
              ))}
            </div>
          ) : recentRuns.length === 0 ? (
            <EmptyState
              icon={PlayCircle}
              title="No runs yet"
              description="Add a requirement and press Run to kick off Stryker's first execution for this project."
              action={
                <Link href={`/projects/${projectId}/requirements`} className="text-sm font-medium text-primary hover:underline">
                  Go to Requirements →
                </Link>
              }
            />
          ) : (
            recentRuns.map((run) => (
              <Link
                key={run.id}
                href={`/projects/${projectId}/runs/${run.id}`}
                className="flex items-center justify-between rounded-lg px-2 py-2.5 text-sm transition-colors hover:bg-secondary/50"
              >
                <StatusBadge status={run.status} />
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span>{formatConfidence(run.confidence_score)} confidence</span>
                  <span>{formatDuration(run.duration_ms)}</span>
                  <span>{formatDate(run.finished_at ?? run.started_at)}</span>
                </div>
              </Link>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
