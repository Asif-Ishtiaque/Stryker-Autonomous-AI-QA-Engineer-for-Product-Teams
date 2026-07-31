"use client";

import { Loader2, TriangleAlert } from "lucide-react";
import { useEvidenceUrl } from "@/lib/queries";

export function EvidenceImage({
  projectId,
  runId,
  evidenceId,
  enabled,
  alt = "Evidence screenshot",
}: {
  projectId: string;
  runId: string;
  evidenceId: string;
  enabled: boolean;
  alt?: string;
}) {
  const { data, isLoading, isError } = useEvidenceUrl(projectId, runId, evidenceId, enabled);

  if (!enabled) return null;
  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-border bg-muted/30">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (isError || !data?.url) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 rounded-lg border border-border bg-muted/30 text-sm text-muted-foreground">
        <TriangleAlert className="h-5 w-5" />
        Couldn&apos;t load this artifact.
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-lg border border-border bg-black/20">
      {/* eslint-disable-next-line @next/next/no-img-element -- presigned MinIO URLs are arbitrary hosts and short-lived, next/image adds no value here */}
      <img src={data.url} alt={alt} className="max-h-[70vh] w-full object-contain" />
    </div>
  );
}

export function EvidenceVideo({
  projectId,
  runId,
  evidenceId,
  enabled,
}: {
  projectId: string;
  runId: string;
  evidenceId: string;
  enabled: boolean;
}) {
  const { data, isLoading, isError } = useEvidenceUrl(projectId, runId, evidenceId, enabled);

  if (!enabled) return null;
  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-border bg-muted/30">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (isError || !data?.url) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 rounded-lg border border-border bg-muted/30 text-sm text-muted-foreground">
        <TriangleAlert className="h-5 w-5" />
        Couldn&apos;t load this artifact.
      </div>
    );
  }

  return (
    <video src={data.url} controls className="max-h-[70vh] w-full rounded-lg border border-border bg-black" />
  );
}
