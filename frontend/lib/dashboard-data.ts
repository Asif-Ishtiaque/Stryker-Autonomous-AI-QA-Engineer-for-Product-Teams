"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import { projectsApi, requirementsApi, runsApi } from "./api-client";
import type { ProjectOut, RunOut } from "./types";
import { RunStatus, TERMINAL_RUN_STATUSES } from "./types";

export interface DashboardRun extends RunOut {
  projectName: string;
}

export interface FailingRequirement {
  requirementId: string;
  text: string;
  projectId: string;
  projectName: string;
  failureCount: number;
}

export interface HeatmapDay {
  date: string; // yyyy-mm-dd
  count: number;
}

export interface DashboardData {
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
  projects: ProjectOut[];
  totalProjects: number;
  recentRuns: DashboardRun[];
  passRate: number | null;
  averageDurationMs: number | null;
  topFailingRequirements: FailingRequirement[];
  heatmap: HeatmapDay[];
  totalRunsLast8Weeks: number;
}

const HEATMAP_DAYS = 56; // ~8 weeks

export function useDashboardData(): DashboardData {
  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: projectsApi.list });
  const projects = projectsQuery.data ?? [];

  const runsQueries = useQueries({
    queries: projects.map((p) => ({
      queryKey: ["projects", p.id, "runs"],
      queryFn: () => runsApi.list(p.id),
    })),
  });

  const requirementsQueries = useQueries({
    queries: projects.map((p) => ({
      queryKey: ["projects", p.id, "requirements"],
      queryFn: () => requirementsApi.list(p.id),
    })),
  });

  const isLoading =
    projectsQuery.isLoading ||
    (projects.length > 0 && (runsQueries.some((q) => q.isLoading) || requirementsQueries.some((q) => q.isLoading)));

  const allRuns: DashboardRun[] = [];
  projects.forEach((project, idx) => {
    const runs = runsQueries[idx]?.data ?? [];
    runs.forEach((run) => allRuns.push({ ...run, projectName: project.name }));
  });

  const requirementIndex = new Map<string, { text: string; projectId: string; projectName: string }>();
  projects.forEach((project, idx) => {
    const requirements = requirementsQueries[idx]?.data ?? [];
    requirements.forEach((req) => requirementIndex.set(req.id, { text: req.text, projectId: project.id, projectName: project.name }));
  });

  const recentRuns = [...allRuns]
    .sort((a, b) => {
      const aTime = new Date(a.finished_at ?? a.started_at ?? 0).getTime();
      const bTime = new Date(b.finished_at ?? b.started_at ?? 0).getTime();
      return bTime - aTime;
    })
    .slice(0, 10);

  const terminalRuns = allRuns.filter((r) => TERMINAL_RUN_STATUSES.includes(r.status));
  const passedRuns = terminalRuns.filter((r) => r.status === RunStatus.PASSED);
  const passRate = terminalRuns.length > 0 ? passedRuns.length / terminalRuns.length : null;

  const durations = allRuns.map((r) => r.duration_ms).filter((d): d is number => d != null);
  const averageDurationMs = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : null;

  const failureCounts = new Map<string, number>();
  allRuns
    .filter((r) => r.status === RunStatus.FAILED || r.status === RunStatus.ERRORED)
    .forEach((r) => failureCounts.set(r.requirement_id, (failureCounts.get(r.requirement_id) ?? 0) + 1));

  const topFailingRequirements: FailingRequirement[] = Array.from(failureCounts.entries())
    .map(([requirementId, failureCount]) => {
      const meta = requirementIndex.get(requirementId);
      return {
        requirementId,
        failureCount,
        text: meta?.text ?? "(requirement no longer available)",
        projectId: meta?.projectId ?? "",
        projectName: meta?.projectName ?? "Unknown project",
      };
    })
    .sort((a, b) => b.failureCount - a.failureCount)
    .slice(0, 5);

  // Heatmap: bucket run counts per calendar day over the last HEATMAP_DAYS days.
  const dayBuckets = new Map<string, number>();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (let i = 0; i < HEATMAP_DAYS; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    dayBuckets.set(d.toISOString().slice(0, 10), 0);
  }
  allRuns.forEach((run) => {
    const timestamp = run.started_at ?? run.finished_at;
    if (!timestamp) return;
    const key = new Date(timestamp).toISOString().slice(0, 10);
    if (dayBuckets.has(key)) dayBuckets.set(key, (dayBuckets.get(key) ?? 0) + 1);
  });

  const heatmap: HeatmapDay[] = Array.from(dayBuckets.entries())
    .map(([date, count]) => ({ date, count }))
    .sort((a, b) => a.date.localeCompare(b.date));

  const totalRunsLast8Weeks = heatmap.reduce((sum, d) => sum + d.count, 0);

  return {
    isLoading,
    // Per-project runs/requirements queries failing individually just under-counts
    // stats for that project (acceptable degradation) — only the root projects query
    // failing is worth blocking the whole page for, since nothing else can render without it.
    isError: projectsQuery.isError,
    refetch: () => projectsQuery.refetch(),
    projects,
    totalProjects: projects.length,
    recentRuns,
    passRate,
    averageDurationMs,
    topFailingRequirements,
    heatmap,
    totalRunsLast8Weeks,
  };
}
