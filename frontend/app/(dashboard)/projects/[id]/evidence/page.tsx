"use client";

import { useParams } from "next/navigation";
import { Camera } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { EvidenceGalleryItem, type GalleryItem } from "@/components/evidence-gallery-item";
import { useRecentRunsWithSteps } from "@/lib/queries";
import { EvidenceType } from "@/lib/types";

export default function EvidencePage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const { runs, isLoading } = useRecentRunsWithSteps(projectId, 10);

  const items: GalleryItem[] = [];
  for (const run of runs) {
    for (const step of run.steps) {
      const thumbnail = step.evidence.find((e) => e.evidence_type === EvidenceType.SCREENSHOT || e.evidence_type === EvidenceType.VIDEO);
      if (!thumbnail) continue;
      items.push({
        runId: run.id,
        runStatus: run.status,
        runDate: run.finished_at ?? run.started_at,
        stepName: step.name,
        sequence: step.sequence,
        evidence: step.evidence,
        thumbnail,
      });
    }
  }
  items.sort((a, b) => new Date(b.runDate ?? 0).getTime() - new Date(a.runDate ?? 0).getTime());

  return (
    <div className="space-y-6">
      <PageHeader title="Evidence" description="Screenshots and recordings captured across this project's most recent runs." />

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="aspect-video rounded-lg" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState icon={Camera} title="No evidence yet" description="Screenshots and recordings from run steps will show up here once runs execute." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((item, idx) => (
            <EvidenceGalleryItem key={`${item.runId}-${item.sequence}`} item={item} index={idx} projectId={projectId} />
          ))}
        </div>
      )}
    </div>
  );
}
