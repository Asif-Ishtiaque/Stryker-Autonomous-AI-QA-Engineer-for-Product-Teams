"use client";

import { useEffect, useState } from "react";
import { ExternalLink, Loader2, TriangleAlert } from "lucide-react";
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

const HTML_PREVIEW_LIMIT = 20_000;

/** Renders a captured DOM snapshot (a raw .html file in MinIO) as a text preview.
 * This is NOT an image — it must not go through EvidenceImage's <img> tag, which only
 * ever shows a broken-image icon for an HTML payload. */
export function EvidenceHtmlSnapshot({
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
  const { data, isLoading: isLoadingUrl, isError: isUrlError } = useEvidenceUrl(projectId, runId, evidenceId, enabled);
  const [html, setHtml] = useState<string | null>(null);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    if (!data?.url) return;
    let cancelled = false;
    setHtml(null);
    setFetchError(false);
    fetch(data.url)
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`);
        return res.text();
      })
      .then((text) => {
        if (!cancelled) setHtml(text);
      })
      .catch(() => {
        if (!cancelled) setFetchError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [data?.url]);

  if (!enabled) return null;
  if (isLoadingUrl || (data?.url && html === null && !fetchError)) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-border bg-muted/30">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (isUrlError || fetchError || !data?.url) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 rounded-lg border border-border bg-muted/30 text-sm text-muted-foreground">
        <TriangleAlert className="h-5 w-5" />
        Couldn&apos;t load this artifact.
      </div>
    );
  }

  const truncated = html !== null && html.length > HTML_PREVIEW_LIMIT;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">Captured page HTML</span>
        <a
          href={data.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
        >
          Open raw HTML <ExternalLink className="h-3 w-3" />
        </a>
      </div>
      <pre className="max-h-96 overflow-auto rounded-lg bg-black/30 p-3 text-xs leading-relaxed text-foreground/90">
        {html?.slice(0, HTML_PREVIEW_LIMIT)}
        {truncated ? "\n\n… truncated, use \"Open raw HTML\" for the full document." : ""}
      </pre>
    </div>
  );
}
