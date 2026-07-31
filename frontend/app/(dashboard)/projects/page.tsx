"use client";

import { useState } from "react";
import { FolderKanban, Plus } from "lucide-react";
import { Topbar } from "@/components/topbar";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ProjectCard } from "@/components/project-card";
import { NewProjectDialog } from "@/components/new-project-dialog";
import { useProjects } from "@/lib/queries";

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  const [newProjectOpen, setNewProjectOpen] = useState(false);

  return (
    <>
      <Topbar />
      <div className="mx-auto w-full max-w-6xl flex-1 space-y-6 p-6">
        <PageHeader
          title="Projects"
          description="Everything Stryker is watching over."
          actions={
            <Button onClick={() => setNewProjectOpen(true)}>
              <Plus className="h-4 w-4" />
              New project
            </Button>
          }
        />

        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-44 rounded-xl" />
            ))}
          </div>
        ) : !projects || projects.length === 0 ? (
          <EmptyState
            icon={FolderKanban}
            title="No projects yet"
            description="Projects group requirements, credentials, knowledge, and run history for one product surface."
            action={
              <Button onClick={() => setNewProjectOpen(true)}>
                <Plus className="h-4 w-4" />
                New project
              </Button>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project, idx) => (
              <ProjectCard key={project.id} project={project} index={idx} />
            ))}
          </div>
        )}
      </div>

      <NewProjectDialog open={newProjectOpen} onOpenChange={setNewProjectOpen} />
    </>
  );
}
