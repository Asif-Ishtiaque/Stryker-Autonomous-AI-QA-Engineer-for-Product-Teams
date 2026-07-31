"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { ListPlus, Plus } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RequirementCard } from "@/components/requirement-card";
import { NewRequirementDialog } from "@/components/new-requirement-dialog";
import { useRequirements } from "@/lib/queries";

export default function RequirementsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const { data: requirements, isLoading } = useRequirements(projectId);
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Requirements"
        description="Describe what should work, in plain English. Stryker plans and executes the rest."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4" />
            New requirement
          </Button>
        }
      />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      ) : !requirements || requirements.length === 0 ? (
        <EmptyState
          icon={ListPlus}
          title="No requirements yet"
          description={'Try something like: "Verify Admin can create an invoice. It should appear in the list and the customer balance should update."'}
          action={
            <Button onClick={() => setOpen(true)}>
              <Plus className="h-4 w-4" />
              New requirement
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {requirements.map((requirement) => (
            <RequirementCard key={requirement.id} projectId={projectId} requirement={requirement} />
          ))}
        </div>
      )}

      <NewRequirementDialog projectId={projectId} open={open} onOpenChange={setOpen} />
    </div>
  );
}
