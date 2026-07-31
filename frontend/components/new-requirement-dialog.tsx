"use client";

import { useState } from "react";
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateRequirement, useCredentials } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";
import type { RequirementOut } from "@/lib/types";

const EXAMPLE_PLACEHOLDER =
  "Verify Admin can create an invoice. It should appear in the list and the customer balance should update.";

export function NewRequirementDialog({
  projectId,
  open,
  onOpenChange,
  onCreated,
}: {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: (requirement: RequirementOut) => void;
}) {
  const [text, setText] = useState("");
  const [credentialProfileId, setCredentialProfileId] = useState<string | undefined>(undefined);
  const createRequirement = useCreateRequirement(projectId);
  const { data: credentials } = useCredentials(projectId);

  async function handleSubmit() {
    if (!text.trim()) {
      toast.error("Describe what should happen first.");
      return;
    }
    try {
      const requirement = await createRequirement.mutateAsync({
        text: text.trim(),
        credential_profile_id: credentialProfileId ?? null,
      });
      toast.success("Requirement added");
      setText("");
      setCredentialProfileId(undefined);
      onOpenChange(false);
      onCreated?.(requirement);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to create requirement.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New requirement</DialogTitle>
          <DialogDescription>
            Describe the behavior in plain English — no scripts, no DSL. Stryker&apos;s AI will plan and execute it.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid gap-1.5">
            <Label htmlFor="requirement-text">What should happen?</Label>
            <Textarea
              id="requirement-text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={EXAMPLE_PLACEHOLDER}
              className="min-h-[120px]"
              autoFocus
            />
          </div>

          <div className="grid gap-1.5">
            <Label>Credential profile (optional)</Label>
            <Select
              value={credentialProfileId ?? "none"}
              onValueChange={(v) => setCredentialProfileId(v === "none" ? undefined : v)}
            >
              <SelectTrigger>
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
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={createRequirement.isPending}>
            {createRequirement.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Add requirement
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
