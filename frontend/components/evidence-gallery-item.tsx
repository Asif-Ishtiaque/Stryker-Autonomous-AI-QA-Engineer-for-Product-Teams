"use client";

import { useState } from "react";
import { Camera, Video as VideoIcon } from "lucide-react";
import { motion } from "framer-motion";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { EvidenceImage, EvidenceVideo } from "@/components/evidence-media";
import { ArtifactViewer } from "@/components/artifact-viewer";
import { StatusBadge } from "@/components/status-badge";
import { formatDate } from "@/lib/utils";
import type { EvidenceOut } from "@/lib/types";
import { EvidenceType } from "@/lib/types";

export interface GalleryItem {
  runId: string;
  runStatus: string;
  runDate: string | null;
  stepName: string;
  sequence: number;
  evidence: EvidenceOut[];
  thumbnail: EvidenceOut;
}

export function EvidenceGalleryItem({ item, index, projectId }: { item: GalleryItem; index: number; projectId: string }) {
  const [open, setOpen] = useState(false);
  const isVideo = item.thumbnail.evidence_type === EvidenceType.VIDEO;

  return (
    <>
      <motion.button
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.03 }}
        onClick={() => setOpen(true)}
        className="group relative overflow-hidden rounded-lg border border-border text-left transition-colors hover:border-primary/40"
      >
        <div className="aspect-video bg-muted/30">
          {isVideo ? (
            <EvidenceVideo projectId={projectId} runId={item.runId} evidenceId={item.thumbnail.id} enabled />
          ) : (
            <EvidenceImage projectId={projectId} runId={item.runId} evidenceId={item.thumbnail.id} enabled alt={item.stepName} />
          )}
        </div>
        <div className="flex items-center justify-between gap-2 p-2.5">
          <div>
            <p className="flex items-center gap-1.5 text-xs font-medium">
              {isVideo ? <VideoIcon className="h-3 w-3" /> : <Camera className="h-3 w-3" />}
              <span className="line-clamp-1">{item.stepName}</span>
            </p>
            <p className="mt-0.5 text-[11px] text-muted-foreground">{formatDate(item.runDate)}</p>
          </div>
          <StatusBadge status={item.runStatus} />
        </div>
      </motion.button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>{item.stepName}</DialogTitle>
          </DialogHeader>
          <ArtifactViewer projectId={projectId} runId={item.runId} evidence={item.evidence} />
        </DialogContent>
      </Dialog>
    </>
  );
}
