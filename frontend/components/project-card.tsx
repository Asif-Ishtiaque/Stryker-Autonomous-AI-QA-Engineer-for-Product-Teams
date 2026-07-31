"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PlatformIcon, PLATFORM_LABELS } from "@/components/platform-icon";
import { useProjectStats } from "@/lib/queries";
import { formatConfidence } from "@/lib/utils";
import type { ProjectOut } from "@/lib/types";

const STATUS_VARIANT: Record<string, "success" | "secondary" | "outline"> = {
  active: "success",
  paused: "outline",
  archived: "secondary",
};

export function ProjectCard({ project, index = 0 }: { project: ProjectOut; index?: number }) {
  const { data: stats, isLoading } = useProjectStats(project.id);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.04 }}>
      <Link href={`/projects/${project.id}`}>
        <Card className="h-full transition-colors hover:border-primary/40 hover:bg-secondary/20">
          <CardHeader className="flex-row items-start justify-between space-y-0 pb-2">
            <div className="flex items-center gap-2 text-muted-foreground">
              <PlatformIcon platform={project.platform} className="h-4 w-4" />
              <span className="text-xs font-medium uppercase tracking-wide">{PLATFORM_LABELS[project.platform]}</span>
            </div>
            <Badge variant={STATUS_VARIANT[project.status] ?? "secondary"} className="capitalize">
              {project.status}
            </Badge>
          </CardHeader>
          <CardContent>
            <h3 className="font-semibold leading-tight">{project.name}</h3>
            {project.description && <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{project.description}</p>}

            <div className="mt-4 flex items-center justify-between text-sm">
              {isLoading ? (
                <Skeleton className="h-4 w-24" />
              ) : (
                <span className="text-muted-foreground">
                  {stats?.pass_rate != null ? (
                    <>
                      <span className="font-medium text-foreground">{formatConfidence(stats.pass_rate)}</span> pass rate
                    </>
                  ) : (
                    "No runs yet"
                  )}
                </span>
              )}
              <span className="text-xs text-muted-foreground">{stats?.run_count ?? 0} runs</span>
            </div>

            {project.tags.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {project.tags.slice(0, 4).map((tag) => (
                  <Badge key={tag} variant="outline" className="text-[11px]">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </Link>
    </motion.div>
  );
}
