"use client";

import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  chatApi,
  credentialsApi,
  knowledgeApi,
  projectsApi,
  reportsApi,
  requirementsApi,
  runsApi,
} from "./api-client";
import type {
  ChatMessageRequest,
  CredentialCreate,
  ProjectCreate,
  ProjectUpdate,
  ReportGenerateRequest,
  RequirementCreate,
  RunCreate,
  SemanticSearchRequest,
} from "./types";

export const qk = {
  projects: ["projects"] as const,
  project: (id: string) => ["projects", id] as const,
  projectStats: (id: string) => ["projects", id, "stats"] as const,
  credentials: (projectId: string) => ["projects", projectId, "credentials"] as const,
  knowledge: (projectId: string) => ["projects", projectId, "knowledge"] as const,
  requirements: (projectId: string) => ["projects", projectId, "requirements"] as const,
  requirement: (projectId: string, id: string) => ["projects", projectId, "requirements", id] as const,
  runs: (projectId: string) => ["projects", projectId, "runs"] as const,
  run: (projectId: string, runId: string) => ["projects", projectId, "runs", runId] as const,
  reports: (projectId: string, runId: string) => ["projects", projectId, "runs", runId, "reports"] as const,
};

// ---------------------------------------------------------------------------
// projects
// ---------------------------------------------------------------------------

export function useProjects(opts: { enabled?: boolean } = {}) {
  return useQuery({ queryKey: qk.projects, queryFn: projectsApi.list, enabled: opts.enabled ?? true });
}

export function useProject(projectId: string | undefined) {
  return useQuery({
    queryKey: qk.project(projectId ?? ""),
    queryFn: () => projectsApi.get(projectId as string),
    enabled: !!projectId,
  });
}

export function useProjectStats(projectId: string | undefined) {
  return useQuery({
    queryKey: qk.projectStats(projectId ?? ""),
    queryFn: () => projectsApi.stats(projectId as string),
    enabled: !!projectId,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProjectCreate) => projectsApi.create(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.projects }),
  });
}

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProjectUpdate) => projectsApi.update(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.project(projectId) });
      queryClient.invalidateQueries({ queryKey: qk.projects });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => projectsApi.remove(projectId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.projects }),
  });
}

// ---------------------------------------------------------------------------
// credentials
// ---------------------------------------------------------------------------

export function useCredentials(projectId: string | undefined) {
  return useQuery({
    queryKey: qk.credentials(projectId ?? ""),
    queryFn: () => credentialsApi.list(projectId as string),
    enabled: !!projectId,
  });
}

export function useCreateCredential(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CredentialCreate) => credentialsApi.create(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.credentials(projectId) }),
  });
}

export function useDeleteCredential(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (credentialId: string) => credentialsApi.remove(projectId, credentialId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.credentials(projectId) }),
  });
}

// ---------------------------------------------------------------------------
// knowledge
// ---------------------------------------------------------------------------

export function useKnowledgeSources(projectId: string | undefined) {
  return useQuery({
    queryKey: qk.knowledge(projectId ?? ""),
    queryFn: () => knowledgeApi.list(projectId as string),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasPending = data?.some((s) => s.status === "pending" || s.status === "processing");
      return hasPending ? 4000 : false;
    },
  });
}

export function useUploadKnowledge(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => knowledgeApi.upload(projectId, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.knowledge(projectId) }),
  });
}

export function useDeleteKnowledge(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) => knowledgeApi.remove(projectId, sourceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.knowledge(projectId) }),
  });
}

export function useKnowledgeSearch(projectId: string) {
  return useMutation({
    mutationFn: (payload: SemanticSearchRequest) => knowledgeApi.search(projectId, payload),
  });
}

// ---------------------------------------------------------------------------
// requirements
// ---------------------------------------------------------------------------

export function useRequirements(projectId: string | undefined) {
  return useQuery({
    queryKey: qk.requirements(projectId ?? ""),
    queryFn: () => requirementsApi.list(projectId as string),
    enabled: !!projectId,
  });
}

export function useCreateRequirement(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RequirementCreate) => requirementsApi.create(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.requirements(projectId) }),
  });
}

export function useAnalyzeRequirement(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (requirementId: string) => requirementsApi.analyze(projectId, requirementId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.requirements(projectId) }),
  });
}

// ---------------------------------------------------------------------------
// runs
// ---------------------------------------------------------------------------

export function useRuns(projectId: string | undefined) {
  return useQuery({
    queryKey: qk.runs(projectId ?? ""),
    queryFn: () => runsApi.list(projectId as string),
    enabled: !!projectId,
  });
}

export function useRun(projectId: string | undefined, runId: string | undefined, opts: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: qk.run(projectId ?? "", runId ?? ""),
    queryFn: () => runsApi.get(projectId as string, runId as string),
    enabled: !!projectId && !!runId,
    refetchInterval: opts.poll ? 5000 : false,
  });
}

export function useCreateRun(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RunCreate) => runsApi.create(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.runs(projectId) }),
  });
}

export function useCancelRun(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => runsApi.cancel(projectId, runId),
    onSuccess: (_data, runId) => {
      queryClient.invalidateQueries({ queryKey: qk.run(projectId, runId) });
      queryClient.invalidateQueries({ queryKey: qk.runs(projectId) });
    },
  });
}

/**
 * `runsApi.list` (GET /projects/{id}/runs) does not eager-load steps/evidence
 * on the backend (see RunRepository.list_for_project vs get_with_steps), so
 * building an evidence gallery requires fetching full run detail
 * (GET /runs/{run_id}, which DOES eager-load steps+evidence) for each of the
 * most recent runs individually.
 */
export function useRecentRunsWithSteps(projectId: string | undefined, limit = 8) {
  const runsQuery = useRuns(projectId);
  const recentIds = (runsQuery.data ?? [])
    .slice()
    .sort((a, b) => new Date(b.started_at ?? b.finished_at ?? 0).getTime() - new Date(a.started_at ?? a.finished_at ?? 0).getTime())
    .slice(0, limit)
    .map((r) => r.id);

  const detailQueries = useQueries({
    queries: recentIds.map((runId) => ({
      queryKey: qk.run(projectId ?? "", runId),
      queryFn: () => runsApi.get(projectId as string, runId),
      enabled: !!projectId,
    })),
  });

  return {
    isLoading: runsQuery.isLoading || detailQueries.some((q) => q.isLoading),
    runs: detailQueries.map((q) => q.data).filter((r): r is NonNullable<typeof r> => !!r),
  };
}

// ---------------------------------------------------------------------------
// reports
// ---------------------------------------------------------------------------

export function useEvidenceUrl(projectId: string, runId: string, evidenceId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["projects", projectId, "runs", runId, "evidence", evidenceId ?? "", "url"],
    queryFn: () => runsApi.evidenceUrl(projectId, runId, evidenceId as string),
    enabled: !!evidenceId && enabled,
    staleTime: 5 * 60_000,
  });
}

export function useReports(projectId: string, runId: string | undefined) {
  return useQuery({
    queryKey: qk.reports(projectId, runId ?? ""),
    queryFn: () => reportsApi.list(projectId, runId as string),
    enabled: !!runId,
  });
}

export function useGenerateReports(projectId: string, runId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ReportGenerateRequest) => reportsApi.generate(projectId, runId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.reports(projectId, runId) }),
  });
}

// ---------------------------------------------------------------------------
// chat
// ---------------------------------------------------------------------------

export function useSendChatMessage() {
  return useMutation({
    mutationFn: (payload: ChatMessageRequest) => chatApi.send(payload),
  });
}
