"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Loader2, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TagInput } from "@/components/tag-input";
import { useDeleteProject, useProject, useUpdateProject } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";
import { ProjectEnvironment, ProjectStatus } from "@/lib/types";

const ENV_LABELS: Record<ProjectEnvironment, string> = {
  production: "Production",
  staging: "Staging",
  qa: "QA",
  development: "Development",
};

const STATUS_LABELS: Record<ProjectStatus, string> = {
  active: "Active",
  paused: "Paused",
  archived: "Archived",
};

export default function ProjectSettingsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const router = useRouter();
  const { data: project, isLoading } = useProject(projectId);
  const updateProject = useUpdateProject(projectId);
  const deleteProject = useDeleteProject();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [environment, setEnvironment] = useState<ProjectEnvironment>(ProjectEnvironment.STAGING);
  const [status, setStatus] = useState<ProjectStatus>(ProjectStatus.ACTIVE);
  const [baseUrl, setBaseUrl] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    if (!project) return;
    setName(project.name);
    setDescription(project.description);
    setEnvironment(project.environment);
    setStatus(project.status);
    setBaseUrl(project.base_url);
    setTags(project.tags);
  }, [project]);

  async function handleSave() {
    if (!/^https?:\/\/.+/i.test(baseUrl.trim())) {
      toast.error("Base URL must start with http:// or https:// — e.g. https://staging.myapp.com");
      return;
    }
    try {
      await updateProject.mutateAsync({
        name: name.trim(),
        description: description.trim(),
        environment,
        status,
        base_url: baseUrl.trim(),
        tags,
      });
      toast.success("Project updated");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to update project.");
    }
  }

  async function handleDelete() {
    try {
      await deleteProject.mutateAsync(projectId);
      toast.success("Project deleted");
      router.push("/projects");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to delete project.");
    }
  }

  if (isLoading || !project) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-96 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Update project details, or archive/delete it entirely." />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">General</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="settings-name">Name</Label>
            <Input id="settings-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="settings-description">Description</Label>
            <Textarea id="settings-description" value={description} onChange={(e) => setDescription(e.target.value)} className="min-h-[70px]" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-1.5">
              <Label>Environment</Label>
              <Select value={environment} onValueChange={(v) => setEnvironment(v as ProjectEnvironment)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(ProjectEnvironment).map((e) => (
                    <SelectItem key={e} value={e}>
                      {ENV_LABELS[e]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label>Status</Label>
              <Select value={status} onValueChange={(v) => setStatus(v as ProjectStatus)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(ProjectStatus).map((s) => (
                    <SelectItem key={s} value={s}>
                      {STATUS_LABELS[s]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="settings-base-url">Base URL</Label>
            <Input id="settings-base-url" type="url" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label>Tags</Label>
            <TagInput value={tags} onChange={setTags} />
          </div>
          <div>
            <Button onClick={handleSave} disabled={updateProject.isPending}>
              {updateProject.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Save changes
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-destructive">Danger zone</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Delete this project</p>
            <p className="text-sm text-muted-foreground">Permanently removes the project, its requirements, runs, and knowledge base.</p>
          </div>
          <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
            <Trash2 className="h-4 w-4" />
            Delete project
          </Button>
        </CardContent>
      </Card>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete &quot;{project.name}&quot;?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">This cannot be undone.</p>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleteProject.isPending}>
              {deleteProject.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
