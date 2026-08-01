"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TagInput } from "@/components/tag-input";
import { PLATFORM_LABELS } from "@/components/platform-icon";
import { useCreateProject } from "@/lib/queries";
import { Platform, ProjectEnvironment } from "@/lib/types";
import { ApiError } from "@/lib/api-client";

const ENV_LABELS: Record<ProjectEnvironment, string> = {
  production: "Production",
  staging: "Staging",
  qa: "QA",
  development: "Development",
};

export function NewProjectDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const createProject = useCreateProject();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [platform, setPlatform] = useState<Platform>(Platform.WEB);
  const [environment, setEnvironment] = useState<ProjectEnvironment>(ProjectEnvironment.STAGING);
  const [baseUrl, setBaseUrl] = useState("");
  const [tags, setTags] = useState<string[]>([]);

  function reset() {
    setName("");
    setDescription("");
    setPlatform(Platform.WEB);
    setEnvironment(ProjectEnvironment.STAGING);
    setBaseUrl("");
    setTags([]);
  }

  async function handleSubmit() {
    if (!name.trim() || !baseUrl.trim()) {
      toast.error("Name and base URL are required.");
      return;
    }
    if (!/^https?:\/\/.+/i.test(baseUrl.trim())) {
      toast.error("Base URL must start with http:// or https:// — e.g. https://staging.myapp.com");
      return;
    }
    try {
      const project = await createProject.mutateAsync({
        name: name.trim(),
        description: description.trim(),
        platform,
        environment,
        base_url: baseUrl.trim(),
        tags,
      });
      toast.success(`${project.name} created`);
      reset();
      onOpenChange(false);
      router.push(`/projects/${project.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to create project.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New project</DialogTitle>
          <DialogDescription>Tell Stryker what you&apos;re testing. You can add requirements next.</DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid gap-1.5">
            <Label htmlFor="project-name">Name</Label>
            <Input id="project-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Checkout flow" autoFocus />
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="project-description">Description</Label>
            <Textarea
              id="project-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this project cover?"
              className="min-h-[70px]"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-1.5">
              <Label>Platform</Label>
              <Select value={platform} onValueChange={(v) => setPlatform(v as Platform)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(Platform).map((p) => (
                    <SelectItem key={p} value={p}>
                      {PLATFORM_LABELS[p]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
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
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="project-base-url">Base URL</Label>
            <Input
              id="project-base-url"
              type="url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://staging.myapp.com"
            />
          </div>

          <div className="grid gap-1.5">
            <Label>Tags</Label>
            <TagInput value={tags} onChange={setTags} placeholder="checkout, billing, p0…" />
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={createProject.isPending}>
            {createProject.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Create project
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
