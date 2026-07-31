"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { FolderKanban, LayoutDashboard, ListPlus, Plus, Settings } from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { useProjects } from "@/lib/queries";
import { useAuth } from "@/lib/auth";
import { NewProjectDialog } from "@/components/new-project-dialog";
import { NewRequirementDialog } from "@/components/new-requirement-dialog";
import { toast } from "sonner";

interface CommandPaletteContextValue {
  open: () => void;
}

const CommandPaletteContext = createContext<CommandPaletteContextValue | null>(null);

export function CommandPaletteProvider({ children }: { children: React.ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [newRequirementOpen, setNewRequirementOpen] = useState(false);
  const router = useRouter();
  const params = useParams<{ id?: string }>();
  const { isAuthenticated } = useAuth();
  const { data: projects } = useProjects({ enabled: isAuthenticated });

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const currentProjectId = typeof params?.id === "string" ? params.id : undefined;

  const value = useMemo<CommandPaletteContextValue>(() => ({ open: () => setPaletteOpen(true) }), []);

  if (!isAuthenticated) return <>{children}</>;

  return (
    <CommandPaletteContext.Provider value={value}>
      {children}

      <CommandDialog open={paletteOpen} onOpenChange={setPaletteOpen}>
        <CommandInput placeholder="Jump to a project, or create something new…" />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>

          <CommandGroup heading="Actions">
            <CommandItem
              onSelect={() => {
                setPaletteOpen(false);
                router.push("/dashboard");
              }}
            >
              <LayoutDashboard className="h-4 w-4" />
              Go to dashboard
            </CommandItem>
            <CommandItem
              onSelect={() => {
                setPaletteOpen(false);
                setNewProjectOpen(true);
              }}
            >
              <Plus className="h-4 w-4" />
              New project
            </CommandItem>
            <CommandItem
              onSelect={() => {
                setPaletteOpen(false);
                if (currentProjectId) {
                  setNewRequirementOpen(true);
                } else {
                  toast.info("Open a project first to add a requirement to it.");
                  router.push("/projects");
                }
              }}
            >
              <ListPlus className="h-4 w-4" />
              New requirement{currentProjectId ? "" : " (pick a project)"}
            </CommandItem>
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Projects">
            {projects?.map((project) => (
              <CommandItem
                key={project.id}
                value={project.name}
                onSelect={() => {
                  setPaletteOpen(false);
                  router.push(`/projects/${project.id}`);
                }}
              >
                <FolderKanban className="h-4 w-4" />
                {project.name}
              </CommandItem>
            ))}
            <CommandItem
              onSelect={() => {
                setPaletteOpen(false);
                router.push("/projects");
              }}
            >
              <Settings className="h-4 w-4" />
              View all projects
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>

      <NewProjectDialog open={newProjectOpen} onOpenChange={setNewProjectOpen} />
      {currentProjectId && (
        <NewRequirementDialog projectId={currentProjectId} open={newRequirementOpen} onOpenChange={setNewRequirementOpen} />
      )}
    </CommandPaletteContext.Provider>
  );
}

export function useCommandPalette(): CommandPaletteContextValue {
  const ctx = useContext(CommandPaletteContext);
  if (!ctx) throw new Error("useCommandPalette must be used within a CommandPaletteProvider");
  return ctx;
}
