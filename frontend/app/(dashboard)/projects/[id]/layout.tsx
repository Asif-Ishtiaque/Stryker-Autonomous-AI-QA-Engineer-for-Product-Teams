"use client";

import { useParams } from "next/navigation";
import { Loader2, MessageCircle } from "lucide-react";
import { Topbar } from "@/components/topbar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ProjectTabs } from "@/components/project-tabs";
import { PlatformIcon, PLATFORM_LABELS } from "@/components/platform-icon";
import { useProject } from "@/lib/queries";
import { useChat } from "@/components/chat/chat-provider";

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const { data: project, isLoading } = useProject(projectId);
  const chat = useChat();

  return (
    <>
      <Topbar>
        {project && (
          <div className="flex items-center gap-2.5">
            <PlatformIcon platform={project.platform} className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">{project.name}</span>
            <Badge variant="outline" className="capitalize">
              {project.environment}
            </Badge>
          </div>
        )}
      </Topbar>

      <div className="flex flex-1 flex-col">
        <div className="flex items-center justify-between px-6 pt-5">
          {isLoading || !project ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : (
            <div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{PLATFORM_LABELS[project.platform]}</span>
                <span>·</span>
                <a href={project.base_url} target="_blank" rel="noreferrer" className="hover:text-foreground hover:underline">
                  {project.base_url}
                </a>
              </div>
            </div>
          )}
          <Button variant="outline" size="sm" onClick={() => chat.openChat(projectId)}>
            <MessageCircle className="h-3.5 w-3.5" />
            Ask Stryker
          </Button>
        </div>

        <div className="mt-4">
          <ProjectTabs projectId={projectId} />
        </div>

        <div className="mx-auto w-full max-w-6xl flex-1 p-6">{children}</div>
      </div>
    </>
  );
}
