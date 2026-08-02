"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Clock, FolderKanban, Plus } from "lucide-react";
import { Topbar } from "@/components/topbar";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { StatTile } from "@/components/dashboard/stat-tile";
import { ExecutionHeatmap } from "@/components/dashboard/execution-heatmap";
import { InsightsPanel } from "@/components/dashboard/insights-panel";
import { NewProjectDialog } from "@/components/new-project-dialog";
import { useDashboardData } from "@/lib/dashboard-data";
import { formatConfidence, formatDate, formatDuration } from "@/lib/utils";

export default function DashboardPage() {
  const data = useDashboardData();
  const [newProjectOpen, setNewProjectOpen] = useState(false);

  return (
    <>
      <Topbar />
      <div className="mx-auto w-full max-w-6xl flex-1 space-y-6 p-6">
        <PageHeader
          title="Dashboard"
          description="A live overview of everything Stryker is testing for you."
          actions={
            <Button onClick={() => setNewProjectOpen(true)}>
              <Plus className="h-4 w-4" />
              New project
            </Button>
          }
        />

        {data.isError ? (
          <ErrorState description="Couldn't load your dashboard." onRetry={data.refetch} />
        ) : data.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
        ) : data.totalProjects === 0 ? (
          <EmptyState
            icon={FolderKanban}
            title="No projects yet"
            description="Create your first project to start describing requirements in plain English and let Stryker plan and run them."
            action={
              <Button onClick={() => setNewProjectOpen(true)}>
                <Plus className="h-4 w-4" />
                New project
              </Button>
            }
          />
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatTile label="Total projects" value={data.totalProjects} icon={FolderKanban} />
              <StatTile
                label="Pass rate"
                value={data.passRate != null ? formatConfidence(data.passRate) : "—"}
                icon={CheckCircle2}
                hint="Across all finished runs"
              />
              <StatTile
                label="Avg. run duration"
                value={formatDuration(data.averageDurationMs)}
                icon={Clock}
              />
              <StatTile
                label="Runs, last 8 weeks"
                value={data.totalRunsLast8Weeks}
                icon={AlertTriangle}
              />
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <div className="space-y-4 lg:col-span-2">
                <ExecutionHeatmap days={data.heatmap} />

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium text-muted-foreground">Recent runs</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1">
                    {data.recentRuns.length === 0 ? (
                      <p className="py-6 text-center text-sm text-muted-foreground">No runs yet — start one from a project&apos;s Requirements tab.</p>
                    ) : (
                      data.recentRuns.map((run, idx) => (
                        <motion.div
                          key={run.id}
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: idx * 0.03 }}
                        >
                          <Link
                            href={`/projects/${run.project_id}/runs/${run.id}`}
                            className="flex items-center justify-between rounded-lg px-2 py-2.5 text-sm transition-colors hover:bg-secondary/50"
                          >
                            <div className="flex items-center gap-3">
                              <StatusBadge status={run.status} />
                              <span className="text-muted-foreground">{run.projectName}</span>
                            </div>
                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                              <span>{formatConfidence(run.confidence_score)} confidence</span>
                              <span>{formatDuration(run.duration_ms)}</span>
                              <span>{formatDate(run.finished_at ?? run.started_at)}</span>
                            </div>
                          </Link>
                        </motion.div>
                      ))
                    )}
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-4">
                <InsightsPanel data={data} />

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium text-muted-foreground">Top failing requirements</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {data.topFailingRequirements.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No failures recorded — nice.</p>
                    ) : (
                      data.topFailingRequirements.map((req) => (
                        <Link
                          key={req.requirementId}
                          href={req.projectId ? `/projects/${req.projectId}/requirements` : "#"}
                          className="block rounded-lg p-2 -mx-2 transition-colors hover:bg-secondary/50"
                        >
                          <p className="line-clamp-2 text-sm">{req.text}</p>
                          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                            <span>{req.projectName}</span>
                            <span>·</span>
                            <span className="font-medium text-destructive">{req.failureCount} failure{req.failureCount === 1 ? "" : "s"}</span>
                          </div>
                        </Link>
                      ))
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </>
        )}
      </div>

      <NewProjectDialog open={newProjectOpen} onOpenChange={setNewProjectOpen} />
    </>
  );
}
