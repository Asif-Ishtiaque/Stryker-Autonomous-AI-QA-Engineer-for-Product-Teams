"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import { Loader2, Play, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RequirementAnalysisCard } from "@/components/requirement-analysis-card";
import { useAnalyzeRequirement, useCreateRun, useCredentials, useUpdateRequirement } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";
import type { RequirementOut } from "@/lib/types";

export function RequirementCard({ projectId, requirement }: { projectId: string; requirement: RequirementOut }) {
  const router = useRouter();
  const analyze = useAnalyzeRequirement(projectId);
  const createRun = useCreateRun(projectId);
  const updateRequirement = useUpdateRequirement(projectId);
  const { data: credentials } = useCredentials(projectId);
  const [analysis, setAnalysis] = useState(requirement.ai_analysis);
  const [showAnalysis, setShowAnalysis] = useState(false);

  async function handleCredentialChange(value: string) {
    const credentialProfileId = value === "none" ? null : value;
    try {
      await updateRequirement.mutateAsync({ requirementId: requirement.id, payload: { credential_profile_id: credentialProfileId } });
      toast.success(credentialProfileId ? "Credential profile attached" : "Credential profile removed");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to update credential profile.");
    }
  }

  async function handleAnalyze() {
    const toastId = toast.loading("Analyzing requirement… this can take up to a minute.");
    try {
      const result = await analyze.mutateAsync(requirement.id);
      setAnalysis(result);
      setShowAnalysis(true);
      toast.success("Analysis complete", { id: toastId });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Analysis failed.", { id: toastId });
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
              {analyze.isPending ? "Analyzing…" : "Analyze"}
            </Button>
            <Button size="sm" onClick={handleRun} disabled={createRun.isPending}>
              {createRun.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              Run
            </Button>
          </div>
        </div>

        <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <span>Credential profile:</span>
          <Select
            value={requirement.credential_profile_id ?? "none"}
            onValueChange={handleCredentialChange}
            disabled={updateRequirement.isPending}
          >
            <SelectTrigger className="h-6 w-auto gap-1 rounded-md border-none bg-transparent px-1.5 py-0 text-xs text-foreground shadow-none hover:bg-accent">
              <SelectValue placeholder="No credentials needed" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No credentials needed</SelectItem>
              {credentials?.map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

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
