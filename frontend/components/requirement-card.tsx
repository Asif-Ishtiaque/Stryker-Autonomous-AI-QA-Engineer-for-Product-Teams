"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import { Loader2, Play, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { RequirementAnalysisCard } from "@/components/requirement-analysis-card";
import { useAnalyzeRequirement, useCreateRun, useCredentials } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";
import type { RequirementOut } from "@/lib/types";

export function RequirementCard({ projectId, requirement }: { projectId: string; requirement: RequirementOut }) {
  const router = useRouter();
  const analyze = useAnalyzeRequirement(projectId);
  const createRun = useCreateRun(projectId);
  const { data: credentials } = useCredentials(projectId);
  const [analysis, setAnalysis] = useState(requirement.ai_analysis);
  const [showAnalysis, setShowAnalysis] = useState(false);

  const credentialLabel = credentials?.find((c) => c.id === requirement.credential_profile_id)?.label;

  async function handleAnalyze() {
    try {
      const result = await analyze.mutateAsync(requirement.id);
      setAnalysis(result);
      setShowAnalysis(true);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Analysis failed.");
    }
  }

  async function handleRun() {
    try {
      const run = await createRun.mutateAsync({ requirement_id: requirement.id });
      toast.success("Run started");
      router.push(`/projects/${projectId}/runs/${run.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to start run.");
    }
  }

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <p className="flex-1 text-sm leading-relaxed">{requirement.text}</p>
          <div className="flex shrink-0 items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleAnalyze} disabled={analyze.isPending}>
              {analyze.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
              Analyze
            </Button>
            <Button size="sm" onClick={handleRun} disabled={createRun.isPending}>
              {createRun.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              Run
            </Button>
          </div>
        </div>

        {credentialLabel && <p className="mt-2 text-xs text-muted-foreground">Uses credential profile: {credentialLabel}</p>}

        <AnimatePresence initial={false}>
          {analysis && showAnalysis && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="mt-4">
                <RequirementAnalysisCard analysis={analysis} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {analysis && !showAnalysis && (
          <button
            onClick={() => setShowAnalysis(true)}
            className="mt-2 text-xs font-medium text-primary hover:underline"
          >
            View Stryker&apos;s analysis
          </button>
        )}
      </CardContent>
    </Card>
  );
}
