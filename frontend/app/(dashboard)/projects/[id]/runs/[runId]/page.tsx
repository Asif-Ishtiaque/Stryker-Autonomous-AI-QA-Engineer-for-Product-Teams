"use client";

import { useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, ArrowLeft, Ban, Loader2, ShieldAlert, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { ConfidenceGauge } from "@/components/confidence-gauge";
import { StepTimeline } from "@/components/step-timeline";
import { ReportMenu } from "@/components/report-menu";
import { LiveBrowserStream } from "@/components/live-browser-stream";
import { ReasoningPanel, LiveConsolePanel, LiveNetworkPanel } from "@/components/mission-control-panels";
import { ErrorState } from "@/components/error-state";
import { useCancelRun, useRun, qk } from "@/lib/queries";
import { useRunEvents } from "@/lib/ws";
import {
  deriveConsoleLog,
  deriveLiveSteps,
  deriveNetworkLog,
  deriveReasoningLog,
  isRunTerminal,
  latestConfidenceScore,
  latestPhaseMessage,
  latestRunStatus,
} from "@/lib/run-events";
import { RunStatus } from "@/lib/types";
import { ApiError } from "@/lib/api-client";
import { formatDate, formatDuration } from "@/lib/utils";

const SEVERITY_VARIANT: Record<string, "destructive" | "warning" | "secondary" | "outline"> = {
  critical: "destructive",
  high: "destructive",
  medium: "warning",
  low: "secondary",
};

export default function RunPage() {
  const params = useParams<{ id: string; runId: string }>();
  const projectId = params.id;
  const runId = params.runId;
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: run, isLoading, isError, refetch } = useRun(projectId, runId);
  const cancelRun = useCancelRun(projectId);

  const knownTerminal = run ? isRunTerminal(run.status) : false;
  const shouldConnect = !!run && !knownTerminal;
  const { events } = useRunEvents(shouldConnect ? runId : null, { enabled: shouldConnect });

  useEffect(() => {
    const last = events[events.length - 1];
    if (last && isRunTerminal(last.run_status)) {
      queryClient.invalidateQueries({ queryKey: qk.run(projectId, runId) });
      queryClient.invalidateQueries({ queryKey: qk.runs(projectId) });
    }
  }, [events, projectId, runId, queryClient]);

  const liveSteps = useMemo(() => deriveLiveSteps(events), [events]);
  const displayStatus = run ? latestRunStatus(events, run.status) : RunStatus.QUEUED;
  const phaseMessage = latestPhaseMessage(events);
  const displayConfidence = latestConfidenceScore(events, run?.confidence_score);
  const reasoningLog = useMemo(() => deriveReasoningLog(events), [events]);
  const consoleLog = useMemo(() => deriveConsoleLog(events), [events]);
  const networkLog = useMemo(() => deriveNetworkLog(events), [events]);

  const usingFinalSteps = knownTerminal && (run?.steps.length ?? 0) > 0;
  const isLive = shouldConnect;

  async function handleCancel() {
    try {
      await cancelRun.mutateAsync(runId);
      toast.success("Run cancelled");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to cancel run.");
    }
  }

  if (isError) {
    return (
      <div className="mx-auto w-full max-w-4xl p-6">
        <ErrorState title="Couldn't load this run" onRetry={() => refetch()} />
      </div>
    );
  }

  if (isLoading || !run) {
    return (
      <div className="mx-auto w-full max-w-4xl space-y-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  const canCancel = !isRunTerminal(displayStatus);

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => router.push(`/projects/${projectId}/runs`)}>
          <ArrowLeft className="h-4 w-4" />
          All runs
        </Button>
        <div className="flex items-center gap-2">
          {canCancel && (
            <Button variant="outline" size="sm" onClick={handleCancel} disabled={cancelRun.isPending}>
              {cancelRun.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Ban className="h-3.5 w-3.5" />}
              Cancel run
            </Button>
          )}
          {isRunTerminal(displayStatus) && <ReportMenu projectId={projectId} runId={runId} />}
        </div>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-6 p-6">
          <div>
            <div className="flex items-center gap-3">
              <StatusBadge status={displayStatus} className="text-sm" />
              {run.severity && (
                <Badge variant={SEVERITY_VARIANT[run.severity] ?? "outline"} className="capitalize">
                  {run.severity} severity
                </Badge>
              )}
            </div>
            {phaseMessage && !isRunTerminal(displayStatus) && (
              <p className="mt-2 text-sm text-muted-foreground">{phaseMessage}</p>
            )}
            <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
              <span>Started {formatDate(run.started_at)}</span>
              {run.duration_ms != null && <span>Duration {formatDuration(run.duration_ms)}</span>}
            </div>
            {run.error_message && (
              <p className="mt-2 flex items-start gap-1.5 text-sm text-destructive">
                <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
                {run.error_message}
              </p>
            )}
            {run.root_cause_hypothesis && (
              <p className="mt-2 flex items-start gap-1.5 text-sm text-warning">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                {run.root_cause_hypothesis}
              </p>
            )}
          </div>
          <ConfidenceGauge score={displayConfidence} />
        </CardContent>
      </Card>

      {isLive && (
        <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
          <LiveBrowserStream runId={runId} enabled={isLive} />
          <ReasoningPanel entries={reasoningLog} />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Execution timeline</CardTitle>
        </CardHeader>
        <CardContent>
          {usingFinalSteps ? (
            <StepTimeline projectId={projectId} runId={runId} steps={run.steps} />
          ) : (
            <StepTimeline projectId={projectId} runId={runId} liveSteps={liveSteps} />
          )}
        </CardContent>
      </Card>

      {isLive && (
        <div className="grid gap-4 lg:grid-cols-2">
          <LiveNetworkPanel entries={networkLog} />
          <LiveConsolePanel entries={consoleLog} />
        </div>
      )}

      {run.validation_checklist && Object.keys(run.validation_checklist).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <ShieldAlert className="h-4 w-4" />
              Validation findings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-64 overflow-auto rounded-lg bg-black/20 p-3 text-xs leading-relaxed">
              {JSON.stringify(run.validation_checklist, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      {run.report_markdown && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Report</CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm prose-invert max-w-none whitespace-pre-wrap text-sm leading-relaxed">
            {run.report_markdown}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
